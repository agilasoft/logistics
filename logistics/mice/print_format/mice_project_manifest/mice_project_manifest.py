# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Row builder for the MICE Project Manifest print format."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, strip_html

SHIPMENT_TYPES = ("Air Shipment", "Sea Shipment")
DECLARATION_TYPES = ("Declaration", "Customer Declaration")


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
			"exhibitor",
			"exhibitor_name",
			"description",
			"total_packages",
			"total_weight",
			"total_weight_uom",
			"total_volume",
			"total_volume_uom",
			"sales_invoice",
			"sales_quote",
			"required_by",
		],
		order_by="docket_date asc, creation asc",
	)

	rows: list[dict[str, Any]] = []
	for dk in dockets:
		rows.append(_build_row(dk, org_name))
	return rows


def _build_row(dk: dict[str, Any], org_name: str) -> dict[str, str]:
	docket_name = dk.get("name") or ""
	shipment_type, shipment_name = _find_primary_shipment(docket_name)
	shipment = _load_doc(shipment_type, shipment_name) if shipment_name else None

	agent = _freight_agent_label(shipment, dk.get("sales_quote"))
	eta_mnl = _format_date(_shipment_field(shipment, "eta"))
	clearance_date = _declaration_clearance_date(docket_name)
	awb_bl = _awb_or_bl(shipment_type, shipment)
	vsl_flight = _vessel_or_flight(shipment_type, shipment)

	exhibitor_label = (dk.get("exhibitor_name") or "").strip()
	if not exhibitor_label and dk.get("exhibitor"):
		exhibitor_label = (
			frappe.db.get_value("Customer", dk.get("exhibitor"), "customer_name")
			or dk.get("exhibitor")
			or ""
		)

	description = _docket_description(dk)
	ingress = _ingress_schedule(docket_name, dk.get("required_by"))
	contact = _exhibitor_contact(dk.get("exhibitor"))
	billing_invoice = (dk.get("sales_invoice") or "").strip()
	amount = _sales_invoice_amount(billing_invoice)

	return {
		"job_no": (dk.get("job_number") or "").strip() or "-",
		"exhibitor": exhibitor_label or "-",
		"agent": agent or "-",
		"org": org_name or "-",
		"eta_mnl": eta_mnl or "-",
		"clearance_date": clearance_date or "-",
		"awb_bl": awb_bl or "-",
		"vsl_flight": vsl_flight or "-",
		"qty_pkgs": _format_qty(dk.get("total_packages")),
		"g_weight_kg": _format_weight(dk),
		"volume_cbm": _format_volume(dk),
		"description": description or "-",
		"ingress_schedule": ingress or "-",
		"contact": contact or "-",
		"billing_invoice": billing_invoice or "-",
		"amount": amount or "-",
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


def _find_primary_shipment(docket_name: str) -> tuple[str, str]:
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)
	from logistics.utils.linked_service_usage import latest_shipment_from_usage

	candidates: list[tuple[str, str]] = []
	for ls in get_linked_services_for_booking("Docket", docket_name):
		jt, jn = latest_shipment_from_usage(ls.name)
		if jt in SHIPMENT_TYPES and jn:
			candidates.append((jt, jn))

	if not candidates:
		from logistics.mice.doctype.mice_project.mice_project import (
			_resolve_docket_operational_jobs,
		)

		for row in _resolve_docket_operational_jobs(docket_name):
			jt = (row.get("job_type") or "").strip()
			jn = (row.get("job_no") or "").strip()
			if jt in SHIPMENT_TYPES and jn:
				candidates.append((jt, jn))

	if not candidates:
		return "", ""

	for preferred in SHIPMENT_TYPES:
		for jt, jn in candidates:
			if jt == preferred:
				return jt, jn
	return candidates[0]


def _load_doc(doctype: str, name: str):
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None
	return frappe.get_doc(doctype, name)


def _freight_agent_label(shipment, sales_quote: str | None) -> str:
	agent_link = None
	if shipment is not None:
		agent_link = getattr(shipment, "freight_agent", None)
	if not agent_link and sales_quote and frappe.db.exists("Sales Quote", sales_quote):
		sq = frappe.get_doc("Sales Quote", sales_quote)
		if shipment and shipment.doctype == "Sea Shipment":
			agent_link = getattr(sq, "freight_agent_sea", None) or getattr(
				sq, "freight_agent", None
			)
		else:
			agent_link = getattr(sq, "freight_agent", None) or getattr(
				sq, "freight_agent_sea", None
			)
	if not agent_link:
		return ""
	if frappe.db.exists("Freight Agent", agent_link):
		return (
			frappe.db.get_value("Freight Agent", agent_link, "freight_agent_name")
			or agent_link
		)
	return str(agent_link)


def _shipment_field(shipment, fieldname: str):
	if shipment is None:
		return None
	return getattr(shipment, fieldname, None)


def _declaration_clearance_date(docket_name: str) -> str:
	from logistics.mice.doctype.mice_project.mice_project import (
		_resolve_docket_operational_jobs,
	)

	best_actual = None
	best_expected = None
	for row in _resolve_docket_operational_jobs(docket_name):
		jt = (row.get("job_type") or "").strip()
		jn = (row.get("job_no") or "").strip()
		if jt not in DECLARATION_TYPES or not jn:
			continue
		if not frappe.db.exists(jt, jn):
			continue
		actual = frappe.db.get_value(jt, jn, "actual_clearance_date")
		expected = frappe.db.get_value(jt, jn, "expected_clearance_date")
		if actual and (best_actual is None or actual > best_actual):
			best_actual = actual
		if expected and (best_expected is None or expected > best_expected):
			best_expected = expected

	return _format_date(best_actual or best_expected)


