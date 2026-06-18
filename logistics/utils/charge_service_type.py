# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Sales Quote Charge rows are scoped by service_type (Air, Sea, Transport, Customs, Warehousing in the UI;
canonical lowercase air/sea/transport/custom/warehousing is used for comparisons). Legacy label ``Custom`` is accepted.

Operational charge tables mirror this. Helpers build filters when copying quote → booking/shipment/job.

Air and Sea Booking/Shipment documents fetch Sales Quote Charge rows for **both** Air and Sea
``service_type`` values when the quote filter would otherwise restrict to one mode (separate billing
or internal-job detail), so multimodal quotes still populate charges on either leg.

Internal jobs do not take line items from the Sales Quote; they take charge rows from the Main Job
document whose **service_type** matches the internal job (e.g. Transport / Customs).
When separate_billings_per_service_type is off on the Sales Quote, Declaration Order / Declaration
receive **all** quote charge rows (combined billing). Sea/Air/Transport bookings use main-job routing
rules in their own populate paths. When separate billings is on, declaration documents receive only
Customs-scoped lines (plus legacy ``Sales Quote Customs``), filtered by the order's customs fields.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint

# Same options as Sales Quote Charge.service_type / Change Request Charge.service_type (stored as UI labels).
SERVICE_TYPE_SELECT_OPTIONS = "Air\nSea\nTransport\nCustoms\nWarehousing\nSpecial Project\nMICE"

IMPLIED_SERVICE_TYPE_BY_DOCTYPE = {
	"Air Booking": "Air",
	"Air Shipment": "Air",
	"Sea Booking": "Sea",
	"Sea Shipment": "Sea",
	"Transport Order": "Transport",
	"Transport Job": "Transport",
	"Declaration": "Customs",
	"Declaration Order": "Customs",
	"Warehouse Job": "Warehousing",
	"Inbound Order": "Warehousing",
	"Special Project": "Special Project",
	"Project Order": "Special Project",
	"Project Job": "Special Project",
	"Exhibit": "Exhibits",
	"Exhibit Job": "Exhibits",
	"Exhibit Order": "Exhibits",
	"MICE Project": "MICE",
	"MICE Job": "MICE",
	"MICE Order": "MICE",
	"Docket": "Exhibits",
}


def canonical_charge_service_type_for_storage(value):
	"""
	Normalize charge-line service_type to canonical lowercase (air, sea, transport, custom, warehousing)
	for comparisons and filters. Accepts UI labels (Air, Customs, …) and legacy ``Custom`` / lowercase DB values.
	"""
	if value is None:
		return None
	s = (value if isinstance(value, str) else str(value)).strip()
	if not s:
		return None
	low = s.lower()
	if low in ("custom", "customs"):
		return "custom"
	if low in ("air", "sea", "transport", "warehousing", "special project", "exhibits"):
		return low
	if low in ("events", "mice"):
		return "exhibits"
	legacy_title = {
		"Air": "air",
		"Sea": "sea",
		"Transport": "transport",
		"Custom": "custom",
		"Customs": "custom",
		"Warehousing": "warehousing",
		"Special Project": "special project",
		"Exhibits": "exhibits",
		"MICE": "exhibits",
		"Events": "exhibits",
	}
	return legacy_title.get(s)


# Select options on Sea/Air Booking (and similar) charge child tables use Title Case labels.
OPERATIONAL_CHARGE_CHILD_SERVICE_TYPE_OPTIONS = (
	"Air\nSea\nTransport\nCustoms\nWarehousing\nSpecial Project\nMICE"
)

_OPERATIONAL_BOOKING_CHARGE_SERVICE_TYPE_LABELS = {
	"air": "Air",
	"sea": "Sea",
	"transport": "Transport",
	"custom": "Customs",
	"warehousing": "Warehousing",
	"exhibits": "MICE",
	"special project": "Special Project",
}


