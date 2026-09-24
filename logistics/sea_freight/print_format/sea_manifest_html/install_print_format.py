#!/usr/bin/env python3
"""Install or update the Sea Manifest HTML print format for Sea Shipment."""
import os

import frappe

PRINT_FORMAT_NAME = "Sea Manifest HTML"
DOC_TYPE = "Sea Shipment"
MODULE = "Sea Freight"


def _html_path():
	return os.path.join(os.path.dirname(__file__), "sea_manifest_html.html")


def install_sea_manifest_html_print_format():
	html_path = _html_path()
	if not os.path.isfile(html_path):
		frappe.throw(f"Print format HTML not found: {html_path}")

	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	values = {
		"html": html_content,
		"doc_type": DOC_TYPE,
		"module": MODULE,
		"custom_format": 1,
		"print_format_type": "Jinja",
		"disabled": 0,
		"font_size": 8,
		"margin_top": 6,
		"margin_bottom": 6,
		"margin_left": 6,
		"margin_right": 6,
		"page_number": "Hide",
	}

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		print_format = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
		print_format.update(values)
		print_format.save(ignore_permissions=True)
		print(f"Updated Print Format: {PRINT_FORMAT_NAME}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": PRINT_FORMAT_NAME,
				"standard": "No",
				"align_labels_right": 0,
				"line_breaks": 0,
				"print_format_builder": 0,
				"raw_printing": 0,
				"show_section_headings": 0,
				**values,
			}
		)
		print_format.insert(ignore_permissions=True)
		print(f"Created Print Format: {PRINT_FORMAT_NAME}")

	frappe.db.commit()
	print("Sea Manifest HTML print format installed.")


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_sea_manifest_html_print_format()
	else:
		print(
			"Usage: bench execute "
			"logistics.sea_freight.print_format.sea_manifest_html.install_print_format."
			"install_sea_manifest_html_print_format"
		)
