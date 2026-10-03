# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Tariff Charge → operational booking charge helpers.

Tariff child rows (``Tariff Charge``) share the same pricing field shape as ``Sales Quote Charge``.
Booking controllers already map quote rows via ``_map_sales_quote_*_to_charge``; this module adapts
tariff rows into quote-like dicts and filters them for Sea / Air bookings.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from logistics.pricing_center.doctype.tariff.tariff_rate_rows import iter_tariff_charges_for_service
from logistics.utils.charge_service_type import (
	canonical_charge_service_type_for_storage,
	implied_service_type_for_doctype,
)

BOOKING_DOCTYPES = frozenset({"Sea Booking", "Air Booking"})
SALES_QUOTE_DOCTYPE = "Sales Quote"

_ORG_SCOPE_KEYS = frozenset({"branch", "cost_center", "profit_center"})
_GCFTS_ALLOWED_KEYS: frozenset[str] | None = None

_TARIFF_CHILD_META = frozenset(
	{
		"name",
		"idx",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"parent",
		"parentfield",
		"parenttype",
		"doctype",
	}
)

GCFT_FILTER_KEYS: dict[str, frozenset[str]] = {
	"Sea Booking": frozenset({"origin_port", "destination_port", "shipping_line"}),
	"Air Booking": frozenset({"origin_port", "destination_port", "airline"}),
	SALES_QUOTE_DOCTYPE: frozenset(
		{"origin_port", "destination_port", "shipping_line", "airline"}
	),
}


def _parse_gcft_filter_overrides(doctype: str, filter_overrides) -> dict[str, str]:
	if not filter_overrides:
		return {}
	if isinstance(filter_overrides, str):
		try:
			filter_overrides = frappe.parse_json(filter_overrides)
		except Exception:
			return {}
	if not isinstance(filter_overrides, dict):
		return {}
	allowed = GCFT_FILTER_KEYS.get(doctype, frozenset())
	out: dict[str, str] = {}
	for k, v in filter_overrides.items():
		if k not in allowed:
			continue
		out[k] = "" if v is None else str(v).strip()
	return out


def _pick_gcft_field(doc, overrides: dict, param_key: str, doc_attr: str) -> str:
	if not overrides:
		return (getattr(doc, doc_attr, None) or "").strip()
	if param_key in overrides:
		return (overrides[param_key] or "").strip()
	return ""


def _effective_booking_corridor(doc, overrides: dict) -> tuple[str, str, str | None, str | None]:
	"""(origin, destination, airline, shipping_line)."""
	if doc.doctype == "Sea Booking":
		o = _pick_gcft_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcft_field(doc, overrides, "destination_port", "destination_port")
		sl = _pick_gcft_field(doc, overrides, "shipping_line", "shipping_line")
		return o, d, None, (sl or None)
	if doc.doctype == "Air Booking":
		o = _pick_gcft_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcft_field(doc, overrides, "destination_port", "destination_port")
		al = _pick_gcft_field(doc, overrides, "airline", "airline")
		return o, d, (al or None), None
	if doc.doctype == SALES_QUOTE_DOCTYPE:
		o = _pick_gcft_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcft_field(doc, overrides, "destination_port", "destination_port")
		al = _pick_gcft_field(doc, overrides, "airline", "airline")
		sl = _pick_gcft_field(doc, overrides, "shipping_line", "shipping_line")
		return o, d, (al or None), (sl or None)
	return "", "", None, None


def _booking_customer(doc) -> str | None:
	if doc.doctype in BOOKING_DOCTYPES:
		return (getattr(doc, "local_customer", None) or "").strip() or None
	if doc.doctype == SALES_QUOTE_DOCTYPE:
		return (getattr(doc, "customer", None) or "").strip() or None
	return None


def _customer_matches_job(tariff_customer: str | None, job_customer: str | None) -> bool:
	return (tariff_customer or "").strip().lower() == (job_customer or "").strip().lower()


def _tariff_is_valid_on_date(tariff_doc, on_date=None) -> bool:
	if not cint(getattr(tariff_doc, "is_active", 0)):
		return False
	ref = getdate(on_date or today())
	vf = getattr(tariff_doc, "valid_from", None)
	vt = getattr(tariff_doc, "valid_to", None)
	if vf and getdate(vf) > ref:
		return False
	if vt and getdate(vt) < ref:
		return False
	return True


