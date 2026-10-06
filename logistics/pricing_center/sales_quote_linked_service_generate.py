# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Preview and create Sales Quote linked services from main scope and containers."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from logistics.time_sensitive.service_linking import MAX_LINKED_SERVICE_ADD_QUANTITY

RECIPE_TRANSPORT_CONTAINER = "transport_container"
RECIPE_TRANSPORT_MAIN = "transport_main"
RECIPE_CUSTOMS_MAIN = "customs_main"

_SHARED_FIELDS = (
	"company",
	"branch",
	"cost_center",
	"profit_center",
	"shipper",
	"consignee",
)

_TRANSPORT_MAIN_FIELDS = (
	"location_type",
	"location_from",
	"location_to",
	"transport_template",
	"vehicle_type",
	"container_type",
	"container_no",
	"pick_mode",
	"drop_mode",
	"load_type",
	"transport_mode",
)

_CUSTOMS_FIELDS = (
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
)

_CONTAINER_MAIN_SERVICES = frozenset({"Sea", "MICE"})


def preview_linked_services_from_quote(quote) -> dict[str, Any]:
	"""Return generate proposals. Field values are informational; create recomputes them."""
	proposals: list[dict[str, Any]] = []
	main_service = (getattr(quote, "main_service", None) or "").strip()

	if main_service in _CONTAINER_MAIN_SERVICES:
		for row in getattr(quote, "containers", None) or []:
			fields = _shared_fields(quote)
			container_type = _filled(getattr(row, "type", None))
			if container_type and _linked_service_has_field("container_type"):
				fields["container_type"] = container_type
			proposals.append(
				{
					"key": RECIPE_TRANSPORT_CONTAINER,
					"service_type": "Transport",
					"container_row": row.name,
					"label": _container_label(row),
					"detail": _container_detail(row),
					"quantity": 1,
					"fields": fields,
				}
			)

	if main_service == "Transport":
		fields = _transport_main_fields(quote)
		if _has_service_fields(fields, _TRANSPORT_MAIN_FIELDS):
			proposals.append(
				{
					"key": RECIPE_TRANSPORT_MAIN,
					"service_type": "Transport",
					"container_row": None,
					"label": _("Transport from main"),
					"detail": _transport_main_detail(fields),
					"quantity": 1,
					"fields": fields,
				}
			)

	if main_service == "Customs":
		fields = _customs_fields(quote)
		if _has_service_fields(fields, _CUSTOMS_FIELDS):
			proposals.append(
				{
					"key": RECIPE_CUSTOMS_MAIN,
					"service_type": "Customs",
					"container_row": None,
					"label": _("Customs from main"),
					"detail": _customs_detail(fields),
					"quantity": 1,
					"fields": fields,
				}
			)

	return {"name": quote.name, "proposals": proposals}


def create_linked_services_from_quote(quote, proposals) -> dict[str, Any]:
	"""Insert selected proposals. Ignores client field values and recomputes from the quote."""
	created: list[str] = []
	for item in _parse_proposals(proposals):
		if not isinstance(item, dict):
			frappe.throw(_("Each proposal must be an object."))
		key = (item.get("key") or "").strip()
		if key == RECIPE_TRANSPORT_CONTAINER:
			created.extend(_create_transport_from_container(quote, item))
		elif key == RECIPE_TRANSPORT_MAIN:
			created.append(_create_transport_from_main(quote))
		elif key == RECIPE_CUSTOMS_MAIN:
			created.append(_create_customs_from_main(quote))
		else:
			frappe.throw(_("Unknown linked service recipe {0}.").format(key or _("(blank)")))

	quote.flags._linked_services_view_cached = False
	if "linked_services" in quote.__dict__:
		del quote.__dict__["linked_services"]

	return {
		"name": quote.name,
		"linked_services": created,
		"created": len(created),
	}


def _create_transport_from_container(quote, item: dict) -> list[str]:
	main_service = (getattr(quote, "main_service", None) or "").strip()
	if main_service not in _CONTAINER_MAIN_SERVICES:
		frappe.throw(
			_("Transport from containers is only available when the main service is Sea or MICE.")
		)
	quantity = _proposal_quantity(item, editable=True)
	if quantity == 0:
		return []

	row_name = (item.get("container_row") or item.get("container_row_name") or "").strip()
	if not row_name:
		frappe.throw(_("Container row is required."))
	row = _container_row(quote, row_name)

	fields = _shared_fields(quote)
	container_type = _filled(getattr(row, "type", None))
	if container_type and _linked_service_has_field("container_type"):
		fields["container_type"] = container_type

	return [_insert_linked_service(quote, "Transport", fields, quantity=quantity)]


def _create_transport_from_main(quote) -> str:
	if (getattr(quote, "main_service", None) or "").strip() != "Transport":
		frappe.throw(
			_("Transport from main is only available when the main service is Transport.")
		)
	fields = _transport_main_fields(quote)
	if not _has_service_fields(fields, _TRANSPORT_MAIN_FIELDS):
		frappe.throw(_("Main service has no transport parameters to copy."))
	return _insert_linked_service(quote, "Transport", fields)


