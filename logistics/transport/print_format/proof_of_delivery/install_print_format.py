#!/usr/bin/env python3
"""Install or update Proof of Delivery print format for Transport Leg."""
import os

import frappe

UNSAFE_LETTER_HEAD_PATTERN = 'get_doc("Company", doc.company)'


def fix_cargonext_letter_head():
	"""Fix CargoNext letter head: Transport Leg has no company field."""
	lh_path = os.path.join(os.path.dirname(__file__), "cargonext_letter_head.html")
	if not os.path.exists(lh_path):
		return

	with open(lh_path, encoding="utf-8") as f:
		fixed_content = f.read()

	for name in frappe.get_all("Letter Head", pluck="name"):
		content = frappe.db.get_value("Letter Head", name, "content") or ""
		if UNSAFE_LETTER_HEAD_PATTERN not in content:
			continue

		lh = frappe.get_doc("Letter Head", name)
		lh.content = fixed_content
		lh.save(ignore_permissions=True)
		print(f"Fixed Letter Head: {name}")


def install_proof_of_delivery_print_format():
	html_path = os.path.join(os.path.dirname(__file__), "proof_of_delivery.html")
	with open(html_path, encoding="utf-8") as f:
		html_content = f.read()

	name = "Proof of Delivery HTML"
	if frappe.db.exists("Print Format", name):
		print_format = frappe.get_doc("Print Format", name)
		print_format.html = html_content
		print_format.doc_type = "Transport Leg"
		print_format.custom_format = 1
		print_format.print_format_type = "Jinja"
		print_format.save()
		print(f"Updated Print Format: {name}")
	else:
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": name,
				"doc_type": "Transport Leg",
				"module": "Transport",
				"standard": "No",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"html": html_content,
				"font_size": 9,
				"disabled": 0,
			}
		)
		print_format.insert(ignore_permissions=True)
		print(f"Created Print Format: {name}")

	fix_cargonext_letter_head()
	frappe.db.commit()


if __name__ == "__main__":
	import sys

	site = sys.argv[1] if len(sys.argv) > 1 else None
	if site:
		frappe.init(site=site)
		frappe.connect()
		install_proof_of_delivery_print_format()
	else:
		print("Usage: bench execute logistics.transport.print_format.proof_of_delivery.install_print_format.install_proof_of_delivery_print_format")
