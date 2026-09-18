# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Refresh Air Freight workspace and sidebar with CASSLink links.

Do not use import_file_by_path(force=True) on Workspace: deleting the existing
Workspace runs after_delete → shutil.rmtree on the app workspace folder.
"""

from __future__ import unicode_literals

import json
import os

import frappe
from frappe.modules.utils import get_app_level_directory_path

_LINK_TYPE_DOCTYPE = {
	"DocType": "DocType",
	"Report": "Report",
	"Page": "Page",
	"Workspace": "Workspace",
}


def execute():
	_sync_workspace()
	_sync_sidebar()
	frappe.clear_cache()


def _sync_workspace():
	path = frappe.get_app_path(
		"logistics", "air_freight", "workspace", "air_freight", "air_freight.json"
	)
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as fh:
		data = json.load(fh)
	_upsert_from_json("Workspace", "Air Freight", data, child_tables=("links", "shortcuts", "charts", "number_cards"))


def _sync_sidebar():
	path = os.path.join(get_app_level_directory_path("workspace_sidebar", "logistics"), "air_freight.json")
	if not os.path.exists(path):
		return
	with open(path, encoding="utf-8") as fh:
		data = json.load(fh)
	_upsert_from_json("Workspace Sidebar", "Air Freight", data, child_tables=("items",))


def _upsert_from_json(doctype, name, data, child_tables=()):
	ignore = {"doctype", "name", "modified", "modified_by", "creation", "owner", "idx"}
	data = _drop_missing_link_targets(data, child_tables)
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
	else:
		payload = {k: v for k, v in data.items() if k not in ignore and k not in child_tables}
		payload["doctype"] = doctype
		doc = frappe.get_doc(payload)
		for table in child_tables:
			for row in data.get(table) or []:
				doc.append(table, row)
		_save_workspace_doc(doc, insert=True)
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
	_save_workspace_doc(doc, insert=False)


def _save_workspace_doc(doc, insert):
	# GoConnect Settings (and similar optional-app links) are not on every site.
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	# Workspace.on_update exports JSON to the app folder; skip that in migrate.
	frappe.flags.in_import = True
	try:
		if insert:
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)
	finally:
		frappe.flags.in_import = False


def _drop_missing_link_targets(data, child_tables):
	"""Skip desk links whose DocType/Report/Page is not installed on this site."""
	out = dict(data)
	for table in child_tables:
		rows = out.get(table) or []
		kept = [row for row in rows if _link_target_exists(row)]
		if table == "links":
			kept = _recount_card_breaks(kept)
		out[table] = kept
	return out


def _link_target_exists(row):
	target = row.get("link_to")
	if not target or row.get("type") in ("Card Break", "Section Break"):
		return True
	link_type = row.get("link_type") or row.get("type")
	doctype = _LINK_TYPE_DOCTYPE.get(link_type)
	if not doctype:
		return True
	return bool(frappe.db.exists(doctype, target))


def _recount_card_breaks(rows):
	result = []
	i = 0
	while i < len(rows):
		row = dict(rows[i])
		if row.get("type") == "Card Break":
			count = 0
			j = i + 1
			while j < len(rows) and rows[j].get("type") != "Card Break":
				if rows[j].get("type") == "Link":
					count += 1
				j += 1
			row["link_count"] = count
		result.append(row)
		i += 1
	return result