def _create_customs_from_main(quote) -> str:
	if (getattr(quote, "main_service", None) or "").strip() != "Customs":
		frappe.throw(_("Customs from main is only available when the main service is Customs."))
	fields = _customs_fields(quote)
	if not _has_service_fields(fields, _CUSTOMS_FIELDS):
		frappe.throw(_("Main service has no customs parameters to copy."))
	return _insert_linked_service(quote, "Customs", fields)


def _insert_linked_service(
	quote, service_type: str, fields: dict[str, str], quantity: int = 1
) -> str:
	from logistics.time_sensitive.service_linking import (
		apply_linked_service_quantity,
		validate_linked_service_type,
	)
	from logistics.utils.linked_service_compat import linked_service_doctype

	service_type = validate_linked_service_type(service_type)
	linked = frappe.new_doc(linked_service_doctype())
	linked.service_type = service_type
	linked.parent_booking_type = "Sales Quote"
	linked.parent_booking_name = quote.name
	allowed = _linked_service_fieldnames()
	for fieldname, value in fields.items():
		if fieldname in allowed and fieldname not in ("service_type", "name", "quantity"):
			setattr(linked, fieldname, value)
	apply_linked_service_quantity(linked, quantity)
	linked.insert(ignore_permissions=True)
	return linked.name


def _container_row(quote, row_name: str):
	for row in getattr(quote, "containers", None) or []:
		if row.name == row_name:
			return row
	frappe.throw(_("Container row {0} is not on this Sales Quote.").format(row_name))


def _parse_proposals(proposals) -> list:
	if proposals is None or proposals == "":
		return []
	parsed = frappe.parse_json(proposals)
	if isinstance(parsed, dict):
		parsed = [parsed]
	if not isinstance(parsed, list):
		frappe.throw(_("Proposals must be a list."))
	return parsed


def _proposal_quantity(item: dict, *, editable: bool) -> int:
	if not editable:
		return 1
	raw = item.get("quantity")
	if raw in (None, ""):
		return 1
	quantity = cint(raw)
	if quantity < 0:
		frappe.throw(_("Quantity cannot be negative."))
	if quantity > MAX_LINKED_SERVICE_ADD_QUANTITY:
		frappe.throw(
			_("Quantity cannot exceed {0} per container row.").format(
				MAX_LINKED_SERVICE_ADD_QUANTITY
			)
		)
	return quantity


def _shared_fields(quote) -> dict[str, str]:
	return _copy_fields(quote, _SHARED_FIELDS)


def _transport_main_fields(quote) -> dict[str, str]:
	fields = _shared_fields(quote)
	fields.update(_copy_fields(quote, _TRANSPORT_MAIN_FIELDS))
	return fields


def _customs_fields(quote) -> dict[str, str]:
	fields = _shared_fields(quote)
	fields.update(_copy_fields(quote, _CUSTOMS_FIELDS))
	return fields


def _copy_fields(source, fieldnames: tuple[str, ...]) -> dict[str, str]:
	copied: dict[str, str] = {}
	for fieldname in fieldnames:
		if not _linked_service_has_field(fieldname):
			continue
		value = _filled(getattr(source, fieldname, None))
		if value:
			copied[fieldname] = value
	return copied


def _has_service_fields(fields: dict[str, str], service_fieldnames: tuple[str, ...]) -> bool:
	return any(fieldname in fields for fieldname in service_fieldnames)


def _filled(value) -> str | None:
	if value is None:
		return None
	text = str(value).strip()
	return text or None


def _container_label(row) -> str:
	parts = []
	for fieldname in ("type", "size", "delivery_modes"):
		value = _filled(getattr(row, fieldname, None))
		if value:
			parts.append(value)
	if parts:
		return _("Transport · {0}").format(" · ".join(parts))
	return _("Transport · container {0}").format(getattr(row, "idx", None) or "")


def _container_detail(row) -> str:
	container_type = _filled(getattr(row, "type", None))
	if container_type:
		return _("Container type {0}").format(container_type)
	return _("Container type is blank on this row.")


def _transport_main_detail(fields: dict[str, str]) -> str:
	bits = []
	origin = fields.get("location_from")
	destination = fields.get("location_to")
	if origin or destination:
		bits.append(f"{origin or '—'} → {destination or '—'}")
	for fieldname in ("vehicle_type", "container_type", "container_no"):
		if fields.get(fieldname):
			bits.append(fields[fieldname])
	return " · ".join(bits)


def _customs_detail(fields: dict[str, str]) -> str:
	return " · ".join(fields[fieldname] for fieldname in _CUSTOMS_FIELDS if fields.get(fieldname))


def _linked_service_fieldnames() -> set[str]:
	return {df.fieldname for df in frappe.get_meta("Linked Service").fields}


def _linked_service_has_field(fieldname: str) -> bool:
	return fieldname in _linked_service_fieldnames()
