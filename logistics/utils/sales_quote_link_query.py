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
		AND sqc.service_type = 'Air'
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
	"""``corridor_origin`` empty = do not filter that end."""
	return (
		f"(TRIM(IFNULL(%(corridor_origin)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.origin_port,'')) = TRIM(IFNULL(%(corridor_origin)s,'')))"
	)


def _d_wildcard_port(alias: str) -> str:
	"""``corridor_dest`` empty = do not filter that end."""
	return (
		f"(TRIM(IFNULL(%(corridor_dest)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.destination_port,'')) = TRIM(IFNULL(%(corridor_dest)s,'')))"
	)


def _o_wildcard_loc_from(alias: str) -> str:
	return (
		f"(TRIM(IFNULL(%(corridor_origin)s,'')) = '' OR "
		f"TRIM(IFNULL({alias}.location_from,'')) = TRIM(IFNULL(%(corridor_origin)s,'')))"
	)


def _d_wildcard_loc_to(alias: str) -> str:
	return (
		f"(TRIM(IFNULL(%(corridor_dest)s,'')) = '' OR "
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
			AND sqc.service_type = %(service_type)s
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
			AND sqc.service_type = 'Transport'
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

	Each of ``customs_authority``, ``declaration_type``, ``customs_broker`` may be empty (after trim) to
	mean *no* filter on that attribute (any value on a charge line matches).

	For broker, when a job broker is set, a blank broker on a line still matches any quote broker.

	Legacy transport mode: when ``job_transport_mode`` is NULL/empty, do not filter by mode; otherwise
	legacy lines must match (unified charge rows are not restricted by mode).
	"""
	return """(
		EXISTS (
			SELECT 1 FROM `tabSales Quote Charge` sqc
			WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
			AND sqc.service_type = 'Customs'
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
	params: dict[str, Any] = {
		"name": sales_quote_name,
		"service_type": st,
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
	params: dict[str, Any] = {"name": sales_quote_name, "job_airline": ja}
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
	job_airline: str | None = None,
	job_shipping_line: str | None = None,
	customs_authority: str | None = None,
	declaration_type: str | None = None,
	customs_broker: str | None = None,
	job_transport_mode: str | None = None,
) -> list[str]:
	"""Sales Quote names that have unified or legacy charge rows for ``service_type``.

	Returns **Regular** quotations only (Action → Get Charges from Quotation — excludes One-off and Project).
	Only **submitted** quotes (``docstatus`` = 1) are returned.

	Corridor matching uses **Sales Quote Charge** (unified) rows, legacy service charge rows, or header
	fields on the quotation (not routing legs).

	For **Customs**, ``customs_authority`` / ``declaration_type`` / ``customs_broker`` each narrow the
	list when set; an empty value is a wildcard for that attribute. ``job_transport_mode`` still applies
	only to legacy lines (see ``_customs_declaration_charge_match_sql``).

	**Sea / Air / Transport**: empty ``corridor_origin`` and/or ``corridor_dest`` (after trim) is a
	wildcard for that end. For **Air** with both ports empty and ``job_airline`` set, only airline
	matching applies (equivalent to the former airline-only path). For **Sea**, ``job_shipping_line`` narrows
	by line or header; blank on a quotation line matches any line.
	"""
	service_type = (service_type or "").strip()
	if service_type not in SERVICE_LEGACY_TABLE:
		return []

	limit = cint(limit) or 100
	co = (corridor_origin or "").strip()
	cd = (corridor_dest or "").strip()
	ca = (customs_authority or "").strip()
	dt = (declaration_type or "").strip()
	cb = (customs_broker or "").strip()
	ja = (job_airline or "").strip() if service_type == "Air" else ""
	jsl = (job_shipping_line or "").strip() if service_type == "Sea" else ""

	params: dict[str, Any] = {"service_type": service_type, "limit": limit}
	if service_type == "Customs":
		jtm = (job_transport_mode or "").strip() or None
		params["customs_authority"] = ca
		params["declaration_type"] = dt
		params["customs_broker"] = cb
		params["job_transport_mode"] = jtm
		eligibility = _customs_declaration_charge_match_sql()
	else:
		params["corridor_origin"] = co
		params["corridor_dest"] = cd
		if ja:
			params["job_airline"] = ja
		if jsl:
			params["job_shipping_line"] = jsl
		eligibility = _corridor_match_sql(
			service_type, job_airline=ja or None, job_shipping_line=jsl or None
		)
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
