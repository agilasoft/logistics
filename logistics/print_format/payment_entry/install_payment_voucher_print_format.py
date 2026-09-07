"""Install / refresh Payment Entry Payment Voucher HTML print format from repo HTML."""

from __future__ import annotations

import os

import frappe

PRINT_FORMAT_NAME = "Payment Voucher HTML"
DOC_TYPE = "Payment Entry"


def _html_path() -> str:
	app_root = os.path.dirname(frappe.get_app_path("logistics"))
	return os.path.join(app_root, "print_format", "payment_entry", "payment_voucher.html")


def install_payment_voucher_print_format() -> None:
	with open(_html_path(), encoding="utf-8") as handle:
		html = handle.read()

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		print_format = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
		print_format.html = html
		print_format.doc_type = DOC_TYPE
		print_format.module = "Logistics"
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.save(ignore_permissions=True)
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
