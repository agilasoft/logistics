# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import flt

from logistics.utils.invoice_dispute import (
	get_outstanding_invoices_for_party,
	partition_invoices_by_dispute,
)


def execute(filters=None):
	filters = filters or {}
	reference_doctype = "Sales Invoice" if filters.get("party_type") == "Customer" else "Purchase Invoice"
	invoices = get_outstanding_invoices_for_party(
		reference_doctype,
		filters.get("party"),
		company=filters.get("company"),
		as_on_date=filters.get("as_on_date"),
	)
	regular, disputed = partition_invoices_by_dispute(reference_doctype, invoices)

	columns = _columns(reference_doctype)
	data = []
	data.extend(_section_header(_("Outstanding Invoices")))
	data.extend(_invoice_rows(regular))
	data.append({})
	data.extend(_section_header(_("Disputed Invoices")))
	data.extend(_invoice_rows(disputed, include_dispute=True))

	report_summary = _summary(regular, disputed)
	return columns, data, None, None, report_summary


def _columns(reference_doctype):
	return [
		{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": reference_doctype, "width": 140},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		{"label": _("Dispute"), "fieldname": "dispute", "fieldtype": "Link", "options": "Dispute", "width": 120},
		{"label": _("Dispute Status"), "fieldname": "dispute_status", "fieldtype": "Data", "width": 110},
		{"label": _("Remarks"), "fieldname": "dispute_remarks", "fieldtype": "Data", "width": 220},
	]


def _section_header(label):
	return [{"invoice": label, "bold": 1}]


def _invoice_rows(rows, include_dispute=False):
	out = []
	for inv in rows:
		row = {
			"invoice": inv.get("name"),
			"posting_date": inv.get("posting_date"),
			"due_date": inv.get("due_date"),
			"outstanding_amount": flt(inv.get("outstanding_amount")),
			"currency": inv.get("currency"),
		}
		if include_dispute:
			row["dispute"] = inv.get("dispute")
			row["dispute_status"] = inv.get("dispute_status")
			row["dispute_remarks"] = inv.get("dispute_remarks")
		out.append(row)
	return out


def _summary(regular, disputed):
	reg_total = sum(flt(r.get("outstanding_amount")) for r in regular)
	disp_total = sum(flt(r.get("outstanding_amount")) for r in disputed)
	return [
		{"label": _("Outstanding Invoices"), "value": len(regular), "indicator": "blue"},
		{
			"label": _("Outstanding Balance"),
			"value": flt(reg_total, 2),
			"datatype": "Currency",
			"indicator": "green",
		},
		{"label": _("Disputed Invoices"), "value": len(disputed), "indicator": "orange"},
		{
			"label": _("Disputed Balance"),
			"value": flt(disp_total, 2),
			"datatype": "Currency",
			"indicator": "red",
		},
	]
