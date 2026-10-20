# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Add Bulk Update Studio to the Utilities workspace and Logistics sidebar.

The page record is reloaded from app JSON. Existing workspace and sidebar
rows are left in place; only the new link is inserted.
"""

from __future__ import annotations

import json

import frappe


PAGE = "bulk-update-studio"


def execute():
	frappe.flags.in_patch = True
	frappe.reload_doc("logistics", "page", "bulk_update_studio", force=True)
	_ensure_workspace()
	_ensure_sidebar()
	frappe.clear_cache()


def _ensure_workspace():
	if not frappe.db.exists("Workspace", "Utilities"):
		return
	doc = frappe.get_doc("Workspace", "Utilities")
	if not any(row.link_to == PAGE for row in (doc.shortcuts or [])):
		doc.append(
			"shortcuts",
			{
				"type": "Page",
				"link_to": PAGE,
				"label": "Bulk Update Studio",
				"color": "Blue",
				"doc_view": "",
			},
		)
	if not any(row.link_to == PAGE for row in (doc.links or [])):
		doc.append(
			"links",
			{
				"type": "Link",
				"link_type": "Page",
				"link_to": PAGE,
				"label": "Bulk Update Studio",
				"hidden": 0,
				"is_query_report": 0,
				"link_count": 0,
				"onboard": 0,
			},
		)
	content = _load_content(doc.content)
	if not any(block.get("id") == "bulk-update-studio-shortcut" for block in content):
		content.append(
			{
				"id": "bulk-update-studio-shortcut",
				"type": "shortcut",
				"data": {"shortcut_name": "Bulk Update Studio", "col": 4},
			}
		)
		doc.content = json.dumps(content, separators=(",", ":"), ensure_ascii=False)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)


def _ensure_sidebar():
	if not frappe.db.exists("Sidebar", "Logistics"):
		return
	doc = frappe.get_doc("Sidebar", "Logistics")
	if any(row.link_to == PAGE for row in (doc.items or [])):
		return
	rows = []
	inserted = False
	for row in doc.items:
		rows.append(_child_dict(row))
		if row.link_to == "role-permission-matrix":
			rows.append(_studio_sidebar_item())
			inserted = True
	if not inserted:
		rows.append(_studio_sidebar_item())
	doc.set("items", [])
	for row in rows:
		doc.append("items", row)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)


def _studio_sidebar_item():
	return {
		"type": "Link",
		"label": "Bulk Update Studio",
		"link_type": "Page",
		"link_to": PAGE,
		"icon": "pencil",
		"child": 0,
		"collapsible": 1,
		"keep_closed": 0,
		"show_arrow": 0,
		"indent": 0,
	}


def _child_dict(row):
	data = row.as_dict()
	for key in (
		"name",
		"idx",
		"parent",
		"parentfield",
		"parenttype",
		"doctype",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
	):
		data.pop(key, None)
	return data


def _load_content(raw):
	if not raw:
		return []
	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		return []
	return data if isinstance(data, list) else []
