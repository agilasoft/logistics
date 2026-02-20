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
		{"fieldname": "sea_shipment", "label": _("Sea Shipment"), "fieldtype": "Link", "options": "Sea Shipment", "width": 150},
		{"fieldname": "booking_date", "label": _("Booking Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "billing_status", "label": _("Billing Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "total_charges", "label": _("Total Charges"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Data", "width": 80},
		{"fieldname": "days_since_booking", "label": _("Days Since Booking"), "fieldtype": "Int", "width": 130},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 120},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	# Use COALESCE for billing_status in case column is missing in some envs
	data = frappe.db.sql("""
		SELECT
			ss.name as sea_shipment,
			ss.booking_date,
			ss.local_customer as customer,
			COALESCE(ss.billing_status, 'Not Billed') as billing_status,
			COALESCE(SUM(sfc.total_amount), 0) as total_charges,
			COALESCE(MAX(sfc.currency), 'USD') as currency,
			DATEDIFF(CURDATE(), ss.booking_date) as days_since_booking,
			ss.company
		FROM `tabSea Shipment` ss
		LEFT JOIN `tabSea Freight Charges` sfc ON sfc.parent = ss.name
		WHERE ss.docstatus = 1
		{conditions}
		GROUP BY ss.name
		ORDER BY ss.booking_date DESC, ss.name DESC
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
	if filters.get("customer"):
		conditions.append("ss.local_customer = %(customer)s")
	if filters.get("billing_status"):
		conditions.append("COALESCE(ss.billing_status, 'Not Billed') = %(billing_status)s")
	if filters.get("unbilled_only"):
		conditions.append("COALESCE(ss.billing_status, 'Not Billed') IN ('Not Billed', 'Pending')")
	if filters.get("overdue_days"):
		conditions.append("DATEDIFF(CURDATE(), ss.booking_date) > %(overdue_days)s")
		if not filters.get("unbilled_only"):
			conditions.append("COALESCE(ss.billing_status, 'Not Billed') IN ('Not Billed', 'Pending')")
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data):
	if not data:
		return None
	status_count = {"Not Billed": 0, "Pending": 0, "Billed": 0, "Partially Billed": 0, "Overdue": 0, "Cancelled": 0}
	for row in data:
		status = (row.get("billing_status") or "Not Billed").strip()
		status_count[status] = status_count.get(status, 0) + 1
	return {
		"data": {
			"labels": list(status_count.keys()),
			"datasets": [{"name": _("Billing Status"), "values": list(status_count.values())}]
		},
		"type": "pie",
		"colors": ["#7cd6fd", "#ffa00a", "#28a745", "#5e64ff", "#ff5858", "#743ee2"]
	}


def get_summary(data):
	if not data:
		return []
	total_shipments = len(data)
	total_charges = sum(flt(r.get("total_charges")) for r in data)
	billed_count = sum(1 for r in data if (r.get("billing_status") or "").strip() in ["Billed", "Partially Billed"])
	unbilled_count = total_shipments - billed_count
	overdue_count = sum(1 for r in data if flt(r.get("days_since_booking"), 0) > 30 and (r.get("billing_status") or "").strip() in ["Not Billed", "Pending"])
	return [
		{"label": _("Total Shipments"), "value": total_shipments, "indicator": "blue"},
		{"label": _("Total Charges"), "value": f"{total_charges:,.2f}", "indicator": "blue"},
		{"label": _("Billed Shipments"), "value": billed_count, "indicator": "green"},
		{"label": _("Unbilled Shipments"), "value": unbilled_count, "indicator": "orange"},
		{"label": _("Overdue (>30 days)"), "value": overdue_count, "indicator": "red"},
	]
