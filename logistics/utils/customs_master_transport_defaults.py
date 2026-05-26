# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt

"""Transport header defaults for internal-job customs documents from MBL/MAWB only."""

from __future__ import annotations

import frappe
from frappe.utils import cint

from logistics.utils.customs_country_defaults import (
	_CUSTOMS_DOCTYPES,
	_load_main_job_doc,
	_set_if_empty,
	country_from_unloco,
)


def _sea_vessel_flight_display(master_bill) -> str | None:
	vessel = (getattr(master_bill, "vessel", None) or "").strip()
	voyage = (getattr(master_bill, "voyage_no", None) or "").strip()
	if vessel and voyage:
		return f"{vessel} / {voyage}"
	if vessel:
		return vessel
	if voyage:
		return voyage
	return None


def _apply_from_master_bill(doc, main_job_doc) -> bool:
	mbl_name = (getattr(main_job_doc, "master_bill", None) or "").strip()
	if not mbl_name or not frappe.db.exists("Master Bill", mbl_name):
		return False

	try:
		mbl = frappe.get_cached_doc("Master Bill", mbl_name)
	except Exception:
		return False

	_set_if_empty(doc, "vessel_flight_number", _sea_vessel_flight_display(mbl))
	_set_if_empty(doc, "transport_document_number", getattr(mbl, "master_bl", None))

	origin = country_from_unloco(getattr(mbl, "origin_port", None))
	if origin:
		_set_if_empty(doc, "country_of_origin", origin)

	destination = country_from_unloco(getattr(mbl, "destination_port", None))
	if destination:
		_set_if_empty(doc, "country_of_destination", destination)

	return True


def _apply_from_master_air_waybill(doc, main_job_doc) -> bool:
	mawb_name = (getattr(main_job_doc, "master_awb", None) or "").strip()
	if not mawb_name or not frappe.db.exists("Master Air Waybill", mawb_name):
		return False

	try:
		mawb = frappe.get_cached_doc("Master Air Waybill", mawb_name)
	except Exception:
		return False

	_set_if_empty(doc, "vessel_flight_number", getattr(mawb, "flight_no", None))
	_set_if_empty(doc, "transport_document_number", getattr(mawb, "master_awb_no", None))

	origin = country_from_unloco(getattr(mawb, "origin_airport", None))
	if origin:
		_set_if_empty(doc, "country_of_origin", origin)

	destination = country_from_unloco(getattr(mawb, "destination_airport", None))
	if destination:
		_set_if_empty(doc, "country_of_destination", destination)

	return True


def apply_internal_job_master_transport_defaults(doc) -> None:
	"""Fill transport header fields from Master Bill / Master Air Waybill on the main freight job only."""
	if doc.doctype not in _CUSTOMS_DOCTYPES or not cint(getattr(doc, "is_internal_job", 0)):
		return

	main_job_doc = _load_main_job_doc(doc)
	if not main_job_doc:
		return

	main_job_type = (getattr(doc, "main_job_type", None) or "").strip()
	if main_job_type == "Sea Shipment":
		_apply_from_master_bill(doc, main_job_doc)
	elif main_job_type == "Air Shipment":
		_apply_from_master_air_waybill(doc, main_job_doc)
