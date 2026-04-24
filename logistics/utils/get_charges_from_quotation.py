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

**Corridor match**: Sea/Air jobs use ``origin_port`` / ``destination_port``; **Air Booking** also matches
``airline`` when it is set (quotation charge row or header airline must match or be blank for that row).
Transport Order uses ``location_from`` / ``location_to``. **Declaration Order** uses ``customs_authority``,
``declaration_type``, ``customs_broker``, and optionally ``transport_mode`` (with **Sales Quote
Charge** / **Sales Quote Customs** rows as described in ``sales_quote_link_query``), not POL/POD
as the primary gate.

The quotation must have a **charge row** (unified or legacy) or **header** ports/locations that
match that corridor. **Sales Quote** routing legs are not used for this filter. Preview/apply
enforce the same rule (for non–Declaration Order jobs).

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
from logistics.utils.operational_rep_fields import copy_operational_rep_fields_from_sales_quote_doc
from logistics.utils.sales_quote_link_query import (
	fetch_eligible_regular_sales_quote_names,
	sales_quote_matches_declaration_order_filters,
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


def _job_airline_for_gcfq(doc) -> str | None:
	"""Airline link on Air Booking for Get Charges from Quotation filtering; ``None`` if unset (no airline gate)."""
	if doc.doctype != "Air Booking":
		return None
	al = (getattr(doc, "airline", None) or "").strip()
	return al or None


def _gcfq_list_filters_payload(
	doctype: str,
	customer: str,
	origin: str,
	dest: str,
	service_type: str,
	**kwargs,
) -> dict:
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
					"Origin and destination must match a charge row (or legacy line) on the quotation, "
					"or the quotation header — not Sales Quote routing legs"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	if doctype == "Declaration Order":
		extra = [
			{"label": _("Customs Authority"), "value": kwargs.get("customs_authority") or ""},
			{"label": _("Declaration Type"), "value": kwargs.get("declaration_type") or ""},
			{"label": _("Customs Broker"), "value": kwargs.get("customs_broker") or ""},
		]
		tm = (kwargs.get("transport_mode_display") or "").strip()
		if tm:
			extra.append({"label": _("Transport Mode"), "value": tm})
		pol = (kwargs.get("port_of_loading") or "").strip()
		pod = (kwargs.get("port_of_discharge") or "").strip()
		if pol or pod:
			extra.append({"label": _("Port of Loading"), "value": pol})
			extra.append({"label": _("Port of Discharge"), "value": pod})
		return {
			"service_type": service_type,
			"customer_label": _("Customer"),
			"customer": customer,
			"extra_criteria": extra,
			"rules": [
				_("Submitted quotations only (draft quotations are excluded)"),
				_("Regular quotations only (One-off quotations are excluded)"),
				_("Valid until is not set or is on or after today"),
				_("Status is not Lost or Expired"),
				_(
					"Customs charge lines must match Customs Authority, Declaration Type, and Customs Broker "
					"(blank broker on a quotation line matches any broker)"
				),
				_(
					"When Transport Mode is set, legacy customs lines with a transport mode must match it; "
					"unified Customs charge lines are not filtered by mode"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	al = (kwargs.get("airline") or "").strip()
	extra_criteria = []
	if al:
		extra_criteria.append({"label": _("Airline"), "value": al})
	rules = [
		_("Submitted quotations only (draft quotations are excluded)"),
		_("Regular quotations only (One-off quotations are excluded)"),
		_("Valid until is not set or is on or after today"),
		_("Status is not Lost or Expired"),
		_(
			"Origin and destination must match a charge row (or legacy line) on the quotation, "
			"or the quotation header — not Sales Quote routing legs"
		),
	]
	if al:
		rules.append(
			_(
				"When Airline is set on the booking, the quotation must match that airline on a charge row "
				"or header (blank airline on a quotation line matches any carrier)"
			)
		)
	rules.append(_("Respects your permission to read Sales Quote records"))
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
	if extra_criteria:
		out["extra_criteria"] = extra_criteria
	return out


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


def _declaration_order_customs_keys(doc):
	"""Return (authority, declaration_type, broker, transport_mode_link_or_none)."""
	ca = (getattr(doc, "customs_authority", None) or "").strip()
	dt = (getattr(doc, "declaration_type", None) or "").strip()
	cb = (getattr(doc, "customs_broker", None) or "").strip()
	jtm = (getattr(doc, "transport_mode", None) or "").strip() or None
	return ca, dt, cb, jtm


def _declaration_customs_mismatch_message_for_preview(doc, sales_quote: str) -> str | None:
	ca, dt, cb, jtm = _declaration_order_customs_keys(doc)
	if not ca or not dt or not cb:
		return str(
			_("Set Customs Authority, Declaration Type, and Customs Broker before loading charges from a quotation.")
		)
	if not sales_quote_matches_declaration_order_filters(sales_quote, ca, dt, cb, jtm):
		return str(_("Sales Quote {0} does not match this document's customs scope.").format(sales_quote))
	return None


def _corridor_mismatch_message_for_preview(doc, service_type: str, sales_quote: str) -> str | None:
	"""Return error message if corridor does not match, else None (for API preview responses)."""
	origin, dest = _job_corridor(doc)
	if not origin or not dest:
		return str(_("Set origin and destination on this document before loading charges from a quotation."))
	ja = _job_airline_for_gcfq(doc)
	if not sales_quote_matches_job_corridor(sales_quote, service_type, origin, dest, job_airline=ja):
		if ja:
			return str(
				_("Sales Quote {0} does not match this document's air corridor (ports and airline).").format(
					sales_quote
				)
			)
		return str(_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote))
	return None


def _assert_sales_quote_corridor_matches_job(doc, service_type: str, sales_quote: str):
	origin, dest = _job_corridor(doc)
	if not origin or not dest:
		frappe.throw(_("Set origin and destination on this document before loading charges from a quotation."))
	ja = _job_airline_for_gcfq(doc)
	if not sales_quote_matches_job_corridor(sales_quote, service_type, origin, dest, job_airline=ja):
		if ja:
			frappe.throw(
				_("Sales Quote {0} does not match this document's air corridor (ports and airline).").format(
					sales_quote
				)
			)
		frappe.throw(
			_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote)
		)


def _assert_sales_quote_matches_declaration_order(doc, sales_quote: str):
	ca, dt, cb, jtm = _declaration_order_customs_keys(doc)
	if not ca or not dt or not cb:
		frappe.throw(
			_("Set Customs Authority, Declaration Type, and Customs Broker before loading charges from a quotation.")
		)
	if not sales_quote_matches_declaration_order_filters(sales_quote, ca, dt, cb, jtm):
		frappe.throw(_("Sales Quote {0} does not match this document's customs scope.").format(sales_quote))


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

	if doctype == "Declaration Order":
		ca, dt, cb, jtm = _declaration_order_customs_keys(doc)
		if not ca or not dt or not cb:
			return {
				"quotes": [],
				"message": _(
					"Set Customs Authority, Declaration Type, and Customs Broker before loading charges from a quotation."
				),
				"filters": None,
			}
		origin, dest = _job_corridor(doc)
		tm_disp = ""
		if jtm:
			tm_disp = frappe.db.get_value("Transport Mode", jtm, "mode_name") or jtm
		filters_payload = _gcfq_list_filters_payload(
			doctype,
			customer,
			origin or "",
			dest or "",
			service_type,
			customs_authority=ca,
			declaration_type=dt,
			customs_broker=cb,
			transport_mode_display=tm_disp,
			port_of_loading=(getattr(doc, "port_of_loading", None) or "").strip(),
			port_of_discharge=(getattr(doc, "port_of_discharge", None) or "").strip(),
		)
		names = fetch_eligible_regular_sales_quote_names(
			service_type,
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			customs_authority=ca,
			declaration_type=dt,
			customs_broker=cb,
			job_transport_mode=jtm,
		)
		empty_msg = _("No matching Sales Quotes found for this customs scope.")
	else:
		origin, dest = _job_corridor(doc)
		if not origin or not dest:
			_corridor_msg = _("Set origin and destination on this document before loading charges from a quotation.")
			return {
				"quotes": [],
				"message": _corridor_msg,
				"filters": None,
			}

		job_airline = _job_airline_for_gcfq(doc) if doctype == "Air Booking" else None
		filters_payload = _gcfq_list_filters_payload(
			doctype,
			customer,
			origin,
			dest,
			service_type,
			**({"airline": job_airline} if job_airline else {}),
		)

		names = fetch_eligible_regular_sales_quote_names(
			service_type,
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			corridor_origin=origin,
			corridor_dest=dest,
			job_airline=job_airline,
		)
		empty_msg = _("No matching Sales Quotes found for this corridor.")

	names = [n for n in names if _sales_quote_row_eligible_for_gcfq_list(n, customer)]
	if not names:
		return {
			"quotes": [],
			"message": empty_msg,
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

	if doctype == "Declaration Order":
		corr_err = _declaration_customs_mismatch_message_for_preview(doc, sales_quote)
	else:
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
	if doctype == "Declaration Order":
		_assert_sales_quote_matches_declaration_order(doc, sales_quote)
	else:
		_assert_sales_quote_corridor_matches_job(doc, service_type, sales_quote)

	doc.flags.skip_sales_quote_on_change = True
	doc.sales_quote = sales_quote
	_sync_quote_fields(doc)
	copy_operational_rep_fields_from_sales_quote_doc(doc, sq)

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
