# Copyright (c) 2026, Agilasoft and contributors
"""File Warehousing reports under the Reports & Analysis cards."""

from __future__ import annotations

import json
import os

import frappe

WORKSPACE_NAME = "Warehousing"


def execute():
	frappe.flags.in_patch = True
	_sync_workspace()
	frappe.clear_cache()


def _sync_workspace():
	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(app_path, "warehousing", "workspace", "warehousing", "warehousing.json")
	if not os.path.isfile(workspace_path):
		return
	with open(workspace_path, encoding="utf-8") as f:
		data = json.load(f)
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		doc = frappe.get_doc("Workspace", WORKSPACE_NAME)
	else:
		doc = frappe.new_doc("Workspace")
		doc.name = WORKSPACE_NAME
		doc.label = data.get("label") or WORKSPACE_NAME
		doc.title = data.get("title") or WORKSPACE_NAME
		doc.module = data.get("module") or "Warehousing"
		doc.public = 1

	doc.content = data.get("content") or doc.content
	doc.public = data.get("public", 1)
	doc.module = data.get("module") or "Warehousing"
	doc.title = data.get("title") or WORKSPACE_NAME
	doc.label = data.get("label") or WORKSPACE_NAME
	_replace_children(doc, "links", data.get("links") or [])
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _replace_children(doc, fieldname, rows):
	doc.set(fieldname, [])
	for row in rows:
		payload = {k: v for k, v in row.items() if k not in ("doctype", "name", "parent", "parentfield", "parenttype")}
		doc.append(fieldname, payload)
