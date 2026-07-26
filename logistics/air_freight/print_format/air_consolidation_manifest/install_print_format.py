#!/usr/bin/env python3
"""Install or update the Air Consolidation Manifest print format."""
import os

import frappe

PRINT_FORMAT_NAME = "Air Consolidation Manifest"
DOC_TYPE = "Air Consolidation"
MODULE = "Air Freight"


def _html_path():
	# Prefer module template under air_freight/print_format/
	module_html = os.path.join(os.path.dirname(__file__), "air_consolidation_manifest.html")
	if os.path.isfile(module_html):
		return module_html
	# Fallback: apps/logistics/print_format/air_consolidation_manifest/
	app_root = os.path.dirname(
		os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
	)
	consolidated = os.path.join(
		app_root, "print_format", "air_consolidation_manifest", "air_consolidation_manifest.html"
	)
	return consolidated


def install_air_consolidation_manifest_print_format():
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
				"font_size": 9,
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
	print("Air Consolidation Manifest print format installed.")


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_air_consolidation_manifest_print_format()
	else:
		print(
			"Usage: bench execute "
			"logistics.air_freight.print_format.air_consolidation_manifest.install_print_format."
			"install_air_consolidation_manifest_print_format"
		)
