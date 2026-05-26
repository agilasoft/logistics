# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Link search for Sales Quote: quotes that include charge lines for the requested service type (unified + legacy)."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.utils import cint

from logistics.utils.charge_service_type import (
	canonical_charge_service_type_for_storage,
	iter_sales_quote_charge_service_type_db_values_for_canonical,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.sales_quote_service_eligibility import SERVICE_LEGACY_TABLE

_SALES_QUOTE_TABLE_COLUMNS_KEY = "table_columns::tabSales Quote"


def _invalidate_sales_quote_table_column_cache() -> None:
	"""Bust column list cache used by ``has_column`` — same key is read via client_cache and frappe.cache."""
	for delete in (frappe.cache.delete_value, frappe.client_cache.delete_value):
		try:
			delete(_SALES_QUOTE_TABLE_COLUMNS_KEY)
		except Exception:
			pass


def _ensure_sales_quote_columns_for_permissions() -> None:
	"""If DB is behind DocType (e.g. missing ``company``), ``get_match_cond`` can emit invalid SQL."""
	if not frappe.db.table_exists("Sales Quote") or not frappe.db.exists("DocType", "Sales Quote"):
		return
	try:
		# Stale ``table_columns::*`` can make ``has_column`` look current and skip ``updatedb``.
		_invalidate_sales_quote_table_column_cache()
		if frappe.db.has_column("Sales Quote", "company"):
			return
	except frappe.db.TableMissingError:
		return

	frappe.db.updatedb("Sales Quote")
	_invalidate_sales_quote_table_column_cache()


def _sales_quote_match_cond() -> str:
	"""Permission SQL for raw queries on ``Sales Quote``; relies on ``company`` column."""
	_ensure_sales_quote_columns_for_permissions()
	if not frappe.db.has_column("Sales Quote", "company"):
		frappe.throw(
			_(
				"The Sales Quote table is missing required columns (for example `company`). "
				"Please run `bench migrate` for this site and reload."
			),
			title=_("Database out of date"),
		)
	raw = get_match_cond("Sales Quote")
	if not raw:
		return raw
	# Raw queries use ``FROM `tabSales Quote` sq``; ``get_match_cond`` qualifies columns as
	# ``(`tabSales Quote`.`company` ...)``. MariaDB/MySQL reject ``tabSales Quote``.col in WHERE
	# when the table is aliased as ``sq`` (Error 1054 Unknown column).
	fixed = raw.replace("`tabSales Quote`", "sq")
	if frappe.db.db_type == "postgres":
		fixed = fixed.replace('"tabSales Quote"', "sq")
	return fixed


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


def _air_corridor_job_airline_sql(alias: str) -> str:
	"""When ``job_airline`` query param is set: quote row/header airline blank = any carrier."""
	# Case-insensitive: Link names can differ in casing between booking and charge row.
	return f""" AND (
		IFNULL({alias}.airline,'') = ''
		OR LOWER(TRIM(IFNULL({alias}.airline,''))) = LOWER(TRIM(%(job_airline)s))
	)"""


def _sea_corridor_job_shipping_line_sql(alias: str) -> str:
	"""When ``job_shipping_line`` is set: blank shipping_line on a charge row or header = any line."""
	return f""" AND (
		IFNULL({alias}.shipping_line,'') = ''
		OR LOWER(TRIM(IFNULL({alias}.shipping_line,''))) = LOWER(TRIM(%(job_shipping_line)s))
	)"""


def _airline_only_match_sql() -> str:
	"""SQL fragment: at least one Air row (unified or legacy) with blank or matching job airline. No O/D."""
	unified = f"""EXISTS (
		SELECT 1 FROM `tabSales Quote Charge` sqc
		WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
		AND sqc.service_type IN %(service_types)s
		{_air_corridor_job_airline_sql("sqc")}
	)"""
	legacy = ""
	legacy_dt = SERVICE_LEGACY_TABLE.get("Air")
	if legacy_dt and frappe.db.table_exists(legacy_dt):
		legacy = f""" OR EXISTS (
			SELECT 1 FROM `tab{legacy_dt}` leg
			WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
			{_air_corridor_job_airline_sql("leg")}
		)"""
	return f"({unified}{legacy})"


def _o_wildcard_port(alias: str) -> str:
	"""Match origin with wildcards on both sides.

	- Empty ``corridor_origin`` (job) => do not filter that end.
	- Empty quote value (row/header) => wildcard (matches any job origin).
	"""
	return (
		f"(TRIM(IFNULL(%(corridor_origin)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.origin_port,'')) = '' OR "
		f"TRIM(IFNULL({alias}.origin_port,'')) = TRIM(IFNULL(%(corridor_origin)s,'')))"
	)


def _d_wildcard_port(alias: str) -> str:
	"""Match destination with wildcards on both sides.

	- Empty ``corridor_dest`` (job) => do not filter that end.
	- Empty quote value (row/header) => wildcard (matches any job destination).
	"""
	return (
		f"(TRIM(IFNULL(%(corridor_dest)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.destination_port,'')) = '' OR "
		f"TRIM(IFNULL({alias}.destination_port,'')) = TRIM(IFNULL(%(corridor_dest)s,'')))"
	)


def _o_wildcard_loc_from(alias: str) -> str:
	return (
		f"(TRIM(IFNULL(%(corridor_origin)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.location_from,'')) = '' OR "
		f"TRIM(IFNULL({alias}.location_from,'')) = TRIM(IFNULL(%(corridor_origin)s,'')))"
	)


def _d_wildcard_loc_to(alias: str) -> str:
	return (
		f"(TRIM(IFNULL(%(corridor_dest)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.location_to,'')) = '' OR "
		f"TRIM(IFNULL({alias}.location_to,'')) = TRIM(IFNULL(%(corridor_dest)s,'')))"
	)


def _corridor_match_sql_charges_header_legacy(
	service_type: str, job_airline: str | None = None, job_shipping_line: str | None = None
) -> str:
	"""SQL fragment — corridor via unified charges, legacy child rows, or header (Sales Quote) fields.

	Empty ``corridor_origin`` and/or ``corridor_dest`` (after trim) is a wildcard for that end
	(only the non-empty job ends constrain the match).
	For **Air**, ``job_airline`` narrows Sea/Air port rows. For **Sea**, ``job_shipping_line`` narrows
	unified/legacy/header rows the same way (blank on quotation = wildcard).
	"""
	st = (service_type or "").strip()
	air_al = ""
	if st == "Air" and (job_airline or "").strip():
		air_al = _air_corridor_job_airline_sql("sqc")
	sea_sl = ""
	if st == "Sea" and (job_shipping_line or "").strip():
		sea_sl = _sea_corridor_job_shipping_line_sql("sqc")
	if st in ("Sea", "Air"):
		oq = _o_wildcard_port("sqc")
		dq = _d_wildcard_port("sqc")
		unified = f"""EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type IN %(service_types)s
			AND {oq}
			AND {dq}
			{air_al}
			{sea_sl}
		)"""
		child_dt = SERVICE_LEGACY_TABLE.get(st)
		legacy = ""
		leg_air = ""
		if st == "Air" and (job_airline or "").strip():
			leg_air = _air_corridor_job_airline_sql("leg")
		leg_sea = ""
		if st == "Sea" and (job_shipping_line or "").strip():
			leg_sea = _sea_corridor_job_shipping_line_sql("leg")
		if child_dt and frappe.db.table_exists(child_dt):
			ol = _o_wildcard_port("leg")
			dl = _d_wildcard_port("leg")
			legacy = f""" OR EXISTS (
				SELECT 1 FROM `tab{child_dt}` leg
				WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
				AND {ol}
				AND {dl}
				{leg_air}
				{leg_sea}
			)"""
		hdr_air = ""
		if st == "Air" and (job_airline or "").strip():
			hdr_air = _air_corridor_job_airline_sql("sq")
		hdr_sea = ""
		if st == "Sea" and (job_shipping_line or "").strip():
			hdr_sea = _sea_corridor_job_shipping_line_sql("sq")
		h_o = _o_wildcard_port("sq")
		h_d = _d_wildcard_port("sq")
		parent_ports = f""" OR (
			{h_o}
			AND {h_d}
			{hdr_air}
			{hdr_sea}
		)"""
		return f"({unified}{legacy}{parent_ports})"
	if st == "Transport":
		lf = _o_wildcard_loc_from("sqc")
		lt = _d_wildcard_loc_to("sqc")
		unified = f"""EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type IN %(service_types)s
			AND {lf}
			AND {lt}
		)"""
		legacy = ""
		child_dt = SERVICE_LEGACY_TABLE.get("Transport")
		if child_dt and frappe.db.table_exists(child_dt):
			lf2 = _o_wildcard_loc_from("leg")
			lt2 = _d_wildcard_loc_to("leg")
			legacy = f""" OR EXISTS (
				SELECT 1 FROM `tab{child_dt}` leg
				WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
				AND {lf2}
				AND {lt2}
			)"""
		ph_lf = _o_wildcard_loc_from("sq")
		ph_lt = _d_wildcard_loc_to("sq")
		parent_loc = f""" OR (
			{ph_lf}
			AND {ph_lt}
		)"""
		return f"({unified}{legacy}{parent_loc})"
	return "(1=0)"


def _customs_declaration_charge_match_sql() -> str:
	"""SQL fragment (references ``sq``): Customs quotes matching Declaration Order filters.

	Each of ``customs_authority``, ``declaration_type``, and ``customs_broker`` may be empty (after trim) to
	mean *no* filter on that attribute (any value on a charge line matches).

	For broker, when a job broker is set, a blank broker on a line still matches any quote broker; a
	non-blank line broker must equal the filter value exactly (Broker link name).

	Legacy transport mode: when ``job_transport_mode`` is NULL/empty, do not filter by mode; otherwise
	legacy lines must match (unified charge rows are not restricted by mode).
	"""
	return """(
		EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type IN ('Custom', 'Customs', 'custom')
			AND (
				TRIM(IFNULL(%(customs_authority)s,'')) = ''
				OR TRIM(IFNULL(sqc.customs_authority,'')) = TRIM(IFNULL(%(customs_authority)s,''))
			)
			AND (
				TRIM(IFNULL(%(declaration_type)s,'')) = ''
				OR TRIM(IFNULL(sqc.declaration_type,'')) = TRIM(IFNULL(%(declaration_type)s,''))
			)
			AND (
				TRIM(IFNULL(%(customs_broker)s,'')) = ''
				OR IFNULL(sqc.customs_broker,'') = ''
				OR TRIM(IFNULL(sqc.customs_broker,'')) = TRIM(IFNULL(%(customs_broker)s,''))
			)
		)
		OR EXISTS (
			SELECT 1 FROM `tabSales Quote Customs` leg
			WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
			AND (
				TRIM(IFNULL(%(customs_authority)s,'')) = ''
				OR TRIM(IFNULL(leg.customs_authority,'')) = TRIM(IFNULL(%(customs_authority)s,''))
			)
			AND (
				TRIM(IFNULL(%(declaration_type)s,'')) = ''
				OR TRIM(IFNULL(leg.declaration_type,'')) = TRIM(IFNULL(%(declaration_type)s,''))
			)
			AND (
				TRIM(IFNULL(%(customs_broker)s,'')) = ''
				OR IFNULL(leg.customs_broker,'') = ''
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


def _declaration_order_charge_row_value(row, fieldname: str) -> str:
	if isinstance(row, dict):
		return (row.get(fieldname) or "").strip()
	return (getattr(row, fieldname, None) or "").strip()


def _legacy_customs_row_transport_mode_matches(row_transport_mode: str, job_transport_mode: str) -> bool:
	"""Match legacy ``Sales Quote Customs``.transport_mode to a Transport Mode link (see SQL in ``_customs_declaration_charge_match_sql``)."""
	if not (row_transport_mode or "").strip():
		return True
	tm = frappe.db.get_value(
		"Transport Mode",
		job_transport_mode,
		["sea", "air", "transport"],
		as_dict=True,
	)
	if not tm:
		return True
	rtm = row_transport_mode.strip()
	if rtm == "Sea" and cint(tm.get("sea")):
		return True
	if rtm == "Air" and cint(tm.get("air")):
		return True
	if rtm in ("Road", "Rail") and cint(tm.get("transport")):
		return True
	return False


def sales_quote_customs_charge_row_matches_declaration_order_filters(
	row,
	customs_authority: str = "",
	declaration_type: str = "",
	customs_broker: str = "",
	job_transport_mode: str | None = None,
	*,
	is_legacy_customs_row: bool = False,
) -> bool:
	"""True when a single customs charge row matches Declaration Order filters (empty filter = wildcard)."""
	ca = (customs_authority or "").strip()
	dt = (declaration_type or "").strip()
	cb = (customs_broker or "").strip()
	row_ca = _declaration_order_charge_row_value(row, "customs_authority")
	row_dt = _declaration_order_charge_row_value(row, "declaration_type")
	row_cb = _declaration_order_charge_row_value(row, "customs_broker")

	if ca and row_ca != ca:
		return False
	if dt and row_dt != dt:
		return False
	if cb and row_cb and row_cb != cb:
		return False

	jtm = (job_transport_mode or "").strip() or None
	if jtm and is_legacy_customs_row:
		row_tm = _declaration_order_charge_row_value(row, "transport_mode")
		if row_tm and not _legacy_customs_row_transport_mode_matches(row_tm, jtm):
			return False
	return True


def filter_customs_charge_rows_for_declaration_order(parent_doc, rows):
	"""Keep customs charge rows that match the order's customs filters (all matching lines, not just the first)."""
	if getattr(parent_doc, "doctype", None) not in ("Declaration Order", "Declaration"):
		return list(rows or [])
	ca = (getattr(parent_doc, "customs_authority", None) or "").strip()
	dt = (getattr(parent_doc, "declaration_type", None) or "").strip()
	cb = (getattr(parent_doc, "customs_broker", None) or "").strip()
	jtm = (getattr(parent_doc, "transport_mode", None) or "").strip() or None
	if not any((ca, dt, cb, jtm)):
		return list(rows or [])
	out = []
	for row in rows or []:
		is_legacy = not _declaration_order_charge_row_value(row, "service_type")
		if sales_quote_customs_charge_row_matches_declaration_order_filters(
			row,
			ca,
			dt,
			cb,
			jtm,
			is_legacy_customs_row=is_legacy,
		):
			out.append(row)
	return out


def _main_service_header_match_sql() -> str:
	"""SQL fragment (references ``sq``): quotation ``main_service`` must match the job's service."""
	return "sq.main_service IN %(main_service_variants)s"


def sales_quote_matches_main_service(sales_quote_name: str, service_type: str) -> bool:
	"""True when the Sales Quote header ``main_service`` matches the operational job service (e.g. Customs)."""
	if not sales_quote_name or not (service_type or "").strip():
		return False
	if not frappe.db.exists("Sales Quote", sales_quote_name):
		return False
	ms = frappe.db.get_value("Sales Quote", sales_quote_name, "main_service")
	return sales_quote_charge_service_types_equal(ms, service_type)


def sales_quote_matches_declaration_order_filters(
	sales_quote_name: str,
	customs_authority: str,
	declaration_type: str,
	customs_broker: str,
	job_transport_mode: str | None = None,
) -> bool:
	"""True if the Sales Quote has a Customs line matching the non-empty order filters (empties = wildcard)."""
	ca = (customs_authority or "").strip()
	dt = (declaration_type or "").strip()
	cb = (customs_broker or "").strip()
	jtm = (job_transport_mode or "").strip() or None
	match_sql = _customs_declaration_charge_match_sql()
	params: dict[str, Any] = {
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


def _corridor_match_sql(
	service_type: str,
	job_airline: str | None = None,
	job_shipping_line: str | None = None,
) -> str:
	"""SQL fragment (references ``sq``) — job O/D vs unified charge rows, legacy charge rows, or header ports/locations.

	Sales Quote routing legs are not used for corridor filtering (Get Charges from Quotation list/preview/apply).

	For **Air**, optional ``job_airline`` narrows to quotes whose matching charge row or header airline is blank
	(wildcard) or equals the job airline. For **Sea**, optional ``job_shipping_line`` does the same for shipping lines.
	"""
	st = (service_type or "").strip()
	if st not in ("Sea", "Air", "Transport"):
		return "(1=1)"
	return _corridor_match_sql_charges_header_legacy(
		service_type, job_airline=job_airline, job_shipping_line=job_shipping_line
	)


def sales_quote_matches_job_corridor(
	sales_quote_name: str,
	service_type: str,
	corridor_origin: str,
	corridor_dest: str,
	job_airline: str | None = None,
	job_shipping_line: str | None = None,
) -> bool:
	"""True if charge rows or header O/D (and carrier for Air/Sea) match, same rules as list filter (wildcards allowed)."""
	o = (corridor_origin or "").strip()
	d = (corridor_dest or "").strip()
	st = (service_type or "").strip()
	if st not in SERVICE_LEGACY_TABLE:
		return False
	ja = (job_airline or "").strip() if st == "Air" else ""
	jsl = (job_shipping_line or "").strip() if st == "Sea" else ""
	if st == "Air" and ja and not o and not d:
		return sales_quote_matches_job_airline_only(sales_quote_name, ja)
	match_sql = _corridor_match_sql(
		st, job_airline=ja or None, job_shipping_line=jsl or None
	)
	service_types = tuple(iter_sales_quote_charge_service_type_db_values_for_canonical(st))
	if not service_types:
		return False
	params: dict[str, Any] = {
		"name": sales_quote_name,
		"service_type": st,
		"service_types": service_types,
		"corridor_origin": o,
		"corridor_dest": d,
	}
	if ja:
		params["job_airline"] = ja
	if jsl:
		params["job_shipping_line"] = jsl
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


def sales_quote_matches_job_airline_only(sales_quote_name: str, job_airline: str) -> bool:
	"""True if the quote has an Air line (or legacy) with blank airline or same as ``job_airline`` (no O/D gate)."""
	ja = (job_airline or "").strip()
	if not ja:
		return False
	match_sql = _airline_only_match_sql()
	service_types = tuple(iter_sales_quote_charge_service_type_db_values_for_canonical("Air"))
	if not service_types:
		return False
	params: dict[str, Any] = {"name": sales_quote_name, "job_airline": ja, "service_types": service_types}
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

	st_variants = tuple(iter_sales_quote_charge_service_type_db_values_for_canonical(service_type))
	if not st_variants:
		return []

	start = cint(start)
	page_len = cint(page_len) or 20

	txt_cond = ""
	params: dict[str, Any] = {"service_types": st_variants, "start": start, "page_len": page_len}
	if txt:
		params["txt"] = f"%{txt}%"
		txt_cond = "AND (sq.name LIKE %(txt)s OR IFNULL(sq.customer,'') LIKE %(txt)s)"

	legacy_sql = _legacy_exists_clause(service_type)

	eligibility = f"""( EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type IN %(service_types)s
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

	match_cond = _sales_quote_match_cond()

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


def _org_dimensions_header_match_sql() -> str:
	"""Quote header vs job Branch / Cost Center / Profit Center.

	Empty job value = no filter on that dimension. Non-empty job value matches quotes whose header is
	blank (wildcard) or equals the job — same idea as corridor ports on the quotation side.
	"""
	return """AND (
		TRIM(IFNULL(%(job_branch)s,'')) = ''
		OR TRIM(IFNULL(sq.branch,'')) = ''
		OR TRIM(IFNULL(sq.branch,'')) = TRIM(IFNULL(%(job_branch)s,''))
	)
	AND (
		TRIM(IFNULL(%(job_cost_center)s,'')) = ''
		OR TRIM(IFNULL(sq.cost_center,'')) = ''
		OR TRIM(IFNULL(sq.cost_center,'')) = TRIM(IFNULL(%(job_cost_center)s,''))
	)
	AND (
		TRIM(IFNULL(%(job_profit_center)s,'')) = ''
		OR TRIM(IFNULL(sq.profit_center,'')) = ''
		OR TRIM(IFNULL(sq.profit_center,'')) = TRIM(IFNULL(%(job_profit_center)s,''))
	)"""


def sales_quote_matches_job_org_dimensions(
	sales_quote_name: str,
	job_branch: str | None = None,
	job_cost_center: str | None = None,
	job_profit_center: str | None = None,
) -> bool:
	"""True when each non-empty job dimension matches the Sales Quote header.

	A blank value on the quotation header acts as a wildcard for that dimension; a non-blank header must
	equal the job value when the job filter is set.
	"""
	br = (job_branch or "").strip()
	cc = (job_cost_center or "").strip()
	pc = (job_profit_center or "").strip()
	if not br and not cc and not pc:
		return True
	row = frappe.db.get_value(
		"Sales Quote",
		sales_quote_name,
		["branch", "cost_center", "profit_center"],
		as_dict=True,
	)
	if not row:
		return False
	if br:
		qb = (row.get("branch") or "").strip()
		if qb and qb != br:
			return False
	if cc:
		qcc = (row.get("cost_center") or "").strip()
		if qcc and qcc != cc:
			return False
	if pc:
		qpc = (row.get("profit_center") or "").strip()
		if qpc and qpc != pc:
			return False
	return True


def fetch_eligible_regular_sales_quote_names(
	service_type: str,
	customer: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	limit: int = 100,
	corridor_origin: str | None = None,
	corridor_dest: str | None = None,
	job_airline: str | None = None,
	job_shipping_line: str | None = None,
	customs_authority: str | None = None,
	declaration_type: str | None = None,
	customs_broker: str | None = None,
	job_transport_mode: str | None = None,
	job_branch: str | None = None,
	job_cost_center: str | None = None,
	job_profit_center: str | None = None,
) -> list[str]:
	"""Sales Quote names eligible for Action → Get Charges from Quotation.

	Returns **Regular** quotations only (excludes One-off and Project). Only **submitted** quotes
	(``docstatus`` = 1) are returned.

	**Main service**: the quotation header ``main_service`` must match the job (e.g. Declaration Order →
	Customs, Air Booking → Air). Charge-line existence alone does not qualify a quote.

	Optional narrowing (when dialog / job filters are set):

	- **Customs**: ``customs_authority`` / ``declaration_type`` / ``customs_broker`` / ``job_transport_mode``
	  (legacy lines only for mode) via ``_customs_declaration_charge_match_sql``.
	- **Sea / Air / Transport**: corridor / airline / shipping line via charge rows or header
	  (see ``_corridor_match_sql``).

	**Org dimensions**: Branch / Cost Center / Profit Center on the quote header vs job (blank = wildcard).
	"""
	service_type = (service_type or "").strip()
	if service_type not in SERVICE_LEGACY_TABLE:
		return []

	limit = cint(limit) or 100
	service_types = tuple(iter_sales_quote_charge_service_type_db_values_for_canonical(service_type))
	if not service_types:
		return []
	co = (corridor_origin or "").strip()
	cd = (corridor_dest or "").strip()
	ca = (customs_authority or "").strip()
	dt = (declaration_type or "").strip()
	cb = (customs_broker or "").strip()
	ja = (job_airline or "").strip() if service_type == "Air" else ""
	jsl = (job_shipping_line or "").strip() if service_type == "Sea" else ""

	params: dict[str, Any] = {
		"service_type": service_type,
		"service_types": service_types,
		"main_service_variants": service_types,
		"limit": limit,
	}
	eligibility = _main_service_header_match_sql()
	if canonical_charge_service_type_for_storage(service_type) == "custom":
		jtm = (job_transport_mode or "").strip() or None
		params["customs_authority"] = ca
		params["declaration_type"] = dt
		params["customs_broker"] = cb
		params["job_transport_mode"] = jtm
		if ca or dt or cb or jtm:
			eligibility = f"({eligibility}) AND {_customs_declaration_charge_match_sql()}"
	else:
		params["corridor_origin"] = co
		params["corridor_dest"] = cd
		if ja:
			params["job_airline"] = ja
		if jsl:
			params["job_shipping_line"] = jsl
		if co or cd or ja or jsl:
			eligibility = f"({eligibility}) AND {_corridor_match_sql(service_type, job_airline=ja or None, job_shipping_line=jsl or None)}"
	params["job_branch"] = (job_branch or "").strip()
	params["job_cost_center"] = (job_cost_center or "").strip()
	params["job_profit_center"] = (job_profit_center or "").strip()
	org_sql = _org_dimensions_header_match_sql()
	# Action → Get Charges from Quotation: **Regular** quotes only (excludes One-off, Project, blank).
	regular_only_where = "TRIM(IFNULL(sq.quotation_type,'')) = 'Regular'"

	customer_cond = ""
	if (customer or "").strip():
		params["customer"] = customer.strip()
		# Case-insensitive so list matches booking Local Customer / Customer vs Sales Quote.customer reliably.
		customer_cond = (
			"AND LOWER(TRIM(IFNULL(sq.customer,''))) = LOWER(TRIM(%(customer)s))"
		)

	match_cond = _sales_quote_match_cond()
	sql = f"""
		SELECT sq.name
		FROM `tabSales Quote` sq
		WHERE {eligibility}
		AND {regular_only_where}
		{customer_cond}
		AND IFNULL(sq.status,'') NOT IN ('Lost','Expired')
		AND (sq.valid_until IS NULL OR sq.valid_until >= CURDATE())
		AND sq.docstatus = 1
		{org_sql}
		{match_cond}
		ORDER BY sq.modified DESC
		LIMIT %(limit)s
	"""
	params["limit"] = limit
	rows = frappe.db.sql(sql, params)
	return [r[0] for r in rows] if rows else []
