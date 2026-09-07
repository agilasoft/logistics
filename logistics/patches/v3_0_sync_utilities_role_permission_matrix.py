# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Install Role Permission Matrix on the Utilities workspace and sidebar.

Do not use import_file_by_path(force=True) on Workspace: deleting the existing
Workspace runs after_delete → shutil.rmtree on the app workspace folder.
"""

from __future__ import unicode_literals

import json
import os

import frappe
from frappe.modules.utils import get_app_level_directory_path


def execute():
	_sync_workspace()
	_sync_sidebar()
	frappe.clear_cache()


def _sync_workspace():
	path = frappe.get_app_path(
		"logistics", "logistics", "workspace", "utilities", "utilities.json"
	)
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as fh:
		data = json.load(fh)
	_upsert_from_json(
		"Workspace",
		"Utilities",
		data,
		child_tables=("links", "shortcuts", "charts", "number_cards", "roles"),
	)


def _sync_sidebar():
	path = os.path.join(get_app_level_directory_path("workspace_sidebar", "logistics"), "utilities.json")
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as fh:
		data = json.load(fh)
	_upsert_from_json("Workspace Sidebar", "Utilities", data, child_tables=("items",))


def _upsert_from_json(doctype, name, data, child_tables=()):
	ignore = {"doctype", "name", "modified", "modified_by", "creation", "owner", "idx"}
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
	else:
		payload = {k: v for k, v in data.items() if k not in ignore and k not in child_tables}
		payload["doctype"] = doctype
		doc = frappe.get_doc(payload)
		for table in child_tables:
			for row in data.get(table) or []:
				doc.append(table, row)
		doc.insert(ignore_permissions=True)
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
	doc.flags.ignore_permissions = True
	frappe.flags.in_import = True
	try:
		if doctype == "Workspace" and not doc.get("type"):
			doc.type = "Workspace"
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags.in_import = False
