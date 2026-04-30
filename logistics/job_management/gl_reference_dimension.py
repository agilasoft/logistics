# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Accounting Dimension fields for reference DocTypes (e.g. Job Number, Container) on GL / JE / invoice lines.

ERPNext adds Link fields when Accounting Dimension records exist for those document types.
"""

from __future__ import unicode_literals

import frappe


def _cache_key(document_type):
	return "logistics:ad_field:{0}".format(document_type)


def get_accounting_dimension_fieldname(document_type):
	"""Fieldname added to child tables / GL for the active dimension with this reference DocType."""
	if not document_type:
		return None

	def _load():
		row = frappe.db.sql(
			"""
			SELECT fieldname FROM `tabAccounting Dimension`
			WHERE disabled = 0 AND document_type = %s
			LIMIT 1
			""",
			(document_type,),
			as_dict=True,
		)
		if not row:
			return ""
		return (row[0].get("fieldname") or "").strip()

	val = frappe.cache().get_value(_cache_key(document_type), _load)
	return val if val else None


def reference_dimension_row_dict(target_doctype, reference_document_type, link_value):
	"""Return {fieldname: link_value} for target_doctype rows when dimension is configured."""
	if not link_value or not target_doctype or not reference_document_type:
		return {}
	fn = get_accounting_dimension_fieldname(reference_document_type)
	if not fn:
		return {}
	try:
		if not frappe.get_meta(target_doctype).get_field(fn):
			return {}
	except Exception:
		return {}
	return {fn: link_value}


def clear_reference_dimension_field_caches():
	for document_type in ("Job Number", "Container"):
		frappe.cache.delete_value(_cache_key(document_type))
