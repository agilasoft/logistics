# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Sales Quote Charge rows are scoped by service_type (air, sea, transport, custom, warehousing),
aligned with Load Type module checkboxes. Legacy Title Case values are still accepted.

Operational charge tables mirror this. Helpers build filters when copying quote → booking/shipment/job.

Internal jobs do not take line items from the Sales Quote; they take charge rows from the Main Job
document whose **service_type** matches the internal job (e.g. Transport / Customs).
Main service documents can receive all quote charges when separate_billings_per_service_type is off
and the document is the main job (routing leg, or quote main_service fallback with no legs) or
is_main_service is set.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint

# Same options as Sales Quote Charge.service_type / Change Request Charge.service_type (lowercase = module keys).
SERVICE_TYPE_SELECT_OPTIONS = "air\nsea\ntransport\ncustom\nwarehousing"

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
}


def canonical_charge_service_type_for_storage(value):
	"""
	Normalize charge-line service_type to stored select values: air, sea, transport, custom, warehousing.
	Accepts legacy Title Case (Air, Customs, …) and aliases (customs → custom).
	"""
	if value is None:
		return None
	s = (value if isinstance(value, str) else str(value)).strip()
	if not s:
		return None
	low = s.lower()
	if low in ("custom", "customs"):
		return "custom"
	if low in ("air", "sea", "transport", "warehousing"):
		return low
	legacy_title = {
		"Air": "air",
		"Sea": "sea",
		"Transport": "transport",
		"Customs": "custom",
		"Warehousing": "warehousing",
	}
	return legacy_title.get(s)


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
	"""Value to use in frappe filters against Sales Quote Charge.service_type (DB storage form)."""
	return canonical_charge_service_type_for_storage(value)


def iter_sales_quote_charge_service_type_db_values_for_canonical(canonical_or_label):
	"""Possible ``service_type`` DB values for one logical charge service (during Title Case migration)."""
	c = canonical_charge_service_type_for_storage(canonical_or_label)
	if not c:
		return []
	legacy_title = {
		"air": "Air",
		"sea": "Sea",
		"transport": "Transport",
		"custom": "Customs",
		"warehousing": "Warehousing",
	}
	title = legacy_title.get(c)
	out = [c]
	if title:
		out.append(title)
	return out


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
	"Customs": "Declaration Order",
	"custom": "Declaration Order",
	"customs": "Declaration Order",
	"Warehousing": "Inbound Order",
	"warehousing": "Inbound Order",
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
	st = (getattr(row, "service_type", None) or "").strip()
	mapped = default_job_type_for_internal_job_service_type(st)
	if mapped:
		return mapped
	return (getattr(row, "job_type", None) or "").strip()


def on_validate_main_service_internal_job(doc, method=None):
	"""Doc event: Main Service and Internal Job are mutually exclusive.

	If Internal Job is set, Main Service is cleared (including when both are 1 after client/race/dialog).
	Does not throw. One-off–linked docs are not forced to main-only here — creation flows set flags;
	internal jobs on One-off quotes must keep ``is_internal_job`` through validate.
	"""
	if not hasattr(doc, "is_internal_job") or not hasattr(doc, "is_main_service"):
		return
	if cint(getattr(doc, "is_internal_job", 0)):
		doc.is_main_service = 0


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
	"""
	row_st = canonical_charge_service_type_for_storage(_sq_charge_row_field(row, "service_type"))

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


def filter_sales_quote_charge_rows_for_operational_doc(parent_doc, rows):
	"""Narrow Sales Quote Charge fetch results to rows that match the job's routing parameters."""
	if not rows or not parent_doc:
		return rows
	return [r for r in rows if sales_quote_charge_row_matches_operational_routing(parent_doc, r)]


def sales_quote_charge_filters(parent_doc, sales_quote_doc, implied_service_type=None):
	"""
	Build filters dict for frappe.get_all("Sales Quote Charge", filters=..., ...).

	When the result has no service_type key, fetch all charge rows for the quote (subject to caller
	also handling legacy child tables without service_type).
	"""
	from logistics.utils.routing_quote_context import routing_leg_service_type_for_parent

	implied_service_type = implied_service_type or implied_service_type_for_doctype(parent_doc.doctype)
	base = {"parent": sales_quote_doc.name, "parenttype": "Sales Quote"}
	if cint(getattr(parent_doc, "is_internal_job", 0)):
		# Quote filters are not used to populate internal job charges (see internal_job_charge_copy);
		# kept for any legacy callers that still query Sales Quote Charge for internal jobs.
		if implied_service_type:
			base["service_type"] = normalize_charge_row_filter_service_type(implied_service_type) or implied_service_type
		return base
	rt_st = routing_leg_service_type_for_parent(parent_doc, sales_quote_doc)
	if rt_st:
		base["service_type"] = normalize_charge_row_filter_service_type(rt_st) or rt_st
		return base
	separate = cint(getattr(sales_quote_doc, "separate_billings_per_service_type", 0))
	# When separate billing is OFF, always fetch all charges regardless of routing/main-job
	if not separate:
		return base
	if implied_service_type:
		base["service_type"] = normalize_charge_row_filter_service_type(implied_service_type) or implied_service_type
	return base


def _sq_charge_service_type(row):
	return getattr(row, "service_type", None) or (row.get("service_type") if isinstance(row, dict) else None)


def _is_customs_sq_charge_row(row) -> bool:
	"""True if this Sales Quote Charge row is Customs / custom module."""
	return canonical_charge_service_type_for_storage(_sq_charge_service_type(row)) == "custom"


def customs_charges_rows_from_sales_quote_doc(parent_doc, sales_quote_doc):
	"""
	List of Sales Quote Charge child rows for Declaration / Declaration Order charge population.

	- Internal jobs: Customs lines only (from the quote).
	- Separate billings on, or not the quote main job: Customs lines only.
	- Separate billings off and main job: all quote charge rows (same rule as Sea/Air main jobs).
	"""
	rows = list(getattr(sales_quote_doc, "charges", None) or [])
	customs_only = [c for c in rows if _is_customs_sq_charge_row(c)]
	if cint(getattr(parent_doc, "is_internal_job", 0)):
		return customs_only
	separate = cint(getattr(sales_quote_doc, "separate_billings_per_service_type", 0))
	main_like = is_parent_main_job_for_quote_charges(parent_doc, sales_quote_doc) or cint(
		getattr(parent_doc, "is_main_service", 0)
	)
	if not separate and main_like:
		return rows
	return customs_only


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
