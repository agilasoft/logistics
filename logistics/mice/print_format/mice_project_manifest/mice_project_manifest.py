# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Row builder for the MICE Project Manifest print format."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, strip_html

from logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html import (
	_linked_service_rows,
)


def get_mice_project_manifest_rows(mice_project) -> list[dict[str, Any]]:
	"""Return one manifest row dict per non-cancelled Docket on the MICE Project."""
	project_name = _project_name(mice_project)
	if not project_name:
		return []

	org_name = _organizer_name(_field(mice_project, "organizer"))

	dockets = frappe.get_all(
		"Docket",
		filters={"exhibit": project_name, "docstatus": ["<", 2]},
		fields=[
			"name",
			"job_number",
			"exhibitor_name",
			"total_packages",
			"total_weight",
			"total_weight_uom",
			"total_volume",
			"total_volume_uom",
			"sales_invoice",
		],
		order_by="docket_date asc, creation asc",
	)

	rows: list[dict[str, Any]] = []
	for dk in dockets:
		rows.append(_build_row(dk, org_name))
	return rows


def _build_row(dk: dict[str, Any], org_name: str) -> dict[str, str]:
	"""Build one row from the MICE Project organizer, Docket, and Commodity."""
	exhibitor_label = (dk.get("exhibitor_name") or "").strip()
	description = _docket_description(dk)
	billing_invoice = (dk.get("sales_invoice") or "").strip()
	freight = _freight_columns(dk)

	return {
		"job_no": (dk.get("job_number") or "").strip() or "-",
		"exhibitor": exhibitor_label or "-",
		"agent": freight["agent"] or "-",
		"org": org_name or "-",
		"eta_mnl": freight["eta_mnl"] or "-",
		"clearance_date": freight["clearance_date"] or "-",
		"awb_bl": freight["awb_bl"] or "-",
		"vsl_flight": freight["vsl_flight"] or "-",
		"qty_pkgs": _format_qty(dk.get("total_packages")),
		"g_weight_kg": _format_weight(dk),
		"volume_cbm": _format_volume(dk),
		"description": description or "-",
		"ingress_schedule": "",
		"contact": "",
		"billing_invoice": billing_invoice or "-",
	}


def _freight_columns(dk: dict[str, Any]) -> dict[str, str]:
	"""Agent, ETA, clearance, house document, and vessel or flight for one Docket."""
	docket_name = (dk.get("name") or "").strip()
	services = _linked_service_rows("Docket", docket_name) if docket_name else []
	service_names = [name for name in ((row.get("name") or "").strip() for row in services) if name]
	shipment = _primary_shipment(service_names)
	declarations = _declaration_rows(service_names, dk.get("job_number"))

	awb_bl = _house_number(shipment) or _first_text(declarations, "transport_document_number")
	eta = (shipment or {}).get("eta") or _first_value(declarations, "eta")
	vsl_flight = _vessel_flight(shipment) or _first_text(declarations, "vessel_flight_number")

	return {
		"agent": _agent_label(services),
		"eta_mnl": _format_manifest_date(eta),
		"clearance_date": _clearance_date(declarations),
		"awb_bl": awb_bl,
		"vsl_flight": vsl_flight,
	}


def _agent_label(services: list[dict[str, Any]]) -> str:
	agent_id = ""
	for service in services:
		agent_id = (service.get("freight_agent") or service.get("freight_agent_sea") or "").strip()
		if agent_id:
			break
	if not agent_id:
		return ""
	if not frappe.db.exists("DocType", "Freight Agent"):
		return agent_id
	name = frappe.db.get_value("Freight Agent", agent_id, "freight_agent_name")
	return (name or "").strip() or agent_id


