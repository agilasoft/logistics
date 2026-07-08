"""Install / refresh Purchase Invoice BIR Form 2307 print format from repo HTML."""

from __future__ import annotations

import os

import frappe

from logistics.print_format.pdf_generator import ensure_chrome_pdf_generator_option, preferred_pdf_generator

PRINT_FORMAT_NAME = "BIR 2307"
DOC_TYPE = "Purchase Invoice"
HTML_REL_PATH = "print_format/purchase_invoice/bir_2307.html"


def _app_root() -> str:
	return os.path.dirname(frappe.get_app_path("logistics"))


def _read_html() -> str:
	with open(os.path.join(_app_root(), HTML_REL_PATH), encoding="utf-8") as handle:
		return handle.read()


def _upsert_print_format(html: str) -> None:
	pdf_generator = preferred_pdf_generator()
	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		frappe.db.set_value(
			"Print Format",
			PRINT_FORMAT_NAME,
			{
				"doc_type": DOC_TYPE,
				"module": "Logistics",
				"html": html,
				"pdf_generator": pdf_generator,
				"disabled": 0,
			},
			update_modified=False,
		)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": PRINT_FORMAT_NAME,
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


def install_bir_2307_print_format() -> None:
	ensure_chrome_pdf_generator_option()

	try:
		from logistics.print_format.purchase_invoice.bir_2307_pdf import ensure_template_pdf

		ensure_template_pdf()
	except Exception as exc:
		if frappe.flags.in_install or frappe.flags.in_patch:
			frappe.log_error(title="BIR Form 2307 vector template not installed", message=str(exc))
		else:
			raise

	_upsert_print_format(_read_html())
