# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, getdate

INVOICE_REFERENCE_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


def execute(filters=None):
	filters = filters or {}
	reference_doctype = "Sales Invoice" if filters.get("party_type") == "Customer" else "Purchase Invoice"
	invoices = get_outstanding_invoices_for_party(
		reference_doctype,
		filters.get("party"),
		company=filters.get("company"),
		as_on_date=filters.get("as_on_date"),
	)

	columns = _columns(reference_doctype)
	data = _invoice_rows(invoices)
	report_summary = _summary(invoices)
	return columns, data, None, None, report_summary


def _columns(reference_doctype):
	return [
		{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": reference_doctype, "width": 140},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
	]


def _invoice_rows(rows):
	out = []
	for inv in rows:
		out.append(
			{
				"invoice": inv.get("name"),
				"posting_date": inv.get("posting_date"),
				"due_date": inv.get("due_date"),
				"outstanding_amount": flt(inv.get("outstanding_amount")),
				"currency": inv.get("currency"),
			}
		)
	return out


def _summary(invoices):
	total = sum(flt(r.get("outstanding_amount")) for r in invoices)
	return [
		{"label": _("Outstanding Invoices"), "value": len(invoices), "indicator": "blue"},
		{
			"label": _("Outstanding Balance"),
			"value": flt(total, 2),
			"datatype": "Currency",
			"indicator": "green",
		},
	]


def _party_column(reference_doctype):
	if reference_doctype == "Sales Invoice":
		return "customer", "customer_name"
	return "supplier", "supplier_name"


def get_outstanding_invoices_for_party(reference_doctype, party, company=None, as_on_date=None):
	"""Outstanding submitted invoices for a customer or supplier."""
	if reference_doctype not in INVOICE_REFERENCE_DOCTYPES or not party:
		return []

	party_field, party_name_field = _party_column(reference_doctype)
	where = [
		"docstatus = 1",
		"outstanding_amount > 0",
		f"`{party_field}` = %(party)s",
	]
	values = {"party": party}
	if company:
		where.append("company = %(company)s")
		values["company"] = company
	if as_on_date:
		where.append("posting_date <= %(as_on_date)s")
		values["as_on_date"] = getdate(as_on_date)

	return frappe.db.sql(
		"""
		SELECT
			name,
			posting_date,
			due_date,
			grand_total,
			outstanding_amount,
			currency,
			company,
			{party_field} AS party,
			{party_name_field} AS party_name
		FROM `tab{reference_doctype}`
		WHERE {where_sql}
		ORDER BY posting_date, name
		""".format(
			party_field=party_field,
			party_name_field=party_name_field,
			reference_doctype=reference_doctype,
			where_sql=" AND ".join(where),
		),
		values,
		as_dict=True,
	)
