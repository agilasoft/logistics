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
Dialog **filter_overrides** (per-module keys in ``GCFQ_FILTER_KEYS``) refine corridor / customs matching
for listing, preview, and apply **without** saving the job document first.

**Corridor match**: Sea Booking uses ``origin_port`` / ``destination_port``. **Air Booking** matches
those ports when both are set, and ``airline`` when set (quotation charge row or header). If the
booking has ``airline`` but either port is missing, eligible quotes are filtered **by airline only**
(unified/legacy Air charge lines). Transport Order uses ``location_from`` / ``location_to``. **Declaration Order**: same customer, Regular submitted quotations that include **Customs** charge lines.
When **Customs Authority**, **Declaration Type**, and **Customs Broker** are all set on the order, the list is
narrowed to quotations whose customs charge rows match (see ``sales_quote_link_query``); otherwise every
eligible Customs quotation for the customer is listed.

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
	sales_quote_matches_job_airline_only,
	sales_quote_matches_job_corridor,
)
from logistics.utils.sales_quote_service_eligibility import sales_quote_has_service_charges
from logistics.utils.sales_quote_routing import apply_sales_quote_routing_to_booking

JOB_DOCTYPES = frozenset({"Sea Booking", "Air Booking", "Transport Order", "Declaration Order"})

# Whitelisted keys for Action → Get Charges from Quotation dialog filters (client-sent).
GCFQ_FILTER_KEYS: dict[str, frozenset[str]] = {
	"Sea Booking": frozenset({"origin_port", "destination_port"}),
	"Air Booking": frozenset({"origin_port", "destination_port", "airline"}),
	"Transport Order": frozenset({"location_from", "location_to"}),
	"Declaration Order": frozenset(
		{
			"customs_authority",
			"declaration_type",
			"customs_broker",
			"transport_mode",
			"port_of_loading",
			"port_of_discharge",
		}
	),
}


def _parse_gcfq_filter_overrides(doctype: str, filter_overrides) -> dict[str, str]:
	"""Sanitize client filter payload to allowed string keys only."""
	if not filter_overrides:
		return {}
	if isinstance(filter_overrides, str):
		try:
			filter_overrides = frappe.parse_json(filter_overrides)
		except Exception:
			return {}
	if not isinstance(filter_overrides, dict):
		return {}
	allowed = GCFQ_FILTER_KEYS.get(doctype, frozenset())
	out: dict[str, str] = {}
	for k, v in filter_overrides.items():
		if k not in allowed:
			continue
		if v is None:
			out[k] = ""
		else:
			out[k] = str(v).strip()
	return out


def _pick_gcfq_field(doc, overrides: dict, param_key: str, doc_attr: str) -> str:
	"""Use dialog override when the client sent this key; otherwise the saved document."""
	if param_key in overrides:
		return (overrides[param_key] or "").strip()
	return (getattr(doc, doc_attr, None) or "").strip()


def _effective_sea_air_transport_corridor(
	doc, overrides: dict
) -> tuple[str, str, str | None]:
	"""(origin, destination, airline) — airline only for Air Booking."""
	dt = doc.doctype
	if dt == "Sea Booking":
		o = _pick_gcfq_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcfq_field(doc, overrides, "destination_port", "destination_port")
		return o, d, None
	if dt == "Air Booking":
		o = _pick_gcfq_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcfq_field(doc, overrides, "destination_port", "destination_port")
		al = _pick_gcfq_field(doc, overrides, "airline", "airline")
		return o, d, (al or None)
	if dt == "Transport Order":
		o = _pick_gcfq_field(doc, overrides, "location_from", "location_from")
		d = _pick_gcfq_field(doc, overrides, "location_to", "location_to")
		return o, d, None
	return "", "", None


def _effective_declaration_order_filter_fields(
	doc, overrides: dict
) -> tuple[str, str, str, str | None, str, str]:
	"""authority, declaration_type, broker, transport_mode name or None, pol, pod."""
	ca = _pick_gcfq_field(doc, overrides, "customs_authority", "customs_authority")
	dt = _pick_gcfq_field(doc, overrides, "declaration_type", "declaration_type")
	cb = _pick_gcfq_field(doc, overrides, "customs_broker", "customs_broker")
	tm_raw = _pick_gcfq_field(doc, overrides, "transport_mode", "transport_mode")
	jtm = tm_raw or None
	pol = _pick_gcfq_field(doc, overrides, "port_of_loading", "port_of_loading")
	pod = _pick_gcfq_field(doc, overrides, "port_of_discharge", "port_of_discharge")
	return ca, dt, cb, jtm, pol, pod


