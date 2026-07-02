#!/usr/bin/env python3
"""Install or update Warehouse Job print formats (shared HTML, one per job type)."""
import os

import frappe

PRINT_FORMATS = [
	"Warehouse Job",
	"Warehouse Job - Putaway",
	"Warehouse Job - Pick",
	"Warehouse Job - Move",
	"Warehouse Job - Stocktake",
	"Warehouse Job - VAS",
]


def _upsert_print_format(name: str, html_content: str) -> None:
	if frappe.db.exists("Print Format", name):
		print_format = frappe.get_doc("Print Format", name)
		print_format.html = html_content
		print_format.doc_type = "Warehouse Job"
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.save()
		print(f"Updated Print Format: {name}")
		return

	print_format = frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": name,
			"doc_type": "Warehouse Job",
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


def install_warehouse_job_print_formats():
	html_path = os.path.join(os.path.dirname(__file__), "warehouse_job.html")
	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	for name in PRINT_FORMATS:
		_upsert_print_format(name, html_content)

	frappe.db.commit()
	print(
		"Warehouse Job print formats installed. "
		"Use Print on Warehouse Job and select the matching format."
	)


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_warehouse_job_print_formats()
	else:
		print(
			"Usage: bench execute "
			"logistics.warehousing.print_format.warehouse_job.install_print_format.install_warehouse_job_print_formats"
		)
