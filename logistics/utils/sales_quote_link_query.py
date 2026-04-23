# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Link search for Sales Quote: quotes that include charge lines for the requested service type (unified + legacy)."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.desk.reportview import get_match_cond
from frappe.utils import cint

from logistics.utils.sales_quote_service_eligibility import SERVICE_LEGACY_TABLE


def _ensure_sales_quote_columns_for_permissions() -> None:
	"""If DB is behind DocType (e.g. missing ``company``), ``get_match_cond`` can emit invalid SQL."""
	if not frappe.db.table_exists("Sales Quote") or not frappe.db.exists("DocType", "Sales Quote"):
		return
	try:
		if frappe.db.has_column("Sales Quote", "company"):
			return
	except frappe.db.TableMissingError:
		return

	frappe.db.updatedb("Sales Quote")
	frappe.client_cache.delete_value("table_columns::tabSales Quote")


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


def _has_sales_quote_routing_legs_sql() -> str:
	"""SQL fragment (references ``sq``): true if this Sales Quote has at least one routing leg row."""
	return """EXISTS (
		SELECT 1 FROM `tabSales Quote Routing Leg` rlx
		WHERE rlx.parent = sq.name AND rlx.parenttype = 'Sales Quote'
	)"""


def _corridor_match_sql_charges_header_legacy(service_type: str) -> str:
	"""SQL fragment — corridor via unified charges, legacy child rows, or header only (no routing legs table)."""
	st = (service_type or "").strip()
	co, cd = "%(corridor_origin)s", "%(corridor_dest)s"
	if st in ("Sea", "Air"):
		unified = f"""EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type = %(service_type)s
			AND IFNULL(sqc.origin_port,'') = {co}
			AND IFNULL(sqc.destination_port,'') = {cd}
		)"""
		child_dt = SERVICE_LEGACY_TABLE.get(st)
		legacy = ""
		if child_dt and frappe.db.table_exists(child_dt):
			legacy = f""" OR EXISTS (
				SELECT 1 FROM `tab{child_dt}` leg
				WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
				AND IFNULL(leg.origin_port,'') = {co}
				AND IFNULL(leg.destination_port,'') = {cd}
			)"""
		parent_ports = f""" OR (
			IFNULL(sq.origin_port,'') = {co} AND IFNULL(sq.destination_port,'') = {cd}
		)"""
		return f"({unified}{legacy}{parent_ports})"
	if st == "Transport":
		unified = f"""EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type = 'Transport'
			AND IFNULL(sqc.location_from,'') = {co}
			AND IFNULL(sqc.location_to,'') = {cd}
		)"""
		legacy = ""
		child_dt = SERVICE_LEGACY_TABLE.get("Transport")
		if child_dt and frappe.db.table_exists(child_dt):
			legacy = f""" OR EXISTS (
				SELECT 1 FROM `tab{child_dt}` leg
				WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
				AND IFNULL(leg.location_from,'') = {co}
				AND IFNULL(leg.location_to,'') = {cd}
			)"""
		parent_loc = f""" OR (
			IFNULL(sq.location_from,'') = {co} AND IFNULL(sq.location_to,'') = {cd}
		)"""
		return f"({unified}{legacy}{parent_loc})"
	return "(1=0)"


def _corridor_match_sql_routing_legs_only(service_type: str) -> str:
	"""SQL fragment — job O/D must match a Sales Quote Routing Leg (origin/destination + mode flags)."""
	st = (service_type or "").strip()
	co, cd = "%(corridor_origin)s", "%(corridor_dest)s"
	if st in ("Sea", "Air"):
		tm_flag = "IFNULL(tm.air, 0) = 1" if st == "Air" else "IFNULL(tm.sea, 0) = 1"
		return f"""EXISTS (
			SELECT 1 FROM `tabSales Quote Routing Leg` rl
			INNER JOIN `tabTransport Mode` tm ON tm.name = rl.mode
			WHERE rl.parent = sq.name AND rl.parenttype = 'Sales Quote'
			AND IFNULL(rl.origin,'') = {co}
			AND IFNULL(rl.destination,'') = {cd}
			AND {tm_flag}
		)"""
	if st == "Transport":
		return f"""EXISTS (
			SELECT 1 FROM `tabSales Quote Routing Leg` rl
			INNER JOIN `tabTransport Mode` tm ON tm.name = rl.mode
			WHERE rl.parent = sq.name AND rl.parenttype = 'Sales Quote'
			AND IFNULL(rl.origin,'') = {co}
			AND IFNULL(rl.destination,'') = {cd}
			AND IFNULL(tm.transport, 0) = 1
		)"""
	return "(1=0)"