def _gcfq_airline_only_effective(
	service_type: str, job_airline: str | None, origin: str, dest: str
) -> bool:
	ja = (job_airline or "").strip()
	if (service_type or "").strip() != "Air" or not ja:
		return False
	return not (origin and dest)


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
					"When Customs Authority, Declaration Type, and Customs Broker are all set on this order, "
					"only quotations with matching customs charge lines are listed (blank broker on a line matches any broker); "
					"if any of those fields is blank, all quotations with Customs charges for this customer are listed"
				),
				_(
					"When Transport Mode is set, legacy customs lines with a transport mode must match it; "
					"unified Customs charge lines are not filtered by mode"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	al = (kwargs.get("airline") or "").strip()
	airline_only = bool(kwargs.get("airline_only_mode"))
	extra_criteria = []
	if al:
		extra_criteria.append({"label": _("Airline"), "value": al})
	rules = [
		_("Submitted quotations only (draft quotations are excluded)"),
		_("Regular quotations only (One-off quotations are excluded)"),
		_("Valid until is not set or is on or after today"),
		_("Status is not Lost or Expired"),
	]
	if airline_only and al:
		rules.append(
			_(
				"With Airline set and ports not both filled, only quotations with an Air charge line "
				"matching that carrier (or a blank line airline) are listed — not Sales Quote routing legs"
			)
		)
	else:
		rules.append(
			_(
				"Origin and destination must match a charge row (or legacy line) on the quotation, "
				"or the quotation header — not Sales Quote routing legs"
			)
		)
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
	out["airline_only_mode"] = airline_only
	return out


def _corridor_mismatch_message_for_preview(
	doc, service_type: str, sales_quote: str, overrides: dict | None = None
) -> str | None:
	"""Return error message if corridor does not match, else None (for API preview responses)."""
	ov = overrides or {}
	origin, dest, ja_eff = _effective_sea_air_transport_corridor(doc, ov)
	ja = (ja_eff or "").strip() or None if doc.doctype == "Air Booking" else None
	airline_only = _gcfq_airline_only_effective(service_type, ja, origin, dest)
	if doc.doctype == "Air Booking" and airline_only:
		if not sales_quote_matches_job_airline_only(sales_quote, (ja or "").strip()):
			return str(
				_("Sales Quote {0} does not match this document's airline (charge lines).").format(sales_quote)
			)
		return None
	if not origin or not dest:
		return str(
			_("Set origin and destination in the filters or on the document before loading charges from a quotation.")
		)
	if not sales_quote_matches_job_corridor(sales_quote, service_type, origin, dest, job_airline=ja):
		if ja:
			return str(
				_("Sales Quote {0} does not match this document's air corridor (ports and airline).").format(
					sales_quote
				)
			)
		return str(_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote))
	return None


def _assert_sales_quote_corridor_matches_job(
	doc, service_type: str, sales_quote: str, overrides: dict | None = None
):
	ov = overrides or {}
	origin, dest, ja_eff = _effective_sea_air_transport_corridor(doc, ov)
	ja = (ja_eff or "").strip() or None if doc.doctype == "Air Booking" else None
	airline_only = _gcfq_airline_only_effective(service_type, ja, origin, dest)
	if doc.doctype == "Air Booking" and airline_only:
		if not sales_quote_matches_job_airline_only(sales_quote, (ja or "").strip()):
			frappe.throw(
				_("Sales Quote {0} does not match this document's airline (charge lines).").format(sales_quote)
			)
		return
	if not origin or not dest:
		frappe.throw(
			_(
				"Set origin and destination in the filters or on the document before loading charges from a quotation."
			)
		)
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


