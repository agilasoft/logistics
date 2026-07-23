#!/usr/bin/env python3
"""Install or update Transport Order POD HTML print format."""
import json
import os

import frappe

PRINT_FORMAT_NAME = "Transport Order POD HTML"
DOC_TYPE = "Transport Order"
MODULE = "Transport"


def _html_path():
	return os.path.join(os.path.dirname(__file__), "transport_order_pod_html.html")


def _json_path():
	return os.path.join(os.path.dirname(__file__), "transport_order_pod_html.json")


def read_html():
	with open(_html_path(), encoding="utf-8") as f:
		return f.read()


def write_fixture_json(html_content=None):
	"""Write/update the standard Print Format JSON fixture from the HTML file."""
	html_content = html_content if html_content is not None else read_html()
	fixture = {
		"absolute_value": 0,
		"align_labels_right": 0,
		"creation": "2026-07-22 00:00:00.000000",
		"custom_format": 1,
		"default_print_language": "en",
		"disabled": 0,
		"doc_type": DOC_TYPE,
		"docstatus": 0,
		"doctype": "Print Format",
		"font_size": 14,
		"html": html_content,
		"idx": 0,
		"line_breaks": 0,
		"margin_bottom": 15.0,
		"margin_left": 15.0,
		"margin_right": 15.0,
		"margin_top": 15.0,
		"modified": "2026-07-22 00:00:00.000000",
		"modified_by": "Administrator",
		"module": MODULE,
		"name": PRINT_FORMAT_NAME,
		"owner": "Administrator",
		"page_number": "Hide",
		"pdf_generator": "chrome",
		"print_format_builder": 0,
		"print_format_builder_beta": 0,
		"print_format_for": "DocType",
		"print_format_type": "Jinja",
		"raw_printing": 0,
		"show_section_headings": 0,
		"standard": "Yes",
	}
	with open(_json_path(), "w", encoding="utf-8") as f:
		json.dump(fixture, f, indent=1, ensure_ascii=False)
		f.write("\n")
	return fixture


def install_transport_order_pod_html_print_format():
	html_content = read_html()

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		print_format = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
		print_format.html = html_content
		print_format.doc_type = DOC_TYPE
		print_format.module = MODULE
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.pdf_generator = "chrome"
		print_format.page_number = "Hide"
		print_format.standard = "Yes"
		print_format.save(ignore_permissions=True)
		print(f"Updated Print Format: {PRINT_FORMAT_NAME}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": PRINT_FORMAT_NAME,
				"doc_type": DOC_TYPE,
				"module": MODULE,
				"standard": "Yes",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"html": html_content,
				"font_size": 14,
				"disabled": 0,
				"pdf_generator": "chrome",
				"page_number": "Hide",
				"margin_top": 15.0,
				"margin_bottom": 15.0,
				"margin_left": 15.0,
				"margin_right": 15.0,
			}
		)
		print_format.insert(ignore_permissions=True)
		print(f"Created Print Format: {PRINT_FORMAT_NAME}")

	frappe.db.commit()
	return PRINT_FORMAT_NAME


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_transport_order_pod_html_print_format()
	else:
		print(
			"Usage: bench execute logistics.transport.print_format."
			"transport_order_pod_html.install_print_format.install_transport_order_pod_html_print_format"
		)
