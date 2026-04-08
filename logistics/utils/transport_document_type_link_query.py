# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Link search for Transport Document Type filtered by allowed Transport Mode (Table MultiSelect)."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import cint


def _parse_filters(filters: Any) -> dict:
	if filters is None:
		return {}
	if isinstance(filters, str):
		try:
			return json.loads(filters)
		except Exception:
			return {}
	if isinstance(filters, dict):
		return dict(filters)
	return {}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def transport_document_type_by_mode_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""filters: optional transport_mode (Transport Mode name). If empty, all types are searchable."""
	_ = (as_dict, kwargs)
	f = _parse_filters(filters)
	transport_mode = (f.get("transport_mode") or "").strip()
	start = cint(start)
	page_len = cint(page_len) or 20
	txt_like = f"%{txt}%" if txt else None

	if transport_mode:
		params: dict[str, Any] = {
			"transport_mode": transport_mode,
			"start": start,
			"page_len": page_len,
		}
		txt_cond = ""
		if txt_like:
			params["txt"] = txt_like
			txt_cond = " AND (tdt.name LIKE %(txt)s OR tdt.document_type_name LIKE %(txt)s)"
		sql = f"""
			SELECT DISTINCT tdt.name, tdt.document_type_name
			FROM `tabTransport Document Type` tdt
			INNER JOIN `tabTransport Document Type Transport Mode` m
				ON m.parent = tdt.name AND m.parenttype = 'Transport Document Type'
			WHERE m.transport_mode = %(transport_mode)s
			{txt_cond}
			ORDER BY tdt.document_type_name ASC
			LIMIT %(start)s, %(page_len)s
		"""
		return frappe.db.sql(sql, params)

	params2: dict[str, Any] = {"start": start, "page_len": page_len}
	txt_cond = ""
	if txt_like:
		params2["txt"] = txt_like
		txt_cond = " WHERE (name LIKE %(txt)s OR document_type_name LIKE %(txt)s)"
	sql = f"""
		SELECT name, document_type_name
		FROM `tabTransport Document Type`
		{txt_cond}
		ORDER BY document_type_name ASC
		LIMIT %(start)s, %(page_len)s
	"""
	return frappe.db.sql(sql, params2)
