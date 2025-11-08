# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Scheduled Tasks for Sea Freight Delay and Penalty Alerts
"""

from __future__ import unicode_literals
import frappe
from datetime import datetime, timedelta


def check_sea_shipment_delays():
	"""
	Check for delays in Sea Shipments (hourly task)
	Updates delay tracking fields and sends alerts
	"""
	try:
		settings = frappe.get_single("Sea Freight Settings")
		
		if not getattr(settings, "enable_delay_alerts", 1):
			return
		
		# Get active shipments that need delay checking
		# Check shipments that are not closed/cancelled
		active_shipments = frappe.get_all(
			"Sea Shipment",
			filters={
				"docstatus": ["!=", 2],  # Not cancelled
				"shipping_status": ["not in", ["Closed", "Cancelled"]]
			},
			fields=["name", "shipping_status", "last_delay_check"],
			limit=100  # Limit to avoid too many operations
		)
		
		if not active_shipments:
			return
		
		updated_count = 0
		alert_count = 0
		
		for shipment in active_shipments:
			try:
				doc = frappe.get_doc("Sea Shipment", shipment.name)
				
				# Check delays
				doc.check_delays()
				doc.save(ignore_permissions=True)
				
				updated_count += 1
				
				if doc.has_delays and doc.delay_alert_sent:
					alert_count += 1
					
			except Exception as e:
				frappe.log_error(f"Error checking delays for Sea Shipment {shipment.name}: {str(e)}")
				continue
		
		frappe.db.commit()
		
		if updated_count > 0:
			frappe.log_error(
				title="Sea Shipment Delay Check Completed",
				message=f"Checked {updated_count} shipments, {alert_count} alerts sent"
			)
		
	except Exception as e:
		frappe.log_error(f"Check sea shipment delays error: {str(e)}")


def check_sea_shipment_penalties():
	"""
	Check for penalties in Sea Shipments (hourly task)
	Calculates detention and demurrage penalties and sends alerts
	"""
	try:
		settings = frappe.get_single("Sea Freight Settings")
		
		if not getattr(settings, "enable_penalty_alerts", 1):
			return
		
		# Get shipments that are discharged or in transit (where penalties can occur)
		active_shipments = frappe.get_all(
			"Sea Shipment",
			filters={
				"docstatus": ["!=", 2],  # Not cancelled
				"shipping_status": ["in", [
					"Discharged from Vessel",
					"Customs Clearance (Import)",
					"Available for Pick-Up",
					"Out for Delivery",
					"Delivered"
				]]
			},
			fields=["name", "shipping_status", "last_penalty_check"],
			limit=100  # Limit to avoid too many operations
		)
		
		if not active_shipments:
			return
		
		updated_count = 0
		penalty_count = 0
		
		for shipment in active_shipments:
			try:
				doc = frappe.get_doc("Sea Shipment", shipment.name)
				
				# Calculate penalties
				doc.calculate_penalties()
				doc.save(ignore_permissions=True)
				
				updated_count += 1
				
				if doc.has_penalties and doc.penalty_alert_sent:
					penalty_count += 1
					
			except Exception as e:
				frappe.log_error(f"Error calculating penalties for Sea Shipment {shipment.name}: {str(e)}")
				continue
		
		frappe.db.commit()
		
		if updated_count > 0:
			frappe.log_error(
				title="Sea Shipment Penalty Check Completed",
				message=f"Checked {updated_count} shipments, {penalty_count} penalties detected"
			)
		
	except Exception as e:
		frappe.log_error(f"Check sea shipment penalties error: {str(e)}")


def check_impending_penalties():
	"""
	Check for impending penalties (daily task)
	Alerts users about upcoming penalties to minimize costs
	"""
	try:
		settings = frappe.get_single("Sea Freight Settings")
		
		if not getattr(settings, "enable_penalty_alerts", 1):
			return
		
		free_time_days = getattr(settings, "default_free_time_days", 7)
		
		# Get shipments that are approaching free time limit
		# Check shipments discharged in the last (free_time_days + 1) days
		from frappe.utils import now_datetime, getdate
		from datetime import timedelta
		
		check_date = getdate(now_datetime()) - timedelta(days=int(free_time_days) + 1)
		
		# Get shipments that might be approaching penalty threshold
		shipments = frappe.get_all(
			"Sea Shipment",
			filters={
				"docstatus": ["!=", 2],  # Not cancelled
				"shipping_status": ["in", [
					"Discharged from Vessel",
					"Customs Clearance (Import)",
					"Available for Pick-Up"
				]],
				"has_penalties": 0  # Not yet penalized
			},
			fields=["name", "shipping_status", "eta"],
			limit=50
		)
		
		if not shipments:
			return
		
		impending_count = 0
		
		for shipment in shipments:
			try:
				doc = frappe.get_doc("Sea Shipment", shipment.name)
				
				# Check if approaching free time limit
				discharge_date = None
				
				# Try to get discharge date from milestone
				discharge_milestone = frappe.get_all(
					"Job Milestone",
					filters={
						"job_type": "Sea Shipment",
						"job_number": doc.name,
						"milestone": "SF-DISCHARGED"
					},
					fields=["actual_end"],
					limit=1
				)
				
				if discharge_milestone and discharge_milestone[0].actual_end:
					discharge_date = getdate(discharge_milestone[0].actual_end)
				elif doc.eta:
					discharge_date = getdate(doc.eta)
				
				if discharge_date:
					today = getdate(now_datetime())
					days_since_discharge = (today - discharge_date).days
					
					# Alert if approaching free time limit (within 2 days)
					if days_since_discharge >= (free_time_days - 2) and days_since_discharge < free_time_days:
						# Send impending penalty alert
						doc._send_impending_penalty_alert(days_since_discharge, free_time_days)
						impending_count += 1
						
			except Exception as e:
				frappe.log_error(f"Error checking impending penalties for Sea Shipment {shipment.name}: {str(e)}")
				continue
		
		frappe.db.commit()
		
		if impending_count > 0:
			frappe.log_error(
				title="Impending Penalty Check Completed",
				message=f"Checked {len(shipments)} shipments, {impending_count} impending penalties alerted"
			)
		
	except Exception as e:
		frappe.log_error(f"Check impending penalties error: {str(e)}")