def _assert_sales_quote_has_customs_charges(sales_quote: str):
	if not sales_quote_has_service_charges(sales_quote, "Customs"):
		frappe.throw(
			_("Sales Quote {0} has no Customs charge lines.").format(sales_quote),
			title=_("Invalid Sales Quote"),
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
def list_sales_quotes_for_job(doctype: str, docname: str, filter_overrides=None):
	"""Return regular (non–One-off) Sales Quotes eligible for Get Charges from Quotation.

	``filter_overrides``: optional JSON dict of dialog filter fields (see ``GCFQ_FILTER_KEYS``).
	Values override the saved document for listing only.
	"""
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

	ov = _parse_gcfq_filter_overrides(doctype, filter_overrides)

	if doctype == "Declaration Order":
		ca, dt, cb, jtm, pol, pod = _effective_declaration_order_filter_fields(doc, ov)
		tm_disp = ""
		if jtm:
			tm_disp = frappe.db.get_value("Transport Mode", jtm, "mode_name") or jtm
		filters_payload = _gcfq_list_filters_payload(
			doctype,
			customer,
			pol or "",
			pod or "",
			service_type,
			customs_authority=ca,
			declaration_type=dt,
			customs_broker=cb,
			transport_mode_display=tm_disp,
			port_of_loading=pol,
			port_of_discharge=pod,
		)
		names = fetch_eligible_regular_sales_quote_names(
			service_type,
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			customs_authority=ca or None,
			declaration_type=dt or None,
			customs_broker=cb or None,
			job_transport_mode=jtm,
		)
		empty_msg = (
			_("No matching Sales Quotes found for this customs scope.")
			if (ca and dt and cb)
			else _("No matching Sales Quotes found.")
		)
	else:
		origin, dest, job_airline = _effective_sea_air_transport_corridor(doc, ov)
		job_airline = (job_airline or "").strip() or None if doctype == "Air Booking" else None
		airline_only = _gcfq_airline_only_effective(service_type, job_airline, origin, dest)
		if (not origin or not dest) and not (doctype == "Air Booking" and job_airline):
			_corridor_msg = _(
				"Set origin and destination in the filters above (or on the document). For Air Booking you can use an airline only."
			)
			filters_payload = _gcfq_list_filters_payload(
				doctype,
				customer,
				origin or "",
				dest or "",
				service_type,
				**(
					{"airline": job_airline, "airline_only_mode": True}
					if (airline_only and job_airline)
					else ({"airline": job_airline} if job_airline else {})
				),
			)
			return {
				"quotes": [],
				"message": _corridor_msg,
				"filters": filters_payload,
			}
		if airline_only and job_airline:
			filters_payload = _gcfq_list_filters_payload(
				doctype,
				customer,
				origin or "",
				dest or "",
				service_type,
				airline=job_airline,
				airline_only_mode=True,
			)
		else:
			filters_payload = _gcfq_list_filters_payload(
				doctype,
				customer,
				origin,
				dest,
				service_type,
				**({"airline": job_airline} if job_airline else {}),
			)

		list_co, list_cd = (None, None) if airline_only else (origin, dest)
		names = fetch_eligible_regular_sales_quote_names(
			service_type,
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			corridor_origin=list_co,
			corridor_dest=list_cd,
			job_airline=job_airline,
		)
		empty_msg = (
			_("No matching Sales Quotes found for this airline.")
			if airline_only
			else _("No matching Sales Quotes found for this corridor.")
		)

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
def preview_quotation_charges_for_job(
	doctype: str, docname: str, sales_quote: str, filter_overrides=None
):
	"""Preview charges (and routing for Sea/Air) without saving."""
	if doctype not in JOB_DOCTYPES or not sales_quote:
		return {"error": _("Invalid arguments.")}

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	service_type = implied_service_type_for_doctype(doctype)
	if not service_type:
		return {"error": _("Could not determine service type for {0}.").format(doctype)}

	ov = _parse_gcfq_filter_overrides(doctype, filter_overrides)

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
		if not sales_quote_has_service_charges(sales_quote, "Customs"):
			return {
				"error": str(_("Sales Quote {0} has no Customs charge lines.").format(sales_quote)),
			}
		corr_err = None
	else:
		corr_err = _corridor_mismatch_message_for_preview(doc, service_type, sales_quote, ov)
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
def apply_quotation_charges_to_job(
	doctype: str, docname: str, sales_quote: str, filter_overrides=None
):
	"""Set ``sales_quote``, routing (Sea/Air), and charges; then save."""
	if doctype not in JOB_DOCTYPES or not sales_quote:
		frappe.throw(_("Invalid arguments."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "write", doc=doc, throw=True)

	if doc.docstatus != 0:
		frappe.throw(_("Only draft documents can load charges from a quotation."))

	ov = _parse_gcfq_filter_overrides(doctype, filter_overrides)

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
		_assert_sales_quote_has_customs_charges(sales_quote)
	else:
		_assert_sales_quote_corridor_matches_job(doc, service_type, sales_quote, ov)

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
