# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Add Permission Studio to Utilities and mark User Permissions it owns.

Do not use import_file_by_path(force=True) on Workspace: deleting the existing
Workspace runs after_delete and removes the app workspace folder.
"""

from __future__ import unicode_literals

import json
import os

import frappe


def execute():
	_ensure_ownership_fields()
	_sync_workspace()
	_sync_sidebar()
	frappe.clear_cache()


def _ensure_ownership_fields():
	if not frappe.db.table_exists("User Permission"):
		return
	from logistics.permissions.studio_api import ensure_ownership_fields

	ensure_ownership_fields()


def _sync_workspace():
	path = frappe.get_app_path("logistics", "logistics", "workspace", "utilities", "utilities.json")
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as handle:
		data = json.load(handle)
	_upsert_from_json(
		"Workspace",
		"Utilities",
		data,
		child_tables=("links", "shortcuts", "charts", "number_cards", "roles"),
	)


def _sync_sidebar():
	if not frappe.db.exists("DocType", "Sidebar"):
		return
	path = frappe.get_app_path("logistics", "logistics", "sidebar", "logistics", "logistics.json")
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as handle:
		data = json.load(handle)
	_upsert_from_json("Sidebar", data.get("name") or "Logistics", data, child_tables=("items",))


def _upsert_from_json(doctype, name, data, child_tables=()):
	ignore = {"doctype", "name", "modified", "modified_by", "creation", "owner", "idx"}
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
	else:
		payload = {key: value for key, value in data.items() if key not in ignore and key not in child_tables}
		payload["doctype"] = doctype
		doc = frappe.get_doc(payload)
		for table in child_tables:
			for row in data.get(table) or []:
				doc.append(table, row)
		_save(doc, insert=True)
		return

	for key, value in data.items():
		if key in ignore or key in child_tables:
			continue
		if doc.meta.has_field(key):
			doc.set(key, value)
	for table in child_tables:
		if not doc.meta.has_field(table):
			continue
		doc.set(table, [])
		for row in data.get(table) or []:
			doc.append(table, row)
	if doctype == "Workspace" and not doc.get("type"):
		doc.type = "Workspace"
	_save(doc, insert=False)


def _save(doc, insert):
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	frappe.flags.in_import = True
	try:
		if insert:
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)
	finally:
		frappe.flags.in_import = False
