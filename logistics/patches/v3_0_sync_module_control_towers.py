# Copyright (c) 2026, Agilasoft and contributors
"""Install Control Tower dashboards for the remaining logistics modules."""

from __future__ import annotations

import json
import os

import frappe

from logistics.control_tower.module_tower import TOWERS


def execute():
	frappe.flags.in_patch = True
	for tower in TOWERS.values():
		_reload_reports(tower)
		_reload_page(tower)
	_sync_dashboard_assets()
	for tower in TOWERS.values():
		_sync_workspace(tower)
		_sync_sidebar(tower)
	frappe.clear_cache()


def _reload_reports(tower):
	prefix = tower["prefix"].upper()
	names = [
		frappe.scrub("{0} Job Files Detail".format(prefix)),
		frappe.scrub("{0} Milestone Lead Time".format(prefix)),
		frappe.scrub(tower["dimension"]["report"]),
		frappe.scrub("{0} Returned Billings".format(prefix)),
		frappe.scrub("{0} Module Snapshot".format(prefix)),
	]
	for name in names:
		frappe.reload_doc(tower["folder"], "report", name, force=True)


def _reload_page(tower):
	route = tower["title"].lower().replace(" ", "-")
	frappe.reload_doc(tower["folder"], "page", route.replace("-", "_"), force=True)


def _sync_dashboard_assets():
	from frappe.utils.dashboard import sync_dashboards

	sync_dashboards(app="logistics")


def _sync_workspace(tower):
	workspace_name = tower["workspace"]
	slug = frappe.scrub(workspace_name)
	data = _load_json(tower["folder"], "workspace", slug, "{0}.json".format(slug))
	if not data:
		return
	if frappe.db.exists("Workspace", workspace_name):
		doc = frappe.get_doc("Workspace", workspace_name)
	else:
		doc = frappe.new_doc("Workspace")
		doc.name = workspace_name
	doc.label = data.get("label") or workspace_name
	doc.title = data.get("title") or workspace_name
	doc.module = data.get("module") or tower["module"]
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


def _sync_sidebar(tower):
	sidebar_name = tower["sidebar"]
	slug = frappe.scrub(sidebar_name)
	data = _load_json(tower["folder"], "sidebar", slug, "{0}.json".format(slug))
	if not data:
		return
	if frappe.db.exists("Sidebar", sidebar_name):
		doc = frappe.get_doc("Sidebar", sidebar_name)
	else:
		doc = frappe.new_doc("Sidebar")
		doc.name = sidebar_name
	doc.title = data.get("title") or sidebar_name
	doc.module = data.get("module") or tower["module"]
	doc.app = data.get("app") or "logistics"
	doc.header_icon = data.get("header_icon") or doc.header_icon
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
