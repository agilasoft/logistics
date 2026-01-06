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
	"""
	Sync active flights (hourly task)
	Updates real-time status for flights currently in progress
	"""
	try:
		settings = frappe.get_single('Flight Schedule Settings')
		
		if not settings.enable_realtime_tracking:
			return
		
		# Get active flights from last 24 hours
		yesterday = datetime.now() - timedelta(days=1)
		
		active_flights = frappe.get_all(
			"Flight Schedule",
			filters={
				"flight_status": ["in", ["Scheduled", "Active", "EnRoute"]],
				"departure_time_scheduled": [">=", yesterday]
			},
			fields=["name", "flight_number", "departure_time_scheduled"],
			limit=50  # Limit to avoid too many API calls
		)
		
		if not active_flights:
			return
		
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		aggregator = get_aggregator()
		
		updated_count = 0
		failed_count = 0
		
		for flight in active_flights:
			try:
				# Get updated flight data
				flight_data = aggregator.get_real_time_flight(flight.flight_number)
				
				# Update the flight schedule
				doc = frappe.get_doc("Flight Schedule", flight.name)
				for key, value in flight_data.items():
					if value is not None and hasattr(doc, key):
						setattr(doc, key, value)
				doc.save(ignore_permissions=True)
				
				updated_count += 1
				
			except Exception as e:
				frappe.log_error(f"Error updating flight {flight.flight_number}: {str(e)}")
				failed_count += 1
				continue
		
		frappe.db.commit()
		
		frappe.log_error(
			title="Flight Sync Completed",
			message=f"Updated: {updated_count}, Failed: {failed_count}"
		)
		
	except Exception as e:
		frappe.log_error(f"Sync active flights error: {str(e)}")


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
				except:
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

