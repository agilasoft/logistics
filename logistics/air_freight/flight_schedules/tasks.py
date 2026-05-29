# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Scheduled Tasks for Flight Schedule Sync
"""

from __future__ import unicode_literals
import frappe
from datetime import datetime, timedelta


def sync_active_flights():
	"""Sync the live position of every active Flight Schedule with a single
	OpenSky ``/states/all`` call.

	Triggered by the scheduler (every 10 minutes by default) so the dashboard's
	Live Flights tab has a recent fall-back position even when the OpenSky
	free-tier daily quota is exhausted or when no user has the tab open.
	"""
	try:
		settings = frappe.get_single('Flight Schedule Settings')

		if not settings.enable_realtime_tracking:
			return
		if not getattr(settings, "opensky_enabled", 0):
			return

		# Active flights with a reasonable departure window.
		now = datetime.now()
		since = now - timedelta(days=1)
		until = now + timedelta(days=1)

		# Two sources of "active" Flight Schedules:
		# (a) flights with a scheduled departure in the [now-1d, now+1d] corridor
		#     and an operational status, AND
		# (b) flights linked to any non-cancelled Air Shipment via its Master AWB,
		#     regardless of departure_time_scheduled (which is frequently NULL
		#     when MAWB rows are seeded from PDF/EDI and not from a feed).
		active_flights = frappe.db.sql(
			"""
			SELECT DISTINCT fs.name, fs.flight_number, fs.airline_iata, fs.airline_icao
			FROM `tabFlight Schedule` fs
			WHERE fs.flight_number IS NOT NULL AND fs.flight_number != ''
			  AND (
				(fs.flight_status IN ('Scheduled','Active','EnRoute','Delayed')
				 AND fs.departure_time_scheduled BETWEEN %(since)s AND %(until)s)
				OR fs.name IN (
					SELECT mawb.flight_schedule
					FROM `tabMaster Air Waybill` mawb
					INNER JOIN `tabAir Shipment` ash ON ash.master_awb = mawb.name
					WHERE mawb.flight_schedule IS NOT NULL
					  AND mawb.flight_schedule != ''
					  AND ash.docstatus < 2
				)
			  )
			""",
			{"since": since, "until": until},
			as_dict=True,
		) or []
		if not active_flights:
			return

		# Build IATA -> ICAO airline lookup once.
		iata_to_icao = {}
		try:
			rows = frappe.get_all(
				"Airline",
				fields=["iata_code", "icao_code"],
				filters={"iata_code": ["is", "set"]},
				limit_page_length=0,
			)
			for r in rows:
				iata = (r.get("iata_code") or "").strip().upper()
				icao = (r.get("icao_code") or "").strip().upper()
				if iata and icao:
					iata_to_icao.setdefault(iata, icao)
		except Exception:
			pass

		# Collect every candidate ADS-B callsign across all flights.
		import re
		non_alnum = re.compile(r"[^A-Z0-9]")
		flight_callsigns = {}  # fs_name -> [callsigns...]
		wanted = set()
		for f in active_flights:
			fn_raw = (f.flight_number or "").upper()
			fn = non_alnum.sub("", fn_raw)
			if not fn:
				continue
			cands = [fn]
			m = re.search(r"(\d+)$", fn)
			digits = m.group(1) if m else ""
			prefix = fn[: -len(digits)] if digits else ""
			icao = (f.airline_icao or "").strip().upper()
			iata = (f.airline_iata or "").strip().upper()
			if digits:
				if iata and iata == prefix:
					ic = icao or iata_to_icao.get(iata, "")
					if ic:
						cands.append(ic + digits)
				elif prefix and len(prefix) == 2:
					ic = iata_to_icao.get(prefix, "")
					if ic:
						cands.append(ic + digits)
				elif not prefix and icao:
					cands.append(icao + digits)
				if icao:
					cand = icao + digits
					if cand not in cands:
						cands.append(cand)
			flight_callsigns[f.name] = cands
			for c in cands:
				if c:
					wanted.add(c)

		if not wanted:
			return

		# Provider chain: OpenSky (one bulk call) → free no-auth ADS-B aggregators
		# (per-callsign) as automatic fallback when OpenSky is unreachable.
		from logistics.air_freight.flight_schedules.opensky.connector import OpenSkyConnector
		states = {}
		provider_used = None
		try:
			settings_obj = frappe.get_single("Flight Schedule Settings")
		except Exception:
			settings_obj = None
		if settings_obj and getattr(settings_obj, "opensky_enabled", 0):
			try:
				connector = OpenSkyConnector()
				states = connector.get_states_for_callsigns(list(wanted)) or {}
				if states:
					provider_used = "OpenSky Network"
			except Exception as e:
				frappe.log_error(f"sync_active_flights: OpenSky fetch failed: {str(e)}")

		if not states:
			try:
				from logistics.air_freight.flight_schedules.adsb_aggregator.connector import (
					AdsbAggregatorConnector,
				)
				agg = AdsbAggregatorConnector()
				states = agg.get_states_for_callsigns(list(wanted), timeout=10) or {}
				if states:
					provider_used = agg.last_provider_used or "adsb.lol"
			except Exception as e:
				frappe.log_error(f"sync_active_flights: adsb.lol/fi fetch failed: {str(e)}")

		if not states:
			return

		updated = 0
		for f in active_flights:
			cands = flight_callsigns.get(f.name) or []
			state = None
			for c in cands:
				if c in states:
					state = states[c]
					break
			if not state:
				continue
			updates = {}
			if state.get("latitude") is not None:
				updates["latitude"] = state["latitude"]
			if state.get("longitude") is not None:
				updates["longitude"] = state["longitude"]
			if state.get("altitude_meters") is not None:
				updates["altitude_meters"] = state["altitude_meters"]
			if state.get("speed_kmh") is not None:
				updates["speed_kmh"] = state["speed_kmh"]
			if state.get("heading") is not None:
				updates["heading"] = state["heading"]
			if state.get("vertical_speed_ms") is not None:
				updates["vertical_speed_ms"] = state["vertical_speed_ms"]
			if state.get("is_on_ground") is not None:
				updates["is_on_ground"] = 1 if state["is_on_ground"] else 0
			pos_at = state.get("last_position_update") or state.get("last_contact")
			if pos_at:
				updates["last_position_update"] = pos_at
			updates["last_updated"] = now
			updates["sync_status"] = "Synced"
			updates["data_source"] = state.get("data_source") or provider_used or "OpenSky Network"
			if not updates:
				continue
			try:
				frappe.db.set_value("Flight Schedule", f.name, updates, update_modified=False)
				updated += 1
			except Exception as e:
				frappe.log_error(f"sync_active_flights: failed to update {f.name}: {str(e)}")
		frappe.db.commit()

		# Log success silently (only log on first run / failures to keep noise down).
		if updated:
			try:
				frappe.get_doc({
					"doctype": "Flight Schedule Sync Log",
					"data_source": provider_used or "OpenSky Network",
					"sync_type": "Real-time Tracking",
					"status": "Success",
					"records_fetched": len(states),
					"records_updated": updated,
				}).insert(ignore_permissions=True)
				frappe.db.commit()
			except Exception:
				pass

	except Exception as e:
		frappe.log_error(f"Sync active flights error: {str(e)}\n{frappe.get_traceback()}")


def sync_airport_master():
	"""
	Sync airport master data (daily task)
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		results = aggregator.sync_all_providers("Airport Master")
		
		total_synced = sum(r.get("count", 0) for r in results.values() if r.get("success"))
		
		frappe.log_error(
			title="Airport Master Sync",
			message=f"Synced {total_synced} airports. Results: {results}"
		)
		
	except Exception as e:
		frappe.log_error(f"Sync airport master error: {str(e)}")


