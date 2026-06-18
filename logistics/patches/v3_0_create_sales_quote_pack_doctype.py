# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Ensure Sales Quote Pack print format exists after doctype migration."""

from __future__ import unicode_literals

import frappe
import os


def execute():
	_install_pack_print_format()


def _install_pack_print_format():
	pf_dir = os.path.join(
		frappe.get_app_path("logistics"),
		"pricing_center",
		"print_format",
		"sales_quote_pack",
	)
	pf_json = os.path.join(pf_dir, "sales_quote_pack.json")
	pf_html = os.path.join(pf_dir, "sales_quote_pack.html")
	if not os.path.isfile(pf_json):
		return
	if frappe.db.exists("Print Format", "Sales Quote Pack"):
		return
	with open(pf_json) as f:
		data = frappe.parse_json(f.read())
	if os.path.isfile(pf_html):
		with open(pf_html) as hf:
			data["html"] = hf.read()
	doc = frappe.get_doc(data)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
