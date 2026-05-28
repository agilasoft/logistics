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
SERVICE_TYPE_SELECT_OPTIONS = "Air\nSea\nTransport\nCustoms\nWarehousing\nSpecial Project\nExhibits"

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
	if low == "events":
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
		"Events": "exhibits",
	}
	return legacy_title.get(s)


# Select options on Sea/Air Booking (and similar) charge child tables use Title Case labels.
_OPERATIONAL_BOOKING_CHARGE_SERVICE_TYPE_LABELS = {
	"air": "Air",
	"sea": "Sea",
	"transport": "Transport",
	"custom": "Customs",
	"warehousing": "Warehousing",
	"exhibits": "Exhibits",
	"special project": "Special Project",
}


def operational_booking_charge_service_type_label(value, default="Sea"):
	"""
	Map Sales Quote Charge ``service_type`` (lowercase canonical or legacy labels) to operational
	booking charge row Select values: Air, Sea, Transport, Customs, Warehousing.
	"""
	c = canonical_charge_service_type_for_storage(value)
	if c and c in _OPERATIONAL_BOOKING_CHARGE_SERVICE_TYPE_LABELS:
		return _OPERATIONAL_BOOKING_CHARGE_SERVICE_TYPE_LABELS[c]
	s = (value or "").strip()
	if s == "Custom":
		return "Customs"
	if s in ("Air", "Sea", "Transport", "Customs", "Warehousing", "Special Project", "Exhibits"):
		return s
	return default


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
		out.append("Events")
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
	"""Doc event: delegate to sales_quote_ms_ij_rules (mutual exclusivity + quote-type rules)."""
	from logistics.utils.sales_quote_ms_ij_rules import apply_sales_quote_ms_ij_rules

	apply_sales_quote_ms_ij_rules(doc, method)


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


def filter_sales_quote_charge_rows_for_operational_doc(parent_doc, rows):
	"""Narrow Sales Quote Charge fetch results to rows that match the job's routing parameters."""
	if not rows or not parent_doc:
		return rows
	if getattr(parent_doc, "doctype", None) in _PROGRAMME_CHARGE_PARENT_DOCTYPES:
		return rows
	return [r for r in rows if sales_quote_charge_row_matches_operational_routing(parent_doc, r)]


def sales_quote_charge_filters(parent_doc, sales_quote_doc, implied_service_type=None):
	"""
	Build filters dict for frappe.get_all("Sales Quote Charge", filters=..., ...).

	When the result has no service_type key, fetch all charge rows for the quote (subject to caller
	also handling legacy child tables without service_type).

	For Air/Sea Booking and Shipment, a service_type restriction to Air or Sea includes both modes
	(see ``use_combined_air_sea_sales_quote_charge_service_type_filter``).
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
	- Separate billings **off**: **all** unified quote charge rows (+ legacy customs not already present).
	- Separate billings **on**: Customs-scoped lines only, filtered by order customs fields.
	"""
	from logistics.utils.sales_quote_link_query import filter_customs_charge_rows_for_declaration_order

	rows = list(getattr(sales_quote_doc, "charges", None) or [])
	legacy_rows = _legacy_customs_rows_for_quote(sales_quote_doc.name)
	if hasattr(sales_quote_doc, "customs") and sales_quote_doc.customs:
		legacy_rows = _merge_unified_and_legacy_customs_rows(legacy_rows, list(sales_quote_doc.customs))

	if cint(getattr(parent_doc, "is_internal_job", 0)):
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