def operational_booking_charge_service_type_label(value, default="Sea"):
	"""
	Map Sales Quote Charge ``service_type`` (lowercase canonical or legacy labels) to operational
	booking charge row Select values: Air, Sea, Transport, Customs, Warehousing, Special Project, MICE.
	"""
	c = canonical_charge_service_type_for_storage(value)
	if c and c in _OPERATIONAL_BOOKING_CHARGE_SERVICE_TYPE_LABELS:
		return _OPERATIONAL_BOOKING_CHARGE_SERVICE_TYPE_LABELS[c]
	s = (value or "").strip()
	if s == "Custom":
		return "Customs"
	if s == "Exhibits":
		return "MICE"
	if s in (
		"Air",
		"Sea",
		"Transport",
		"Customs",
		"Warehousing",
		"Special Project",
		"MICE",
	):
		return s
	return default


def filter_operational_doc_charges_for_internal_job_row(parent_doc, row=None):
	"""Keep charge rows matching the Internal Job line service type; normalize Select labels."""
	if not parent_doc:
		return
	row_st = (getattr(row, "service_type", None) or "").strip() if row else ""
	implied = implied_service_type_for_doctype(getattr(parent_doc, "doctype", None) or "")
	scope_canonical = canonical_charge_service_type_for_storage(row_st or implied)
	default_label = operational_booking_charge_service_type_label(
		row_st or implied, default=implied or "Transport"
	)
	kept = []
	for charge in list(getattr(parent_doc, "charges", None) or []):
		raw_st = (getattr(charge, "service_type", None) or "").strip()
		ch_canonical = canonical_charge_service_type_for_storage(raw_st)
		if scope_canonical and ch_canonical and ch_canonical != scope_canonical:
			continue
		charge.service_type = operational_booking_charge_service_type_label(
			raw_st or row_st or implied, default=default_label
		)
		kept.append(charge)
	parent_doc.set("charges", kept)


_MICE_PROGRAMME_CHARGE_DOCTYPES = frozenset(("MICE Project Charges",))


def programme_charge_service_type_label(value, charge_doctype=None, default=None):
	"""Map quote charge ``service_type`` to programme charge child Select options."""
	c = canonical_charge_service_type_for_storage(value)
	if charge_doctype in _MICE_PROGRAMME_CHARGE_DOCTYPES:
		if c == "exhibits":
			return "MICE"
		s = (value or "").strip()
		if s in ("Exhibits", "Events", "mice"):
			return "MICE"
	return operational_booking_charge_service_type_label(
		value, default=default if default is not None else "Sea"
	)


def charge_service_type_to_load_type_flag_field(service_type):
	"""Load Type DocType checkbox fieldname for this charge service_type (uses 'customs' on Load Type, not 'custom')."""
	c = canonical_charge_service_type_for_storage(service_type)
	if not c:
		return None
	if c == "custom":
		return "customs"
	return c


def sales_quote_charge_service_types_equal(a, b):
	"""Compare two service_type values (charge row or implied vs main_service) in canonical form."""
	ca = canonical_charge_service_type_for_storage(a)
	cb = canonical_charge_service_type_for_storage(b)
	return bool(ca and cb and ca == cb)


def normalize_charge_row_filter_service_type(value):
	"""Canonical lowercase for internal use; prefer ``iter_sales_quote_charge_service_type_db_values_for_canonical`` for DB filters."""
	return canonical_charge_service_type_for_storage(value)


