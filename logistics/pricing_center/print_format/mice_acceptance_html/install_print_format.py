#!/usr/bin/env python3
"""Install MICE Acceptance HTML print format."""
import os

import frappe

PRINT_FORMAT_NAME = "MICE Acceptance HTML"
DOC_TYPE = "Sales Quote"
MODULE = "Pricing Center"


def install_mice_acceptance_html_print_format():
	html_path = os.path.join(os.path.dirname(__file__), "mice_acceptance_html.html")
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
		print_format.standard = "No"
		print_format.save(ignore_permissions=True)
		print(f"Updated existing print format: {PRINT_FORMAT_NAME}")
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
		print(f"Created print format: {PRINT_FORMAT_NAME}")

	frappe.db.commit()
	print(
		f"{PRINT_FORMAT_NAME} installed. Use Print > {PRINT_FORMAT_NAME} on Sales Quote."
	)
	return PRINT_FORMAT_NAME


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_mice_acceptance_html_print_format()
	else:
		print(
			"Usage: bench --site <site> execute "
			"logistics.pricing_center.print_format.mice_acceptance_html."
			"install_print_format.install_mice_acceptance_html_print_format"
		)
