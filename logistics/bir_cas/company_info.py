# Copyright (c) 2026, Agilasoft and contributors

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import format_datetime, now_datetime


def _company_address_text(company_name: str) -> str:
	if not company_name:
		return ""
	addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company_name],
		],
		fields=["name"],
		limit=1,
	)
	if not addresses:
		return ""
	addr = frappe.get_doc("Address", addresses[0].name)
	parts = [p for p in (addr.address_line1, addr.address_line2) if p]
	city_line = (
		f"{addr.city or ''}"
		f"{(', ' + addr.state) if addr.state else ''}"
		f"{(', ' + addr.country) if addr.country else ''}"
	).strip(", ")
	if city_line.strip():
		parts.append(city_line.strip())
	return ", ".join(parts)


def _bir_cas_settings(company: str) -> dict[str, Any] | None:
	if not company or not frappe.db.exists("DocType", "BIR CAS Settings"):
		return None
	name = frappe.db.get_value("BIR CAS Settings", {"company": company}, "name")
	if not name:
		return None
	return frappe.get_doc("BIR CAS Settings", name).as_dict()


def resolve_company_from_filters(filters) -> str | None:
	if not filters:
		return None
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if not isinstance(filters, dict):
		return None
	company = filters.get("company")
	if company:
		return company
	return frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)


def get_cas_header_context(
	*,
	company: str | None,
	report_title: str,
	period_label: str | None = None,
	filters=None,
) -> dict[str, str]:
	company = company or resolve_company_from_filters(filters)
	if not company:
		company = frappe.defaults.get_user_default("Company") or ""

	company_name = company
	tin = ""
	address = ""

	bir = _bir_cas_settings(company) if company else None
	if bir:
		company_name = bir.get("company_name") or company_name
		tin = bir.get("tin") or ""
		address = (bir.get("business_address") or "").strip()
		if not address:
			city_bits = ", ".join(
				p
				for p in (
					bir.get("city"),
					bir.get("state"),
					bir.get("postal_code"),
				)
				if p
			)
			address = city_bits

	if company and frappe.db.exists("Company", company):
		company_doc = frappe.get_doc("Company", company)
		if not company_name:
			company_name = company_doc.company_name or company
		if not tin:
			tin = company_doc.tax_id or getattr(company_doc, "tin", None) or ""

	if not address and company:
		address = _company_address_text(company)

	user = frappe.session.user if frappe.session else "Guest"
	full_name = frappe.db.get_value("User", user, "full_name") or user
	generated_at = format_datetime(now_datetime(), "MM-dd-yyyy HH:mm:ss")

	return {
		"company_name": company_name or "",
		"company_address": address or "",
		"tin": tin or "",
		"report_title": (report_title or "").strip(),
		"period_label": (period_label or "").strip(),
		"generated_by": full_name,
		"generated_at": generated_at,
	}