def _tariff_matches_job_customer(tariff_doc, job_customer: str | None) -> bool:
	if not job_customer:
		return False
	tt = (getattr(tariff_doc, "tariff_type", None) or "").strip()
	if tt in ("", "All Customers"):
		return True
	if tt == "Customer":
		return _customer_matches_job(getattr(tariff_doc, "customer", None), job_customer)
	if tt == "Customer Group":
		cg = (getattr(tariff_doc, "customer_group", None) or "").strip()
		if not cg:
			return False
		return frappe.db.get_value("Customer", job_customer, "customer_group") == cg
	if tt == "Territory":
		ter = (getattr(tariff_doc, "territory", None) or "").strip()
		if not ter:
			return False
		return frappe.db.get_value("Customer", job_customer, "territory") == ter
	if tt == "Specific Customers":
		for row in getattr(tariff_doc, "customers", None) or []:
			if _customer_matches_job(getattr(row, "customer", None), job_customer):
				return True
		return False
	if tt == "Agent":
		# Agent tariffs are not customer-scoped; list when customer is set on the booking.
		return True
	return False


def _wildcard_link_match(row_value: str | None, job_value: str | None) -> bool:
	rv = (row_value or "").strip()
	jv = (job_value or "").strip()
	if not jv:
		return True
	if not rv:
		return True
	return rv.lower() == jv.lower()


def tariff_charge_row_matches_booking_corridor(
	row,
	*,
	doctype: str,
	origin: str,
	destination: str,
	airline: str | None = None,
	shipping_line: str | None = None,
) -> bool:
	"""True when corridor fields on the tariff line match the booking (blank line = wildcard)."""
	def _g(fn):
		return getattr(row, fn, None) if not isinstance(row, dict) else row.get(fn)

	o = (origin or "").strip()
	d = (destination or "").strip()
	if o or d:
		if not _wildcard_link_match(_g("origin_port"), o):
			return False
		if not _wildcard_link_match(_g("destination_port"), d):
			return False
	if doctype == "Sea Booking" and (shipping_line or "").strip():
		if not _wildcard_link_match(_g("shipping_line"), shipping_line):
			return False
	if doctype == "Air Booking" and (airline or "").strip():
		if not _wildcard_link_match(_g("airline"), airline):
			return False
	return True


def _row_is_active_on_date(row, on_date=None) -> bool:
	ref = getdate(on_date or today())
	if hasattr(row, "tariff_rate_active") and row.tariff_rate_active is not None:
		if not cint(row.tariff_rate_active):
			return False
	vf = getattr(row, "tariff_valid_from", None)
	vt = getattr(row, "tariff_valid_to", None)
	if vf and getdate(vf) > ref:
		return False
	if vt and getdate(vt) < ref:
		return False
	return True


def filter_tariff_charge_rows_for_booking(
	parent_doc,
	tariff_doc,
	service_type: str,
	*,
	origin: str = "",
	destination: str = "",
	airline: str | None = None,
	shipping_line: str | None = None,
) -> list[Any]:
	"""Return Tariff Charge rows eligible for this booking (service + corridor + row validity)."""
	dt = getattr(parent_doc, "doctype", None) or ""
	out: list[Any] = []
	for row in iter_tariff_charges_for_service(tariff_doc, service_type):
		if not _row_is_active_on_date(row):
			continue
		if not tariff_charge_row_matches_booking_corridor(
			row,
			doctype=dt,
			origin=origin,
			destination=destination,
			airline=airline,
			shipping_line=shipping_line,
		):
			continue
		out.append(row)
	return out


def _tariff_row_field(row, fieldname: str):
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _corridor_doctype_for_tariff_row(row) -> str:
	st = canonical_charge_service_type_for_storage(_tariff_row_field(row, "service_type") or "")
	if st == "air":
		return "Air Booking"
	if st == "sea":
		return "Sea Booking"
	return SALES_QUOTE_DOCTYPE


def _sq_context_value(sq_doc, overrides: dict | None, fieldname: str) -> str:
	ov = overrides or {}
	if fieldname in ov:
		return (ov.get(fieldname) or "").strip()
	return (getattr(sq_doc, fieldname, None) or "").strip()


