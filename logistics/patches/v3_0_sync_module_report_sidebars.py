# Copyright (c) 2026, Agilasoft and contributors
"""Refresh module sidebars so report groups follow each workspace's report cards."""

from __future__ import annotations

import json
import os

import frappe


# Path is relative to the logistics app. Name is the Sidebar document name.
SIDEBARS = (
	("air_freight/sidebar/air_freight/air_freight.json", "Air Freight"),
	("netting/sidebar/netting/netting.json", "Netting"),
	("sea_freight/sidebar/sea_freight/sea_freight.json", "Sea Freight"),
	("transport/sidebar/transport/transport.json", "Transport"),
	("sustainability/sidebar/sustainability/sustainability.json", "Sustainability"),
	("special_projects/sidebar/special_projects/special_projects.json", "Special Projects"),
	("mice/sidebar/mice/mice.json", "MICE"),
	("pricing_center/sidebar/pricing_center/pricing_center.json", "Pricing Center"),
	("intercompany/sidebar/intercompany/intercompany.json", "Intercompany"),
	("control_tower/sidebar/control_tower/control_tower.json", "Control Tower"),
)


def execute():
	for relative_path, name in SIDEBARS:
		_sync_sidebar(relative_path, name)
	frappe.clear_cache()


def _sync_sidebar(relative_path, name):
	sidebar_path = os.path.join(frappe.get_app_path("logistics"), *relative_path.split("/"))
	if not os.path.isfile(sidebar_path):
		return
	with open(sidebar_path, encoding="utf-8") as handle:
		data = json.load(handle)
	if frappe.db.exists("Sidebar", name):
		doc = frappe.get_doc("Sidebar", name)
	else:
		doc = frappe.new_doc("Sidebar")
		doc.name = name
	doc.title = data.get("title") or name
	doc.module = data.get("module") or name
	doc.app = data.get("app") or "logistics"
	doc.header_icon = data.get("header_icon") or ""
	doc.standard = 1
	_replace_children(doc, "items", data.get("items") or [])
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _replace_children(doc, fieldname, rows):
	doc.set(fieldname, [])
	for row in rows:
		payload = {
			key: value
			for key, value in row.items()
			if key not in ("doctype", "name", "parent", "parentfield", "parenttype")
		}
		doc.append(fieldname, payload)
