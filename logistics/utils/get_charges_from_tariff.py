# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Tariff → booking charge flow (Sea Booking, Air Booking).

**Regular bookings**: create Sea Booking or Air Booking first, then use
**Action → Get Charges from Tariff** to pick an active tariff and apply charge lines.
This is the tariff counterpart to **Action → Get Charges from Quotation**.

**Customer match**: tariffs are listed when their type rules match the booking's
``local_customer`` (Customer, Customer Group, Territory, Specific Customers, All Customers, Agent).

**Corridor match**: Sea uses ``origin_port`` / ``destination_port`` and optional ``shipping_line``.
Air uses ports and optional ``airline``. Blank values on a tariff charge row are wildcards.

**Mutual exclusivity with Sales Quote**: when a Sales Quote is already linked on the booking,
the tariff action is hidden on the desk — charges should come from the quotation path instead.
"""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.charge_service_type import implied_service_type_for_doctype
from logistics.utils.tariff_charge_copy import (
	BOOKING_DOCTYPES,
	booking_customer,
	effective_booking_corridor,
	fetch_eligible_tariff_names,
	filter_tariff_charge_rows_for_booking,
	gcft_list_filters_payload,
	parse_gcft_filter_overrides,
	tariff_charge_row_as_quote_like_dict,
)


@contextmanager
def _suppress_msgprint():
	orig = frappe.msgprint

	def _noop(*args, **kwargs):
		return None

	frappe.msgprint = _noop  # type: ignore[assignment]
	try:
		yield
	finally:
		frappe.msgprint = orig  # type: ignore[assignment]


def _assert_no_sales_quote_linked(doc):
	from logistics.utils.operational_rep_fields import _resolve_sales_quote_name_from_doc

	if _resolve_sales_quote_name_from_doc(doc):
		frappe.throw(
			_("A Sales Quote is already linked. Use Get Charges from Quotation or clear the Sales Quote first."),
			title=_("Sales Quote linked"),
		)


def _tariff_preview_rows(doc, tariff_name: str, overrides: dict | None = None) -> dict:
	"""Build preview response using the booking's populate_charges_from_tariff whitelisted API."""
	ov = overrides or {}
	if doc.doctype == "Sea Booking":
		from logistics.sea_freight.doctype.sea_booking.sea_booking import populate_charges_from_tariff

		return populate_charges_from_tariff(doc.name, tariff_name, filter_overrides=ov)
	if doc.doctype == "Air Booking":
		from logistics.air_freight.doctype.air_booking.air_booking import populate_charges_from_tariff

		return populate_charges_from_tariff(doc.name, tariff_name, filter_overrides=ov)
	return {"error": _("Unsupported document type."), "charges": []}