def tariff_charge_row_matches_sales_quote_context(
	sq_doc,
	row,
	overrides: dict | None = None,
) -> bool:
	"""True when a Tariff Charge line matches the Sales Quote header (blank tariff field = wildcard)."""
	from logistics.utils.sales_quote_charge_parameters import SALES_QUOTE_CHARGE_PARAMETER_FIELDS

	ov = overrides or {}
	origin, dest, airline, shipping_line = _effective_booking_corridor(sq_doc, ov)
	corridor_dt = _corridor_doctype_for_tariff_row(row)
	if not tariff_charge_row_matches_booking_corridor(
		row,
		doctype=corridor_dt,
		origin=origin,
		destination=dest,
		airline=airline,
		shipping_line=shipping_line,
	):
		return False

	st = canonical_charge_service_type_for_storage(_tariff_row_field(row, "service_type") or "")
	if st == "transport":
		plf = _sq_context_value(sq_doc, ov, "location_from")
		plt = _sq_context_value(sq_doc, ov, "location_to")
		rlf = (_tariff_row_field(row, "location_from") or "").strip()
		rlt = (_tariff_row_field(row, "location_to") or "").strip()
		if rlf and plf and rlf.lower() != plf.lower():
			return False
		if rlt and plt and rlt.lower() != plt.lower():
			return False

	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		if fn in (
			"origin_port",
			"destination_port",
			"airline",
			"shipping_line",
			"location_from",
			"location_to",
		):
			continue
		sq_val = _sq_context_value(sq_doc, ov, fn)
		row_val = (_tariff_row_field(row, fn) or "").strip()
		if sq_val and row_val and sq_val.lower() != row_val.lower():
			return False
	return True


def filter_tariff_charge_rows_for_sales_quote(
	sq_doc,
	tariff_doc,
	filter_overrides: dict | None = None,
) -> list[Any]:
	"""Tariff Charge rows on *tariff_doc* that match the Sales Quote routing/parameters."""
	ov = _parse_gcft_filter_overrides(SALES_QUOTE_DOCTYPE, filter_overrides)
	ref_date = getattr(sq_doc, "date", None) or today()
	out: list[Any] = []
	for row in getattr(tariff_doc, "rates", None) or []:
		if not _row_is_active_on_date(row, on_date=ref_date):
			continue
		if not tariff_charge_row_matches_sales_quote_context(sq_doc, row, ov):
			continue
		if not (_tariff_row_field(row, "item_code") or "").strip():
			continue
		out.append(row)
	return out


def tariff_charge_row_to_sales_quote_charge_dict(row, tariff_name: str) -> dict:
	"""Map a Tariff Charge row to a new Sales Quote Charge child dict."""
	from logistics.utils.get_charges_from_quotation import _SQ_CHARGE_COPY_FIELDS

	quote_like = tariff_charge_row_as_quote_like_dict(row, tariff_name)
	try:
		valid = {f.fieldname for f in frappe.get_meta("Sales Quote Charge").fields}
	except Exception:
		valid = set(quote_like.keys())

	out: dict[str, Any] = {}
	for fn in _SQ_CHARGE_COPY_FIELDS:
		if fn not in valid:
			continue
		val = quote_like.get(fn)
		if val is None or val == "":
			continue
		out[fn] = val

	for fn, val in quote_like.items():
		if fn in out or fn not in valid:
			continue
		if val is None or val == "":
			continue
		out[fn] = val

	out["revenue_tariff"] = tariff_name
	out["cost_tariff"] = tariff_name
	if not out.get("revenue_calculation_method") and quote_like.get("calculation_method"):
		out["revenue_calculation_method"] = quote_like["calculation_method"]
	if not out.get("item_code"):
		return {}
	return out


def tariff_has_matching_charge_rows(
	parent_doc,
	tariff_doc,
	service_type: str,
	*,
	origin: str = "",
	destination: str = "",
	airline: str | None = None,
	shipping_line: str | None = None,
) -> bool:
	return bool(
		filter_tariff_charge_rows_for_booking(
			parent_doc,
			tariff_doc,
			service_type,
			origin=origin,
			destination=destination,
			airline=airline,
			shipping_line=shipping_line,
		)
	)


