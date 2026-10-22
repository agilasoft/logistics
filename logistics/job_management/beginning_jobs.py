# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Create pending old-system files without a Sales Quote, booking, or order.

Each file is a normal operational document inserted under the number the user
typed. Milestones, job tasks, documents, and the Job Number come from the
existing save hooks.
"""

from __future__ import unicode_literals

import re

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.job_management.prior_system_posting import PRIOR_SYSTEM_POSTED_STATUS
from logistics.utils.charge_service_type import implied_service_type_for_doctype
from logistics.utils.service_role_rules import (
	apply_linked_service_satellite_flags,
	apply_main_service_flags,
)

BEGINNING_JOB_DOCTYPES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Declaration",
	"Warehouse Job",
)

SERVICE_TYPE_TO_DOCTYPE = {
	"Air": "Air Shipment",
	"Sea": "Sea Shipment",
	"Transport": "Transport Job",
	"Customs": "Declaration",
	"Warehousing": "Warehouse Job",
	"Cross-Docking": "Warehouse Job",
}

_FILE_SPECS = {
	"Air Shipment": {
		"customer_field": "local_customer",
		"date_field": "booking_date",
		"naming_series": "ASP-.#########",
	},
	"Sea Shipment": {
		"customer_field": "local_customer",
		"date_field": "booking_date",
		"naming_series": "SSP.#########",
	},
	"Transport Job": {
		"customer_field": "customer",
		"date_field": "booking_date",
		"naming_series": "TRJ.#########",
	},
	"Declaration": {
		"customer_field": "customer",
		"date_field": "declaration_date",
		"naming_series": "CD.#########",
	},
	"Warehouse Job": {
		"customer_field": "customer",
		"date_field": "job_open_date",
		"naming_series": "WJ-.##########",
	},
}

_HEADER_FIELDS = (
	"company",
	"branch",
	"cost_center",
	"profit_center",
	"direction",
	"shipper",
	"consignee",
	"origin_port",
	"destination_port",
	"shipping_line",
	"airline",
	"load_type",
	"transport_mode",
	"vehicle_type",
	"container_type",
	"container_no",
	"location_from",
	"location_to",
	"customs_authority",
	"declaration_type",
	"transport_job_type",
	"reference_no",
	"notes",
	"milestone_template",
	"document_list_template",
	"job_task_template",
	"entry_type",
	"house_type",
	"description",
	"total_weight",
	"total_volume",
)

_PARTY_ALIASES = {
	"Declaration": {
		"shipper": "exporter_shipper",
		"consignee": "importer_consignee",
	},
}

_JOB_NUMBER_RE = re.compile(r"^[\w][\w.\- ]{0,138}$", re.UNICODE)


def validate_beginning_job(doc, method=None):
	"""Keep the beginning-job flag and prior-system statuses on the tool's path."""
	meta = getattr(doc, "meta", None)
	if meta is None or not meta.has_field("is_beginning_job"):
		return

	current = cint(getattr(doc, "is_beginning_job", 0))
	previous = 0
	if not doc.is_new() and doc.name and frappe.db.exists(doc.doctype, doc.name):
		previous = cint(frappe.db.get_value(doc.doctype, doc.name, "is_beginning_job"))

	allowed = bool(getattr(frappe.flags, "in_beginning_job", False))
	if current and not previous and not allowed:
		frappe.throw(
			_("Beginning Job can only be set by the Beginning Jobs tool."),
			title=_("Beginning Job"),
		)
	if previous and not current:
		frappe.throw(
			_("Beginning Job cannot be cleared."),
			title=_("Beginning Job"),
		)

	if current:
		return
	for row in doc.get("charges") or []:
		for fieldname, label in (
			("sales_invoice_status", _("Revenue")),
			("purchase_invoice_status", _("Cost")),
		):
			status = (getattr(row, fieldname, None) or "").strip()
			if status == PRIOR_SYSTEM_POSTED_STATUS:
				frappe.throw(
					_("{0} posted in the prior system is only valid on a Beginning Job.").format(label),
					title=_("Beginning Job"),
				)


