# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Sales Quote Charge rows are scoped by service_type (Air, Sea, Transport, Customs, Warehousing).
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

# Same options as Sales Quote Charge.service_type
SERVICE_TYPE_SELECT_OPTIONS = "Air\nSea\nTransport\nCustoms\nWarehousing"

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

# Internal Job Detail: user selects Service Type; Job Type is set automatically to the target DocType.
INTERNAL_JOB_DETAIL_JOB_TYPE_BY_SERVICE_TYPE = {
	"Air": "Air Booking",
	"Sea": "Sea Booking",
	"Transport": "Transport Order",
	"Customs": "Declaration Order",
	"Warehousing": "Inbound Order",
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
	"""Doc event: internal jobs cannot be tagged as main service."""
	sq_name = doc.get("sales_quote")
	if sq_name and frappe.db.exists("Sales Quote", sq_name):
		qt = frappe.db.get_value("Sales Quote", sq_name, "quotation_type")
		if qt == "One-off":
			if hasattr(doc, "is_main_service"):
				doc.is_main_service = 1
			if hasattr(doc, "is_internal_job"):
				doc.is_internal_job = 0
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
		return implied_service_type_for_doctype(parent_doc.doctype) == ms
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
	row_st = (_sq_charge_row_field(row, "service_type") or "").strip()

	if row_st == "Transport":
		plf = (getattr(parent_doc, "location_from", None) or "").strip()
		plt = (getattr(parent_doc, "location_to", None) or "").strip()
		rlf = (_sq_charge_row_field(row, "location_from") or "").strip()
		rlt = (_sq_charge_row_field(row, "location_to") or "").strip()
		if rlf and plf and rlf != plf:
			return False
		if rlt and plt and rlt != plt:
			return False
		return True

	if row_st in ("Sea", "Air"):
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
			base["service_type"] = implied_service_type
		return base
	rt_st = routing_leg_service_type_for_parent(parent_doc, sales_quote_doc)
	if rt_st:
		base["service_type"] = rt_st
		return base
	separate = cint(getattr(sales_quote_doc, "separate_billings_per_service_type", 0))
	# When separate billing is OFF, always fetch all charges regardless of routing/main-job
	if not separate:
		return base
	if implied_service_type:
		base["service_type"] = implied_service_type
	return base


def _sq_charge_service_type(row):
	return getattr(row, "service_type", None) or (row.get("service_type") if isinstance(row, dict) else None)


def _is_customs_sq_charge_row(row) -> bool:
	"""True if this Sales Quote Charge row is Customs (case-insensitive)."""
	st = (_sq_charge_service_type(row) or "").strip().lower()
	return st == "customs"


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
	required = (required_service_type or implied_service_type_for_doctype(getattr(doc, "doctype", None)) or "").strip()
	charges = list(getattr(doc, "charges", None) or [])
	matching = [row for row in charges if _row_service_type(row) == required] if required else charges
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
