"""Install / refresh Payment Entry BDO Bank Cheque print format from repo HTML."""

from __future__ import annotations

import os

import frappe

PRINT_FORMAT_NAME = "Bank Cheque"
DOC_TYPE = "Payment Entry"


def _html_path() -> str:
	app_root = os.path.dirname(frappe.get_app_path("logistics"))
	return os.path.join(app_root, "print_format", "payment_entry", "bank_cheque.html")


def install_bank_cheque_print_format() -> None:
	with open(_html_path(), encoding="utf-8") as handle:
		html = handle.read()

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		frappe.db.set_value("Print Format", PRINT_FORMAT_NAME, "html", html, update_modified=False)
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