def fetch_eligible_tariff_names(
	doctype: str,
	parent_doc,
	job_customer: str,
	service_type: str,
	*,
	origin: str = "",
	destination: str = "",
	airline: str | None = None,
	shipping_line: str | None = None,
	limit: int = 150,
) -> list[str]:
	"""Active tariffs with at least one matching charge line for this booking or Sales Quote."""
	ref_date = today()
	if doctype == SALES_QUOTE_DOCTYPE and parent_doc is not None:
		ref_date = getattr(parent_doc, "date", None) or today()

	names = frappe.get_all(
		"Tariff",
		filters={"is_active": 1},
		fields=["name"],
		order_by="modified desc",
		limit_page_length=limit * 3,
	)
	eligible: list[str] = []
	for row in names:
		name = row.name
		try:
			tariff_doc = frappe.get_doc("Tariff", name)
		except Exception:
			continue
		if not _tariff_is_valid_on_date(tariff_doc, on_date=ref_date):
			continue
		if not _tariff_matches_job_customer(tariff_doc, job_customer):
			continue
		if doctype == SALES_QUOTE_DOCTYPE:
			if not filter_tariff_charge_rows_for_sales_quote(parent_doc, tariff_doc):
				continue
		elif not tariff_has_matching_charge_rows(
			parent_doc,
			tariff_doc,
			service_type,
			origin=origin,
			destination=destination,
			airline=airline,
			shipping_line=shipping_line,
		):
			continue
		eligible.append(name)
		if len(eligible) >= limit:
			break
	return eligible


def tariff_charge_row_as_quote_like_dict(row, tariff_name: str) -> dict:
	"""Adapt a Tariff Charge row so booking ``_map_sales_quote_*`` mappers can consume it."""
	if hasattr(row, "as_dict"):
		out = row.as_dict()
	else:
		out = dict(row)
	out["revenue_tariff"] = tariff_name
	out["cost_tariff"] = tariff_name
	out["use_tariff_in_revenue"] = 0
	out["use_tariff_in_cost"] = 0
	if not out.get("calculation_method") and out.get("revenue_calculation_method"):
		out["calculation_method"] = out["revenue_calculation_method"]
	st = out.get("service_type")
	if st:
		canon = canonical_charge_service_type_for_storage(st)
		label_by_canon = {
			"air": "Air",
			"sea": "Sea",
			"transport": "Transport",
			"custom": "Customs",
			"warehousing": "Warehousing",
		}
		out["service_type"] = label_by_canon.get(canon, st)
	return out


def gcft_list_filters_payload(
	doctype: str,
	customer: str,
	origin: str,
	dest: str,
	service_type: str,
	**kwargs,
) -> dict:
	"""Structured labels for the Get Charges from Tariff dialog."""
	if doctype == SALES_QUOTE_DOCTYPE:
		extra = []
		sl = (kwargs.get("shipping_line") or "").strip()
		al = (kwargs.get("airline") or "").strip()
		if sl:
			extra.append({"label": _("Shipping Line"), "value": sl})
		if al:
			extra.append({"label": _("Airline"), "value": al})
		rules = [
			_("Active tariffs only"),
			_("Tariff validity must include the quote date"),
			_("Customer must match the tariff type rules (Customer, Group, Territory, etc.)"),
			_("Tariff charge lines must match Sales Quote routing and parameter fields"),
			_("Blank values on a tariff line match any value on the quote"),
		]
		out = {
			"service_type": service_type or _("All"),
			"customer_label": _("Customer"),
			"customer": customer,
			"origin_label": _("Origin Port"),
			"origin": origin,
			"destination_label": _("Destination Port"),
			"destination": dest,
			"rules": rules,
		}
		if extra:
			out["extra_criteria"] = extra
		return out
	if service_type == "Sea":
		sl = (kwargs.get("shipping_line") or "").strip()
		extra = [{"label": _("Shipping Line"), "value": sl}] if sl else []
		rules = [
			_("Active tariffs only"),
			_("Tariff validity must include today"),
			_("Customer must match the tariff type rules (Customer, Group, Territory, etc.)"),
			_("At least one Sea charge line must match the corridor filters"),
			_("Blank origin, destination, or shipping line on a tariff line matches any value"),
		]
		out = {
			"service_type": service_type,
			"customer_label": _("Local Customer"),
			"customer": customer,
			"origin_label": _("Origin Port"),
			"origin": origin,
			"destination_label": _("Destination Port"),
			"destination": dest,
			"rules": rules,
		}
		if extra:
			out["extra_criteria"] = extra
		return out
	al = (kwargs.get("airline") or "").strip()
	extra = [{"label": _("Airline"), "value": al}] if al else []
	rules = [
		_("Active tariffs only"),
		_("Tariff validity must include today"),
		_("Customer must match the tariff type rules (Customer, Group, Territory, etc.)"),
		_("At least one Air charge line must match the corridor filters"),
		_("Blank origin, destination, or airline on a tariff line matches any value"),
	]
	out = {
		"service_type": service_type,
		"customer_label": _("Local Customer"),
		"customer": customer,
		"origin_label": _("Origin Port"),
		"origin": origin,
		"destination_label": _("Destination Port"),
		"destination": dest,
		"rules": rules,
	}
	if extra:
		out["extra_criteria"] = extra
	return out


