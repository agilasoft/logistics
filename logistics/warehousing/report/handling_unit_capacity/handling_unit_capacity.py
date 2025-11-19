# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, get_datetime, now_datetime, format_datetime
from typing import Dict, List, Any, Optional
import json


def execute(filters=None):
	"""Execute the Handling Unit Capacity report"""
	filters = frappe._dict(filters or {})
	
	# Validate required filters
	if not filters.get("company"):
		# Try to get default company
		default_company = frappe.defaults.get_user_default("Company")
		if not default_company:
			frappe.msgprint(_("Please select a Company filter to view the report."), alert=True)
			columns = get_columns()
			return columns, [], None, None, []
	
	columns = get_columns()
	data = get_data(filters)
	
	# Ensure data is a list (handle None/empty cases)
	if not data:
		data = []
	
	chart = make_chart(data) if data else None
	summary = make_summary(data) if data else []
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns - organized logically for better readability"""
	return [
		# Handling Unit Identifiers Section
		{
			"label": _("Handling Unit"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Handling Unit",
			"width": 150,
		},
		{
			"label": _("Type"),
			"fieldname": "type",
			"fieldtype": "Link",
			"options": "Handling Unit Type",
			"width": 130,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 130,
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Link",
			"options": "Brand",
			"width": 120,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 130,
		},
		# Volume Capacity Section
		{
			"label": _("Max Volume"),
			"fieldname": "max_volume",
			"fieldtype": "Float",
			"precision": 3,
			"width": 120,
		},
		{
			"label": _("Current Volume"),
			"fieldname": "current_volume",
			"fieldtype": "Float",
			"precision": 3,
			"width": 130,
		},
		{
			"label": _("Available Volume"),
			"fieldname": "available_volume",
			"fieldtype": "Float",
			"precision": 3,
			"width": 130,
		},
		{
			"label": _("Volume UOM"),
			"fieldname": "capacity_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		# Weight Capacity Section
		{
			"label": _("Max Weight"),
			"fieldname": "max_weight",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Current Weight"),
			"fieldname": "current_weight",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
		{
			"label": _("Available Weight"),
			"fieldname": "available_weight",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
		{
			"label": _("Weight UOM"),
			"fieldname": "weight_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		# Utilization & Status Section
		{
			"label": _("Utilization %"),
			"fieldname": "utilization_percentage",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Capacity Status"),
			"fieldname": "capacity_status",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Efficiency Score"),
			"fieldname": "efficiency_score",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 130,
		},
		# Alert Configuration Section
		{
			"label": _("Alerts Enabled"),
			"fieldname": "enable_capacity_alerts",
			"fieldtype": "Check",
			"width": 120,
		},
		{
			"label": _("Volume Alert %"),
			"fieldname": "volume_alert_threshold",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Weight Alert %"),
			"fieldname": "weight_alert_threshold",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Utilization Alert %"),
			"fieldname": "utilization_alert_threshold",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 140,
		},
		# Metadata Section
		{
			"label": _("Last Updated"),
			"fieldname": "modified",
			"fieldtype": "Datetime",
			"width": 150,
		}
	]


def get_data(filters):
	"""Get report data"""
	# Build WHERE clause
	where_clauses = ["hu.docstatus != 2"]  # Exclude cancelled
	params = {}
	
	# Company filter (required)
	company = filters.get("company")
	if not company:
		# Try to get default company
		company = frappe.defaults.get_user_default("Company")
	
	if company:
		where_clauses.append("hu.company = %(company)s")
		params["company"] = company
	else:
		# If still no company, return empty data
		frappe.msgprint(_("Please select a Company filter to view the report."), alert=True)
		return []
	
	# Branch filter
	if filters.get("branch"):
		where_clauses.append("hu.branch = %(branch)s")
		params["branch"] = filters.get("branch")
	
	# Type filter
	if filters.get("type"):
		where_clauses.append("hu.type = %(type)s")
		params["type"] = filters.get("type")
	
	# Status filter
	if filters.get("status"):
		where_clauses.append("hu.status = %(status)s")
		params["status"] = filters.get("status")
	
	# Brand filter
	if filters.get("brand"):
		where_clauses.append("hu.brand = %(brand)s")
		params["brand"] = filters.get("brand")
	
	# Supplier filter
	if filters.get("supplier"):
		where_clauses.append("hu.supplier = %(supplier)s")
		params["supplier"] = filters.get("supplier")
	
	# Show inactive filter
	if not filters.get("show_inactive"):
		where_clauses.append("hu.status != 'Inactive'")
	
	# Capacity alerts only filter
	if filters.get("capacity_alerts_only"):
		where_clauses.append("hu.enable_capacity_alerts = 1")
	
	where_sql = " AND ".join(where_clauses)
	
	# Main query
	sql = f"""
		SELECT
			hu.name,
			hu.type,
			hu.status,
			hu.brand,
			hu.supplier,
			hu.max_volume,
			hu.current_volume,
			hu.capacity_uom,
			hu.max_weight,
			hu.current_weight,
			hu.weight_uom,
			hu.utilization_percentage,
			hu.enable_capacity_alerts,
			hu.volume_alert_threshold,
			hu.weight_alert_threshold,
			hu.utilization_alert_threshold,
			hu.modified,
			hu.branch,
			hu.company,
			-- Calculate capacity status
			CASE
				WHEN hu.utilization_percentage >= COALESCE(hu.utilization_alert_threshold, 90) THEN 'Critical'
				WHEN hu.utilization_percentage >= COALESCE(hu.volume_alert_threshold, 80) THEN 'Warning'
				ELSE 'Good'
			END AS capacity_status
		FROM `tabHandling Unit` hu
		WHERE {where_sql}
		ORDER BY
			hu.company, hu.branch, hu.type, hu.utilization_percentage DESC, hu.name
	"""
	
	data = frappe.db.sql(sql, params, as_dict=True)
	
	# Apply utilization threshold filter
	if filters.get("utilization_threshold"):
		threshold = flt(filters.get("utilization_threshold"))
		data = [row for row in data if flt(row.get("utilization_percentage", 0)) >= threshold]
	
	# Calculate additional metrics and ensure proper formatting
	for row in data:
		# Calculate available capacity
		row["available_volume"] = flt(row.get("max_volume", 0)) - flt(row.get("current_volume", 0))
		row["available_weight"] = flt(row.get("max_weight", 0)) - flt(row.get("current_weight", 0))
		
		# Calculate efficiency score
		efficiency_score = calculate_efficiency_score(row)
		row["efficiency_score"] = flt(efficiency_score, 1)
		
		# Ensure all numeric fields are properly formatted
		row["max_volume"] = flt(row.get("max_volume", 0), 3)
		row["current_volume"] = flt(row.get("current_volume", 0), 3)
		row["max_weight"] = flt(row.get("max_weight", 0), 2)
		row["current_weight"] = flt(row.get("current_weight", 0), 2)
		row["utilization_percentage"] = flt(row.get("utilization_percentage", 0), 1)
		
		# Ensure string fields are properly formatted
		row["status"] = str(row.get("status") or "")
		row["capacity_status"] = str(row.get("capacity_status") or "Good")
		row["name"] = str(row.get("name") or "")
		row["type"] = str(row.get("type") or "")
		row["company"] = str(row.get("company") or "")
		row["branch"] = str(row.get("branch") or "")
	
	return data


def calculate_efficiency_score(row):
	"""Calculate efficiency score based on utilization and status"""
	utilization = flt(row.get("utilization_percentage", 0))
	status = row.get("status", "")
	
	# Base score from utilization
	if utilization >= 90:
		base_score = 100  # Optimal utilization
	elif utilization >= 75:
		base_score = 85   # Good utilization
	elif utilization >= 50:
		base_score = 70   # Moderate utilization
	elif utilization >= 25:
		base_score = 50   # Low utilization
	else:
		base_score = 25   # Very low utilization
	
	# Adjust based on status
	if status == "In Use":
		status_multiplier = 1.0
	elif status == "Available":
		status_multiplier = 0.8
	elif status == "Under Maintenance":
		status_multiplier = 0.6
	else:  # Inactive
		status_multiplier = 0.3
	
	return min(100, base_score * status_multiplier)


def make_chart(data):
	"""Create chart data"""
	if not data:
		return None
	
	# Group by utilization ranges
	utilization_ranges = {
		"0-25%": 0,
		"25-50%": 0,
		"50-75%": 0,
		"75-90%": 0,
		"90-100%": 0,
		"Over 100%": 0
	}
	
	for row in data:
		util = flt(row.get("utilization_percentage", 0))
		if util <= 25:
			utilization_ranges["0-25%"] += 1
		elif util <= 50:
			utilization_ranges["25-50%"] += 1
		elif util <= 75:
			utilization_ranges["50-75%"] += 1
		elif util <= 90:
			utilization_ranges["75-90%"] += 1
		elif util <= 100:
			utilization_ranges["90-100%"] += 1
		else:
			utilization_ranges["Over 100%"] += 1
	
	return {
		"data": {
			"labels": list(utilization_ranges.keys()),
			"datasets": [{
				"name": "Handling Units",
				"values": list(utilization_ranges.values())
			}]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#ff6b6b", "#ffa726", "#ffeb3b", "#66bb6a", "#42a5f5", "#ef5350"]
	}


def make_summary(data):
	"""Create summary data"""
	if not data:
		return []
	
	total_units = len(data)
	in_use = len([row for row in data if row.get("status") == "In Use"])
	available = len([row for row in data if row.get("status") == "Available"])
	under_maintenance = len([row for row in data if row.get("status") == "Under Maintenance"])
	inactive = len([row for row in data if row.get("status") == "Inactive"])
	
	# Calculate average utilization
	utilizations = [flt(row.get("utilization_percentage", 0)) for row in data if row.get("utilization_percentage")]
	avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
	
	# Count capacity alerts
	critical_alerts = len([row for row in data if row.get("capacity_status") == "Critical"])
	warning_alerts = len([row for row in data if row.get("capacity_status") == "Warning"])
	
	# Calculate total capacity
	total_max_volume = sum([flt(row.get("max_volume", 0)) for row in data])
	total_current_volume = sum([flt(row.get("current_volume", 0)) for row in data])
	total_max_weight = sum([flt(row.get("max_weight", 0)) for row in data])
	total_current_weight = sum([flt(row.get("current_weight", 0)) for row in data])
	
	return [
		{
			"label": _("Total Handling Units"),
			"value": total_units,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("In Use"),
			"value": in_use,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Available"),
			"value": available,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("Under Maintenance"),
			"value": under_maintenance,
			"indicator": "orange",
			"datatype": "Int"
		},
		{
			"label": _("Average Utilization"),
			"value": avg_utilization,
			"indicator": "orange" if avg_utilization >= 90 else "green",
			"datatype": "Percent",
			"precision": 1
		},
		{
			"label": _("Critical Alerts"),
			"value": critical_alerts,
			"indicator": "red",
			"datatype": "Int"
		},
		{
			"label": _("Warning Alerts"),
			"value": warning_alerts,
			"indicator": "orange",
			"datatype": "Int"
		},
		{
			"label": _("Total Volume Capacity"),
			"value": total_max_volume,
			"indicator": "blue",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Volume Utilization"),
			"value": (total_current_volume / total_max_volume * 100) if total_max_volume > 0 else 0,
			"indicator": "green",
			"datatype": "Percent",
			"precision": 1
		}
	]


@frappe.whitelist()
def export_to_excel(filters):
	"""Export report data to Excel"""
	import pandas as pd
	from frappe.utils import get_site_path
	import os
	
	# Get data
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
	columns, data = get_columns(), get_data(filters)
	
	# Convert to DataFrame
	df = pd.DataFrame(data)
	
	# Create Excel file
	file_path = get_site_path("private", "files", "handling_unit_capacity_report.xlsx")
	os.makedirs(os.path.dirname(file_path), exist_ok=True)
	
	with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
		df.to_excel(writer, sheet_name='Handling Unit Capacity', index=False)
		
		# Add summary sheet
		summary_data = make_summary(data)
		summary_df = pd.DataFrame(summary_data)
		summary_df.to_excel(writer, sheet_name='Summary', index=False)
	
	# Return file URL
	file_url = f"/private/files/handling_unit_capacity_report.xlsx"
	
	return {
		"file_url": file_url,
		"message": _("Report exported successfully")
	}


@frappe.whitelist()
def get_capacity_insights(filters):
	"""Get capacity insights and recommendations"""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
	data = get_data(filters)
	
	insights = []
	
	# High utilization insights
	high_util_units = [row for row in data if flt(row.get("utilization_percentage", 0)) >= 90]
	if high_util_units:
		insights.append({
			"type": "warning",
			"title": _("High Utilization Alert"),
			"message": _("{0} handling units are at or above 90% capacity").format(len(high_util_units)),
			"action": _("Consider redistributing inventory or adding capacity")
		})
	
	# Low utilization insights
	low_util_units = [row for row in data if flt(row.get("utilization_percentage", 0)) < 25 and row.get("status") == "In Use"]
	if low_util_units:
		insights.append({
			"type": "info",
			"title": _("Low Utilization Opportunity"),
			"message": _("{0} handling units are underutilized").format(len(low_util_units)),
			"action": _("Consider consolidating inventory or optimizing space")
		})
	
	# Maintenance insights
	maintenance_units = [row for row in data if row.get("status") == "Under Maintenance"]
	if maintenance_units:
		insights.append({
			"type": "info",
			"title": _("Maintenance Status"),
			"message": _("{0} handling units are under maintenance").format(len(maintenance_units)),
			"action": _("Monitor maintenance schedules and plan capacity accordingly")
		})
	
	return insights
