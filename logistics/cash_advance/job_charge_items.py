# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Resolve charge row Item codes for a Job Number (for Cash Advance liquidation lines)."""

from __future__ import unicode_literals

import json
from typing import Any, List, Optional

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


# Parent doctype field on Job Number → charges child table field name
_JOB_TYPE_CHARGES_FIELD = {
	"Air Booking": "charges",
	"Air Shipment": "charges",
	"Sea Booking": "charges",
	"Sea Shipment": "charges",
	"Transport Job": "charges",
	"Transport Order": "charges",
	"Warehouse Job": "charges",
	"Declaration": "charges",
	"Declaration Order": "charges",
	"General Job": "charges",
}


def _item_code_from_charge_row(charge) -> Optional[str]:
	return (
		getattr(charge, "item_code", None)
		or getattr(charge, "charge_item", None)
		or None
	)


def get_item_codes_for_job_number(job_number: Optional[str]) -> List[str]:
	"""Distinct Item codes from the operational job linked to this Job Number."""
	if not job_number or not frappe.db.exists("Job Number", job_number):
		return []

	jn = frappe.get_doc("Job Number", job_number)
	job_type, job_name = jn.job_type, jn.job_no
	if not job_type or not job_name or not frappe.db.exists(job_type, job_name):
		return []

	charges_field = _JOB_TYPE_CHARGES_FIELD.get(job_type)
	if not charges_field:
		return []

	job = frappe.get_doc(job_type, job_name)
	rows = job.get(charges_field) or []

	seen = set()
	out = []
	for ch in rows:
		code = _item_code_from_charge_row(ch)
		if code and code not in seen and frappe.db.exists("Item", code):
			seen.add(code)
			out.append(code)

	return out


@frappe.whitelist()
def get_charge_item_codes(job_number):
	"""Return list of Item names allowed on Cash Advance liquidation for this Job Number."""
	if not job_number:
		return []
	return get_item_codes_for_job_number(job_number)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs):
	"""Link search: Item restricted to charge rows on the Job Number's operational document."""
	_ = (as_dict, kwargs, doctype, searchfield)
	f = _parse_filters(filters)
	job_number = (f.get("job_number") or "").strip()
	start = cint(start)
	page_len = cint(page_len) or 20

	codes = get_item_codes_for_job_number(job_number) if job_number else []
	if not codes:
		return []

	in_clause = ", ".join(["%s"] * len(codes))
	params: List[Any] = list(codes)
	txt_filter = ""
	if txt:
		txt_filter = " AND (name LIKE %s OR item_name LIKE %s)"
		t = "%" + txt + "%"
		params.extend([t, t])
	params.extend([start, page_len])
	sql = """
		SELECT name, item_name
		FROM `tabItem`
		WHERE name IN ({in_clause}) AND disabled = 0{txt_filter}
		ORDER BY name ASC
		LIMIT %s, %s
	""".format(in_clause=in_clause, txt_filter=txt_filter)
	return frappe.db.sql(sql, tuple(params))
