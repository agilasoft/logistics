# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Detect the site-specific accounting dimension field that links GL / JE rows to Item.

ERPNext adds a Link field to "Item" on GL Entry and Journal Entry Account when
an Accounting Dimension is configured for Item (label may be "Dimension Item" etc.).
"""

from __future__ import unicode_literals

import frappe


def get_item_link_fieldname(doctype):
	"""
	Return the fieldname of the first Link field pointing to DocType Item on `doctype`,
	or None if not present.
	"""
	if not doctype or not frappe.db.table_exists(doctype):
		return None

	def _find():
		for df in frappe.get_meta(doctype).fields:
			if getattr(df, "fieldtype", None) == "Link" and df.options == "Item":
				return df.fieldname
		return None

	cache_key = "logistics:item_dim_field:{0}".format(doctype)
	val = frappe.cache().get_value(cache_key, _find)
	return val or None


def item_row_dict(doctype, item_code):
	"""Return {fieldname: item_code} for use on GL Entry / Journal Entry Account rows."""
	if not item_code:
		return {}
	# Prefer the active Item Accounting Dimension field when present — JE Account / GL Entry
	# can have more than one Link to Item; the wrong one leaves profitability dimensions blank.
	if doctype in ("Journal Entry Account", "GL Entry"):
		fn_ad = get_item_accounting_dimension_fieldname()
		if fn_ad:
			try:
				if frappe.get_meta(doctype).get_field(fn_ad):
					return {fn_ad: item_code}
			except Exception:
				pass
	fn = get_item_link_fieldname(doctype)
	if not fn:
		return {}
	return {fn: item_code}


def clear_item_field_cache():
	"""Clear cached fieldnames (e.g. after Customize Form changes)."""
	for dt in ("GL Entry", "Journal Entry Account"):
		frappe.cache.delete_value("logistics:item_dim_field:{0}".format(dt))
	frappe.cache.delete_value("logistics:item_accounting_dimension_fieldname")
	frappe.cache.delete_value("logistics:item_accounting_dimension_row")


def on_accounting_dimension_changed(doc, method=None):
	"""Doc hook: refresh cached Item dimension fieldname when dimensions change."""
	clear_item_field_cache()
	try:
		from logistics.job_management.gl_reference_dimension import clear_reference_dimension_field_caches

		clear_reference_dimension_field_caches()
	except Exception:
		pass


def _get_item_accounting_dimension_row():
	"""Single cached row: Item accounting dimension fieldname + label (ERPNext)."""
	def _load():
		row = frappe.db.sql(
			"""
			SELECT fieldname, label FROM `tabAccounting Dimension`
			WHERE disabled = 0 AND document_type = 'Item'
			LIMIT 1
			""",
			as_dict=True,
		)
		return row[0] if row else {}

	return frappe.cache().get_value("logistics:item_accounting_dimension_row", _load)


def get_item_accounting_dimension_fieldname():
	"""
	Fieldname on invoice item rows / GL Entry for the active Accounting Dimension whose
	reference doctype is **Item** (same field is added to SI Item, PI Item, GL Entry, etc.).
	"""
	row = _get_item_accounting_dimension_row()
	fn = (row.get("fieldname") or "").strip()
	return fn or None


def get_item_accounting_dimension_label():
	"""UI label from Accounting Dimension (e.g. 'Item', 'Dimension Item'); None if not configured."""
	row = _get_item_accounting_dimension_row()
	lbl = (row.get("label") or "").strip()
	return lbl or None


def get_item_dimension_fieldname_on_gl_entry():
	"""
	Column on `tabGL Entry` that holds the Item **Accounting Dimension** value (what
	`get_gl_dict` posts). Prefer this over `get_item_link_fieldname`: GL Entry can have
	more than one Link to Item; the wrong field shows blank/mismatched profitability.
	"""
	fn = get_item_accounting_dimension_fieldname()
	if fn:
		try:
			if frappe.get_meta("GL Entry").get_field(fn):
				return fn
		except Exception:
			pass
	return get_item_link_fieldname("GL Entry")


def get_item_accounting_dimension_fieldname_on_child_doctype(child_doctype):
	"""Return Item dimension fieldname only if that field exists on the child doctype (e.g. Sales Invoice Item)."""
	fn = get_item_accounting_dimension_fieldname()
	if not fn or not child_doctype:
		return None
	try:
		if not frappe.get_meta(child_doctype).get_field(fn):
			return None
	except Exception:
		return None
	return fn
