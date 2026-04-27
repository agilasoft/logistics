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


class ShippingLine(Document):
	def validate(self) -> None:
		cto_unlocs: dict[str, set[str]] = {}
		for row in self.ctos or []:
			port = (row.port or "").strip()
			cto = (row.sea_cto or "").strip()
			if not port or not cto:
				continue
			if cto not in cto_unlocs:
				doc = frappe.get_doc("Cargo Terminal Operator", cto)
				cto_unlocs[cto] = {
					(r.unloco or "").strip() for r in (doc.served_unlocs or []) if (r.unloco or "").strip()
				}
			if port not in cto_unlocs[cto]:
				frappe.throw(
					_(
						"Sea CTO {0} is not defined for port {1} on that operator's Served UNLOCOs."
					).format(cto, port)
				)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def shipping_line_cto_by_line_and_port_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""List Cargo Terminal Operator names that appear in Shipping Line CTO for a line + port."""
	_ = (as_dict, kwargs, searchfield, doctype)
	f = _parse_filters(filters)
	shipping_line = (f.get("shipping_line") or "").strip()
	port = (f.get("port") or "").strip()
	start = cint(start)
	page_len = cint(page_len) or 20
	txt_like = f"%{txt}%" if txt else None
	if not shipping_line or not port:
		return []

	p = {
		"sl": shipping_line,
		"port": port,
		"start": start,
		"page_len": page_len,
	}
	txt_cond = ""
	if txt_like:
		p["txt"] = txt_like
		txt_cond = " AND (cto.name LIKE %(txt)s OR cto.cto_name LIKE %(txt)s OR cto.code LIKE %(txt)s)"
	sql = f"""
		SELECT DISTINCT cto.name, cto.cto_name
		FROM `tabShipping Line CTO` slc
		INNER JOIN `tabCargo Terminal Operator` cto ON cto.name = slc.sea_cto
		WHERE slc.parent = %(sl)s
		AND slc.port = %(port)s
		AND cto.is_active = 1 AND cto.sea = 1
		{txt_cond}
		ORDER BY cto.cto_name ASC, cto.name ASC
		LIMIT %(start)s, %(page_len)s
	"""
	return frappe.db.sql(sql, p)


@frappe.whitelist()
def get_shipping_line_cto_names(
	shipping_line: str | None = None, port: str | None = None, leg: str | None = None
) -> list[str]:
	"""Return sea CTO names configured for a shipping line and UNLOCO port. ``leg`` reserved for future direction filter."""
	_ = leg
	sl = (shipping_line or "").strip()
	prt = (port or "").strip()
	if not sl or not prt:
		return []
	return frappe.db.sql_list(
		"""
		SELECT slc.sea_cto
		FROM `tabShipping Line CTO` slc
		INNER JOIN `tabCargo Terminal Operator` cto ON cto.name = slc.sea_cto
		WHERE slc.parent = %s
		AND slc.port = %s
		AND cto.is_active = 1 AND cto.sea = 1
		AND IFNULL(slc.sea_cto, '') != ''
		GROUP BY slc.sea_cto, cto.cto_name
		ORDER BY cto.cto_name ASC, slc.sea_cto ASC
		""",
		(sl, prt),
	)

