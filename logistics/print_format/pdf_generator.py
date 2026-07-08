"""Helpers for Print Format pdf_generator field."""

from __future__ import annotations

import frappe

PROPERTY_SETTER_NAME = "Print Format-pdf_generator-options"


def ensure_chrome_pdf_generator_option() -> None:
	"""Drop stale property setter that hides chrome after Frappe v16 upgrade."""
	if not frappe.db.exists("Property Setter", PROPERTY_SETTER_NAME):
		return

	value = (frappe.db.get_value("Property Setter", PROPERTY_SETTER_NAME, "value") or "").strip()
	options = {option.strip() for option in value.split("\n") if option.strip()}
	if "chrome" in options:
		return

	frappe.delete_doc("Property Setter", PROPERTY_SETTER_NAME, force=1, ignore_permissions=True)
	frappe.clear_cache(doctype="Print Format")


def preferred_pdf_generator() -> str:
	field = frappe.get_meta("Print Format").get_field("pdf_generator")
	options = {option.strip() for option in (field.options or "").split("\n") if option.strip()}
	if "chrome" in options:
		return "chrome"
	return "wkhtmltopdf"