def _customs_declaration_charge_match_sql() -> str:
	"""SQL fragment (references ``sq``): Customs quotes matching Declaration Order filters.

	Matches **Sales Quote Charge** (service_type Customs) OR **Sales Quote Customs** legacy rows:
	``customs_authority``, ``declaration_type``, and broker (charge row broker empty = wildcard).

	Legacy rows may carry ``transport_mode`` (Sea/Air/Road/Rail); when the job has a **Transport Mode**
	link set, legacy rows must match that mode (via ``Transport Mode`` flags) or have blank transport_mode.
	Unified charge rows have no transport mode and are not restricted by job transport mode.
	"""
	# job_transport_mode: NULL/empty = do not filter legacy rows by mode
	return """(
		EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type = 'Customs'
			AND TRIM(IFNULL(sqc.customs_authority,'')) = TRIM(IFNULL(%(customs_authority)s,''))
			AND TRIM(IFNULL(sqc.declaration_type,'')) = TRIM(IFNULL(%(declaration_type)s,''))
			AND (
				IFNULL(sqc.customs_broker,'') = ''
				OR TRIM(IFNULL(sqc.customs_broker,'')) = TRIM(IFNULL(%(customs_broker)s,''))
			)
		)
		OR EXISTS (
			SELECT 1 FROM `tabSales Quote Customs` leg
			WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
			AND TRIM(IFNULL(leg.customs_authority,'')) = TRIM(IFNULL(%(customs_authority)s,''))
			AND TRIM(IFNULL(leg.declaration_type,'')) = TRIM(IFNULL(%(declaration_type)s,''))
			AND (
				IFNULL(leg.customs_broker,'') = ''
				OR TRIM(IFNULL(leg.customs_broker,'')) = TRIM(IFNULL(%(customs_broker)s,''))
			)
			AND (
				%(job_transport_mode)s IS NULL OR TRIM(IFNULL(%(job_transport_mode)s,'')) = ''
				OR IFNULL(leg.transport_mode,'') = ''
				OR EXISTS (
					SELECT 1 FROM `tabTransport Mode` tm
					WHERE tm.name = %(job_transport_mode)s
					AND (
						(leg.transport_mode = 'Sea' AND IFNULL(tm.sea, 0) = 1)
						OR (leg.transport_mode = 'Air' AND IFNULL(tm.air, 0) = 1)
						OR (leg.transport_mode IN ('Road', 'Rail') AND IFNULL(tm.transport, 0) = 1)
					)
				)
			)
		)
	)"""


def sales_quote_matches_declaration_order_filters(
	sales_quote_name: str,
	customs_authority: str,
	declaration_type: str,
	customs_broker: str,
	job_transport_mode: str | None = None,
) -> bool:
	"""True if the Sales Quote has at least one Customs charge row matching Declaration Order scope."""
	ca = (customs_authority or "").strip()
	dt = (declaration_type or "").strip()
	cb = (customs_broker or "").strip()
	if not ca or not dt or not cb:
		return False
	jtm = (job_transport_mode or "").strip() or None
	match_sql = _customs_declaration_charge_match_sql()
	params = {
		"name": sales_quote_name,
		"customs_authority": ca,
		"declaration_type": dt,
		"customs_broker": cb,
		"job_transport_mode": jtm,
	}
	row = frappe.db.sql(
		f"""
		SELECT 1 FROM `tabSales Quote` sq
		WHERE sq.name = %(name)s
		AND {match_sql}
		LIMIT 1
		""",
		params,
	)
	return bool(row)


def _corridor_match_sql(service_type: str) -> str:
	"""SQL fragment (references ``sq``) — corridor match with routing precedence.

	If the quote has **Routing Legs**, the job origin/destination must match a leg (and transport mode).
	If it has **no** routing legs, matching uses unified charges, legacy rows, or header ports/locations only.
	"""
	st = (service_type or "").strip()
	if st not in ("Sea", "Air", "Transport"):
		return "(1=1)"
	has_legs = _has_sales_quote_routing_legs_sql()
	no_legs = f"(NOT {has_legs})"
	non_routing = _corridor_match_sql_charges_header_legacy(service_type)
	routing_only = _corridor_match_sql_routing_legs_only(service_type)
	return f"(({no_legs}) AND ({non_routing})) OR (({has_legs}) AND ({routing_only}))"


