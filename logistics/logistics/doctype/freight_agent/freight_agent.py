# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from logistics.utils.party_code import maybe_set_party_code
from logistics.utils.service_mode_flags import MODULE_FLAG_FIELDS


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


class FreightAgent(Document):
	def validate(self):
		maybe_set_party_code(
			self,
			name_field="freight_agent_name",
			unloco_field="default_unloco",
			code_fieldname="code",
		)
		self.validate_applicable_service_types()

	def validate_applicable_service_types(self):
		if any(getattr(self, field, 0) for field in MODULE_FLAG_FIELDS):
			return
		frappe.throw(
			_("Select at least one Applicable Service Type (Air, Sea, Transport, Customs, or Warehousing)."),
			title=_("Applicable Service Types Required"),
		)
		self._validate_covered_unlocs()

	def _validate_covered_unlocs(self) -> None:
		seen: set[str] = set()
		for row in self.covered_unlocs or []:
			unloco = (row.unloco or "").strip()
			if not unloco:
				continue
			if unloco in seen:
				frappe.throw(
					_("UNLOCO {0} is listed more than once in Covered UNLOCOs.").format(unloco)
				)
			seen.add(unloco)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def freight_agent_by_unloco_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""Restrict Freight Agent to those covering the given UNLOCO."""
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
		txt_cond = (
			" AND (fa.name LIKE %(txt)s OR fa.freight_agent_name LIKE %(txt)s OR fa.code LIKE %(txt)s)"
		)
	sql = f"""
		SELECT DISTINCT fa.name, fa.freight_agent_name
		FROM `tabFreight Agent` fa
		LEFT JOIN `tabFreight Agent Covered Location` loc
			ON loc.parent = fa.name
			AND loc.parenttype = 'Freight Agent'
			AND loc.parentfield = 'covered_unlocs'
			AND loc.unloco = %(unloco)s
		WHERE fa.is_active = 1
		AND (loc.unloco = %(unloco)s OR fa.default_unloco = %(unloco)s)
		{txt_cond}
		ORDER BY fa.freight_agent_name ASC, fa.name ASC
		LIMIT %(start)s, %(page_len)s
	"""
	return frappe.db.sql(sql, p)