def parse_gcft_filter_overrides(doctype: str, filter_overrides) -> dict[str, str]:
	return _parse_gcft_filter_overrides(doctype, filter_overrides)


def effective_booking_corridor(doc, overrides: dict) -> tuple[str, str, str | None, str | None]:
	return _effective_booking_corridor(doc, overrides)


def booking_customer(doc) -> str | None:
	return _booking_customer(doc)


def implied_service_for_booking(doctype: str) -> str | None:
	return implied_service_type_for_doctype(doctype)


def _gcfts_allowed_filter_keys() -> frozenset[str]:
	global _GCFTS_ALLOWED_KEYS
	if _GCFTS_ALLOWED_KEYS is None:
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
			filter_fields_existing_in_doctype,
		)

		keys = set(
			filter_fields_existing_in_doctype(
				SALES_QUOTE_DOCTYPE, list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
			)
		)
		keys |= _ORG_SCOPE_KEYS
		_GCFTS_ALLOWED_KEYS = frozenset(keys)
	return _GCFTS_ALLOWED_KEYS


def parse_gcfts_filter_overrides(filter_overrides) -> dict[str, str]:
	if not filter_overrides:
		return {}
	if isinstance(filter_overrides, str):
		try:
			filter_overrides = frappe.parse_json(filter_overrides)
		except Exception:
			return {}
	if not isinstance(filter_overrides, dict):
		return {}
	allowed = _gcfts_allowed_filter_keys()
	out: dict[str, str] = {}
	for k, v in filter_overrides.items():
		if k not in allowed:
			continue
		out[k] = "" if v is None else str(v).strip()
	return out


def effective_sales_quote_scope_for_tariff(doc, filter_overrides) -> dict[str, str]:
	"""Scope parameters used to pick tariff charge lines (header + org dims; GCFQ-style overrides)."""
	from logistics.utils.sales_quote_charge_parameters import resolve_parameters_from_sales_quote_scope

	ov = parse_gcfts_filter_overrides(filter_overrides)
	if not ov:
		scope = dict(resolve_parameters_from_sales_quote_scope(doc))
		for fn in _ORG_SCOPE_KEYS:
			val = getattr(doc, fn, None)
			if val is not None and str(val).strip():
				scope[fn] = val
		return {k: str(v).strip() for k, v in scope.items() if v is not None and str(v).strip()}
	return {k: (ov.get(k) or "").strip() for k in ov}


def tariff_charge_row_matches_sales_quote_scope(row, scope_filters: dict[str, str]) -> bool:
	"""Blank-or-equal match on Sales Quote scope fields (blank tariff line = wildcard)."""

	def _g(fn):
		return getattr(row, fn, None) if not isinstance(row, dict) else row.get(fn)

	for fn, filter_val in (scope_filters or {}).items():
		fv = (filter_val or "").strip()
		if not fv:
			continue
		if not _wildcard_link_match(_g(fn), fv):
			return False
	return True


def tariff_charge_row_matches_charge_scope(tariff_row, charge_doc, quote_doc=None) -> bool:
	"""Match a tariff line to a Sales Quote Charge using resolved routing parameters."""
	from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters

	params = extract_sales_quote_charge_parameters(charge_doc, quote_doc)
	if not params:
		return True
	filters = {
		k: str(v).strip() for k, v in params.items() if v is not None and str(v).strip()
	}
	return tariff_charge_row_matches_sales_quote_scope(tariff_row, filters)