def create_beginning_jobs(payload):
	"""Insert the main file and any linked service files. Returns their names."""
	payload = _as_dict(payload)
	main_type = (payload.get("file_type") or "").strip()
	if main_type not in BEGINNING_JOB_DOCTYPES:
		frappe.throw(_("Choose a file type."), title=_("Beginning Jobs"))

	header = _as_dict(payload.get("header"))
	legs = [_as_dict(leg) for leg in (payload.get("legs") or [])]
	charges = [_as_dict(row) for row in (payload.get("charges") or [])]
	main_number = (header.get("job_number") or "").strip()
	_validate_legs(main_type, legs, main_number)
	_validate_charge_targets(legs, charges)

	frappe.flags.in_beginning_job = True
	try:
		main = _insert_file(
			main_type,
			header,
			_charges_for(charges, "main"),
			service_role="Main" if legs else None,
		)
		created_legs = []
		for leg in legs:
			service_type = (leg.get("service_type") or "").strip()
			leg_type = SERVICE_TYPE_TO_DOCTYPE[service_type]
			leg_header = _leg_header(header, leg)
			linked = _insert_linked_service(main, service_type, leg_header)
			satellite = _insert_file(
				leg_type,
				leg_header,
				_charges_for(charges, (leg.get("job_number") or "").strip()),
				service_role="Linked",
				main_doc=main,
				linked_service=linked.name,
				service_type=service_type,
			)
			_record_usage(linked.name, main, satellite)
			created_legs.append(
				{
					"linked_service": linked.name,
					"doctype": satellite.doctype,
					"name": satellite.name,
					"service_type": service_type,
				}
			)
	finally:
		frappe.flags.in_beginning_job = False

	return {
		"doctype": main.doctype,
		"name": main.name,
		"job_number": main.job_number,
		"legs": created_legs,
	}


def _as_dict(value):
	if not value:
		return {}
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if isinstance(value, dict):
		return value
	return dict(value)


def _validate_legs(main_type, legs, main_number):
	seen = set()
	for leg in legs:
		service_type = (leg.get("service_type") or "").strip()
		if service_type not in SERVICE_TYPE_TO_DOCTYPE:
			frappe.throw(_("Linked service type {0} is not supported.").format(service_type or _("blank")))
		leg_type = SERVICE_TYPE_TO_DOCTYPE[service_type]
		number = (leg.get("job_number") or "").strip()
		_require_job_number(number, leg_type)
		if number in seen or (leg_type == main_type and number == main_number):
			frappe.throw(_("Linked service number {0} is already used on this file.").format(number))
		seen.add(number)


def _validate_charge_targets(legs, charges):
	leg_numbers = {(leg.get("job_number") or "").strip() for leg in legs}
	for row in charges:
		target = (row.get("applies_to") or "main").strip() or "main"
		if target != "main" and target not in leg_numbers:
			frappe.throw(
				_("Charge {0} is assigned to unknown linked service {1}.").format(
					row.get("item_code") or _("row"), target
				)
			)


def _charges_for(charges, applies_to):
	rows = []
	for row in charges:
		target = (row.get("applies_to") or "main").strip() or "main"
		if target == applies_to:
			rows.append(row)
	return rows


def _leg_header(main_header, leg):
	merged = dict(main_header or {})
	for key, value in (leg or {}).items():
		if value not in (None, ""):
			merged[key] = value
	return merged


