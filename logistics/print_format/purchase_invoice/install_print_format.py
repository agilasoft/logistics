#!/usr/bin/env python3
"""
Install BIR Purchase Invoice and Payable Voucher HTML print formats
"""
import frappe
import os


def _app_root():
	return os.path.dirname(frappe.get_app_path("logistics"))


def _upsert_print_format(name, html_content):
	"""Create or update a Jinja Print Format for Purchase Invoice."""
	if frappe.db.exists("Print Format", name):
		print_format = frappe.get_doc("Print Format", name)
		print_format.html = html_content
		print_format.doc_type = "Purchase Invoice"
		print_format.module = "Logistics"
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.disabled = 0
		print_format.save()
		print(f"✓ Updated existing {name} print format")
	else:
		print_format = frappe.get_doc({
			"doctype": "Print Format",
			"name": name,
			"doc_type": "Purchase Invoice",
			"module": "Logistics",
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
		})
		print_format.insert(ignore_permissions=True)
		print(f"✓ Created new {name} print format")


def install_payable_voucher_print_format():
	"""Install or update Payable Voucher HTML from app-root HTML file."""
	html_path = os.path.join(
		_app_root(), "print_format", "purchase_invoice", "payable_voucher.html"
	)
	with open(html_path, "r", encoding="utf-8") as f:
		html_content = f.read()
	_upsert_print_format("Payable Voucher HTML", html_content)
	print("  Use from Purchase Invoice > Print > Payable Voucher HTML")


def install_purchase_invoice_print_format():
	"""Install or update BIR Purchase Invoice and Payable Voucher HTML formats."""

	# BIR Purchase Invoice (legacy path next to this installer)
	html_path = os.path.join(os.path.dirname(__file__), "purchase_invoice.html")
	with open(html_path, "r", encoding="utf-8") as f:
		html_content = f.read()
	_upsert_print_format("BIR Purchase Invoice", html_content)
	print("  Supports Purchase Invoice, Debit Note, and Credit Note (Return) in one format.")
	print("  Use from Purchase Invoice > Print > BIR Purchase Invoice")

	install_payable_voucher_print_format()

	frappe.db.commit()
	print("✓ Purchase Invoice print formats installed successfully!")


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_purchase_invoice_print_format()
	else:
		print("Please provide a site name as argument")
