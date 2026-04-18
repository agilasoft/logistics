# Copyright (c) 2026, Agilasoft and contributors
"""Insert or update operations Custom HTML Blocks (Air / Sea / Customs / Transport) from fixture."""

import json
import os

import frappe

OPERATIONS_DASHBOARD_BLOCKS = (
	"Air Freight Operations Dashboard",
	"Sea Freight Operations Dashboard",
	"Customs Operations Dashboard",
	"Transport Operations Dashboard",
)


def execute():
	path = os.path.join(frappe.get_app_path("logistics"), "fixtures", "custom_html_block.json")
	if not os.path.isfile(path):
		return
	with open(path, encoding="utf-8") as f:
		rows = json.load(f)
	inserted = 0
	updated = 0
	for row in rows:
		if row.get("doctype") != "Custom HTML Block":
			continue
		name = row.get("name")
		if name not in OPERATIONS_DASHBOARD_BLOCKS:
			continue
		if frappe.db.exists("Custom HTML Block", name):
			doc = frappe.get_doc("Custom HTML Block", name)
			doc.html = row.get("html") or doc.html
			doc.style = row.get("style") or doc.style
			doc.script = row.get("script") or doc.script
			doc.flags.ignore_validate = True
			doc.save(ignore_permissions=True)
			updated += 1
		else:
			frappe.get_doc(
				{
					"doctype": "Custom HTML Block",
					"name": name,
					"owner": row.get("owner") or "Administrator",
					"private": row.get("private", 0),
					"html": row.get("html") or "",
					"style": row.get("style") or "",
					"script": row.get("script") or "",
				}
			).insert(ignore_permissions=True)
			inserted += 1
	if inserted or updated:
		frappe.db.commit()
		print(
			f"  Operations dashboard Custom HTML Blocks: {inserted} inserted, {updated} updated from fixture."
		)
