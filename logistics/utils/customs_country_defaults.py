# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt

"""Country of origin/destination defaults for internal-job customs documents."""

from __future__ import annotations

import frappe
from frappe.utils import cint

_CUSTOMS_DOCTYPES = frozenset({"Declaration Order", "Declaration"})


def _is_empty(value) -> bool:
	if value is None:
		return True
	if isinstance(value, str) and not value.strip():
		return True
	return False


def _set_if_empty(doc, fieldname: str, value):
	if value is None or value == "":
		return
	if not doc.meta.get_field(fieldname):
		return
	if _is_empty(doc.get(fieldname)):
		doc.set(fieldname, value)


def country_from_unloco(unloco_code: str | None) -> str | None:
	"""Resolve a Country name (Link target) from a UNLOCO code."""
	if not unloco_code or not frappe.db.exists("UNLOCO", unloco_code):
		return None

	row = frappe.db.get_value("UNLOCO", unloco_code, ["country", "country_code"], as_dict=True)
	if not row:
		return None

	cc = (row.get("country_code") or "").strip().upper()
	if cc:
		by_code = frappe.db.get_value("Country", {"code": cc}, "name")
		if by_code:
			return by_code

	country_name = (row.get("country") or "").strip()
	if country_name and frappe.db.exists("Country", country_name):
		return country_name

	return None


def _row_get(row, key, default=None):
	if row is None:
		return default
	if isinstance(row, dict):
		return row.get(key, default)
	return getattr(row, key, default)


def _main_job_has_field(main_job_doc, fieldname: str) -> bool:
	meta = getattr(main_job_doc, "meta", None)
	if meta is not None and hasattr(meta, "has_field"):
		return bool(meta.has_field(fieldname))
	return hasattr(main_job_doc, fieldname)


def _first_main_routing_leg(shipment_doc):
	"""First Main routing leg by idx (Sea/Air Shipment routing_legs child table)."""
	legs = sorted(
		getattr(shipment_doc, "routing_legs", None) or [],
		key=lambda r: int(_row_get(r, "idx") or 0),
	)
	for leg in legs:
		if (_row_get(leg, "type") or "").strip() == "Main":
			return leg
	return None


def _origin_port_candidates(doc, main_job_doc) -> list[str]:
	ports: list[str] = []
	if main_job_doc and _main_job_has_field(main_job_doc, "origin_port"):
		ports.append(getattr(main_job_doc, "origin_port", None))
	ports.append(getattr(doc, "port_of_loading", None))
	if main_job_doc and getattr(main_job_doc, "routing_legs", None) is not None:
		leg = _first_main_routing_leg(main_job_doc)
		if leg:
			ports.append(_row_get(leg, "load_port"))
	if main_job_doc and _main_job_has_field(main_job_doc, "mbl_origin_port"):
		ports.append(getattr(main_job_doc, "mbl_origin_port", None))
	return [p for p in ports if p]


def _destination_port_candidates(doc, main_job_doc) -> list[str]:
	ports: list[str] = []
	if main_job_doc and _main_job_has_field(main_job_doc, "destination_port"):
		ports.append(getattr(main_job_doc, "destination_port", None))
	ports.append(getattr(doc, "port_of_discharge", None))
	if main_job_doc and getattr(main_job_doc, "routing_legs", None) is not None:
		leg = _first_main_routing_leg(main_job_doc)
		if leg:
			ports.append(_row_get(leg, "discharge_port"))
	if main_job_doc and _main_job_has_field(main_job_doc, "mbl_destination_port"):
		ports.append(getattr(main_job_doc, "mbl_destination_port", None))
	return [p for p in ports if p]


def _country_from_port_candidates(port_codes: list[str]) -> str | None:
	for port in port_codes:
		country = country_from_unloco(port)
		if country:
			return country
	return None


def _load_main_job_doc(doc):
	main_job_type = getattr(doc, "main_job_type", None)
	main_job = getattr(doc, "main_job", None)
	if not main_job_type or not main_job or not frappe.db.exists(main_job_type, main_job):
		return None
	try:
		return frappe.get_cached_doc(main_job_type, main_job)
	except Exception:
		return None


def _main_job_has_linked_master_transport(main_job_doc) -> bool:
	"""True when the main freight job has a linked Master Bill or Master Air Waybill record."""
	if not main_job_doc:
		return False
	if main_job_doc.doctype == "Sea Shipment":
		mbl = (getattr(main_job_doc, "master_bill", None) or "").strip()
		return bool(mbl and frappe.db.exists("Master Bill", mbl))
	if main_job_doc.doctype == "Air Shipment":
		mawb = (getattr(main_job_doc, "master_awb", None) or "").strip()
		return bool(mawb and frappe.db.exists("Master Air Waybill", mawb))
	return False


def _apply_port_fallback_countries(doc, main_job_doc) -> None:
	"""When MBL/MAWB ports are blank, derive countries from shipment / order UNLOCO ports."""
	if _is_empty(doc.get("country_of_origin")):
		origin = _country_from_port_candidates(_origin_port_candidates(doc, main_job_doc))
		_set_if_empty(doc, "country_of_origin", origin)
	if _is_empty(doc.get("country_of_destination")):
		destination = _country_from_port_candidates(_destination_port_candidates(doc, main_job_doc))
		_set_if_empty(doc, "country_of_destination", destination)


def apply_internal_job_customs_country_defaults(doc):
	"""Fill internal-job customs transport header fields from MBL/MAWB on the main freight job."""
	from logistics.utils.customs_master_transport_defaults import (
		apply_internal_job_master_transport_defaults,
	)

	if doc.doctype not in _CUSTOMS_DOCTYPES or not cint(getattr(doc, "is_internal_job", 0)):
		return

	apply_internal_job_master_transport_defaults(doc)

	main_job_doc = _load_main_job_doc(doc)
	if not main_job_doc or not _main_job_has_linked_master_transport(main_job_doc):
		return

	_apply_port_fallback_countries(doc, main_job_doc)