def iter_sales_quote_charge_service_type_db_values_for_canonical(canonical_or_label):
	"""Possible ``service_type`` DB values for one logical charge service (legacy lowercase + UI Title Case)."""
	c = canonical_charge_service_type_for_storage(canonical_or_label)
	if not c:
		return []
	legacy_title = {
		"air": "Air",
		"sea": "Sea",
		"transport": "Transport",
		"custom": "Customs",
		"warehousing": "Warehousing",
		"special project": "Special Project",
		"exhibits": "Exhibits",
	}
	title = legacy_title.get(c)
	out = [c]
	if title:
		out.append(title)
	if c == "exhibits":
		out.extend(["Events", "MICE", "mice", "Exhibits"])
	# Legacy/older data sometimes stored expanded labels in service_type.
	# Keep these here so link queries and eligibility checks still find the right quotations.
	if c == "air":
		out.extend(["Air Freight", "air freight", "airfreight", "AirFreight"])
	if c == "sea":
		out.extend(["Sea Freight", "sea freight", "seafreight", "SeaFreight"])
	if c == "custom":
		out.append("Custom")
	return list(dict.fromkeys(out))


_QUOTE_CHARGE_AIR_SEA_FETCH_COMBINED_DOCTYPES = frozenset(
	("Air Booking", "Air Shipment", "Sea Booking", "Sea Shipment")
)


def iter_combined_air_sea_sales_quote_charge_service_type_db_values():
	"""DB variants for Sales Quote Charge.service_type that mean Air or Sea (cross-freight fetch)."""
	combined = []
	for c in ("air", "sea"):
		combined.extend(iter_sales_quote_charge_service_type_db_values_for_canonical(c))
	return list(dict.fromkeys(combined))


def use_combined_air_sea_sales_quote_charge_service_type_filter(parent_doc, implied_or_label):
	"""Whether to fetch both Air and Sea quote charge rows for this parent and logical service type."""
	if not parent_doc:
		return False
	if getattr(parent_doc, "doctype", None) not in _QUOTE_CHARGE_AIR_SEA_FETCH_COMBINED_DOCTYPES:
		return False
	c = canonical_charge_service_type_for_storage(implied_or_label)
	return c in ("air", "sea")


def sales_quote_charge_filters_air_sea_service_types_combined():
	"""Filter fragment for Sales Quote Charge queries: any Air or Sea service_type (all DB variants)."""
	variants = iter_combined_air_sea_sales_quote_charge_service_type_db_values()
	if not variants:
		return {}
	if len(variants) == 1:
		return {"service_type": variants[0]}
	return {"service_type": ["in", variants]}


def apply_sales_quote_charge_service_type_to_filters(base, implied_or_label, parent_doc=None):
	"""Set ``service_type`` on a frappe filter dict (handles legacy and Title Case DB values).

	For Air/Sea Booking and Shipment, a filter for logical Air or Sea includes both modes' DB values.
	"""
	if use_combined_air_sea_sales_quote_charge_service_type_filter(parent_doc, implied_or_label):
		variants = iter_combined_air_sea_sales_quote_charge_service_type_db_values()
	else:
		variants = iter_sales_quote_charge_service_type_db_values_for_canonical(implied_or_label)
	if not variants:
		return
	if len(variants) == 1:
		base["service_type"] = variants[0]
	else:
		base["service_type"] = ["in", variants]


def sales_quote_charge_filters_service_type_only(service_type_label):
	"""Filter dict for Sales Quote Charge queries by logical service type (includes legacy Title Case)."""
	variants = iter_sales_quote_charge_service_type_db_values_for_canonical(service_type_label)
	if not variants:
		return {}
	if len(variants) == 1:
		return {"service_type": variants[0]}
	return {"service_type": ["in", variants]}


def count_sales_quote_charges_for_service(parent_name, service_type_label):
	"""Count charge child rows for a quote and service type (legacy + canonical values)."""
	variants = iter_sales_quote_charge_service_type_db_values_for_canonical(service_type_label)
	if not variants:
		return 0
	base = {"parent": parent_name, "parenttype": "Sales Quote"}
	if len(variants) == 1:
		return frappe.db.count("Sales Quote Charge", {**base, "service_type": variants[0]})
	return frappe.db.count("Sales Quote Charge", {**base, "service_type": ["in", variants]})


