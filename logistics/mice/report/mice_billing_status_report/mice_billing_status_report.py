# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "exhibit", "label": _("MICE Project"), "fieldtype": "Link", "options": "MICE Project", "width": 160},
		{"fieldname": "organizer", "label": _("Organizer"), "fieldtype": "Link", "options": "MICE Organizer", "width": 160},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "billing_status", "label": _("Billing Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "lifecycle_stage", "label": _("Lifecycle Stage"), "fieldtype": "Data", "width": 100},
		{"fieldname": "billing_lines", "label": _("Billing Lines"), "fieldtype": "Int", "width": 90},
		{"fieldname": "invoiced_lines", "label": _("Invoiced"), "fieldtype": "Int", "width": 80},
	]
	rows = frappe.db.sql(
		*_query(filters),
		as_dict=1,
	)
	wanted = (filters.get("billing_status") or "").strip()
	data = []
	for row in rows:
		status = classify_project_billing_status(
			row.get("line_count"),
			row.get("pending_count"),
			row.get("invoiced_count"),
			row.get("paid_count"),
			row.get("cancelled_count"),
		)
		if wanted and status != wanted:
			continue
		data.append(
			{
				"exhibit": row.get("exhibit"),
				"organizer": row.get("organizer"),
				"customer": row.get("customer"),
				"billing_status": status,
				"lifecycle_stage": row.get("lifecycle_stage"),
				"billing_lines": _count(row.get("line_count")),
				"invoiced_lines": _count(row.get("invoiced_count")),
			}
		)
	return columns, data


def classify_project_billing_status(
	line_count=0,
	pending_count=0,
	invoiced_count=0,
	paid_count=0,
	cancelled_count=0,
):
	"""Roll MICE Project Billing rows up to one project status.

	Child statuses are Pending, Invoiced, Paid, and Cancelled. Invoiced maps to
	Billed so the result matches the report filter. Blank child status is counted
	as Pending by the query before it reaches this function.
	"""
	total = _count(line_count)
	pending = _count(pending_count)
	invoiced = _count(invoiced_count)
	paid = _count(paid_count)
	cancelled = _count(cancelled_count)
	active = total - cancelled
	if total <= 0:
		return "Not Billed"
	if active <= 0:
		return "Cancelled"
	if paid == active:
		return "Paid"
	if pending == 0 and invoiced + paid == active:
		return "Billed"
	if invoiced + paid == 0:
		return "Pending"
	return "Partially Billed"


def _query(filters):
	conditions = ["ep.docstatus < 2"]
	values = {}
	if filters.get("organizer"):
		conditions.append("ep.organizer = %(organizer)s")
		values["organizer"] = filters["organizer"]
	if filters.get("customer"):
		conditions.append("org.customer = %(customer)s")
		values["customer"] = filters["customer"]
	where = " AND ".join(conditions)
	sql = f"""
		SELECT
			ep.name AS exhibit,
			ep.organizer,
			org.customer AS customer,
			ep.lifecycle_stage,
			IFNULL(bill.line_count, 0) AS line_count,
			IFNULL(bill.pending_count, 0) AS pending_count,
			IFNULL(bill.invoiced_count, 0) AS invoiced_count,
			IFNULL(bill.paid_count, 0) AS paid_count,
			IFNULL(bill.cancelled_count, 0) AS cancelled_count
		FROM `tabMICE Project` ep
		LEFT JOIN `tabMICE Organizer` org ON org.name = ep.organizer
		LEFT JOIN (
			SELECT
				b.parent AS parent,
				COUNT(*) AS line_count,
				SUM(CASE WHEN IFNULL(b.status, '') IN ('', 'Pending') THEN 1 ELSE 0 END) AS pending_count,
				SUM(CASE WHEN b.status = 'Invoiced' THEN 1 ELSE 0 END) AS invoiced_count,
				SUM(CASE WHEN b.status = 'Paid' THEN 1 ELSE 0 END) AS paid_count,
				SUM(CASE WHEN b.status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_count
			FROM `tabMICE Project Billing` b
			GROUP BY b.parent
		) bill ON bill.parent = ep.name
		WHERE {where}
		ORDER BY ep.modified DESC
	"""
	return sql, values


def _count(value):
	return int(value or 0)
