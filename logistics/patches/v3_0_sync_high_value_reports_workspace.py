# Copyright (c) 2026, Agilasoft and contributors
"""Install High Value reports and refresh the workspace shortcuts and cards."""

from __future__ import annotations

import json
import os

import frappe

WORKSPACE_NAME = "High Value"

REPORTS = (
	"high_value_job_health",
	"high_value_sla_aging",
	"high_value_brand_board",
	"high_value_quote_pipeline",
	"high_value_modality_mix",
)


def execute():
	frappe.flags.in_patch = True
	_reload("report", REPORTS)
	_sync_workspace()
	frappe.clear_cache()


def _reload(dt, names):
	for name in names:
		frappe.reload_doc("high_value", dt, name, force=True)


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
	doc.module = data.get("module") or "High Value"
	doc.title = data.get("title") or WORKSPACE_NAME
	doc.label = data.get("label") or WORKSPACE_NAME
	_replace_children(doc, "custom_blocks", data.get("custom_blocks") or [])
	_replace_children(doc, "shortcuts", data.get("shortcuts") or [])
	_replace_children(doc, "links", data.get("links") or [])
	_replace_children(doc, "roles", data.get("roles") or [{"role": "All"}])
	_replace_children(doc, "charts", data.get("charts") or [])
	_replace_children(doc, "number_cards", data.get("number_cards") or [])
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _replace_children(doc, fieldname, rows):
	if not doc.meta.has_field(fieldname):
		return
	doc.set(fieldname, [])
	for row in rows:
		payload = {k: v for k, v in row.items() if k not in ("doctype", "name", "parent", "parentfield", "parenttype")}
		doc.append(fieldname, payload)
