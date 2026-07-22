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

GCFT_FILTER_KEYS: dict[str, frozenset[str]] = {
	"Sea Booking": frozenset({"origin_port", "destination_port", "shipping_line"}),
	"Air Booking": frozenset({"origin_port", "destination_port", "airline"}),
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
	return "", "", None, None


def _booking_customer(doc) -> str | None:
	if doc.doctype in BOOKING_DOCTYPES:
		return (getattr(doc, "local_customer", None) or "").strip() or None
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
	"""Active tariffs with at least one matching charge line for this booking."""
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
		if not _tariff_matches_job_customer(tariff_doc, job_customer):
			continue
		if not tariff_has_matching_charge_rows(
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
