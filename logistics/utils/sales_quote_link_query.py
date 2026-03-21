# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Link search for Sales Quote: allow quotes where main_service matches OR charges include the service type."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.desk.reportview import get_match_cond
from frappe.utils import cint

SERVICE_LEGACY_TABLE: dict[str, str] = {
	"Transport": "Sales Quote Transport",
	"Air": "Sales Quote Air Freight",
	"Sea": "Sales Quote Sea Freight",
	"Customs": "Sales Quote Customs",
	"Warehousing": "Sales Quote Warehouse",
}


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


def _excluded_one_off_sales_quotes(reference_doctype: str | None, reference_name: str | None) -> list[str]:
	if not reference_doctype:
		return []
	try:
		meta = frappe.get_meta(reference_doctype)
	except Exception:
		return []
	if not meta.has_field("sales_quote"):
		return []
	used = frappe.get_all(
		reference_doctype,
		filters={
			"sales_quote": ["is", "set"],
			"name": ["!=", reference_name or ""],
			"docstatus": ["!=", 2],
		},
		pluck="sales_quote",
	)
	if not used:
		return []
	one_off_used = frappe.get_all(
		"Sales Quote",
		filters={"name": ["in", list(set(used))], "quotation_type": "One-off"},
		pluck="name",
	)
	return list(one_off_used)


def _legacy_exists_clause(service_type: str) -> str:
	child_dt = SERVICE_LEGACY_TABLE.get(service_type)
	if not child_dt or not frappe.db.table_exists(child_dt):
		return ""
	tab = f"`tab{child_dt}`"
	return f"""OR EXISTS (
		SELECT 1 FROM {tab} leg
		WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
	)"""


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def sales_quote_by_service_link_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""Link query: Sales Quote eligible for a job type (main_service OR Sales Quote Charge / legacy row).

	filters (dict):
	- service_type (required): Transport | Air | Sea | Customs | Warehousing
	- reference_doctype, reference_name: exclude other docs' linked One-off quotes
	- customer: optional (e.g. Warehouse Contract)
	- dialog_one_off: if truthy, only quotation_type One-off and status not in Converted/Lost/Expired
	"""
	# as_dict / kwargs are passed by frappe.desk.search.search_widget — ignored here.
	_ = (as_dict, kwargs)
	f = _parse_filters(filters)
	service_type = (f.get("service_type") or "").strip()
	if service_type not in SERVICE_LEGACY_TABLE:
		return []

	start = cint(start)
	page_len = cint(page_len) or 20

	txt_cond = ""
	params: dict[str, Any] = {"service_type": service_type, "start": start, "page_len": page_len}
	if txt:
		params["txt"] = f"%{txt}%"
		txt_cond = "AND (sq.name LIKE %(txt)s OR IFNULL(sq.customer,'') LIKE %(txt)s)"

	legacy_sql = _legacy_exists_clause(service_type)

	eligibility = f"""( sq.main_service = %(service_type)s
		OR EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type = %(service_type)s
		)
		{legacy_sql}
	)"""

	if f.get("dialog_one_off"):
		one_off_where = """sq.quotation_type = 'One-off'
			AND IFNULL(sq.status,'') NOT IN ('Converted','Lost','Expired')
			AND (sq.valid_until IS NULL OR sq.valid_until >= CURDATE())"""
		excluded = []
	else:
		one_off_where = """(
			IFNULL(sq.quotation_type,'') != 'One-off'
			OR IFNULL(sq.status,'') != 'Converted'
		)"""
		excluded = _excluded_one_off_sales_quotes(
			(f.get("reference_doctype") or "").strip() or None,
			(f.get("reference_name") or "").strip() or None,
		)

	excluded_cond = ""
	if excluded:
		params["excluded"] = tuple(excluded)
		excluded_cond = "AND (IFNULL(sq.quotation_type,'') != 'One-off' OR sq.name NOT IN %(excluded)s)"

	customer_cond = ""
	customer = (f.get("customer") or "").strip()
	if customer:
		params["customer"] = customer
		customer_cond = "AND sq.customer = %(customer)s"

	if f.get("dialog_one_off"):
		where_block = f"{eligibility} AND {one_off_where}"
	else:
		where_block = f"{eligibility} AND {one_off_where} {excluded_cond}"

	match_cond = get_match_cond("Sales Quote")

	sql = f"""
		SELECT sq.name
		FROM `tabSales Quote` sq
		WHERE {where_block}
		{customer_cond}
		{txt_cond}
		{match_cond}
		ORDER BY sq.modified DESC
		LIMIT %(start)s, %(page_len)s
	"""

	return frappe.db.sql(sql, params)
