# Copyright (c) 2026, Agilasoft and contributors
"""Add the Workflow Center page link to each logistics module workspace and sidebar."""

from __future__ import annotations

import frappe

from logistics.workflow_center.desk_links import apply_sidebar, apply_workspace


_CHILD_SKIP = {
	"doctype",
	"name",
	"parent",
	"parentfield",
	"parenttype",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
}


def execute():
	frappe.flags.in_patch = True
	if frappe.db.exists("DocType", "Page"):
		frappe.reload_doc("logistics", "page", "workflow_center", force=True)
	_sync_workspaces()
	_sync_sidebars()
	frappe.clear_cache()


def _sync_workspaces():
	for name in _logistics_workspace_names():
		if not frappe.db.exists("Workspace", name):
			continue
		doc = frappe.get_doc("Workspace", name)
		payload = {
			"content": doc.content or "[]",
			"shortcuts": [_child_payload(row) for row in doc.shortcuts],
		}
		if not apply_workspace(payload):
			continue
		doc.content = payload["content"]
		_replace_children(doc, "shortcuts", payload["shortcuts"])
		_save(doc)


def _sync_sidebars():
	if not frappe.db.table_exists("Sidebar"):
		return
	for name in frappe.get_all("Sidebar", filters={"app": "logistics"}, pluck="name"):
		doc = frappe.get_doc("Sidebar", name)
		payload = {"items": [_child_payload(row) for row in (doc.items or [])]}
		if not apply_sidebar(payload):
			continue
		_replace_children(doc, "items", payload["items"])
		_save(doc)


def _logistics_workspace_names():
	modules = _module_names()
	if not modules:
		return []
	return frappe.get_all(
		"Workspace",
		filters={"public": 1, "module": ["in", modules]},
		pluck="name",
	)


def _module_names():
	path = frappe.get_app_path("logistics", "modules.txt")
	try:
		with open(path, encoding="utf-8") as handle:
			return [line.strip() for line in handle if line.strip()]
	except OSError:
		return []


def _child_payload(row):
	data = row.as_dict() if hasattr(row, "as_dict") else dict(row)
	return {key: value for key, value in data.items() if key not in _CHILD_SKIP}


def _replace_children(doc, fieldname, rows):
	doc.set(fieldname, [])
	for row in rows:
		doc.append(fieldname, row)


def _save(doc):
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)
