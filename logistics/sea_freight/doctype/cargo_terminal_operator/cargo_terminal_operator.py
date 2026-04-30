# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
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


class CargoTerminalOperator(Document):
	def validate(self) -> None:
		seen: set[str] = set()
		for row in self.served_unlocs or []:
			u = (row.unloco or "").strip()
			if not u:
				continue
			if u in seen:
				frappe.throw(_("UNLOCO {0} is listed more than once in Served UNLOCOs.").format(u))
			seen.add(u)
		if cint(self.sea) and not seen:
			frappe.throw(
				_("For Sea mode, add at least one UNLOCO in Served UNLOCOs (or uncheck Sea).")
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def cargo_terminal_operator_by_unloco_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""Restrict Cargo Terminal Operator to those serving the given UNLOCO and sea-enabled."""
	_ = (as_dict, kwargs, searchfield, doctype)
	f = _parse_filters(filters)
	unloco = (f.get("unloco") or "").strip()
	start = cint(start)
	page_len = cint(page_len) or 20
	txt_like = f"%{txt}%" if txt else None
	if not unloco:
		return []

	p = {
		"unloco": unloco,
		"start": start,
		"page_len": page_len,
	}
	txt_cond = ""
	if txt_like:
		p["txt"] = txt_like
		txt_cond = " AND (cto.name LIKE %(txt)s OR cto.cto_name LIKE %(txt)s OR cto.code LIKE %(txt)s)"
	sql = f"""
		SELECT DISTINCT cto.name, cto.cto_name
		FROM `tabCargo Terminal Operator` cto
		INNER JOIN `tabCTO Unloco` u ON u.parent = cto.name
			AND u.parenttype = 'Cargo Terminal Operator' AND u.parentfield = 'served_unlocs'
		WHERE u.unloco = %(unloco)s
		AND cto.is_active = 1 AND cto.sea = 1
		{txt_cond}
		ORDER BY cto.cto_name ASC, cto.name ASC
		LIMIT %(start)s, %(page_len)s
	"""
	return frappe.db.sql(sql, p)