def _insert_file(
	doctype,
	header,
	charges,
	*,
	service_role=None,
	main_doc=None,
	linked_service=None,
	service_type=None,
):
	_check_create_permission(doctype)
	spec = _FILE_SPECS[doctype]
	number = _require_job_number((header.get("job_number") or "").strip(), doctype)
	if frappe.db.exists(doctype, number):
		frappe.throw(_("{0} {1} already exists.").format(doctype, number))

	doc = frappe.new_doc(doctype)
	doc.naming_series = spec["naming_series"]
	doc.is_beginning_job = 1
	for fieldname in ("job_status", "status"):
		if not doc.get(fieldname):
			_set_if_field(doc, fieldname, "Draft")
	_set_if_field(doc, spec["date_field"], header.get("booking_date") or header.get("job_open_date") or header.get("declaration_date"))
	customer = header.get("customer") or header.get("local_customer")
	_set_if_field(doc, spec["customer_field"], customer)
	for fieldname in _HEADER_FIELDS:
		if header.get(fieldname) not in (None, ""):
			_set_if_field(doc, fieldname, header.get(fieldname))
	_apply_party_aliases(doc, header)
	if doctype == "Warehouse Job":
		doc.type = "Cross Dock" if (service_type or "") == "Cross-Docking" else (header.get("warehouse_type") or "VAS")
	if doctype == "Transport Job" and not doc.get("transport_job_type"):
		doc.transport_job_type = "Non-Container"
	if doctype == "Transport Job" and not doc.get("vehicle_type"):
		# Vehicle Type is required unless Consolidate is set. An old file may not
		# have a vehicle yet, so satisfy that rule without inventing one.
		doc.consolidate = 1
	if doctype in ("Air Shipment", "Sea Shipment") and (
		flt(header.get("total_weight")) > 0 or flt(header.get("total_volume")) > 0
	):
		# There are no packages on a beginning file. Without this override the
		# packing summary replaces the encoded totals with zero, and Air then
		# rejects the draft.
		_set_if_field(doc, "override_volume_weight", 1)
	if service_role == "Main":
		apply_main_service_flags(doc)
	elif service_role == "Linked":
		apply_linked_service_satellite_flags(doc, main_doc.doctype, main_doc.name)
		_set_if_field(doc, "linked_service", linked_service)

	child_service = service_type or implied_service_type_for_doctype(doctype)
	for row in charges:
		_append_charge(doc, row, child_service)

	doc.name = number
	doc.flags.name_set = True
	doc.insert()
	_persist_job_number_link(doc)
	return doc


def _apply_party_aliases(doc, header):
	for source, target in _PARTY_ALIASES.get(doc.doctype, {}).items():
		if header.get(source) not in (None, ""):
			_set_if_field(doc, target, header.get(source))


def _append_charge(doc, row, service_type):
	item_code = (row.get("item_code") or "").strip()
	if not item_code:
		frappe.throw(_("Each charge needs an Item."))
	charge = doc.append("charges", {})
	_set_if_field(charge, "item_code", item_code)
	item_name = row.get("item_name") or frappe.db.get_value("Item", item_code, "item_name")
	_set_if_field(charge, "item_name", item_name)
	_set_if_field(charge, "description", row.get("description") or item_name)
	_set_if_field(charge, "charge_type", (row.get("charge_type") or "Margin").strip() or "Margin")
	_set_if_field(charge, "service_type", service_type)
	_set_if_field(charge, "revenue_calculation_method", "Per Unit")
	_set_if_field(charge, "cost_calculation_method", "Per Unit")
	_set_if_field(charge, "bill_to", row.get("bill_to"))
	_set_if_field(charge, "pay_to", row.get("pay_to"))

	quantity = flt(row.get("quantity") or 1) or 1
	rate = flt(row.get("unit_rate"))
	revenue = flt(row.get("revenue")) or (quantity * rate)
	_set_if_field(charge, "quantity", quantity)
	_set_if_field(charge, "unit_rate", rate)
	currency = row.get("currency") or _company_currency(doc)
	for fieldname in ("currency", "selling_currency"):
		_set_if_field(charge, fieldname, currency)
	if revenue:
		for fieldname in ("estimated_revenue", "actual_revenue", "base_amount"):
			_set_if_field(charge, fieldname, revenue)

	cost_qty = flt(row.get("cost_quantity") or quantity) or quantity
	unit_cost = flt(row.get("unit_cost"))
	cost = flt(row.get("cost")) or (cost_qty * unit_cost)
	_set_if_field(charge, "cost_quantity", cost_qty)
	_set_if_field(charge, "unit_cost", unit_cost)
	cost_currency = row.get("cost_currency") or currency
	_set_if_field(charge, "buying_currency", cost_currency)
	if cost:
		for fieldname in ("estimated_cost", "actual_cost", "cost_base_amount"):
			_set_if_field(charge, fieldname, cost)

	revenue_posted = cint(row.get("revenue_posted"))
	cost_posted = cint(row.get("cost_posted"))
	_set_if_field(
		charge,
		"sales_invoice_status",
		PRIOR_SYSTEM_POSTED_STATUS if revenue_posted else "Not Requested",
	)
	_set_if_field(
		charge,
		"purchase_invoice_status",
		PRIOR_SYSTEM_POSTED_STATUS if cost_posted else "Not Requested",
	)


