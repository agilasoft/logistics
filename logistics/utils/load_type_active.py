# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint

_DOCTYPE_HAS_LOAD_TYPE_CACHE = {}


def _meta_has_load_type_reference(meta):
	for df in meta.fields:
		if df.fieldtype == "Link" and df.options == "Load Type":
			return True
		if df.fieldtype == "Table":
			try:
				cm = frappe.get_meta(df.options)
			except Exception:
				continue
			for cdf in cm.fields:
				if cdf.fieldtype == "Link" and cdf.options == "Load Type":
					return True
	return False


def doctype_references_load_type(doctype):
	if doctype in _DOCTYPE_HAS_LOAD_TYPE_CACHE:
		return _DOCTYPE_HAS_LOAD_TYPE_CACHE[doctype]
	try:
		meta = frappe.get_meta(doctype)
	except Exception:
		_DOCTYPE_HAS_LOAD_TYPE_CACHE[doctype] = False
		return False
	out = _meta_has_load_type_reference(meta)
	_DOCTYPE_HAS_LOAD_TYPE_CACHE[doctype] = out
	return out


def validate_load_type_links_on_doc(doc, method=None):
	if getattr(frappe.flags, "in_install", None) or getattr(frappe.flags, "in_migrate", None):
		return
	if getattr(frappe.flags, "in_import", None):
		return
	if not doctype_references_load_type(doc.doctype):
		return
	prev = doc.get_doc_before_save() if not doc.is_new() else None
	_validate_parent_load_type_links(doc, prev)
	_validate_child_table_load_type_links(doc, prev)


def _validate_parent_load_type_links(doc, prev):
	meta = frappe.get_meta(doc.doctype)
	for df in meta.fields:
		if df.fieldtype != "Link" or df.options != "Load Type":
			continue
		val = doc.get(df.fieldname)
		if not val:
			continue
		if _load_type_is_active(val):
			continue
		old_val = prev.get(df.fieldname) if prev else None
		if prev and old_val == val:
			continue
		frappe.throw(
			_(
				"Load Type {0} is inactive. Choose an active Load Type or set Is Active on that Load Type master."
			).format(frappe.bold(val)),
			title=_("Inactive Load Type"),
		)


def _validate_child_table_load_type_links(doc, prev):
	meta = frappe.get_meta(doc.doctype)
	prev_by_name = {}
	if prev:
		for df in meta.fields:
			if df.fieldtype != "Table":
				continue
			for row in prev.get(df.fieldname) or []:
				if row.name:
					prev_by_name[(df.fieldname, row.name)] = row

	for df in meta.fields:
		if df.fieldtype != "Table":
			continue
		child_meta = frappe.get_meta(df.options)
		link_fields = [cdf for cdf in child_meta.fields if cdf.fieldtype == "Link" and cdf.options == "Load Type"]
		if not link_fields:
			continue
		table_label = df.label or df.fieldname
		for row in doc.get(df.fieldname) or []:
			pr = prev_by_name.get((df.fieldname, row.name)) if row.name else None
			for lf in link_fields:
				val = row.get(lf.fieldname)
				if not val:
					continue
				if _load_type_is_active(val):
					continue
				old_val = pr.get(lf.fieldname) if pr else None
				if pr and old_val == val:
					continue
				frappe.throw(
					_(
						"Load Type {0} is inactive ({1} row {2}). Choose an active Load Type or set Is Active on that Load Type master."
					).format(frappe.bold(val), table_label, row.idx),
					title=_("Inactive Load Type"),
				)


def _load_type_is_active(load_type_name):
	if not frappe.db.exists("Load Type", load_type_name):
		return True
	v = frappe.db.get_value("Load Type", load_type_name, "is_active")
	if v is None:
		return True
	return cint(v) == 1
