# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Remove Permission Studio from the desk and database.

User Permission rows the studio already created stay. Only the ownership
columns (ps_group, ps_signature) are dropped, so those rows become ordinary
User Permissions. Studio groups, templates, activity, and settings are removed.

Do not use import_file_by_path(force=True) on Workspace: deleting the existing
Workspace runs after_delete and removes the app workspace folder.
"""

from __future__ import unicode_literals

import json
import os

import frappe


STUDIO_DOCTYPES = (
	"Permission Studio Settings",
	"Permission Studio Activity",
	"Permission Template",
	"Permission Group",
	"Permission Group Member",
	"Permission Group Value",
)
OWNERSHIP_FIELDS = ("ps_group", "ps_signature")


def execute():
	frappe.flags.in_patch = True
	_drop_ownership_fields()
	_sync_workspace()
	_sync_sidebar()
	_delete_page()
	_delete_doctypes()
	frappe.clear_cache()


def _drop_ownership_fields():
	"""Remove studio columns from User Permission without deleting its rows."""
	if not frappe.db.table_exists("User Permission"):
		return
	if frappe.db.table_exists("Custom Field"):
		for fieldname in OWNERSHIP_FIELDS:
			name = frappe.db.get_value(
				"Custom Field", {"dt": "User Permission", "fieldname": fieldname}, "name"
			)
			if name:
				frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
	if frappe.db.table_exists("Property Setter"):
		for fieldname in OWNERSHIP_FIELDS:
			for name in frappe.get_all(
				"Property Setter",
				filters={"doc_type": "User Permission", "field_name": fieldname},
				pluck="name",
			):
				frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)
	frappe.db.commit()
	for fieldname in OWNERSHIP_FIELDS:
		if frappe.db.has_column("User Permission", fieldname):
			frappe.db.sql_ddl(f"ALTER TABLE `tabUser Permission` DROP COLUMN `{fieldname}`")
	frappe.db.commit()
	frappe.clear_cache(doctype="User Permission")


def _delete_page():
	if frappe.db.exists("Page", "permission-studio"):
		frappe.delete_doc("Page", "permission-studio", force=True, ignore_permissions=True)


def _delete_doctypes():
	for name in STUDIO_DOCTYPES:
		if frappe.db.exists("DocType", name):
			frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
	frappe.db.commit()
	if frappe.db.table_exists("Singles"):
		frappe.db.delete("Singles", {"doctype": "Permission Studio Settings"})
	for name in STUDIO_DOCTYPES:
		if frappe.db.table_exists(name):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{name}`")
	frappe.db.commit()


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
		child_tables=("links", "shortcuts", "charts", "number_cards", "roles", "custom_blocks"),
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
