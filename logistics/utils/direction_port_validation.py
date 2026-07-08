# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Validate trade Direction against Origin/Destination UNLOCO ports for the company country."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_DIRECTIONS = frozenset({"Import", "Export", "Domestic"})


def _strip(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def get_company_country_code(company: str | None) -> str | None:
	"""Return the ISO country code for a Company (e.g. ``PH``, ``US``)."""
	company = _strip(company)
	if not company:
		return None
	country_name = frappe.db.get_value("Company", company, "country")
	if not country_name:
		return None
	code = frappe.db.get_value("Country", country_name, "code")
	return _strip(code).upper() or None


def get_company_country_label(company: str | None) -> str:
	"""Human-readable country for error messages."""
	company = _strip(company)
	if not company:
		return _("the company country")
	country_name = frappe.db.get_value("Company", company, "country")
	if country_name:
		return country_name
	code = get_company_country_code(company)
	return code or _("the company country")


def get_unloco_country_code(unloco: str | None) -> str | None:
	"""Resolve a UNLOCO record to its 2-letter country code."""
	unloco = _strip(unloco)
	if not unloco:
		return None
	if frappe.db.exists("UNLOCO", unloco):
		row = frappe.db.get_value(
			"UNLOCO",
			unloco,
			["country_code", "unlocode"],
			as_dict=True,
		)
		if row:
			cc = _strip(row.get("country_code")).upper()
			if cc:
				return cc
			unlocode = _strip(row.get("unlocode")).upper()
			if len(unlocode) >= 2:
				return unlocode[:2]
	if len(unloco) >= 2:
		return unloco[:2].upper()
	return None


def _port_country_mismatch_message(
	direction: str,
	field_label: str,
	port: str,
	company: str | None,
	*,
	context_label: str | None = None,
) -> str:
	country_label = get_company_country_label(company)
	prefix = f"{context_label}: " if context_label else ""
	return _(
		"{0}For {1}, {2} ({3}) must be in {4}. "
		"Choose a port whose UN/LOCODE country matches the Sales Quote company, or change Direction."
	).format(prefix, direction, field_label, port, country_label)


def validate_direction_port_alignment(
	direction: str | None,
	origin_port: str | None,
	destination_port: str | None,
	company: str | None,
	*,
	context_label: str | None = None,
	require_ports: bool = False,
) -> None:
	"""Raise when Direction and ports are not aligned with the company registered country."""
	direction = _strip(direction)
	if not direction:
		return
	if direction not in _DIRECTIONS:
		return

	company_cc = get_company_country_code(company)
	if not company_cc:
		return

	origin_port = _strip(origin_port) or None
	destination_port = _strip(destination_port) or None

	if require_ports:
		if direction in ("Export", "Domestic") and not origin_port:
			return
		if direction in ("Import", "Domestic") and not destination_port:
			return

	origin_cc = get_unloco_country_code(origin_port) if origin_port else None
	destination_cc = get_unloco_country_code(destination_port) if destination_port else None

	if direction == "Import":
		if not destination_port:
			return
		if destination_cc != company_cc:
			frappe.throw(
				_port_country_mismatch_message(
					direction,
					_("Destination Port"),
					destination_port,
					company,
					context_label=context_label,
				),
				title=_("Direction and Ports Do Not Match"),
			)
	elif direction == "Export":
		if not origin_port:
			return
		if origin_cc != company_cc:
			frappe.throw(
				_port_country_mismatch_message(
					direction,
					_("Origin Port"),
					origin_port,
					company,
					context_label=context_label,
				),
				title=_("Direction and Ports Do Not Match"),
			)
	elif direction == "Domestic":
		if origin_port and origin_cc != company_cc:
			frappe.throw(
				_port_country_mismatch_message(
					direction,
					_("Origin Port"),
					origin_port,
					company,
					context_label=context_label,
				),
				title=_("Direction and Ports Do Not Match"),
			)
		if destination_port and destination_cc != company_cc:
			frappe.throw(
				_port_country_mismatch_message(
					direction,
					_("Destination Port"),
					destination_port,
					company,
					context_label=context_label,
				),
				title=_("Direction and Ports Do Not Match"),
			)


def validate_sales_quote_direction_ports(doc) -> None:
	"""Validate Sales Quote header and Air/Sea charge routing parameters."""
	quotation_type = getattr(doc, "quotation_type", None)
	if quotation_type not in ("One-off", "Regular"):
		return
	if getattr(doc, "additional_charge", 0):
		return

	company = getattr(doc, "company", None)
	main_service = getattr(doc, "main_service", None)

	if main_service in ("Air", "Sea"):
		validate_direction_port_alignment(
			getattr(doc, "direction", None),
			getattr(doc, "origin_port", None),
			getattr(doc, "destination_port", None),
			company,
			context_label=_("Sales Quote"),
			require_ports=True,
		)

	from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage
	from logistics.utils.sales_quote_charge_parameters import effective_charge_row_parameters

	doc_direction = _strip(getattr(doc, "direction", None)) or None
	doc_origin = _strip(getattr(doc, "origin_port", None)) or None
	doc_dest = _strip(getattr(doc, "destination_port", None)) or None

	for idx, row in enumerate(getattr(doc, "charges", None) or [], start=1):
		st = canonical_charge_service_type_for_storage(getattr(row, "service_type", None))
		if st not in ("air", "sea"):
			continue
		params = effective_charge_row_parameters(row, doc)
		direction = _strip(params.get("direction")) or doc_direction
		origin = _strip(params.get("origin_port")) or doc_origin
		destination = _strip(params.get("destination_port")) or doc_dest
		if not direction:
			continue
		validate_direction_port_alignment(
			direction,
			origin,
			destination,
			company,
			context_label=_("Charge line {0}").format(idx),
			require_ports=False,
		)


@frappe.whitelist()
def check_direction_port_alignment(
	direction=None,
	origin_port=None,
	destination_port=None,
	company=None,
):
	"""Desk helper: return alignment result without saving (used by Sales Quote client script)."""
	try:
		validate_direction_port_alignment(
			direction,
			origin_port,
			destination_port,
			company,
			require_ports=False,
		)
	except frappe.ValidationError as exc:
		return {"valid": False, "message": str(exc)}
	return {"valid": True}
