#!/usr/bin/env python3
"""Install or update Gate Pass print format."""
import os

import frappe


def install_gate_pass_print_format():
	html_path = os.path.join(os.path.dirname(__file__), "gate_pass.html")
	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	name = "Gate Pass"
	if frappe.db.exists("Print Format", name):
		print_format = frappe.get_doc("Print Format", name)
		print_format.html = html_content
		print_format.doc_type = "Gate Pass"
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.save()
		print(f"Updated Print Format: {name}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": name,
				"doc_type": "Gate Pass",
				"module": "Warehousing",
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
		print(f"Created Print Format: {name}")

	frappe.db.commit()
	print("Gate Pass print format installed. Use Print > Gate Pass on Gate Pass.")


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_gate_pass_print_format()
	else:
		print("Usage: bench execute logistics.warehousing.print_format.gate_pass.install_print_format.install_gate_pass_print_format")