def allowed_service_types_for_sales_quote(doc) -> set[str]:
	types: set[str] = set()
	ms = canonical_charge_service_type_for_storage(getattr(doc, "main_service", None) or "")
	if ms:
		types.add(ms)
	sq_name = getattr(doc, "name", None)
	if sq_name:
		from logistics.logistics.doctype.linked_service.linked_service import (
			get_linked_services_for_sales_quote,
		)

		for ls in get_linked_services_for_sales_quote(sq_name):
			st = canonical_charge_service_type_for_storage(getattr(ls, "service_type", None) or "")
			if st:
				types.add(st)
	return types


def iter_all_tariff_charge_rows(tariff_doc):
	for row in getattr(tariff_doc, "rates", None) or []:
		yield row


def filter_tariff_charge_rows_for_sales_quote(
	doc,
	tariff_doc,
	filter_overrides=None,
) -> list[Any]:
	"""Tariff Charge rows matching Sales Quote scope parameters and service types on the quote."""
	scope = effective_sales_quote_scope_for_tariff(doc, filter_overrides)
	allowed_st = allowed_service_types_for_sales_quote(doc)
	out: list[Any] = []
	for row in iter_all_tariff_charge_rows(tariff_doc):
		if not _row_is_active_on_date(row):
			continue
		row_st = canonical_charge_service_type_for_storage(getattr(row, "service_type", None) or "")
		if allowed_st and row_st and row_st not in allowed_st:
			continue
		if not tariff_charge_row_matches_sales_quote_scope(row, scope):
			continue
		if not (getattr(row, "item_code", None) or "").strip():
			continue
		out.append(row)
	return out


def tariff_has_matching_charge_rows_for_sales_quote(
	doc,
	tariff_doc,
	filter_overrides=None,
) -> bool:
	return bool(filter_tariff_charge_rows_for_sales_quote(doc, tariff_doc, filter_overrides))


def fetch_eligible_tariff_names_for_sales_quote(
	doc,
	*,
	filter_overrides=None,
	limit: int = 150,
) -> list[str]:
	"""Active tariffs with at least one charge line matching this Sales Quote's scope."""
	customer = sales_quote_customer(doc)
	if not customer:
		return []
	names = frappe.get_all(
		"Tariff",
		filters={"is_active": 1},
		fields=["name"],
		order_by="modified desc",
		limit_page_length=limit * 3,
	)
	eligible: list[str] = []
	for row in names:
		name = row.name
		try:
			tariff_doc = frappe.get_doc("Tariff", name)
		except Exception:
			continue
		if not _tariff_is_valid_on_date(tariff_doc):
			continue
		if not _tariff_matches_job_customer(tariff_doc, customer):
			continue
		if not tariff_has_matching_charge_rows_for_sales_quote(doc, tariff_doc, filter_overrides):
			continue
		eligible.append(name)
		if len(eligible) >= limit:
			break
	return eligible


def tariff_charge_row_as_sales_quote_charge_dict(row, tariff_name: str) -> dict:
	"""Map a Tariff Charge row to a new Sales Quote Charge child dict."""
	charge = tariff_charge_row_as_quote_like_dict(row, tariff_name)
	for k in _TARIFF_CHILD_META:
		charge.pop(k, None)
	charge["use_tariff_in_revenue"] = 1
	charge["use_tariff_in_cost"] = 1
	charge.setdefault("charge_scope", "Main")
	return charge


def sales_quote_customer(doc) -> str | None:
	if getattr(doc, "doctype", None) == SALES_QUOTE_DOCTYPE:
		return (getattr(doc, "customer", None) or "").strip() or None
	return None


def gcfts_list_filters_payload(doc, scope: dict[str, str]) -> dict:
	"""Structured labels for Initialize Tariff Schedule on Sales Quote."""
	rules = [
		_("Active tariffs only"),
		_("Tariff validity must include today"),
		_("Customer must match the tariff type rules (Customer, Group, Territory, etc.)"),
		_(
			"Each tariff charge line must match the Sales Quote scope parameters "
			"(origin, destination, carrier, customs, etc.; blank on the line matches any value)"
		),
		_("Only charge lines for the quote Main Service and Linked Services are included"),
	]
	return {
		"customer_label": _("Customer"),
		"customer": (getattr(doc, "customer", None) or "").strip(),
		"main_service": (getattr(doc, "main_service", None) or "").strip(),
		"scope": scope,
		"rules": rules,
	}
