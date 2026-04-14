# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Rep / Operations Rep / Customer Service Rep — shared with Sales Quote (Employee links)."""

import frappe

REP_FIELD_NAMES = ("sales_rep", "operations_rep", "customer_service_rep")


def _resolve_sales_quote_name_from_doc(source_doc):
	if not source_doc:
		return None
	sq = getattr(source_doc, "sales_quote", None)
	if sq and frappe.db.exists("Sales Quote", sq):
		return sq
	q = getattr(source_doc, "quote", None)
	if q and frappe.db.exists("Sales Quote", q):
		return q
	return None


def copy_operational_rep_fields_from_sales_quote_doc(target_doc, sales_quote_doc):
	"""Set all rep fields on target from a Sales Quote document (typically at create-from-quote time)."""
	if not sales_quote_doc:
		return
	for fn in REP_FIELD_NAMES:
		if hasattr(target_doc, fn):
			setattr(target_doc, fn, getattr(sales_quote_doc, fn, None))


def copy_operational_rep_fields_from_declaration_order(target_doc, declaration_order_doc):
	"""Set all rep fields on target from a Declaration Order (e.g. Declaration create-from-order)."""
	if not declaration_order_doc:
		return
	for fn in REP_FIELD_NAMES:
		if hasattr(target_doc, fn):
			setattr(target_doc, fn, getattr(declaration_order_doc, fn, None))


def copy_operational_rep_fields_from_chain(target_doc, source_doc=None, *, sales_quote_doc=None):
	"""Prefer values on source_doc; fill any blanks from linked Sales Quote on source or explicit sales_quote_doc."""
	if sales_quote_doc is not None:
		for fn in REP_FIELD_NAMES:
			if hasattr(target_doc, fn):
				setattr(target_doc, fn, getattr(sales_quote_doc, fn, None))
		return

	if source_doc is not None:
		for fn in REP_FIELD_NAMES:
			if hasattr(target_doc, fn):
				v = getattr(source_doc, fn, None)
				if v:
					setattr(target_doc, fn, v)

	sqn = _resolve_sales_quote_name_from_doc(source_doc) if source_doc is not None else None
	if not sqn:
		return
	try:
		sq = frappe.get_cached_doc("Sales Quote", sqn)
	except Exception:
		return
	for fn in REP_FIELD_NAMES:
		if not hasattr(target_doc, fn):
			continue
		if not getattr(target_doc, fn, None):
			setattr(target_doc, fn, getattr(sq, fn, None))