# Internal Job Detail: user selects Service Type; Job Type is set automatically to the target DocType.
INTERNAL_JOB_DETAIL_JOB_TYPE_BY_SERVICE_TYPE = {
	"Air": "Air Booking",
	"air": "Air Booking",
	"Sea": "Sea Booking",
	"sea": "Sea Booking",
	"Transport": "Transport Order",
	"transport": "Transport Order",
	"Custom": "Declaration Order",
	"Customs": "Declaration Order",
	"custom": "Declaration Order",
	"customs": "Declaration Order",
	"Warehousing": "Inbound Order",
	"warehousing": "Inbound Order",
	"Special Project": "Project Order",
	"special project": "Project Order",
	"MICE": "MICE Order",
	"mice": "MICE Order",
	"Events": "MICE Order",
	"events": "MICE Order",
	"Exhibits": "Exhibit Job",
	"exhibits": "Exhibit Job",
}

# Routing leg job_type values that identify the same operational leg as the parent document
ROUTING_LEG_JOB_TYPES = {
	"Air Booking": ("Air Booking",),
	"Air Shipment": ("Air Shipment", "Air Booking"),
	"Sea Booking": ("Sea Booking",),
	"Sea Shipment": ("Sea Shipment", "Sea Booking"),
	"Transport Order": ("Transport Order",),
	"Transport Job": ("Transport Job", "Transport Order"),
	"Declaration": ("Declaration", "Declaration Order"),
	"Declaration Order": ("Declaration", "Declaration Order"),
	"Warehouse Job": ("Warehouse Job",),
	"General Job": ("General Job",),
}


def implied_service_type_for_doctype(doctype):
	return IMPLIED_SERVICE_TYPE_BY_DOCTYPE.get(doctype)


def default_job_type_for_internal_job_service_type(service_type):
	"""Operational DocType created from an Internal Job Detail row for this service type."""
	if not service_type:
		return ""
	return INTERNAL_JOB_DETAIL_JOB_TYPE_BY_SERVICE_TYPE.get((service_type or "").strip(), "")


def effective_internal_job_detail_job_type(row):
	"""Operational job type for matching and create flows: mapped service_type wins over stored job_type."""
	if not row:
		return ""
	jt = (getattr(row, "job_type", None) or "").strip()
	if jt in ("Inbound Order", "Release Order", "Transfer Order"):
		return jt
	st = (getattr(row, "service_type", None) or "").strip()
	mapped = default_job_type_for_internal_job_service_type(st)
	if mapped:
		return mapped
	return jt


def on_validate_main_service_internal_job(doc, method=None):
	"""Doc event: delegate to service_role_rules (Main / Linked / Standalone)."""
	from logistics.utils.service_role_rules import apply_service_role_rules

	apply_service_role_rules(doc, method)


def is_parent_main_job_for_quote_charges(parent_doc, sales_quote_doc):
	"""
	Whether parent_doc should be treated as the quote's main job for charge expansion
	(all service types when separate billings is off).
	"""
	sq = sales_quote_doc
	acceptable = ROUTING_LEG_JOB_TYPES.get(parent_doc.doctype)
	legs = getattr(sq, "routing_legs", None) or []
	if legs and acceptable:
		my_name = getattr(parent_doc, "name", None)
		for leg in legs:
			if not cint(getattr(leg, "is_main_job", 0)):
				continue
			if getattr(leg, "job_type", None) not in acceptable:
				continue
			leg_job_no = getattr(leg, "job_no", None)
			if my_name:
				if leg_job_no == my_name:
					return True
			else:
				if not leg_job_no or leg_job_no == my_name:
					return True
		return False
	# No routing legs: same fallback as legacy (main_service on quote)
	if not legs:
		ms = getattr(sq, "main_service", None)
		impl = implied_service_type_for_doctype(parent_doc.doctype)
		return sales_quote_charge_service_types_equal(impl, ms)
	return False


