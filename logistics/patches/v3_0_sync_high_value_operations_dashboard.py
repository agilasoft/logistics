# Copyright (c) 2026, Agilasoft and contributors
"""Install High Value operations dashboard Custom HTML Block and refresh the workspace."""

from __future__ import annotations

import json
import os

import frappe

BLOCK_NAME = "High Value Operations Dashboard"
WORKSPACE_NAME = "High Value"


def execute():
	frappe.flags.in_patch = True
	_reload_sales_quote()
	_sync_custom_html_block()
	_sync_workspace()
	frappe.clear_cache()


def _reload_sales_quote():
	try:
		frappe.reload_doc("pricing_center", "doctype", "sales_quote")
	except Exception:
		try:
			frappe.reload_doctype("Sales Quote")
		except Exception:
			pass


def _sync_custom_html_block():
	path = os.path.join(frappe.get_app_path("logistics"), "fixtures", "custom_html_block.json")
	if not os.path.isfile(path):
		return
	with open(path, encoding="utf-8") as f:
		rows = json.load(f)
	row = next((r for r in rows if r.get("name") == BLOCK_NAME), None)
	if not row:
		return
	if frappe.db.exists("Custom HTML Block", BLOCK_NAME):
		doc = frappe.get_doc("Custom HTML Block", BLOCK_NAME)
		doc.html = row.get("html") or doc.html
		doc.style = row.get("style") or doc.style
		doc.script = row.get("script") or doc.script
		doc.private = row.get("private", 0)
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)
		return
	frappe.get_doc(
		{
			"doctype": "Custom HTML Block",
			"name": BLOCK_NAME,
			"owner": row.get("owner") or "Administrator",
			"private": row.get("private", 0),
			"html": row.get("html") or "",
			"style": row.get("style") or "",
			"script": row.get("script") or "",
		}
	).insert(ignore_permissions=True)


def _sync_workspace():
	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(app_path, "high_value", "workspace", "high_value", "high_value.json")
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
		doc.module = data.get("module") or "High Value"
		doc.public = 1

	doc.content = data.get("content") or doc.content
	doc.icon = data.get("icon") or doc.icon
	doc.indicator_color = data.get("indicator_color") or doc.indicator_color
	doc.public = data.get("public", 1)
	_replace_children(doc, "custom_blocks", data.get("custom_blocks") or [])
	_replace_children(doc, "shortcuts", data.get("shortcuts") or [])
	_replace_children(doc, "links", data.get("links") or [])
	_replace_children(doc, "roles", data.get("roles") or [{"role": "All"}])
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
