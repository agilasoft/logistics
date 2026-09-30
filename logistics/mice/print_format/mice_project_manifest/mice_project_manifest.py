# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Row builder for the MICE Project Manifest print format."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, strip_html


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

	return {
		"job_no": (dk.get("job_number") or "").strip() or "-",
		"exhibitor": exhibitor_label or "-",
		"agent": "-",
		"org": org_name or "-",
		"eta_mnl": "-",
		"clearance_date": "-",
		"awb_bl": "-",
		"vsl_flight": "-",
		"qty_pkgs": _format_qty(dk.get("total_packages")),
		"g_weight_kg": _format_weight(dk),
		"volume_cbm": _format_volume(dk),
		"description": description or "-",
		"ingress_schedule": "",
		"contact": "",
		"billing_invoice": billing_invoice or "-",
	}


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