def _sq_charge_row_field(row, fieldname):
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def sales_quote_charge_row_matches_operational_routing(parent_doc, row):
	"""
	Return False when a Sales Quote Charge row is scoped to different ports/locations than the job.

	Rows with blank origin_port/destination_port (or location_from/location_to for Transport) act as
	wildcards. When the operational document has no port/location set yet, rows are not excluded.

	Air quote rows are not matched to Sea Booking/Shipment ports (and Sea rows not to Air Booking/Shipment):
	charge lines often use different locode semantics per mode, which would wrongly drop multimodal lines.

	Programme service types (``Special Project`` / ``Exhibits``) only fit on programme parents whose
	implied service type is also programme; operational bookings/shipments/orders use child tables
	whose ``service_type`` Select rejects these labels, so the rows must not be copied across.
	"""
	row_st = canonical_charge_service_type_for_storage(_sq_charge_row_field(row, "service_type"))
	parent_dt = getattr(parent_doc, "doctype", None) or ""
	if row_st in ("special project", "exhibits"):
		parent_implied = canonical_charge_service_type_for_storage(
			implied_service_type_for_doctype(parent_dt)
		)
		return parent_implied in ("special project", "exhibits")
	if row_st == "air" and parent_dt in ("Sea Booking", "Sea Shipment"):
		return True
	if row_st == "sea" and parent_dt in ("Air Booking", "Air Shipment"):
		return True

	if row_st == "transport":
		plf = (getattr(parent_doc, "location_from", None) or "").strip()
		plt = (getattr(parent_doc, "location_to", None) or "").strip()
		rlf = (_sq_charge_row_field(row, "location_from") or "").strip()
		rlt = (_sq_charge_row_field(row, "location_to") or "").strip()
		if rlf and plf and rlf != plf:
			return False
		if rlt and plt and rlt != plt:
			return False
		return True

	if row_st in ("sea", "air"):
		pop = (getattr(parent_doc, "origin_port", None) or "").strip()
		pdp = (getattr(parent_doc, "destination_port", None) or "").strip()
		rop = (_sq_charge_row_field(row, "origin_port") or "").strip()
		rdp = (_sq_charge_row_field(row, "destination_port") or "").strip()
		if rop and pop and rop != pop:
			return False
		if rdp and pdp and rdp != pdp:
			return False
		return True

	return True


_PROGRAMME_CHARGE_PARENT_DOCTYPES = frozenset(
	("Special Project", "Exhibit", "Project Job", "Exhibit Job", "Exhibit Order")
)


def _internal_job_param_filter_for_parent(parent_doc) -> dict | None:
	"""Service-scoped Internal Job parameter dict for an IJ-flagged booking/order, or ``None``.

	Used by :func:`filter_sales_quote_charge_rows_for_operational_doc` so that "Get Charges from
	Quotation" on an internal-job-flagged Booking/Order only pulls Sales Quote Charge rows whose
	parameter columns (airline, shipping_line, customs_broker, …) match the canonical Internal Job
	record linked from ``parent_doc.internal_job``. The implied service type from the parent's
	doctype drives which parameter fields are compared (Air / Sea / Transport / Customs).

	Returns ``None`` to opt the row out of additional filtering (no IJ link / Internal Job record
	missing / no meaningful params).
	"""
	if not parent_doc or not cint(getattr(parent_doc, "is_internal_job", 0)):
		return None
	ij_name = (getattr(parent_doc, "internal_job", None) or "").strip()
	if not ij_name:
		return None
	if not frappe.db.exists("Internal Job", ij_name):
		return None
	implied = implied_service_type_for_doctype(getattr(parent_doc, "doctype", None) or "")
	if not implied:
		return None
	try:
		ij_doc = frappe.get_cached_doc("Internal Job", ij_name)
	except Exception:
		return None
	try:
		from logistics.utils.sales_quote_charge_parameters import (
			extract_service_scoped_quote_parameters,
		)
	except Exception:
		return None
	params = extract_service_scoped_quote_parameters(ij_doc, implied)
	return params or None