def _awb_or_bl(shipment_type: str, shipment) -> str:
	if shipment is None:
		return ""
	if shipment_type == "Air Shipment":
		return (
			getattr(shipment, "house_awb_no", None)
			or getattr(shipment, "house_awb", None)
			or ""
		).strip()
	if shipment_type == "Sea Shipment":
		return (getattr(shipment, "house_bl", None) or "").strip()
	return ""


def _vessel_or_flight(shipment_type: str, shipment) -> str:
	if shipment is None:
		return ""
	if shipment_type == "Sea Shipment":
		vessel = (getattr(shipment, "mbl_vessel", None) or getattr(shipment, "vessel", None) or "").strip()
		voyage = (
			getattr(shipment, "mbl_voyage_no", None)
			or getattr(shipment, "voyage_no", None)
			or ""
		).strip()
		if vessel and voyage:
			return f"{vessel} / {voyage}"
		return vessel or voyage
	if shipment_type == "Air Shipment":
		flight = (
			getattr(shipment, "mawb_flight_no", None)
			or getattr(shipment, "flight_no", None)
			or ""
		)
		if not flight and getattr(shipment, "master_awb", None):
			flight = frappe.db.get_value(
				"Master Air Waybill", shipment.master_awb, "flight_no"
			)
		return (flight or "").strip()
	return ""


def _docket_description(dk: dict[str, Any]) -> str:
	raw = dk.get("description")
	if raw:
		text = strip_html(str(raw)).strip()
		if text:
			return text
	packages = frappe.get_all(
		"Docket Package",
		filters={"parent": dk.get("name"), "parenttype": "Docket"},
		fields=["description", "goods_description", "commodity"],
		order_by="idx asc",
		limit_page_length=1,
	)
	if packages:
		row = packages[0]
		for key in ("description", "goods_description", "commodity"):
			val = (row.get(key) or "").strip()
			if val:
				return val
	return ""


def _ingress_schedule(docket_name: str, required_by) -> str:
	from logistics.mice.doctype.mice_project.mice_project import (
		_resolve_docket_operational_jobs,
	)

	best = None
	for row in _resolve_docket_operational_jobs(docket_name):
		jt = (row.get("job_type") or "").strip()
		jn = (row.get("job_no") or "").strip()
		if jt != "Transport Job" or not jn:
			continue
		order_name = frappe.db.get_value("Transport Job", jn, "transport_order")
		if not order_name or not frappe.db.exists("Transport Order", order_name):
			continue
		scheduled = frappe.db.get_value("Transport Order", order_name, "scheduled_date")
		if scheduled and (best is None or scheduled > best):
			best = scheduled
	if best:
		return _format_date(best)
	return _format_date(required_by)


def _exhibitor_contact(customer: str | None) -> str:
	if not customer or not frappe.db.exists("Customer", customer):
		return ""
	cust = frappe.db.get_value(
		"Customer",
		customer,
		["customer_primary_contact", "mobile_no", "email_id"],
		as_dict=True,
	)
	parts: list[str] = []
	contact_name = (cust or {}).get("customer_primary_contact")
	if contact_name and frappe.db.exists("Contact", contact_name):
		cd = frappe.db.get_value(
			"Contact",
			contact_name,
			["first_name", "last_name", "mobile_no", "phone", "email_id"],
			as_dict=True,
		)
		if cd:
			name = " ".join(
				p for p in [(cd.get("first_name") or ""), (cd.get("last_name") or "")] if p
			).strip()
			if name:
				parts.append(name)
			phone = (cd.get("mobile_no") or cd.get("phone") or "").strip()
			if phone:
				parts.append(phone)
			email = (cd.get("email_id") or "").strip()
			if email:
				parts.append(email)
	if not parts:
		mobile = ((cust or {}).get("mobile_no") or "").strip()
		email = ((cust or {}).get("email_id") or "").strip()
		if mobile:
			parts.append(mobile)
		if email:
			parts.append(email)
	return " / ".join(parts)


def _sales_invoice_amount(sales_invoice: str) -> str:
	if not sales_invoice or not frappe.db.exists("Sales Invoice", sales_invoice):
		return ""
	data = frappe.db.get_value(
		"Sales Invoice",
		sales_invoice,
		["grand_total", "currency"],
		as_dict=True,
	)
	if not data or data.get("grand_total") is None:
		return ""
	return frappe.utils.fmt_money(
		data.grand_total, currency=data.get("currency"), precision=2
	)


def _format_date(value) -> str:
	if not value:
		return ""
	try:
		return frappe.utils.formatdate(value, "MM-dd-yyyy")
	except Exception:
		return str(value)


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
	weight = dk.get("total_weight")
	if weight is None:
		return "-"
	uom = (dk.get("total_weight_uom") or "KG").strip()
	label = f"{flt(weight):g} {uom}".strip()
	return label if label else "-"


def _format_volume(dk: dict[str, Any]) -> str:
	volume = dk.get("total_volume")
	if volume is None:
		return "-"
	uom = (dk.get("total_volume_uom") or "CBM").strip()
	label = f"{flt(volume):g} {uom}".strip()
	return label if label else "-"