def _primary_shipment(service_names: list[str]) -> dict[str, Any] | None:
	"""First non-cancelled Air Shipment on these services, else the first Sea Shipment."""
	if not service_names:
		return None
	air = _first_shipment(
		"Air Shipment",
		service_names,
		["name", "house_awb_no", "house_awb", "eta"],
	)
	if air:
		air["mode"] = "air"
		return air
	sea = _first_shipment(
		"Sea Shipment",
		service_names,
		["name", "house_bl", "eta", "master_bill"],
	)
	if sea:
		sea["mode"] = "sea"
		return sea
	return None


def _first_shipment(doctype: str, service_names: list[str], fields: list[str]) -> dict[str, Any] | None:
	if not frappe.db.exists("DocType", doctype):
		return None
	rows = frappe.get_all(
		doctype,
		filters={"linked_service": ["in", service_names], "docstatus": ["<", 2]},
		fields=fields,
		order_by="creation asc",
		limit=1,
	)
	return rows[0] if rows else None


def _house_number(shipment: dict[str, Any] | None) -> str:
	if not shipment:
		return ""
	if shipment.get("mode") == "air":
		return (shipment.get("house_awb_no") or shipment.get("house_awb") or "").strip()
	return (shipment.get("house_bl") or "").strip()


def _vessel_flight(shipment: dict[str, Any] | None) -> str:
	if not shipment:
		return ""
	parent = (shipment.get("name") or "").strip()
	if shipment.get("mode") == "air":
		for leg in _routing_legs("Air Shipment Routing Leg", "Air Shipment", parent):
			flight = (leg.get("flight_no") or "").strip()
			if flight:
				return flight
		return ""
	for leg in _routing_legs("Sea Shipment Routing Leg", "Sea Shipment", parent):
		label = _vessel_label(leg.get("vessel"), leg.get("voyage_no"))
		if label:
			return label
	return _master_bill_vessel(shipment.get("master_bill"))


def _routing_legs(doctype: str, parenttype: str, parent: str) -> list[dict[str, Any]]:
	if not parent or not frappe.db.exists("DocType", doctype):
		return []
	return frappe.get_all(
		doctype,
		filters={"parent": parent, "parenttype": parenttype, "parentfield": "routing_legs"},
		fields=["flight_no", "vessel", "voyage_no"],
		order_by="idx asc",
	)


def _master_bill_vessel(master_bill: str | None) -> str:
	name = (master_bill or "").strip()
	if not name or not frappe.db.exists("DocType", "Master Bill"):
		return ""
	row = frappe.db.get_value("Master Bill", name, ["vessel", "voyage_no"], as_dict=True)
	if not row:
		return ""
	return _vessel_label(row.get("vessel"), row.get("voyage_no"))


def _vessel_label(vessel, voyage) -> str:
	vessel_text = (vessel or "").strip()
	voyage_text = (voyage or "").strip()
	if vessel_text and voyage_text:
		return f"{vessel_text} / {voyage_text}"
	return vessel_text or voyage_text


def _declaration_rows(service_names: list[str], job_number: str | None) -> list[dict[str, Any]]:
	if not frappe.db.exists("DocType", "Declaration"):
		return []
	fields = [
		"name",
		"eta",
		"actual_clearance_date",
		"expected_clearance_date",
		"transport_document_number",
		"vessel_flight_number",
	]
	rows: list[dict[str, Any]] = []
	if service_names:
		rows = frappe.get_all(
			"Declaration",
			filters={"linked_service": ["in", service_names], "docstatus": ["<", 2]},
			fields=fields,
			order_by="creation asc",
		)
	job = (job_number or "").strip()
	if not rows and job:
		rows = frappe.get_all(
			"Declaration",
			filters={"job_number": job, "docstatus": ["<", 2]},
			fields=fields,
			order_by="creation asc",
		)
	return rows


def _clearance_date(declarations: list[dict[str, Any]]) -> str:
	for row in declarations:
		value = row.get("actual_clearance_date") or row.get("expected_clearance_date")
		if value:
			return _format_manifest_date(value)
	return ""


def _first_text(rows: list[dict[str, Any]], fieldname: str) -> str:
	for row in rows:
		text = (row.get(fieldname) or "").strip()
		if text:
			return text
	return ""


