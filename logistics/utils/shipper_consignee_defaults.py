# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

"""Apply Shipper / Consignee master defaults onto freight transactions (empty fields only)."""

from __future__ import annotations

import frappe

SERVICE_BY_DOCTYPE = {
	"Air Booking": "air",
	"Air Shipment": "air",
	"Sea Booking": "sea",
	"Sea Shipment": "sea",
	"Declaration": "customs",
	"Declaration Order": "customs",
	"Transport Order": "transport",
	"Transport Job": "transport",
}

PARTY_FIELDS_BY_DOCTYPE = {
	"Declaration": ("exporter_shipper", "importer_consignee"),
	"Declaration Order": ("exporter_shipper", "importer_consignee"),
}


def _is_empty(value) -> bool:
	if value is None:
		return True
	if isinstance(value, str) and not value.strip():
		return True
	return False


def _set_if_empty(doc, fieldname: str, value):
	if value is None or value == "":
		return
	if not doc.meta.get_field(fieldname):
		return
	current = doc.get(fieldname)
	if _is_empty(current):
		doc.set(fieldname, value)


def _apply_pairs(doc, party_doc, pairs: list[tuple[str, str]]):
	for target, source in pairs:
		_set_if_empty(doc, target, party_doc.get(source))


def _apply_shipper_air(doc, s):
	_apply_pairs(
		doc,
		s,
		[
			("sending_agent", "air_default_sending_agent"),
			("receiving_agent", "air_default_receiving_agent"),
			("broker", "air_default_broker"),
			("document_list_template", "air_default_document_template"),
			("milestone_template", "air_default_milestone_template"),
			("tc_name", "air_default_tc_name"),
			("additional_terms", "air_default_additional_terms"),
			("client_notes", "air_default_client_notes"),
			("notify_party", "default_notify_party"),
			("notify_party_address", "default_notify_party_address"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)


def _apply_shipper_sea_booking(doc, s):
	_apply_pairs(
		doc,
		s,
		[
			("sending_agent", "sea_default_sending_agent"),
			("receiving_agent", "sea_default_receiving_agent"),
			("broker", "sea_default_broker"),
			("freight_consolidator", "sea_default_freight_consolidator"),
			("document_list_template", "sea_default_document_template"),
			("milestone_template", "sea_default_milestone_template"),
			("tc_name", "sea_default_tc_name"),
			("additional_terms", "sea_default_additional_terms"),
			("client_notes", "sea_default_client_notes"),
			("notify_party", "default_notify_party"),
			("notify_party_address", "default_notify_party_address"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)


def _apply_shipper_sea_shipment(doc, s):
	# Sea Shipment.broker links Freight Agent; master sea_default_broker is Broker — do not map here.
	_apply_pairs(
		doc,
		s,
		[
			("sending_agent", "sea_default_sending_agent"),
			("receiving_agent", "sea_default_receiving_agent"),
			("document_list_template", "sea_default_document_template"),
			("milestone_template", "sea_default_milestone_template"),
			("tc_name", "sea_default_tc_name"),
			("additional_terms", "sea_default_additional_terms"),
			("notify_party", "default_notify_party"),
			("notify_party_address", "default_notify_party_address"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)
	_set_if_empty(doc, "external_notes", s.get("sea_default_client_notes"))


def _apply_shipper_customs(doc, s):
	_apply_pairs(
		doc,
		s,
		[
			("customs_broker", "customs_default_broker"),
			("freight_agent", "customs_default_freight_agent"),
			("trade_agreement", "customs_default_trade_agreement"),
			("marks_and_numbers", "customs_default_marks_and_numbers"),
			("document_list_template", "customs_default_document_template"),
			("milestone_template", "customs_default_milestone_template"),
			("special_instructions", "customs_default_special_instructions"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)


def _apply_shipper_transport(doc, s):
	_apply_pairs(
		doc,
		s,
		[
			("document_list_template", "transport_default_document_template"),
			("milestone_template", "transport_default_milestone_template"),
			("client_notes", "transport_default_client_notes"),
			("internal_notes", "transport_default_internal_notes"),
		],
	)
	if doc.doctype == "Transport Job":
		_set_if_empty(doc, "logistics_service_level", s.get("default_service_level"))
	else:
		_set_if_empty(doc, "service_level", s.get("default_service_level"))


def _apply_consignee_air_booking_shipment(doc, c, include_customs_broker: bool):
	pairs = [
		("receiving_agent", "air_default_receiving_agent"),
		("broker", "air_default_broker"),
		("document_list_template", "air_default_document_template"),
		("milestone_template", "air_default_milestone_template"),
		("tc_name", "air_default_tc_name"),
		("client_notes", "air_default_client_notes"),
		("notify_party", "default_notify_party"),
		("notify_party_address", "default_notify_party_address"),
		("service_level", "default_service_level"),
		("incoterm", "default_incoterm"),
	]
	if include_customs_broker:
		pairs = [("customs_broker", "air_default_customs_broker")] + pairs
	_apply_pairs(doc, c, pairs)


def _apply_consignee_sea_booking(doc, c):
	_apply_pairs(
		doc,
		c,
		[
			("receiving_agent", "sea_default_receiving_agent"),
			("broker", "sea_default_broker"),
			("freight_consolidator", "sea_default_freight_consolidator"),
			("document_list_template", "sea_default_document_template"),
			("milestone_template", "sea_default_milestone_template"),
			("tc_name", "sea_default_tc_name"),
			("client_notes", "sea_default_client_notes"),
			("notify_party", "default_notify_party"),
			("notify_party_address", "default_notify_party_address"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)


def _apply_consignee_sea_shipment(doc, c):
	# Same Broker vs Freight Agent mismatch as shipper side for Sea Shipment.
	_apply_pairs(
		doc,
		c,
		[
			("receiving_agent", "sea_default_receiving_agent"),
			("document_list_template", "sea_default_document_template"),
			("milestone_template", "sea_default_milestone_template"),
			("tc_name", "sea_default_tc_name"),
			("notify_party", "default_notify_party"),
			("notify_party_address", "default_notify_party_address"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)
	_set_if_empty(doc, "external_notes", c.get("sea_default_client_notes"))


def _apply_consignee_customs(doc, c):
	_apply_pairs(
		doc,
		c,
		[
			("customs_broker", "customs_default_broker"),
			("freight_agent", "customs_default_freight_agent"),
			("trade_agreement", "customs_default_trade_agreement"),
			("marks_and_numbers", "customs_default_marks_and_numbers"),
			("payment_terms", "customs_default_payment_terms"),
			("document_list_template", "customs_default_document_template"),
			("milestone_template", "customs_default_milestone_template"),
			("special_instructions", "customs_default_special_instructions"),
			("country_of_origin", "customs_default_country_of_origin"),
			("currency", "default_currency"),
			("service_level", "default_service_level"),
			("incoterm", "default_incoterm"),
		],
	)


def _apply_consignee_transport(doc, c):
	_apply_pairs(
		doc,
		c,
		[
			("document_list_template", "transport_default_document_template"),
			("milestone_template", "transport_default_milestone_template"),
			("client_notes", "transport_default_client_notes"),
			("internal_notes", "transport_default_internal_notes"),
		],
	)
	if doc.doctype == "Transport Job":
		_set_if_empty(doc, "logistics_service_level", c.get("default_service_level"))
	else:
		_set_if_empty(doc, "service_level", c.get("default_service_level"))


def apply_shipper_consignee_defaults(doc, shipper: str | None = None, consignee: str | None = None):
	"""Fill empty transaction fields from linked Shipper / Consignee (consignee first, then shipper)."""
	service = SERVICE_BY_DOCTYPE.get(doc.doctype)
	if not service:
		return

	shipper_f, consignee_f = PARTY_FIELDS_BY_DOCTYPE.get(doc.doctype, ("shipper", "consignee"))
	consignee = consignee if consignee is not None else (doc.get(consignee_f) if consignee_f else None)
	shipper = shipper if shipper is not None else (doc.get(shipper_f) if shipper_f else None)

	if consignee:
		cdoc = frappe.get_cached_doc("Consignee", consignee)
		if service == "air":
			_apply_consignee_air_booking_shipment(
				doc, cdoc, include_customs_broker=(doc.doctype == "Air Shipment")
			)
		elif service == "sea":
			if doc.doctype == "Sea Booking":
				_apply_consignee_sea_booking(doc, cdoc)
			else:
				_apply_consignee_sea_shipment(doc, cdoc)
		elif service == "customs":
			_apply_consignee_customs(doc, cdoc)
		elif service == "transport":
			_apply_consignee_transport(doc, cdoc)

	if shipper:
		sdoc = frappe.get_cached_doc("Shipper", shipper)
		if service == "air":
			_apply_shipper_air(doc, sdoc)
		elif service == "sea":
			if doc.doctype == "Sea Booking":
				_apply_shipper_sea_booking(doc, sdoc)
			else:
				_apply_shipper_sea_shipment(doc, sdoc)
		elif service == "customs":
			_apply_shipper_customs(doc, sdoc)
		elif service == "transport":
			_apply_shipper_transport(doc, sdoc)


@frappe.whitelist()
def get_applicable_defaults(target_doctype: str | None = None, shipper: str | None = None, consignee: str | None = None):
	"""Return field→value for client-side population (empty-field rule applied client-side too)."""
	if not target_doctype or target_doctype not in SERVICE_BY_DOCTYPE:
		return {}

	shipper_f, consignee_f = PARTY_FIELDS_BY_DOCTYPE.get(target_doctype, ("shipper", "consignee"))
	service = SERVICE_BY_DOCTYPE[target_doctype]
	mock = frappe.new_doc(target_doctype)
	before = {df.fieldname: mock.get(df.fieldname) for df in mock.meta.fields}
	if consignee:
		cdoc = frappe.get_cached_doc("Consignee", consignee)
		if service == "air":
			_apply_consignee_air_booking_shipment(
				mock, cdoc, include_customs_broker=(target_doctype == "Air Shipment")
			)
		elif service == "sea":
			if target_doctype == "Sea Booking":
				_apply_consignee_sea_booking(mock, cdoc)
			else:
				_apply_consignee_sea_shipment(mock, cdoc)
		elif service == "customs":
			_apply_consignee_customs(mock, cdoc)
		elif service == "transport":
			_apply_consignee_transport(mock, cdoc)

	if shipper:
		sdoc = frappe.get_cached_doc("Shipper", shipper)
		if service == "air":
			_apply_shipper_air(mock, sdoc)
		elif service == "sea":
			if target_doctype == "Sea Booking":
				_apply_shipper_sea_booking(mock, sdoc)
			else:
				_apply_shipper_sea_shipment(mock, sdoc)
		elif service == "customs":
			_apply_shipper_customs(mock, sdoc)
		elif service == "transport":
			_apply_shipper_transport(mock, sdoc)

	out = {}
	for df in mock.meta.fields:
		if df.fieldname in (shipper_f, consignee_f):
			continue
		v = mock.get(df.fieldname)
		if not _is_empty(v) and v != before.get(df.fieldname):
			out[df.fieldname] = v
	return out
