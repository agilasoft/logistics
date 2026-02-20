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
		{"fieldname": "sea_shipment", "label": _("Sea Shipment"), "fieldtype": "Link", "options": "Sea Shipment", "width": 150},
		{"fieldname": "booking_date", "label": _("Booking Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "shipping_status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "origin_port", "label": _("Origin"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "destination_port", "label": _("Destination"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "etd", "label": _("ETD"), "fieldtype": "Date", "width": 100},
		{"fieldname": "eta", "label": _("ETA"), "fieldtype": "Date", "width": 100},
		{"fieldname": "weight", "label": _("Weight (kg)"), "fieldtype": "Float", "precision": 2, "width": 110},
		{"fieldname": "volume", "label": _("Volume (m³)"), "fieldtype": "Float", "precision": 2, "width": 110},
		{"fieldname": "chargeable", "label": _("Chargeable (kg)"), "fieldtype": "Float", "precision": 2, "width": 120},
		{"fieldname": "total_containers", "label": _("Containers"), "fieldtype": "Int", "width": 90},
		{"fieldname": "shipping_line", "label": _("Shipping Line"), "fieldtype": "Link", "options": "Shipping Line", "width": 130},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 120},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql("""
		SELECT
			ss.name as sea_shipment,
			ss.booking_date,
			ss.shipping_status,
			ss.local_customer as customer,
			ss.origin_port,
			ss.destination_port,
			ss.etd,
			ss.eta,
			ss.weight,
			ss.volume,
			ss.chargeable,
			ss.total_containers,
			ss.shipping_line,
			ss.company
		FROM `tabSea Shipment` ss
		WHERE ss.docstatus < 2
		{conditions}
		ORDER BY ss.booking_date DESC, ss.modified DESC
	""".format(conditions=conditions), filters, as_dict=1)
	return data


def get_conditions(filters):
	conditions = []
	if filters.get("from_date"):
		conditions.append("ss.booking_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("ss.booking_date <= %(to_date)s")
	if filters.get("company"):
		conditions.append("ss.company = %(company)s")
	if filters.get("status"):
		conditions.append("ss.shipping_status = %(status)s")
	if filters.get("shipping_line"):
		conditions.append("ss.shipping_line = %(shipping_line)s")
	if filters.get("customer"):
		conditions.append("ss.local_customer = %(customer)s")
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data):
	if not data:
		return None
	from collections import Counter
	by_status = Counter((r.get("shipping_status") or _("Unknown")) for r in data)
	return {
		"data": {
			"labels": list(by_status.keys()),
			"datasets": [{"name": _("Shipments"), "values": list(by_status.values())}]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}


def get_summary(data):
	if not data:
		return []
	total = len(data)
	total_weight = sum(flt(r.get("weight")) for r in data)
	total_volume = sum(flt(r.get("volume")) for r in data)
	return [
		{"label": _("Total Shipments"), "value": total, "indicator": "blue"},
		{"label": _("Total Weight (kg)"), "value": f"{total_weight:,.2f}", "indicator": "blue"},
		{"label": _("Total Volume (m³)"), "value": f"{total_volume:,.2f}", "indicator": "blue"},
	]