def _insert_linked_service(main, service_type, header):
	_check_create_permission("Linked Service")
	doc = frappe.new_doc("Linked Service")
	doc.service_type = service_type
	doc.company = header.get("company")
	doc.parent_booking_type = main.doctype
	doc.parent_booking_name = main.name
	for fieldname in (
		"branch",
		"cost_center",
		"profit_center",
		"direction",
		"shipper",
		"consignee",
		"origin_port",
		"destination_port",
		"shipping_line",
		"airline",
		"load_type",
		"transport_mode",
		"vehicle_type",
		"container_type",
		"container_no",
		"location_from",
		"location_to",
		"customs_authority",
		"declaration_type",
		"reference_no",
		"notes",
		"house_type",
	):
		if fieldname in ("location_from", "location_to") and not header.get("location_type"):
			continue
		if header.get(fieldname) not in (None, ""):
			target = fieldname
			if fieldname == "house_type" and service_type == "Air":
				target = "air_house_type"
			elif fieldname == "house_type" and service_type == "Sea":
				target = "sea_house_type"
			_set_if_field(doc, target, header.get(fieldname))
	doc.insert()
	return doc


def _record_usage(linked_service, main, satellite):
	from logistics.utils.linked_service_usage import (
		USAGE_ROLE_PARENT_BOOKING,
		USAGE_ROLE_SHIPMENT,
		record_linked_service_usage,
	)

	record_linked_service_usage(
		linked_service,
		main.doctype,
		main.name,
		usage_role=USAGE_ROLE_PARENT_BOOKING,
	)
	record_linked_service_usage(
		linked_service,
		satellite.doctype,
		satellite.name,
		usage_role=USAGE_ROLE_SHIPMENT,
	)


def _persist_job_number_link(doc):
	"""Store the Job Number link when after_insert created it only in memory."""
	if doc.get("job_number"):
		return
	existing = frappe.db.get_value(
		"Job Number",
		{"job_type": doc.doctype, "job_no": doc.name},
		"name",
	)
	if not existing:
		return
	frappe.db.set_value(doc.doctype, doc.name, "job_number", existing, update_modified=False)
	doc.job_number = existing


def _require_job_number(number, doctype):
	number = (number or "").strip()
	if not number or not _JOB_NUMBER_RE.match(number):
		frappe.throw(
			_("{0} number {1} must be letters, numbers, spaces, dots, or dashes, and cannot contain /.").format(
				doctype, number or _("blank")
			),
			title=_("Job Number"),
		)
	return number


def _check_create_permission(doctype):
	if not frappe.has_permission(doctype, "create"):
		frappe.throw(_("Not permitted to create {0}.").format(doctype), frappe.PermissionError)


def _set_if_field(doc, fieldname, value):
	if value in (None, ""):
		return
	meta = getattr(doc, "meta", None)
	if meta is not None and not meta.has_field(fieldname):
		return
	if meta is None and not hasattr(doc, fieldname):
		return
	doc.set(fieldname, value)


def _company_currency(doc):
	company = doc.get("company")
	if not company:
		return None
	return frappe.db.get_value("Company", company, "default_currency")
