# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Quotation → booking/order charge flow (product rules).

**One-off Sales Quotes** (``quotation_type`` = One-off): operational jobs must be created **from
the Sales Quote** document (create booking/order actions). They are **not** selectable in
**Action → Get Charges from Quotation**; linkage is set only during that create flow.

**Regular Sales Quotes**: users **create** Sea Booking, Air Booking, Transport Order, or Declaration Order first,
then use **Action → Get Charges from Quotation** to pick a quotation and apply **charges**
(+ **routing legs** on Sea/Air where applicable). The ``sales_quote`` link is **read-only** on
the form and is written only by create-from-quote or by the apply step.

**Customer match**: only Sales Quotes whose ``customer`` matches the job's customer
(``local_customer`` on Sea/Air, ``customer`` on Transport Order) are listed and may be applied.

**Corridor match**: Sea/Air jobs use ``origin_port`` / ``destination_port``; Transport Order uses
``location_from`` / ``location_to``; Declaration Order uses ``port_of_loading`` / ``port_of_discharge``.
Customs quotations do not filter by corridor in SQL (match is always satisfied when ports are set).
If a Sales Quote has **routing legs**, the job corridor must
match a **routing leg** (origin/destination and mode). If it has **no** routing legs, the corridor
may match unified charges, legacy lines, or header ports/locations. Preview/apply enforce the same rule.

**Submitted only**: Only **submitted** Sales Quotes (``docstatus`` = 1) are listed; draft quotations
are excluded.

