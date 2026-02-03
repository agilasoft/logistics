# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt
from datetime import timedelta


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data, filters)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Road Compliance"),
			"fieldtype": "Link",
			"options": "Road Compliance",
			"width": 140,
		},
		{
			"fieldname": "compliance_type",
			"label": _("Compliance Type"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "priority",
			"label": _("Priority"),
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"fieldname": "title",
			"label": _("Title"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "effective_date",
			"label": _("Effective Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "expiry_date",
			"label": _("Expiry Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "days_until_expiry",
			"label": _("Days Until Expiry"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "applies_to_vehicles",
			"label": _("Applies to Vehicles"),
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"fieldname": "applies_to_drivers",
			"label": _("Applies to Drivers"),
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"fieldname": "monitoring_frequency",
			"label": _("Monitoring Frequency"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "alert_before_expiry",
			"label": _("Alert Before Expiry (Days)"),
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"fieldname": "penalty_amount",
			"label": _("Penalty Amount"),
			"fieldtype": "Currency",
			"width": 120,
		},
	]


def get_data(filters):
	filters = filters or {}
	conditions = []
	values = {}

	if filters.get("compliance_type"):
		conditions.append("rc.compliance_type = %(compliance_type)s")
		values["compliance_type"] = filters["compliance_type"]
	if filters.get("status"):
		conditions.append("rc.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("priority"):
		conditions.append("rc.priority = %(priority)s")
		values["priority"] = filters["priority"]
	if filters.get("effective_from"):
		conditions.append("rc.effective_date >= %(effective_from)s")
		values["effective_from"] = filters["effective_from"]
	if filters.get("effective_to"):
		conditions.append("rc.effective_date <= %(effective_to)s")
		values["effective_to"] = filters["effective_to"]

	expiry_filter = filters.get("expiry_filter") or "All"
	today = getdate()

	if expiry_filter == "Expired":
		conditions.append("rc.expiry_date IS NOT NULL AND rc.expiry_date < %(today)s")
		values["today"] = today
	elif expiry_filter == "Expiring in 30 days":
		conditions.append(
			"rc.expiry_date IS NOT NULL AND rc.expiry_date >= %(today)s AND rc.expiry_date <= %(expiry_30)s"
		)
		values["today"] = today
		values["expiry_30"] = today + timedelta(days=30)
	elif expiry_filter == "Expiring in 90 days":
		conditions.append(
			"rc.expiry_date IS NOT NULL AND rc.expiry_date >= %(today)s AND rc.expiry_date <= %(expiry_90)s"
		)
		values["today"] = today
		values["expiry_90"] = today + timedelta(days=90)
	elif expiry_filter == "No expiry date":
		conditions.append("rc.expiry_date IS NULL")

	where_clause = " AND " + " AND ".join(conditions) if conditions else ""

	query = """
		SELECT
			rc.name,
			rc.compliance_type,
			rc.status,
			rc.priority,
			rc.title,
			rc.effective_date,
			rc.expiry_date,
			rc.applies_to_vehicles,
			rc.applies_to_drivers,
			rc.monitoring_frequency,
			rc.alert_before_expiry,
			rc.penalty_amount,
			rc.penalty_currency
		FROM `tabRoad Compliance` rc
		WHERE 1=1
		""" + where_clause + """
		ORDER BY rc.expiry_date IS NULL, rc.expiry_date ASC, rc.priority DESC, rc.modified DESC
	"""

	data = frappe.db.sql(query, values, as_dict=True)

	for row in data:
		row["days_until_expiry"] = None
		if row.get("expiry_date"):
			delta = getdate(row["expiry_date"]) - today
			row["days_until_expiry"] = delta.days

	return data


def get_chart_data(data):
	if not data:
		return None

	# Group by status for pie chart
	by_status = {}
	for row in data:
		s = row.get("status") or _("Unknown")
		by_status[s] = by_status.get(s, 0) + 1

	return {
		"data": {
			"labels": list(by_status.keys()),
			"datasets": [{"name": _("Road Compliance by Status"), "values": list(by_status.values())}],
		},
		"type": "pie",
		"colors": ["#28a745", "#ffc107", "#dc3545", "#6c757d"],
	}


def get_summary(data, filters):
	if not data:
		return []

	today = getdate()
	active = sum(1 for r in data if (r.get("status") or "").lower() == "active")
	expired = sum(1 for r in data if r.get("expiry_date") and getdate(r["expiry_date"]) < today)
	expiring_30 = sum(
		1
		for r in data
		if r.get("expiry_date")
		and today <= getdate(r["expiry_date"]) <= today + timedelta(days=30)
	)
	critical = sum(1 for r in data if (r.get("priority") or "").lower() == "critical")

	return [
		{"label": _("Total Records"), "value": len(data), "indicator": "blue"},
		{"label": _("Active"), "value": active, "indicator": "green"},
		{"label": _("Expired"), "value": expired, "indicator": "red"},
		{"label": _("Expiring in 30 Days"), "value": expiring_30, "indicator": "orange"},
		{"label": _("Critical Priority"), "value": critical, "indicator": "red" if critical else "green"},
	]
