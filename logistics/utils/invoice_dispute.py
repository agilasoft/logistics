# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

"""
Invoice dispute tracking: block payments while Open/Under Review, SOA sections, reporting.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, getdate

ACTIVE_DISPUTE_STATUSES = ("Open", "Under Review")
RESOLVED_DISPUTE_STATUSES = ("Resolved", "Closed")
INVOICE_REFERENCE_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


def get_active_dispute_for_invoice(reference_doctype, reference_name, exclude_name=None):
	if reference_doctype not in INVOICE_REFERENCE_DOCTYPES or not reference_name:
		return None

	filters = {
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"status": ("in", list(ACTIVE_DISPUTE_STATUSES)),
	}
	if exclude_name:
		filters["name"] = ("!=", exclude_name)

	name = frappe.db.get_value("Dispute", filters, "name", order_by="creation desc")
	if not name:
		return None
	return frappe.get_doc("Dispute", name)


def invoice_has_active_dispute(reference_doctype, reference_name):
	return bool(get_active_dispute_for_invoice(reference_doctype, reference_name))


def get_dispute_map(reference_doctype, invoice_names):
	"""Return {invoice_name: dispute_row_dict} for active disputes on the given invoices."""
	if not invoice_names or reference_doctype not in INVOICE_REFERENCE_DOCTYPES:
		return {}

	rows = frappe.get_all(
		"Dispute",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": ("in", invoice_names),
			"status": ("in", list(ACTIVE_DISPUTE_STATUSES)),
		},
		fields=[
			"name",
			"reference_name",
			"status",
			"dispute_reason",
			"remarks",
			"dispute_date",
		],
		order_by="creation desc",
	)
	out = {}
	for row in rows:
		inv = row.reference_name
		if inv not in out:
			out[inv] = row
	return out


def validate_payment_entry_against_disputes(doc, method=None):
	"""Block Payment Entry allocations to invoices with active disputes."""
	for ref in doc.get("references") or []:
		if ref.reference_doctype not in INVOICE_REFERENCE_DOCTYPES or not ref.reference_name:
			continue
		dispute = get_active_dispute_for_invoice(ref.reference_doctype, ref.reference_name)
		if dispute:
			frappe.throw(
				_(
					"Cannot allocate payment to {0} {1}. Active dispute {2} ({3}). "
					"Mark the dispute as Resolved or Closed before paying this invoice."
				).format(
					ref.reference_doctype,
					ref.reference_name,
					dispute.name,
					dispute.status,
				),
				title=_("Invoice Under Dispute"),
			)


def validate_settlement_entry_against_disputes(doc, method=None):
	"""Block Settlement Entry references to disputed invoices."""
	for ref in doc.get("references") or []:
		if ref.reference_doctype not in INVOICE_REFERENCE_DOCTYPES or not ref.reference_name:
			continue
		dispute = get_active_dispute_for_invoice(ref.reference_doctype, ref.reference_name)
		if dispute:
			frappe.throw(
				_(
					"Cannot include {0} {1} in settlement. Active dispute {2} ({3})."
				).format(
					ref.reference_doctype,
					ref.reference_name,
					dispute.name,
					dispute.status,
				),
				title=_("Invoice Under Dispute"),
			)


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

	rows = frappe.db.sql(
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
	return rows


def partition_invoices_by_dispute(reference_doctype, invoices):
	"""Split invoice rows into (regular, disputed) using active disputes."""
	names = [r.get("name") for r in invoices if r.get("name")]
	dispute_map = get_dispute_map(reference_doctype, names)
	regular, disputed = [], []
	for inv in invoices:
		name = inv.get("name")
		d = dispute_map.get(name)
		if d:
			row = dict(inv)
			row["dispute"] = d.name
			row["dispute_status"] = d.status
			row["dispute_reason"] = d.dispute_reason
			row["dispute_remarks"] = _plain_remarks(d.remarks)
			disputed.append(row)
		else:
			regular.append(inv)
	return regular, disputed


def _plain_remarks(html):
	if not html:
		return ""
	from frappe.utils import strip_html

	return strip_html(html)[:500]


def query_disputed_invoices(filters=None):
	"""Rows for Disputed Invoices / AR-AP dispute report."""
	f = frappe._dict(filters or {})
	conditions = ["d.reference_doctype = %(reference_doctype)s"]
	values = {"reference_doctype": f.get("reference_doctype") or "Sales Invoice"}

	if f.get("company"):
		conditions.append("d.company = %(company)s")
		values["company"] = f.company
	if f.get("party"):
		conditions.append("d.party = %(party)s")
		values["party"] = f.party
	if f.get("status"):
		conditions.append("d.status = %(status)s")
		values["status"] = f.status
	else:
		conditions.append("d.status IN %(statuses)s")
		values["statuses"] = list(ACTIVE_DISPUTE_STATUSES + RESOLVED_DISPUTE_STATUSES)

	if f.get("dispute_only"):
		conditions.append("d.status IN %(active_statuses)s")
		values["active_statuses"] = list(ACTIVE_DISPUTE_STATUSES)

	inv_table = f.get("reference_doctype") or "Sales Invoice"

	rows = frappe.db.sql(
		"""
		SELECT
			d.name AS dispute,
			d.status AS dispute_status,
			d.dispute_reason,
			d.dispute_date,
			d.resolution_date,
			d.party,
			d.company,
			d.reference_name AS invoice,
			inv.posting_date,
			inv.due_date,
			inv.outstanding_amount,
			inv.grand_total,
			inv.currency
		FROM `tabDispute` d
		INNER JOIN `tab{inv_table}` inv ON inv.name = d.reference_name
		WHERE {where_sql}
			AND inv.docstatus = 1
			AND IFNULL(inv.outstanding_amount, 0) > 0
		ORDER BY d.dispute_date DESC, d.name DESC
		""".format(inv_table=inv_table, where_sql=" AND ".join(conditions)),
		values,
		as_dict=True,
	)
	return rows


def merge_invoice_dispute_hooks(doc_events):
	def _append(doctype, event, handler):
		cur = doc_events.setdefault(doctype, {}).get(event)
		if cur is None:
			doc_events[doctype][event] = handler
		elif isinstance(cur, list):
			if handler not in cur:
				doc_events[doctype][event] = cur + [handler]
		elif cur != handler:
			doc_events[doctype][event] = [cur, handler]

	_append(
		"Payment Entry",
		"validate",
		"logistics.utils.invoice_dispute.validate_payment_entry_against_disputes",
	)
	_append(
		"Settlement Entry",
		"validate",
		"logistics.utils.invoice_dispute.validate_settlement_entry_against_disputes",
	)
