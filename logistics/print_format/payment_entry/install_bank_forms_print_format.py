"""Install / refresh Payment Entry BDO bank form print formats from repo HTML."""

from __future__ import annotations

import os

import frappe

from logistics.print_format.pdf_generator import ensure_chrome_pdf_generator_option, preferred_pdf_generator

from logistics.print_format.payment_entry.bank_forms_pdf import (
	BLANK_PRINT_FORMAT_NAME,
	LEGACY_BLANK_PRINT_FORMAT_NAME,
	LEGACY_PRINT_FORMAT_NAME,
	PRINT_FORMAT_NAME,
)

PRINT_FORMATS = {
	PRINT_FORMAT_NAME: "print_format/payment_entry/bdo_form.html",
	BLANK_PRINT_FORMAT_NAME: "print_format/payment_entry/bdo_form_blank.html",
	LEGACY_PRINT_FORMAT_NAME: "print_format/payment_entry/bdo_form.html",
	LEGACY_BLANK_PRINT_FORMAT_NAME: "print_format/payment_entry/bdo_form_blank.html",
}
DOC_TYPE = "Payment Entry"


def _app_root() -> str:
	return os.path.dirname(frappe.get_app_path("logistics"))


def _read_html(rel_path: str) -> str:
	with open(os.path.join(_app_root(), rel_path), encoding="utf-8") as handle:
		return handle.read()


def _upsert_print_format(name: str, html: str) -> None:
	pdf_generator = preferred_pdf_generator()
	if frappe.db.exists("Print Format", name):
		frappe.db.set_value(
			"Print Format",
			name,
			{"html": html, "pdf_generator": pdf_generator},
			update_modified=False,
		)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": name,
			"doc_type": DOC_TYPE,
			"module": "Logistics",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"html": html,
			"pdf_generator": pdf_generator,
			"font_size": 8,
			"disabled": 0,
			"align_labels_right": 0,
			"line_breaks": 0,
			"print_format_builder": 0,
			"raw_printing": 0,
			"show_section_headings": 0,
		}
	)
	doc.insert(ignore_permissions=True)


def install_bank_forms_print_format() -> None:
	ensure_chrome_pdf_generator_option()

	try:
		from logistics.print_format.payment_entry.bank_forms_pdf import ensure_template_pdf

		ensure_template_pdf()
	except Exception as exc:
		if frappe.flags.in_install or frappe.flags.in_patch:
			frappe.log_error(title="BDO vector template not installed", message=str(exc))
		else:
			raise

	for name, rel_path in PRINT_FORMATS.items():
		_upsert_print_format(name, _read_html(rel_path))
