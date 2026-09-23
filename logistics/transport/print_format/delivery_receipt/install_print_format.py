#!/usr/bin/env python3
"""Install or update the Delivery Receipt print format for Transport Job."""
import os

import frappe

PRINT_FORMAT_NAME = "Delivery Receipt"
DOC_TYPE = "Transport Job"
MODULE = "Transport"


def _html_path():
	return os.path.join(os.path.dirname(__file__), "delivery_receipt.html")


def install_delivery_receipt_print_format():
	html_path = _html_path()
	if not os.path.isfile(html_path):
		frappe.throw(f"Print format HTML not found: {html_path}")

	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		print_format = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
		print_format.html = html_content
		print_format.doc_type = DOC_TYPE
		print_format.module = MODULE
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.save(ignore_permissions=True)
		print(f"Updated Print Format: {PRINT_FORMAT_NAME}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": PRINT_FORMAT_NAME,
				"doc_type": DOC_TYPE,
				"module": MODULE,
				"standard": "No",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"html": html_content,
				"font_size": 10,
				"disabled": 0,
				"align_labels_right": 0,
				"line_breaks": 0,
				"print_format_builder": 0,
				"raw_printing": 0,
				"show_section_headings": 0,
			}
		)
		print_format.insert(ignore_permissions=True)
		print(f"Created Print Format: {PRINT_FORMAT_NAME}")

	frappe.db.commit()
	print("Delivery Receipt print format installed.")


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_delivery_receipt_print_format()
	else:
		print(
			"Usage: bench execute "
			"logistics.transport.print_format.delivery_receipt.install_print_format."
			"install_delivery_receipt_print_format"
		)
