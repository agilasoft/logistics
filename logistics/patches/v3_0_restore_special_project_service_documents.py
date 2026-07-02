# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Restore stashed Special Project Service rows as top-level documents."""

from __future__ import annotations

import json

import frappe

from logistics.patches.v3_0_migrate_special_project_service_child_to_stash import _STASH_TABLE


def execute():
	if not frappe.db.table_exists(_STASH_TABLE):
		return

	frappe.reload_doc("special_projects", "doctype", "special_project_service", force=True)

	rows = frappe.db.sql(f"SELECT name, row_json FROM `{_STASH_TABLE}`", as_dict=True)
	for row in rows:
		name = (row.get("name") or "").strip()
		if not name:
			continue
		try:
			data = json.loads(row.get("row_json") or "{}")
		except Exception:
			continue
		if frappe.db.exists("Special Project Service", name):
			doc = frappe.get_doc("Special Project Service", name)
			for key, val in data.items():
				if doc.meta.has_field(key):
					doc.set(key, val)
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			continue
		doc = frappe.new_doc("Special Project Service")
		doc.update(data)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True, set_name=name)

	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{_STASH_TABLE}`")
	frappe.db.commit()