@frappe.whitelist()
def list_tariffs_for_job(doctype: str, docname: str, filter_overrides=None):
	"""Return active tariffs eligible for Get Charges from Tariff."""
	if doctype not in BOOKING_DOCTYPES:
		frappe.throw(_("Unsupported document type."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	service_type = implied_service_type_for_doctype(doctype)
	if not service_type:
		frappe.throw(_("Could not determine service type for {0}.").format(doctype))

	customer = booking_customer(doc)
	if not customer:
		return {
			"tariffs": [],
			"message": _("Set Local Customer before loading charges from a tariff."),
			"filters": None,
		}

	ov = parse_gcft_filter_overrides(doctype, filter_overrides)
	origin, dest, airline, shipping_line = effective_booking_corridor(doc, ov)

	extra_kw = {}
	if shipping_line:
		extra_kw["shipping_line"] = shipping_line
	if airline:
		extra_kw["airline"] = airline
	filters_payload = gcft_list_filters_payload(
		doctype, customer, origin, dest, service_type, **extra_kw
	)

	names = fetch_eligible_tariff_names(
		doctype,
		doc,
		customer,
		service_type,
		origin=origin,
		destination=dest,
		airline=airline,
		shipping_line=shipping_line,
	)

	if not names:
		has_corridor = bool((origin or "").strip() or (dest or "").strip())
		if doctype == "Sea Booking":
			has_corridor = has_corridor or bool((shipping_line or "").strip())
		elif doctype == "Air Booking":
			has_corridor = has_corridor or bool((airline or "").strip())
		empty_msg = (
			_("No matching tariffs for this corridor.")
			if has_corridor
			else _("No matching tariffs found.")
		)
		return {"tariffs": [], "message": empty_msg, "filters": filters_payload}

	fields = [
		"name",
		"tariff_name",
		"tariff_type",
		"customer",
		"valid_from",
		"valid_to",
		"description",
		"total_rates",
	]
	rows = frappe.get_all("Tariff", filters={"name": ["in", names]}, fields=fields, order_by="modified desc")
	order = {n: i for i, n in enumerate(names)}
	rows.sort(key=lambda r: order.get(r.name, 9999))
	return {"tariffs": rows, "message": None, "filters": filters_payload}


@frappe.whitelist()
def preview_tariff_charges_for_job(
	doctype: str, docname: str, tariff_name: str, filter_overrides=None
):
	"""Preview tariff charge lines without saving."""
	if doctype not in BOOKING_DOCTYPES or not tariff_name:
		return {"error": _("Invalid arguments.")}

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	if not frappe.db.exists("Tariff", tariff_name):
		return {"error": _("Tariff {0} does not exist.").format(tariff_name)}

	customer = booking_customer(doc)
	if not customer:
		return {"error": _("Set Local Customer on this document first.")}

	tariff_doc = frappe.get_doc("Tariff", tariff_name)
	from logistics.utils.tariff_charge_copy import _tariff_is_valid_on_date, _tariff_matches_job_customer

	if not _tariff_is_valid_on_date(tariff_doc):
		return {"error": _("Tariff {0} is not active or is outside its validity period.").format(tariff_name)}
	if not _tariff_matches_job_customer(tariff_doc, customer):
		return {"error": _("Tariff {0} does not match this booking's customer.").format(tariff_name)}

	ov = parse_gcft_filter_overrides(doctype, filter_overrides)
	service_type = implied_service_type_for_doctype(doctype)
	origin, dest, airline, shipping_line = effective_booking_corridor(doc, ov)
	rows = filter_tariff_charge_rows_for_booking(
		doc,
		tariff_doc,
		service_type or "",
		origin=origin,
		destination=dest,
		airline=airline,
		shipping_line=shipping_line,
	)
	if not rows:
		return {
			"error": _("Tariff {0} has no charge lines matching this booking's corridor.").format(tariff_name),
		}

	return _tariff_preview_rows(doc, tariff_name, ov)


@frappe.whitelist()
def apply_tariff_charges_to_job(
	doctype: str, docname: str, tariff_name: str, filter_overrides=None
):
	"""Replace booking charge lines from a tariff and save."""
	if doctype not in BOOKING_DOCTYPES or not tariff_name:
		frappe.throw(_("Invalid arguments."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "write", doc=doc, throw=True)

	if doc.docstatus != 0:
		frappe.throw(_("Only draft documents can load charges from a tariff."))

	customer = booking_customer(doc)
	if not customer:
		frappe.throw(_("Set Local Customer on this document first."))

	_assert_no_sales_quote_linked(doc)

	tariff_doc = frappe.get_doc("Tariff", tariff_name)
	from logistics.utils.tariff_charge_copy import _tariff_is_valid_on_date, _tariff_matches_job_customer

	if not _tariff_is_valid_on_date(tariff_doc):
		frappe.throw(_("Tariff {0} is not active or is outside its validity period.").format(tariff_name))
	if not _tariff_matches_job_customer(tariff_doc, customer):
		frappe.throw(_("Tariff {0} does not match this booking's customer.").format(tariff_name))

	service_type = implied_service_type_for_doctype(doctype)
	ov = parse_gcft_filter_overrides(doctype, filter_overrides)
	origin, dest, airline, shipping_line = effective_booking_corridor(doc, ov)
	rows = filter_tariff_charge_rows_for_booking(
		doc,
		tariff_doc,
		service_type or "",
		origin=origin,
		destination=dest,
		airline=airline,
		shipping_line=shipping_line,
	)
	if not rows:
		frappe.throw(
			_("Tariff {0} has no charge lines matching this booking's corridor.").format(tariff_name),
			title=_("Cannot apply tariff"),
		)

	with _suppress_msgprint():
		if doctype == "Sea Booking":
			doc._populate_charges_from_tariff(tariff_name, filter_overrides=ov)
		elif doctype == "Air Booking":
			doc._populate_charges_from_tariff(tariff_name, filter_overrides=ov)
			if hasattr(doc, "_normalize_charges_before_save"):
				doc._normalize_charges_before_save()

	doc.save()

	return {
		"success": True,
		"message": _("Charges applied from Tariff {0}.").format(tariff_name),
		"name": doc.name,
		"charges_count": len(doc.get("charges") or []),
	}


def assert_tariff_customer_matches_job_before_submit(doc):
	"""Optional guard: if charge rows reference a tariff, customer must still match."""
	if doc.doctype not in BOOKING_DOCTYPES:
		return
	customer = booking_customer(doc)
	if not customer:
		return
	seen: set[str] = set()
	for ch in doc.get("charges") or []:
		for fn in ("revenue_tariff", "cost_tariff"):
			tn = (getattr(ch, fn, None) or "").strip()
			if not tn or tn in seen:
				continue
			seen.add(tn)
			tariff_customer = None
			if frappe.db.exists("Tariff", tn):
				tariff_doc = frappe.get_doc("Tariff", tn)
				from logistics.utils.tariff_charge_copy import _tariff_matches_job_customer

				if not _tariff_matches_job_customer(tariff_doc, customer):
					frappe.throw(
						_("Tariff {0} does not match this document's customer.").format(tn),
						title=_("Customer mismatch"),
					)