def sales_quote_matches_job_corridor(
	sales_quote_name: str,
	service_type: str,
	corridor_origin: str,
	corridor_dest: str,
) -> bool:
	"""True if the Sales Quote has at least one corridor match for Get Charges from Quotation (same rules as list filter)."""
	o = (corridor_origin or "").strip()
	d = (corridor_dest or "").strip()
	if not o or not d:
		return False
	st = (service_type or "").strip()
	if st not in SERVICE_LEGACY_TABLE:
		return False
	match_sql = _corridor_match_sql(st)
	params: dict[str, Any] = {
		"name": sales_quote_name,
		"service_type": st,
		"corridor_origin": o,
		"corridor_dest": d,
	}
	row = frappe.db.sql(
		f"""
		SELECT 1 FROM `tabSales Quote` sq
		WHERE sq.name = %(name)s
		AND {match_sql}
		LIMIT 1
		""",
		params,
	)
	return bool(row)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def sales_quote_by_service_link_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""Link query: Sales Quote eligible for a job type only if it has charge rows for that service (not main_service alone).

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

	eligibility = f"""( EXISTS (
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

	_ensure_sales_quote_columns_for_permissions()
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


def fetch_eligible_regular_sales_quote_names(
	service_type: str,
	customer: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	limit: int = 100,
	corridor_origin: str | None = None,
	corridor_dest: str | None = None,
	customs_authority: str | None = None,
	declaration_type: str | None = None,
	customs_broker: str | None = None,
	job_transport_mode: str | None = None,
) -> list[str]:
	"""Sales Quote names that have unified or legacy charge rows for ``service_type``.

	Returns **Regular** quotations only (Action → Get Charges from Quotation — excludes One-off and Project).
	Only **submitted** quotes (``docstatus`` = 1) are returned.

	When ``corridor_origin`` and ``corridor_dest`` are both non-empty, only quotes whose corridor
	matches: if the quote has **routing legs**, only a matching **routing leg** counts; otherwise
	unified charges, legacy child, or header fields (same as before).

	For **Customs**, when ``customs_authority``, ``declaration_type``, and ``customs_broker`` are all
	non-empty, **Declaration Order** filters apply instead of corridor matching (see
	``sales_quote_matches_declaration_order_filters``).
	"""
	service_type = (service_type or "").strip()
	if service_type not in SERVICE_LEGACY_TABLE:
		return []

	limit = cint(limit) or 100
	co = (corridor_origin or "").strip()
	cd = (corridor_dest or "").strip()
	use_corridor = bool(co and cd)
	ca = (customs_authority or "").strip()
	dt = (declaration_type or "").strip()
	cb = (customs_broker or "").strip()
	use_customs_filters = service_type == "Customs" and bool(ca and dt and cb)

	params: dict[str, Any] = {"service_type": service_type, "limit": limit}
	if use_customs_filters:
		jtm = (job_transport_mode or "").strip() or None
		params["customs_authority"] = ca
		params["declaration_type"] = dt
		params["customs_broker"] = cb
		params["job_transport_mode"] = jtm
		eligibility = _customs_declaration_charge_match_sql()
	elif use_corridor:
		params["corridor_origin"] = co
		params["corridor_dest"] = cd
		eligibility = _corridor_match_sql(service_type)
	else:
		legacy_sql = _legacy_exists_clause(service_type)
		eligibility = f"""( EXISTS (
				SELECT 1 FROM `tabSales Quote Charge` sqc
				WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
				AND sqc.service_type = %(service_type)s
			)
			{legacy_sql}
		)"""
	# Action → Get Charges from Quotation: **Regular** quotes only (excludes One-off, Project, blank).
	regular_only_where = "TRIM(IFNULL(sq.quotation_type,'')) = 'Regular'"

	customer_cond = ""
	if (customer or "").strip():
		params["customer"] = customer.strip()
		customer_cond = "AND TRIM(IFNULL(sq.customer,'')) = %(customer)s"

	_ensure_sales_quote_columns_for_permissions()
	match_cond = get_match_cond("Sales Quote")
	sql = f"""
		SELECT sq.name
		FROM `tabSales Quote` sq
		WHERE {eligibility}
		AND {regular_only_where}
		{customer_cond}
		AND IFNULL(sq.status,'') NOT IN ('Lost','Expired')
		AND (sq.valid_until IS NULL OR sq.valid_until >= CURDATE())
		AND sq.docstatus = 1
		{match_cond}
		ORDER BY sq.modified DESC
		LIMIT %(limit)s
	"""
	params["limit"] = limit
	rows = frappe.db.sql(sql, params)
	return [r[0] for r in rows] if rows else []
