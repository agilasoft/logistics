#!/usr/bin/env python3
"""Install Summary PB HTML print format (FC00B1-style Periodic Billing)."""
import os

import frappe

PRINT_FORMAT_NAME = "Summary PB HTML"


def install_summary_pb_html_print_format():
	html_path = os.path.join(os.path.dirname(__file__), "summary_pb_html.html")
	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		print_format = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
		print_format.html = html_content
		print_format.doc_type = "Periodic Billing"
		print_format.module = "Warehousing"
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.save(ignore_permissions=True)
		print(f"Updated existing print format: {PRINT_FORMAT_NAME}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": PRINT_FORMAT_NAME,
				"doc_type": "Periodic Billing",
				"module": "Warehousing",
				"standard": "No",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"html": html_content,
				"font_size": 8,
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
		f"{PRINT_FORMAT_NAME} installed. "
		"Open Periodic Billing → Print → Summary PB HTML."
	)


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_summary_pb_html_print_format()
	else:
		print("Please provide a site name as argument")
