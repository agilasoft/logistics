# Copyright (c) 2026, Agilasoft and contributors
# Re-sync Air Freight Operations block: UNLOCO map popup shows country flag (air booking–style emoji).

import json
import os

import frappe


def execute():
	path = os.path.join(frappe.get_app_path("logistics"), "fixtures", "custom_html_block.json")
	if not os.path.isfile(path):
		return
	with open(path, encoding="utf-8") as f:
		rows = json.load(f)
	updated = 0
	for row in rows:
		if row.get("doctype") != "Custom HTML Block":
			continue
		name = row.get("name")
		if not name or not frappe.db.exists("Custom HTML Block", name):
			continue
		doc = frappe.get_doc("Custom HTML Block", name)
		doc.html = row.get("html") or doc.html
		doc.style = row.get("style") or doc.style
		doc.script = row.get("script") or doc.script
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)
		updated += 1
	if updated:
		frappe.db.commit()
		print(f"  Re-synced {updated} Custom HTML Block(s) (UNLOCO popup flag).")