def filter_sales_quote_charge_rows_for_operational_doc(parent_doc, rows):
	"""Narrow Sales Quote Charge fetch results to rows that match the job's routing parameters.

	When the parent is an Internal Job booking/order with ``internal_job`` set, also drop rows whose
	parameter columns don't match the canonical Internal Job (so an IJ Transport Order pulls only
	the lines tagged for that specific Internal Job, not Main-scope or other-IJ rows).
	"""
	if not rows or not parent_doc:
		return rows
	if getattr(parent_doc, "doctype", None) in _PROGRAMME_CHARGE_PARENT_DOCTYPES:
		return rows
	filtered = [r for r in rows if sales_quote_charge_row_matches_operational_routing(parent_doc, r)]

	ij_params = _internal_job_param_filter_for_parent(parent_doc)
	if not ij_params:
		return filtered
	try:
		from logistics.utils.sales_quote_charge_parameters import (
			sales_quote_charge_row_matches_internal_job_detail_params,
		)
	except Exception:
		return filtered
	return [
		r
		for r in filtered
		if sales_quote_charge_row_matches_internal_job_detail_params(r, ij_params)
	]


def is_combined_billing_main_service_booking(parent_doc, sales_quote_doc) -> bool:
	"""True when the quote uses combined billing and *parent_doc* is its main-service job.

	Used by Action → Get Charges from Quotation: with ``separate_billings_per_service_type`` off,
	the main Sea/Air/Transport/Customs booking must receive **all** quote charge rows (not only
	its implied ``service_type``). Matches ``is_main_service`` or the job doctype implied service
	against the quote header ``main_service``.
	"""
	if not parent_doc or not sales_quote_doc:
		return False
	if cint(getattr(parent_doc, "is_internal_job", 0)):
		return False
	if cint(getattr(sales_quote_doc, "separate_billings_per_service_type", 0)):
		return False
	quote_main = getattr(sales_quote_doc, "main_service", None)
	implied = implied_service_type_for_doctype(getattr(parent_doc, "doctype", None))
	if not sales_quote_charge_service_types_equal(implied, quote_main):
		return False
	if cint(getattr(parent_doc, "is_main_service", 0)):
		return True
	# GCFQ on the main-service doctype for this quote (listing already requires main_service match).
	return bool(implied and quote_main)


def _gcfq_main_service_only_flag_set(parent_doc) -> bool:
	"""True when ``Action → Get Charges from Quotation`` requested Main-only charge fetch on this job.

	Set by ``logistics.utils.get_charges_from_quotation`` (apply / preview / list) so charge fetch
	on the Main service booking matches the listing (only the booking's implied service type).
	Internal jobs already fetch only their service type via ``populate_internal_job_charges_from_main_service``;
	this flag enforces the same shape on Main bookings without depending on the quote's
	``separate_billings_per_service_type`` setting.

	Requires ``parent_doc.flags`` to be a real ``dict`` (covers ``frappe._dict`` on Documents) so unit
	tests using bare ``MagicMock`` parents — where any attribute access yields a truthy Mock — do not
	silently look like they have the flag set.
	"""
	flags = getattr(parent_doc, "flags", None)
	if not isinstance(flags, dict):
		return False
	val = flags.get("gcfq_main_service_only")
	if val is None:
		return False
	try:
		return bool(cint(val))
	except (TypeError, ValueError):
		return False


