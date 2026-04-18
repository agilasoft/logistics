# Copyright (c) 2026, Agilasoft and contributors
# Sync workspace "Air Freight Operations Dashboard" Custom HTML Block from app fixture
# so desk picks up script/CSS updates without manual re-import.

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
		print(f"  Synced {updated} Custom HTML Block document(s) from logistics/fixtures/custom_html_block.json.")
