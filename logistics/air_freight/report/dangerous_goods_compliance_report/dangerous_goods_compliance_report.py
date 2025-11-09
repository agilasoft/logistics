# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
from datetime import datetime, timedelta

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data, filters)
	
	return columns, data, None, chart, summary

def get_columns():
	return [
		{
			"fieldname": "air_shipment",
			"label": _("Air Shipment"),
			"fieldtype": "Link",
			"options": "Air Shipment",
			"width": 150
		},
		{
			"fieldname": "booking_date",
			"label": _("Booking Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "contains_dg",
			"label": _("Contains DG"),
			"fieldtype": "Check",
			"width": 100
		},
		{
			"fieldname": "dg_compliance_status",
			"label": _("DG Compliance Status"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "dg_packages_count",
			"label": _("DG Packages"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "radioactive_packages",
			"label": _("Radioactive"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "temp_controlled_dg",
			"label": _("Temp Controlled"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "compliance_issues",
			"label": _("Compliance Issues"),
			"fieldtype": "Int",
			"width": 130
		},
		{
			"fieldname": "emergency_contact",
			"label": _("Emergency Contact"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "emergency_phone",
			"label": _("Emergency Phone"),
			"fieldtype": "Data",
			"width": 130
		},
		{
			"fieldname": "origin_port",
			"label": _("Origin"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "destination_port",
			"label": _("Destination"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get Air Shipments with DG information
	data = frappe.db.sql("""
		SELECT
			aship.name as air_shipment,
			aship.booking_date,
			aship.contains_dangerous_goods as contains_dg,
			aship.dg_compliance_status,
			COALESCE((
				SELECT COUNT(*)
				FROM `tabAir Shipment Packages` asp
				WHERE asp.parent = aship.name
				AND (asp.dg_substance IS NOT NULL OR asp.un_number IS NOT NULL)
			), 0) as dg_packages_count,
			COALESCE((
				SELECT COUNT(*)
				FROM `tabAir Shipment Packages` asp
				WHERE asp.parent = aship.name
				AND asp.is_radioactive = 1
			), 0) as radioactive_packages,
			COALESCE((
				SELECT COUNT(*)
				FROM `tabAir Shipment Packages` asp
				WHERE asp.parent = aship.name
				AND asp.temp_controlled = 1
			), 0) as temp_controlled_dg,
			COALESCE((
				SELECT COUNT(*)
				FROM `tabAir Shipment Packages` asp
				WHERE asp.parent = aship.name
				AND (asp.dg_substance IS NOT NULL OR asp.un_number IS NOT NULL)
				AND (asp.un_number IS NULL OR asp.proper_shipping_name IS NULL OR asp.emergency_contact_name IS NULL)
			), 0) as compliance_issues,
			aship.dg_emergency_contact as emergency_contact,
			aship.dg_emergency_phone as emergency_phone,
			aship.origin_port,
			aship.destination_port,
			aship.status
		FROM
			`tabAir Shipment` aship
		WHERE
			aship.docstatus = 1
			{conditions}
		ORDER BY
			aship.booking_date DESC, aship.name DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("aship.booking_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("aship.booking_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("aship.company = %(company)s")
	
	if filters.get("contains_dg"):
		conditions.append("aship.contains_dangerous_goods = 1")
	
	if filters.get("compliance_status"):
		conditions.append("aship.dg_compliance_status = %(compliance_status)s")
	
	if filters.get("has_compliance_issues"):
		conditions.append("""
			EXISTS (
				SELECT 1
				FROM `tabAir Shipment Packages` asp
				WHERE asp.parent = aship.name
				AND (asp.dg_substance IS NOT NULL OR asp.un_number IS NOT NULL)
				AND (asp.un_number IS NULL OR asp.proper_shipping_name IS NULL OR asp.emergency_contact_name IS NULL)
			)
		""")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Compliance status distribution
	compliance_count = {
		"Compliant": 0,
		"Non-Compliant": 0,
		"Pending": 0,
		"Unknown": 0
	}
	
	for row in data:
		status = row.get("dg_compliance_status") or "Unknown"
		if status in compliance_count:
			compliance_count[status] += 1
		else:
			compliance_count["Unknown"] += 1
	
	chart = {
		"data": {
			"labels": list(compliance_count.keys()),
			"datasets": [{
				"name": "DG Compliance Status",
				"values": list(compliance_count.values())
			}]
		},
		"type": "pie",
		"colors": ["#28a745", "#ff5858", "#ffa00a", "#7cd6fd"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	dg_shipments = sum(1 for row in data if row.get("contains_dg"))
	compliant = sum(1 for row in data if row.get("dg_compliance_status") == "Compliant")
	non_compliant = sum(1 for row in data if row.get("dg_compliance_status") == "Non-Compliant")
	total_dg_packages = sum(flt(row.get("dg_packages_count") or 0) for row in data)
	total_compliance_issues = sum(flt(row.get("compliance_issues") or 0) for row in data)
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("DG Shipments"),
			"value": dg_shipments,
			"indicator": "orange"
		},
		{
			"label": _("Compliant"),
			"value": compliant,
			"indicator": "green"
		},
		{
			"label": _("Non-Compliant"),
			"value": non_compliant,
			"indicator": "red"
		},
		{
			"label": _("Total DG Packages"),
			"value": total_dg_packages,
			"indicator": "orange"
		},
		{
			"label": _("Compliance Issues"),
			"value": total_compliance_issues,
			"indicator": "red"
		}
	]
	
	return summary