def sales_quote_charge_filters(parent_doc, sales_quote_doc, implied_service_type=None):
	"""
	Build filters dict for frappe.get_all("Sales Quote Charge", filters=..., ...).

	When the result has no service_type key, fetch all charge rows for the quote (subject to caller
	also handling legacy child tables without service_type).

	For Air/Sea Booking and Shipment, a service_type restriction to Air or Sea includes both modes
	(see ``use_combined_air_sea_sales_quote_charge_service_type_filter``).

	Action → Get Charges from Quotation passes ``parent_doc.flags.gcfq_main_service_only`` to keep
	Main bookings/orders aligned with the listing filter (implied service type only) when
	``separate_billings_per_service_type`` is on. When separate billings is **off**, the main-service
	booking receives all quote charge rows (see ``is_combined_billing_main_service_booking``).
	"""
	from logistics.utils.routing_quote_context import routing_leg_service_type_for_parent

	implied_service_type = implied_service_type or implied_service_type_for_doctype(parent_doc.doctype)
	base = {"parent": sales_quote_doc.name, "parenttype": "Sales Quote"}
	if cint(getattr(parent_doc, "is_internal_job", 0)):
		# Quote filters are not used to populate internal job charges (see internal_job_charge_copy);
		# kept for any legacy callers that still query Sales Quote Charge for internal jobs.
		if implied_service_type:
			apply_sales_quote_charge_service_type_to_filters(base, implied_service_type, parent_doc)
		return base
	if _gcfq_main_service_only_flag_set(parent_doc):
		# Action → Get Charges from Quotation: per-service filter unless combined billing on main.
		if not is_combined_billing_main_service_booking(parent_doc, sales_quote_doc):
			if implied_service_type:
				apply_sales_quote_charge_service_type_to_filters(base, implied_service_type, parent_doc)
		return base
	rt_st = routing_leg_service_type_for_parent(parent_doc, sales_quote_doc)
	if rt_st:
		apply_sales_quote_charge_service_type_to_filters(base, rt_st, parent_doc)
		return base
	separate = cint(getattr(sales_quote_doc, "separate_billings_per_service_type", 0))
	# When separate billing is OFF, always fetch all charges regardless of routing/main-job
	if not separate:
		return base
	if implied_service_type:
		apply_sales_quote_charge_service_type_to_filters(base, implied_service_type, parent_doc)
	return base


def _sq_charge_service_type(row):
	return getattr(row, "service_type", None) or (row.get("service_type") if isinstance(row, dict) else None)


def _is_customs_sq_charge_row(row) -> bool:
	"""True if this Sales Quote Charge row is Customs / custom module."""
	return canonical_charge_service_type_for_storage(_sq_charge_service_type(row)) == "custom"


def _is_customs_related_sq_charge_row(row) -> bool:
	"""Customs service_type or customs parameters filled on a unified Sales Quote Charge row."""
	if _is_customs_sq_charge_row(row):
		return True
	ca = (_sq_charge_row_field(row, "customs_authority") or "").strip()
	dt = (_sq_charge_row_field(row, "declaration_type") or "").strip()
	cb = (_sq_charge_row_field(row, "customs_broker") or "").strip()
	return bool(ca or dt or cb)


def _legacy_customs_rows_for_quote(sales_quote_name: str) -> list:
	if not frappe.db.table_exists("Sales Quote Customs"):
		return []
	return frappe.get_all(
		"Sales Quote Customs",
		filters={"parent": sales_quote_name, "parenttype": "Sales Quote"},
		order_by="idx",
	)


def _merge_unified_and_legacy_customs_rows(unified_customs: list, legacy_rows: list) -> list:
	"""Combine unified ``Sales Quote Charge`` customs lines with legacy ``Sales Quote Customs`` rows."""
	if not legacy_rows:
		return list(unified_customs)
	if not unified_customs:
		return list(legacy_rows)
	seen = {
		(
			(_sq_charge_row_field(r, "item_code") or "").strip(),
			(_sq_charge_row_field(r, "customs_authority") or "").strip(),
			(_sq_charge_row_field(r, "declaration_type") or "").strip(),
		)
		for r in unified_customs
	}
	out = list(unified_customs)
	for leg in legacy_rows:
		key = (
			(_sq_charge_row_field(leg, "item_code") or "").strip(),
			(_sq_charge_row_field(leg, "customs_authority") or "").strip(),
			(_sq_charge_row_field(leg, "declaration_type") or "").strip(),
		)
		if key not in seen:
			out.append(leg)
			seen.add(key)
	return out


