# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data) if data else []
	return columns, data, None, None, summary


def get_columns():
	return [
		{"fieldname": "consolidation", "label": _("Sea Consolidation"), "fieldtype": "Link", "options": "Sea Consolidation", "width": 160},
		{"fieldname": "consolidation_date", "label": _("Consolidation Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "origin_port", "label": _("Origin"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "destination_port", "label": _("Destination"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "total_shipments", "label": _("Total Shipments"), "fieldtype": "Int", "width": 120},
		{"fieldname": "total_containers", "label": _("Total Containers"), "fieldtype": "Int", "width": 120},
		{"fieldname": "total_weight", "label": _("Total Weight (kg)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "total_volume", "label": _("Total Volume (m³)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "chargeable_weight", "label": _("Chargeable (kg)"), "fieldtype": "Float", "precision": 2, "width": 120},
		{"fieldname": "consolidation_ratio", "label": _("Consolidation Ratio"), "fieldtype": "Float", "precision": 2, "width": 140},
		{"fieldname": "cost_per_kg", "label": _("Cost per kg"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "etd", "label": _("ETD"), "fieldtype": "Date", "width": 100},
		{"fieldname": "eta", "label": _("ETA"), "fieldtype": "Date", "width": 100},
		{"fieldname": "shipping_line", "label": _("Shipping Line"), "fieldtype": "Link", "options": "Shipping Line", "width": 130},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql("""
		SELECT
			sc.name as consolidation,
			sc.consolidation_date,
			sc.status,
			sc.origin_port,
			sc.destination_port,
			(SELECT COUNT(DISTINCT parent) FROM `tabSea Consolidation Shipments` WHERE parent = sc.name) as total_shipments,
			sc.total_containers,
			sc.total_weight,
			sc.total_volume,
			sc.chargeable_weight,
			sc.consolidation_ratio,
			sc.cost_per_kg,
			sc.etd,
			sc.eta,
			sc.shipping_line
		FROM `tabSea Consolidation` sc
		WHERE sc.docstatus < 2
		{conditions}
		ORDER BY sc.consolidation_date DESC, sc.modified DESC
	""".format(conditions=conditions), filters, as_dict=1)
	return data


def get_conditions(filters):
	conditions = []
	if filters.get("from_date"):
		conditions.append("sc.consolidation_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("sc.consolidation_date <= %(to_date)s")
	if filters.get("status"):
		conditions.append("sc.status = %(status)s")
	if filters.get("shipping_line"):
		conditions.append("sc.shipping_line = %(shipping_line)s")
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_summary(data):
	total = len(data)
	total_weight = sum(flt(r.get("total_weight")) for r in data)
	total_volume = sum(flt(r.get("total_volume")) for r in data)
	total_containers = sum(flt(r.get("total_containers") or 0) for r in data)
	return [
		{"label": _("Total Consolidations"), "value": total, "indicator": "blue"},
		{"label": _("Total Weight (kg)"), "value": f"{total_weight:,.2f}", "indicator": "blue"},
		{"label": _("Total Volume (m³)"), "value": f"{total_volume:,.2f}", "indicator": "blue"},
		{"label": _("Total Containers"), "value": int(total_containers), "indicator": "green"},
	]
