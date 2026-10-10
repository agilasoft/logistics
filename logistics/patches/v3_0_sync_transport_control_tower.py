# Copyright (c) 2026, Agilasoft and contributors
"""Install the Transport Control Tower dashboard, workspace shortcut, and sidebar link."""

from __future__ import annotations

import json
import os

import frappe


WORKSPACE_NAME = "Transport"
SIDEBAR_NAME = "Transport"
REPORTS = (
	"tct_job_files_detail",
	"tct_milestone_lead_time",
	"tct_vehicle_type_volumes",
	"tct_returned_billings",
	"tct_module_snapshot",
)


def execute():
	frappe.flags.in_patch = True
	_reload_reports()
	_reload_page()
	_sync_dashboard_assets()
	_sync_workspace()
	_sync_sidebar()
	frappe.clear_cache()


def _reload_reports():
	for name in REPORTS:
		frappe.reload_doc("transport", "report", name, force=True)


def _reload_page():
	frappe.reload_doc("transport", "page", "transport_control_tower", force=True)


def _sync_dashboard_assets():
	"""Import standard Number Cards, Dashboard Charts, and Dashboards."""
	from frappe.utils.dashboard import sync_dashboards

	sync_dashboards(app="logistics")


def _sync_workspace():
	data = _load_json("transport", "workspace", "transport", "transport.json")
	if not data:
		return
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		doc = frappe.get_doc("Workspace", WORKSPACE_NAME)
	else:
		doc = frappe.new_doc("Workspace")
		doc.name = WORKSPACE_NAME
	doc.label = data.get("label") or WORKSPACE_NAME
	doc.title = data.get("title") or WORKSPACE_NAME
	doc.module = data.get("module") or "Transport"
	doc.public = data.get("public", 1)
	doc.content = data.get("content") or doc.content
	doc.icon = data.get("icon") or doc.icon
	doc.indicator_color = data.get("indicator_color") or doc.indicator_color
	_replace_children(doc, "custom_blocks", data.get("custom_blocks") or [])
	_replace_children(doc, "shortcuts", data.get("shortcuts") or [])
	_replace_children(doc, "links", data.get("links") or [])
	_replace_children(doc, "charts", data.get("charts") or [])
	_replace_children(doc, "number_cards", data.get("number_cards") or [])
	if "roles" in data:
		_replace_children(doc, "roles", data.get("roles") or [])
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _sync_sidebar():
	data = _load_json("transport", "sidebar", "transport", "transport.json")
	if not data:
		return
	if frappe.db.exists("Sidebar", SIDEBAR_NAME):
		doc = frappe.get_doc("Sidebar", SIDEBAR_NAME)
	else:
		doc = frappe.new_doc("Sidebar")
		doc.name = SIDEBAR_NAME
	doc.title = data.get("title") or SIDEBAR_NAME
	doc.module = data.get("module") or "Transport"
	doc.app = data.get("app") or "logistics"
	doc.header_icon = data.get("header_icon") or "transport"
	doc.standard = 1
	_replace_children(doc, "items", data.get("items") or [])
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _load_json(*parts):
	path = os.path.join(frappe.get_app_path("logistics"), *parts)
	if not os.path.isfile(path):
		return None
	with open(path, encoding="utf-8") as handle:
		return json.load(handle)


def _replace_children(doc, fieldname, rows):
	if not doc.meta.has_field(fieldname):
		return
	doc.set(fieldname, [])
	for row in rows:
		payload = {
			key: value
			for key, value in row.items()
			if key not in ("doctype", "name", "parent", "parentfield", "parenttype")
		}
		doc.append(fieldname, payload)