def _first_value(rows: list[dict[str, Any]], fieldname: str):
	for row in rows:
		value = row.get(fieldname)
		if value:
			return value
	return None


def _format_manifest_date(value) -> str:
	"""Column date as ``30-SEP-2026``."""
	day = _as_date(value)
	if not day:
		return ""
	return f"{day.day:02d}-{_MONTHS[day.month - 1][:3]}-{day.year}"


def _project_name(mice_project) -> str:
	if isinstance(mice_project, str):
		return mice_project.strip()
	return (_field(mice_project, "name") or "").strip()


def _field(doc, fieldname: str):
	if doc is None:
		return None
	if isinstance(doc, dict):
		return doc.get(fieldname)
	return getattr(doc, fieldname, None)


def _organizer_name(organizer: str | None) -> str:
	if not organizer:
		return ""
	return (
		frappe.db.get_value("MICE Organizer", organizer, "organizer_name") or organizer
	)


def _docket_description(dk: dict[str, Any]) -> str:
	"""Unique Commodity descriptions from the docket's packages, in package order."""
	packages = frappe.get_all(
		"Docket Package",
		filters={"parent": dk.get("name"), "parenttype": "Docket"},
		fields=["commodity"],
		order_by="idx asc",
	)
	codes: list[str] = []
	seen: set[str] = set()
	for row in packages:
		code = (row.get("commodity") or "").strip()
		if code and code not in seen:
			seen.add(code)
			codes.append(code)
	if not codes:
		return ""

	commodities = frappe.get_all(
		"Commodity",
		filters={"name": ["in", codes]},
		fields=["name", "description"],
	)
	by_name = {
		(row.get("name") or ""): strip_html(str(row.get("description") or "")).strip()
		for row in commodities
	}
	parts = [by_name[code] for code in codes if by_name.get(code)]
	return ", ".join(parts)


_MONTHS = (
	"JANUARY",
	"FEBRUARY",
	"MARCH",
	"APRIL",
	"MAY",
	"JUNE",
	"JULY",
	"AUGUST",
	"SEPTEMBER",
	"OCTOBER",
	"NOVEMBER",
	"DECEMBER",
)


def format_mice_manifest_show_dates(open_date, close_date) -> str:
	"""Format show open/close for the manifest subtitle.

	Same month and year: ``25-29 AUGUST 2025``.
	Same year, different months: ``25 AUGUST - 2 SEPTEMBER 2025``.
	Different years: ``25 DECEMBER 2025 - 2 JANUARY 2026``.
	A single date, or both dates equal: ``25 AUGUST 2025``.
	"""
	start = _as_date(open_date)
	end = _as_date(close_date)
	if start and end and end < start:
		start, end = end, start
	if start and end and start != end:
		if start.year == end.year and start.month == end.month:
			return f"{start.day}-{end.day} {_MONTHS[start.month - 1]} {start.year}"
		if start.year == end.year:
			return (
				f"{start.day} {_MONTHS[start.month - 1]} - "
				f"{end.day} {_MONTHS[end.month - 1]} {start.year}"
			)
		return (
			f"{start.day} {_MONTHS[start.month - 1]} {start.year} - "
			f"{end.day} {_MONTHS[end.month - 1]} {end.year}"
		)
	only = start or end
	if not only:
		return ""
	return f"{only.day} {_MONTHS[only.month - 1]} {only.year}"


def _as_date(value):
	if not value:
		return None
	try:
		return frappe.utils.getdate(value)
	except Exception:
		return None


def _format_qty(value) -> str:
	if value is None or value == "":
		return "-"
	qty = flt(value)
	if qty == 0:
		return "0"
	if qty == int(qty):
		return str(int(qty))
	return f"{qty:g}"


def _format_weight(dk: dict[str, Any]) -> str:
	return _format_qty(dk.get("total_weight"))


def _format_volume(dk: dict[str, Any]) -> str:
	return _format_qty(dk.get("total_volume"))
