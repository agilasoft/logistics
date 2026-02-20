# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data) if data else None
	summary = get_summary(data) if data else []
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "route", "label": _("Route"), "fieldtype": "Data", "width": 200},
		{"fieldname": "origin_port", "label": _("Origin"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "destination_port", "label": _("Destination"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "total_shipments", "label": _("Total Shipments"), "fieldtype": "Int", "width": 120},
		{"fieldname": "total_weight", "label": _("Total Weight (kg)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "total_volume", "label": _("Total Volume (m³)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "total_chargeable", "label": _("Total Chargeable (kg)"), "fieldtype": "Float", "precision": 2, "width": 150},
		{"fieldname": "total_revenue", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "avg_revenue_per_kg", "label": _("Avg Revenue/kg"), "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql("""
		SELECT
			CONCAT(ss.origin_port, ' - ', ss.destination_port) as route,
			ss.origin_port,
			ss.destination_port,
			COUNT(DISTINCT ss.name) as total_shipments,
			SUM(ss.weight) as total_weight,
			SUM(ss.volume) as total_volume,
			SUM(ss.chargeable) as total_chargeable,
			SUM(COALESCE(charge_agg.total_charges, 0)) as total_revenue
		FROM `tabSea Shipment` ss
		LEFT JOIN (
			SELECT parent, SUM(total_amount) as total_charges
			FROM `tabSea Freight Charges`
			GROUP BY parent
		) charge_agg ON charge_agg.parent = ss.name
		WHERE ss.docstatus = 1
		{conditions}
		GROUP BY ss.origin_port, ss.destination_port
		ORDER BY total_shipments DESC, total_revenue DESC
	""".format(conditions=conditions), filters, as_dict=1)
	for row in data:
		chargeable = flt(row.get("total_chargeable"))
		revenue = flt(row.get("total_revenue"))
		row["avg_revenue_per_kg"] = revenue / chargeable if chargeable else 0
	return data


def get_conditions(filters):
	conditions = []
	if filters.get("from_date"):
		conditions.append("ss.booking_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("ss.booking_date <= %(to_date)s")
	if filters.get("company"):
		conditions.append("ss.company = %(company)s")
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data):
	if not data:
		return None
	return {
		"data": {
			"labels": [r.get("route") or "" for r in data[:10]],
			"datasets": [{"name": _("Shipments"), "values": [r.get("total_shipments") or 0 for r in data[:10]]}]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}


def get_summary(data):
	total_shipments = sum(flt(r.get("total_shipments")) for r in data)
	total_revenue = sum(flt(r.get("total_revenue")) for r in data)
	total_weight = sum(flt(r.get("total_weight")) for r in data)
	return [
		{"label": _("Total Routes"), "value": len(data), "indicator": "blue"},
		{"label": _("Total Shipments"), "value": int(total_shipments), "indicator": "blue"},
		{"label": _("Total Revenue"), "value": f"{total_revenue:,.2f}", "indicator": "green"},
		{"label": _("Total Weight (kg)"), "value": f"{total_weight:,.2f}", "indicator": "blue"},
	]