def sync_airline_master():
	"""
	Sync airline master data (daily task)
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		results = aggregator.sync_all_providers("Airline Master")
		
		total_synced = sum(r.get("count", 0) for r in results.values() if r.get("success"))
		
		frappe.log_error(
			title="Airline Master Sync",
			message=f"Synced {total_synced} airlines. Results: {results}"
		)
		
	except Exception as e:
		frappe.log_error(f"Sync airline master error: {str(e)}")


def cleanup_old_schedules():
	"""
	Cleanup old flight schedules (daily task)
	Removes schedules older than retention period
	"""
	try:
		settings = frappe.get_single('Flight Schedule Settings')
		retention_days = settings.data_retention_days or 90
		
		cutoff_date = datetime.now() - timedelta(days=retention_days)
		
		# Delete old schedules
		deleted = frappe.db.sql("""
			DELETE FROM `tabFlight Schedule`
			WHERE departure_time_scheduled < %s
			AND flight_status IN ('Landed', 'Cancelled')
		""", (cutoff_date,))
		
		frappe.db.commit()
		
		frappe.log_error(
			title="Flight Schedule Cleanup",
			message=f"Deleted {deleted} old flight schedules older than {retention_days} days"
		)
		
	except Exception as e:
		frappe.log_error(f"Cleanup old schedules error: {str(e)}")


def cleanup_old_sync_logs():
	"""
	Cleanup old sync logs (weekly task)
	"""
	try:
		# Keep logs for 30 days
		cutoff_date = datetime.now() - timedelta(days=30)
		
		frappe.db.sql("""
			DELETE FROM `tabFlight Schedule Sync Log`
			WHERE sync_date < %s
		""", (cutoff_date,))
		
		frappe.db.commit()
		
		frappe.log_error(
			title="Sync Log Cleanup",
			message="Deleted sync logs older than 30 days"
		)
		
	except Exception as e:
		frappe.log_error(f"Cleanup sync logs error: {str(e)}")


def sync_route_data():
	"""
	Sync and update flight route data (weekly task)
	"""
	try:
		# Get unique routes from recent flight schedules
		routes = frappe.db.sql("""
			SELECT DISTINCT 
				airline,
				departure_airport,
				arrival_airport,
				COUNT(*) as frequency
			FROM `tabFlight Schedule`
			WHERE departure_time_scheduled >= DATE_SUB(NOW(), INTERVAL 7 DAY)
			GROUP BY airline, departure_airport, arrival_airport
			HAVING frequency > 1
		""", as_dict=True)
		
		created_count = 0
		
		for route in routes:
			if not route.airline or not route.departure_airport or not route.arrival_airport:
				continue
			
			# Check if route exists
			existing = frappe.db.exists(
				"Flight Route",
				{
					"airline": route.airline,
					"origin_airport": route.departure_airport,
					"destination_airport": route.arrival_airport
				}
			)
			
			if not existing:
				try:
					# Create new route
					doc = frappe.get_doc({
						"doctype": "Flight Route",
						"airline": route.airline,
						"origin_airport": route.departure_airport,
						"destination_airport": route.arrival_airport,
						"frequency": "Daily" if route.frequency >= 7 else "Weekly",
						"is_active": 1
					})
					doc.insert(ignore_permissions=True)
					created_count += 1
				except Exception:
					continue
		
		frappe.db.commit()
		
		frappe.log_error(
			title="Route Data Sync",
			message=f"Created {created_count} new routes from recent flight data"
		)
		
	except Exception as e:
		frappe.log_error(f"Sync route data error: {str(e)}")


def update_air_freight_jobs_with_flight_status():
	"""
	Update Master AWB and Air Shipments with latest flight status (hourly task)
	"""
	try:
		# Get Master AWBs with linked flight schedules that have been updated recently
		awbs = frappe.db.sql("""
			SELECT 
				mawb.name,
				mawb.flight_schedule,
				fs.flight_status,
				fs.departure_time_scheduled,
				fs.departure_time_actual,
				fs.arrival_time_scheduled,
				fs.arrival_time_actual,
				fs.delay_minutes
			FROM `tabMaster Air Waybill` mawb
			INNER JOIN `tabFlight Schedule` fs ON mawb.flight_schedule = fs.name
			WHERE mawb.auto_update_flight_status = 1
			AND fs.flight_status IN ('Scheduled', 'Active', 'EnRoute', 'Landed', 'Delayed')
			AND fs.last_updated > DATE_SUB(NOW(), INTERVAL 2 HOUR)
		""", as_dict=True)
		
		updated_count = 0
		
		for awb in awbs:
			try:
				doc = frappe.get_doc("Master Air Waybill", awb.name)
				
				# Use the sync method to update all fields
				doc.sync_from_flight_schedule()
				doc.save(ignore_permissions=True)
				updated_count += 1
				
			except Exception as e:
				frappe.log_error(f"Error updating Master AWB {awb.name}: {str(e)}")
				continue
		
		frappe.db.commit()
		
		frappe.log_error(
			title="Master AWB Flight Status Updated",
			message=f"Updated {updated_count} Master AWBs with flight status"
		)
		
	except Exception as e:
		frappe.log_error(f"Update master awb flight status error: {str(e)}")

