# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import flt

from logistics.utils.invoice_dispute import query_disputed_invoices


def execute(filters=None):
	filters = filters or {}
	if filters.get("active_only"):
		filters = dict(filters)
		filters["dispute_only"] = 1

	reference_doctype = filters.get("reference_doctype") or "Sales Invoice"
	party_type = filters.get("party_type") or (
		"Customer" if reference_doctype == "Sales Invoice" else "Supplier"
	)
	rows = query_disputed_invoices(filters)
	columns = _columns(reference_doctype, party_type)
	data = []
	for row in rows:
		data.append(
			{
				"dispute": row.dispute,
				"invoice": row.invoice,
				"party": row.party,
				"party_type": party_type,
				"company": row.company,
				"posting_date": row.posting_date,
				"due_date": row.due_date,
				"outstanding_amount": flt(row.outstanding_amount),
				"grand_total": flt(row.grand_total),
				"currency": row.currency,
				"dispute_status": row.dispute_status,
				"dispute_reason": row.dispute_reason,
				"dispute_date": row.dispute_date,
				"resolution_date": row.resolution_date,
			}
		)

	total_outstanding = sum(flt(r.get("outstanding_amount")) for r in data)
	summary = [
		{"label": _("Invoices"), "value": len(data), "indicator": "blue"},
		{
			"label": _("Outstanding (Disputed)"),
			"value": flt(total_outstanding, 2),
			"datatype": "Currency",
			"indicator": "orange",
		},
	]
	return columns, data, None, None, summary


def _columns(reference_doctype, party_type):
	return [
		{"label": _("Dispute"), "fieldname": "dispute", "fieldtype": "Link", "options": "Dispute", "width": 120},
		{
			"label": _("Invoice"),
			"fieldname": "invoice",
			"fieldtype": "Link",
			"options": reference_doctype,
			"width": 140,
		},
		{"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Data", "hidden": 1},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Dynamic Link", "options": "party_type", "width": 140},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 110},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Dispute Status"), "fieldname": "dispute_status", "fieldtype": "Data", "width": 110},
		{"label": _("Reason"), "fieldname": "dispute_reason", "fieldtype": "Data", "width": 140},
		{"label": _("Dispute Date"), "fieldname": "dispute_date", "fieldtype": "Date", "width": 100},
		{"label": _("Resolution Date"), "fieldname": "resolution_date", "fieldtype": "Date", "width": 110},
	]
