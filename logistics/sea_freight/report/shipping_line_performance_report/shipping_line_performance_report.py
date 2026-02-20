# Copyright (c) 2026, www.agilasoft.com and contributors
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
		{"fieldname": "shipping_line", "label": _("Shipping Line"), "fieldtype": "Link", "options": "Shipping Line", "width": 150},
		{"fieldname": "total_shipments", "label": _("Total Shipments"), "fieldtype": "Int", "width": 120},
		{"fieldname": "total_weight", "label": _("Total Weight (kg)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "total_volume", "label": _("Total Volume (m³)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "total_chargeable", "label": _("Total Chargeable (kg)"), "fieldtype": "Float", "precision": 2, "width": 150},
		{"fieldname": "on_time_shipments", "label": _("On-Time Shipments"), "fieldtype": "Int", "width": 130},
		{"fieldname": "delayed_shipments", "label": _("Delayed Shipments"), "fieldtype": "Int", "width": 130},
		{"fieldname": "on_time_percentage", "label": _("On-Time %"), "fieldtype": "Percent", "precision": 1, "width": 100},
		{"fieldname": "avg_departure_delay", "label": _("Avg Departure Delay (hrs)"), "fieldtype": "Float", "precision": 2, "width": 160},
		{"fieldname": "avg_arrival_delay", "label": _("Avg Arrival Delay (hrs)"), "fieldtype": "Float", "precision": 2, "width": 160},
		{"fieldname": "total_revenue", "label": _("Total Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "avg_revenue_per_shipment", "label": _("Avg Revenue/Shipment"), "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql("""
		SELECT
			ss.shipping_line,
			COUNT(DISTINCT ss.name) as total_shipments,
			SUM(ss.weight) as total_weight,
			SUM(ss.volume) as total_volume,
			SUM(ss.chargeable) as total_chargeable,
			SUM(CASE WHEN ss.eta IS NOT NULL AND ss.ata IS NOT NULL
				AND TIMESTAMPDIFF(HOUR, ss.eta, ss.ata) <= 0 THEN 1 ELSE 0 END) as on_time_shipments,
			SUM(CASE WHEN ss.eta IS NOT NULL AND ss.ata IS NOT NULL
				AND TIMESTAMPDIFF(HOUR, ss.eta, ss.ata) > 0 THEN 1 ELSE 0 END) as delayed_shipments,
			CASE
				WHEN COUNT(CASE WHEN ss.eta IS NOT NULL AND ss.ata IS NOT NULL THEN 1 END) > 0
				THEN (SUM(CASE WHEN ss.eta IS NOT NULL AND ss.ata IS NOT NULL
					AND TIMESTAMPDIFF(HOUR, ss.eta, ss.ata) <= 0 THEN 1 ELSE 0 END) * 100.0) /
					COUNT(CASE WHEN ss.eta IS NOT NULL AND ss.ata IS NOT NULL THEN 1 END)
				ELSE 0
			END as on_time_percentage,
			AVG(CASE WHEN ss.etd IS NOT NULL AND ss.atd IS NOT NULL
				THEN TIMESTAMPDIFF(HOUR, ss.etd, ss.atd) ELSE NULL END) as avg_departure_delay,
			AVG(CASE WHEN ss.eta IS NOT NULL AND ss.ata IS NOT NULL
				THEN TIMESTAMPDIFF(HOUR, ss.eta, ss.ata) ELSE NULL END) as avg_arrival_delay,
			SUM(COALESCE(charge_agg.total_charges, 0)) as total_revenue,
			CASE WHEN COUNT(DISTINCT ss.name) > 0
				THEN SUM(COALESCE(charge_agg.total_charges, 0)) / COUNT(DISTINCT ss.name)
				ELSE 0
			END as avg_revenue_per_shipment
		FROM `tabSea Shipment` ss
		LEFT JOIN (
			SELECT parent, SUM(total_amount) as total_charges
			FROM `tabSea Freight Charges`
			GROUP BY parent
		) charge_agg ON charge_agg.parent = ss.name
		WHERE ss.docstatus = 1 AND ss.shipping_line IS NOT NULL
		{conditions}
		GROUP BY ss.shipping_line
		ORDER BY total_shipments DESC, on_time_percentage DESC
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
	if filters.get("shipping_line"):
		conditions.append("ss.shipping_line = %(shipping_line)s")
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data):
	if not data:
		return None
	top = sorted(data, key=lambda x: flt(x.get("total_shipments") or 0), reverse=True)[:10]
	return {
		"data": {
			"labels": [row.get("shipping_line") for row in top],
			"datasets": [{"name": _("On-Time %"), "values": [flt(row.get("on_time_percentage") or 0) for row in top]}]
		},
		"type": "bar",
		"colors": ["#28a745"]
	}


def get_summary(data):
	if not data:
		return []
	total_lines = len(data)
	total_shipments = sum(flt(r.get("total_shipments")) for r in data)
	total_weight = sum(flt(r.get("total_weight")) for r in data)
	total_revenue = sum(flt(r.get("total_revenue")) for r in data)
	avg_on_time = sum(flt(r.get("on_time_percentage")) for r in data) / total_lines if total_lines else 0
	return [
		{"label": _("Total Shipping Lines"), "value": total_lines, "indicator": "blue"},
		{"label": _("Total Shipments"), "value": int(total_shipments), "indicator": "green"},
		{"label": _("Total Weight (kg)"), "value": f"{total_weight:,.2f}", "indicator": "blue"},
		{"label": _("Total Revenue"), "value": f"{total_revenue:,.2f}", "indicator": "green"},
		{"label": _("Avg On-Time %"), "value": f"{avg_on_time:.1f}%", "indicator": "green" if avg_on_time >= 90 else "orange" if avg_on_time >= 75 else "red"},
	]