**Regular only**: Only ``quotation_type`` = **Regular** is listed (One-off and Project are excluded).
"""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.charge_service_type import implied_service_type_for_doctype
from logistics.utils.sales_quote_link_query import (
	fetch_eligible_regular_sales_quote_names,
	sales_quote_matches_job_corridor,
)
from logistics.utils.sales_quote_routing import apply_sales_quote_routing_to_booking

JOB_DOCTYPES = frozenset({"Sea Booking", "Air Booking", "Transport Order", "Declaration Order"})


def _sales_quote_row_eligible_for_gcfq_list(name: str, expected_customer: str) -> bool:
	"""Defensive check: list must match the same rules as preview/apply (Regular, submitted, customer)."""
	row = frappe.db.get_value(
		"Sales Quote",
		name,
		["quotation_type", "docstatus", "customer"],
		as_dict=True,
	)
	if not row:
		return False
	if (row.get("quotation_type") or "").strip() != "Regular":
		return False
	if cint(row.get("docstatus")) != 1:
		return False
	if (row.get("customer") or "").strip() != (expected_customer or "").strip():
		return False
	return True


def assert_one_off_sales_quote_job_rules(doc):
	"""One-off ``Sales Quote`` may only appear on jobs created as main/internal from Sales Quote."""
	if not getattr(doc, "sales_quote", None):
		return
	qtp = frappe.db.get_value("Sales Quote", doc.sales_quote, "quotation_type")
	if (qtp or "") != "One-off":
		return
	from frappe.utils import cint

	if cint(getattr(doc, "is_main_service", 0)) or cint(getattr(doc, "is_internal_job", 0)):
		return
	frappe.throw(
		_(
			"A One-off Sales Quote can only be linked when this document is created from Sales Quote "
			"(main service) or is a valid internal job."
		),
		title=_("Invalid Sales Quote"),
	)


def _job_customer(doc) -> str | None:
	if doc.doctype in ("Sea Booking", "Air Booking"):
		return (getattr(doc, "local_customer", None) or "").strip() or None
	if doc.doctype in ("Transport Order", "Declaration Order"):
		return (getattr(doc, "customer", None) or "").strip() or None
	return None


def _gcfq_list_filters_payload(doctype: str, customer: str, origin: str, dest: str, service_type: str) -> dict:
	"""Structured labels/values + rule lines for the Get Charges from Quotation dialog."""
	if doctype == "Transport Order":
		return {
			"service_type": service_type,
			"customer_label": _("Customer"),
			"customer": customer,
			"origin_label": _("Location From"),
			"origin": origin,
			"destination_label": _("Location To"),
			"destination": dest,
			"rules": [
				_("Submitted quotations only (draft quotations are excluded)"),
				_("Regular quotations only (One-off quotations are excluded)"),
				_("Valid until is not set or is on or after today"),
				_("Status is not Lost or Expired"),
				_(
					"If the quotation has routing legs, origin and destination must match a leg; "
					"otherwise they may match charges, legacy lines, or header fields"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	if doctype == "Declaration Order":
		return {
			"service_type": service_type,
			"customer_label": _("Customer"),
			"customer": customer,
			"origin_label": _("Port of Loading"),
			"origin": origin,
			"destination_label": _("Port of Discharge"),
			"destination": dest,
			"rules": [
				_("Submitted quotations only (draft quotations are excluded)"),
				_("Regular quotations only (One-off quotations are excluded)"),
				_("Valid until is not set or is on or after today"),
				_("Status is not Lost or Expired"),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	return {
		"service_type": service_type,
		"customer_label": _("Local Customer"),
		"customer": customer,
		"origin_label": _("Origin Port"),
		"origin": origin,
		"destination_label": _("Destination Port"),
		"destination": dest,
		"rules": [
			_("Submitted quotations only (draft quotations are excluded)"),
			_("Regular quotations only (One-off quotations are excluded)"),
			_("Valid until is not set or is on or after today"),
			_("Status is not Lost or Expired"),
			_(
				"If the quotation has routing legs, origin and destination must match a leg; "
				"otherwise they may match charges, legacy lines, or header fields"
			),
			_("Respects your permission to read Sales Quote records"),
		],
	}


def _job_corridor(doc) -> tuple[str | None, str | None]:
	"""Return (origin, destination) keys for corridor filtering — Sea/Air ports or Transport locations."""
	if doc.doctype in ("Sea Booking", "Air Booking"):
		o = (getattr(doc, "origin_port", None) or "").strip()
		d = (getattr(doc, "destination_port", None) or "").strip()
		return (o or None, d or None)
	if doc.doctype == "Transport Order":
		o = (getattr(doc, "location_from", None) or "").strip()
		d = (getattr(doc, "location_to", None) or "").strip()
		return (o or None, d or None)
	if doc.doctype == "Declaration Order":
		o = (getattr(doc, "port_of_loading", None) or "").strip()
		d = (getattr(doc, "port_of_discharge", None) or "").strip()
		return (o or None, d or None)
	return (None, None)


def _corridor_mismatch_message_for_preview(doc, service_type: str, sales_quote: str) -> str | None:
	"""Return error message if corridor does not match, else None (for API preview responses)."""
	origin, dest = _job_corridor(doc)
	if not origin or not dest:
		return str(_("Set origin and destination on this document before loading charges from a quotation."))
	if not sales_quote_matches_job_corridor(sales_quote, service_type, origin, dest):
		return str(_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote))
	return None


def _assert_sales_quote_corridor_matches_job(doc, service_type: str, sales_quote: str):
	origin, dest = _job_corridor(doc)
	if not origin or not dest:
		frappe.throw(_("Set origin and destination on this document before loading charges from a quotation."))
	if not sales_quote_matches_job_corridor(sales_quote, service_type, origin, dest):
		frappe.throw(
			_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote)
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


def _sync_quote_fields(doc):
	if doc.doctype == "Sea Booking":
		from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(doc)
	elif doc.doctype == "Air Booking":
		from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(doc)
	elif doc.doctype == "Transport Order":
		from logistics.transport.doctype.transport_order.transport_order import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(doc)


@frappe.whitelist()
def list_sales_quotes_for_job(doctype: str, docname: str):
	"""Return regular (non–One-off) Sales Quotes eligible for Get Charges from Quotation."""
	if doctype not in JOB_DOCTYPES:
		frappe.throw(_("Unsupported document type."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	service_type = implied_service_type_for_doctype(doctype)
	if not service_type:
		frappe.throw(_("Could not determine service type for {0}.").format(doctype))

	customer = _job_customer(doc)
	if not customer:
		return {
			"quotes": [],
			"message": _("Set the customer on this document before loading charges from a quotation."),
			"filters": None,
		}

	origin, dest = _job_corridor(doc)
	if not origin or not dest:
		if doctype == "Declaration Order":
			_corridor_msg = _("Set Port of Loading and Port of Discharge before loading charges from a quotation.")
		else:
			_corridor_msg = _("Set origin and destination on this document before loading charges from a quotation.")
		return {
			"quotes": [],
			"message": _corridor_msg,
			"filters": None,
		}

	filters_payload = _gcfq_list_filters_payload(doctype, customer, origin, dest, service_type)

	names = fetch_eligible_regular_sales_quote_names(
		service_type,
		customer=customer,
		reference_doctype=doctype,
		reference_name=docname,
		limit=150,
		corridor_origin=origin,
		corridor_dest=dest,
	)
	names = [n for n in names if _sales_quote_row_eligible_for_gcfq_list(n, customer)]
	if not names:
		return {
			"quotes": [],
			"message": _("No matching Sales Quotes found for this corridor."),
			"filters": filters_payload,
		}

	fields = [
		"name",
		"customer",
		"status",
		"date",
		"valid_until",
		"company",
		"origin_port",
		"destination_port",
		"location_from",
		"location_to",
	]
	rows = frappe.get_all("Sales Quote", filters={"name": ["in", names]}, fields=fields, order_by="modified desc")
	order = {n: i for i, n in enumerate(names)}
	rows.sort(key=lambda r: order.get(r.name, 9999))
	return {"quotes": rows, "message": None, "filters": filters_payload}


@frappe.whitelist()
def preview_quotation_charges_for_job(doctype: str, docname: str, sales_quote: str):
	"""Preview charges (and routing for Sea/Air) without saving."""
	if doctype not in JOB_DOCTYPES or not sales_quote:
		return {"error": _("Invalid arguments.")}

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	service_type = implied_service_type_for_doctype(doctype)
	if not service_type:
		return {"error": _("Could not determine service type for {0}.").format(doctype)}

	sq = frappe.get_doc("Sales Quote", sales_quote)
	if cint(sq.docstatus) != 1:
		return {"error": _("Only submitted Sales Quotes can be used (draft quotations are excluded).")}
	qtp = (sq.quotation_type or "").strip()
	if qtp != "Regular":
		if qtp == "One-off":
			return {"error": _("One-off quotations cannot be applied from this action.")}
		return {"error": _("Only Regular quotations can be used from this action.")}

	customer = _job_customer(doc)
	if not customer or (sq.customer or "").strip() != (customer or "").strip():
		return {"error": _("Sales Quote customer does not match this document.")}

	corr_err = _corridor_mismatch_message_for_preview(doc, service_type, sales_quote)
	if corr_err:
		return {"error": corr_err}

	if doctype == "Sea Booking":
		from logistics.sea_freight.doctype.sea_booking.sea_booking import populate_charges_from_sales_quote

		return populate_charges_from_sales_quote(docname, sales_quote)
	if doctype == "Air Booking":
		from logistics.air_freight.doctype.air_booking.air_booking import populate_charges_from_sales_quote

		return populate_charges_from_sales_quote(docname, sales_quote)
	if doctype == "Transport Order":
		from logistics.transport.doctype.transport_order.transport_order import populate_charges_from_sales_quote

		return populate_charges_from_sales_quote(docname, sales_quote)
	if doctype == "Declaration Order":
		from logistics.customs.doctype.declaration_order.declaration_order import populate_charges_from_sales_quote

		return populate_charges_from_sales_quote(docname, sales_quote)

	return {"error": _("Unsupported document type.")}


@frappe.whitelist()
def apply_quotation_charges_to_job(doctype: str, docname: str, sales_quote: str):
	"""Set ``sales_quote``, routing (Sea/Air), and charges; then save."""
	if doctype not in JOB_DOCTYPES or not sales_quote:
		frappe.throw(_("Invalid arguments."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "write", doc=doc, throw=True)

	if doc.docstatus != 0:
		frappe.throw(_("Only draft documents can load charges from a quotation."))

	sq = frappe.get_doc("Sales Quote", sales_quote)
	if cint(sq.docstatus) != 1:
		frappe.throw(_("Only submitted Sales Quotes can be used (draft quotations are excluded)."))
	qtp = (sq.quotation_type or "").strip()
	if qtp != "Regular":
		if qtp == "One-off":
			frappe.throw(
				_("One-off Sales Quotes can only be used when creating the job from Sales Quote.")
			)
		frappe.throw(_("Only Regular quotations can be used from this action."))

	customer = _job_customer(doc)
	if not customer:
		frappe.throw(_("Set the customer on this document first."))
	if (sq.customer or "").strip() != (customer or "").strip():
		frappe.throw(_("Sales Quote customer does not match this document."))

	service_type = implied_service_type_for_doctype(doctype)
	if not service_type:
		frappe.throw(_("Could not determine service type for {0}.").format(doctype))
	_assert_sales_quote_corridor_matches_job(doc, service_type, sales_quote)

	doc.flags.skip_sales_quote_on_change = True
	doc.sales_quote = sales_quote
	_sync_quote_fields(doc)

	if doc.meta.has_field("routing_legs"):
		apply_sales_quote_routing_to_booking(doc, sq)

	with _suppress_msgprint():
		if doctype == "Sea Booking":
			doc._populate_charges_from_sales_quote(sq)
		elif doctype == "Air Booking":
			doc._populate_charges_from_sales_quote(sales_quote)
			if hasattr(doc, "_normalize_charges_before_save"):
				doc._normalize_charges_before_save()
		elif doctype == "Transport Order":
			doc._populate_charges_from_sales_quote()
		elif doctype == "Declaration Order":
			doc._populate_charges_from_sales_quote()

	try:
		doc.save()
	finally:
		doc.flags.skip_sales_quote_on_change = False

	return {
		"success": True,
		"message": _("Charges applied from Sales Quote {0}.").format(sales_quote),
		"name": doc.name,
	}
