#!/usr/bin/env python3
"""Install Master Bill of Lading print format for Master Bill."""
import os

import frappe


def install_master_bill_print_format():
	html_path = os.path.join(os.path.dirname(__file__), "master_bill.html")
	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	name = "Master Bill of Lading"
	if frappe.db.exists("Print Format", name):
		print_format = frappe.get_doc("Print Format", name)
		print_format.html = html_content
		print_format.save()
		print(f"Updated existing print format: {name}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": name,
				"doc_type": "Master Bill",
				"module": "Sea Freight",
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
		print(f"Created print format: {name}")

	frappe.db.commit()
	print("Master Bill print format installed. Use Print > Master Bill of Lading on Master Bill.")


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_master_bill_print_format()
	else:
		print("Please provide a site name as argument")