def customs_charges_rows_from_sales_quote_doc(parent_doc, sales_quote_doc):
	"""
	List of Sales Quote Charge child rows for Declaration / Declaration Order charge population.

	- Internal jobs: Customs lines only (from the quote), filtered by order customs fields.
	- Action → Get Charges from Quotation (``flags.gcfq_main_service_only``): Customs lines only
	  when separate billings is on; when separate billings is off and this is the quote's main
	  Customs job, **all** quote charge rows (combined billing).
	- Separate billings **off**: **all** unified quote charge rows (+ legacy customs not already present).
	- Separate billings **on**: Customs-scoped lines only, filtered by order customs fields.
	"""
	from logistics.utils.sales_quote_link_query import filter_customs_charge_rows_for_declaration_order

	rows = list(getattr(sales_quote_doc, "charges", None) or [])
	legacy_rows = _legacy_customs_rows_for_quote(sales_quote_doc.name)
	if hasattr(sales_quote_doc, "customs") and sales_quote_doc.customs:
		legacy_rows = _merge_unified_and_legacy_customs_rows(legacy_rows, list(sales_quote_doc.customs))

	if cint(getattr(parent_doc, "is_internal_job", 0)) or (
		_gcfq_main_service_only_flag_set(parent_doc)
		and not is_combined_billing_main_service_booking(parent_doc, sales_quote_doc)
	):
		customs_rows = _merge_unified_and_legacy_customs_rows(
			[c for c in rows if _is_customs_related_sq_charge_row(c)],
			legacy_rows,
		)
		return filter_customs_charge_rows_for_declaration_order(parent_doc, customs_rows)

	separate = cint(getattr(sales_quote_doc, "separate_billings_per_service_type", 0))
	if not separate:
		return _merge_unified_and_legacy_customs_rows(rows, legacy_rows)

	customs_rows = _merge_unified_and_legacy_customs_rows(
		[c for c in rows if _is_customs_related_sq_charge_row(c)],
		legacy_rows,
	)
	return filter_customs_charge_rows_for_declaration_order(parent_doc, customs_rows)


def _row_service_type(row):
	return (getattr(row, "service_type", None) or (row.get("service_type") if isinstance(row, dict) else None) or "").strip()


def destination_service_charge_validation(doc, required_service_type=None):
	"""
	Build a standard validation payload for destination-specific service charges.
	Used for both warning (conversion/create) and hard block (submit) flows.
	"""
	required_raw = (required_service_type or implied_service_type_for_doctype(getattr(doc, "doctype", None)) or "").strip()
	required = canonical_charge_service_type_for_storage(required_raw) or required_raw
	charges = list(getattr(doc, "charges", None) or [])
	matching = (
		[row for row in charges if canonical_charge_service_type_for_storage(_row_service_type(row)) == required]
		if required
		else charges
	)
	label = getattr(doc, "doctype", "Document")
	return {
		"required_service_type": required,
		"total_charges": len(charges),
		"matching_charges": len(matching),
		"is_valid": bool(required and matching),
		"warning_message": _(
			"No {0} charges found yet. You can continue in draft, but submit will be blocked."
		).format(required or _("required service")),
		"block_message": _(
			"Cannot submit {0}: add at least one {1} charge."
		).format(label, required or _("required service")),
	}


def throw_if_missing_destination_service_charge(doc, required_service_type=None):
	"""Hard-block submit when destination-specific charges are missing."""
	payload = destination_service_charge_validation(doc, required_service_type=required_service_type)
	if not payload.get("is_valid"):
		frappe.throw(payload.get("block_message"))


def assert_destination_service_charges_on_submit_unless_internal_job(doc, required_service_type=None):
	"""Block submit when main-service jobs have no matching charge lines; internal jobs exempt."""
	if cint(getattr(doc, "is_internal_job", 0)):
		return
	throw_if_missing_destination_service_charge(doc, required_service_type=required_service_type)
