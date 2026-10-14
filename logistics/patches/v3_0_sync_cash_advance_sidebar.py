# Copyright (c) 2026, Agilasoft and contributors
"""Replace the flat Cash Advance sidebar with the shared module layout."""

from __future__ import annotations

import json
import os

import frappe


SIDEBAR_NAME = "Cash Advance"


def execute():
	frappe.flags.in_patch = True
	_sync_sidebar()
	frappe.clear_cache()


def _sync_sidebar():
	sidebar_path = os.path.join(
		frappe.get_app_path("logistics"),
		"cash_advance",
		"sidebar",
		"cash_advance",
		"cash_advance.json",
	)
	if not os.path.isfile(sidebar_path):
		return
	with open(sidebar_path, encoding="utf-8") as handle:
		data = json.load(handle)
	if frappe.db.exists("Sidebar", SIDEBAR_NAME):
		doc = frappe.get_doc("Sidebar", SIDEBAR_NAME)
	else:
		doc = frappe.new_doc("Sidebar")
		doc.name = SIDEBAR_NAME
	doc.title = data.get("title") or SIDEBAR_NAME
	doc.module = data.get("module") or "Cash Advance"
	doc.app = data.get("app") or "logistics"
	doc.header_icon = data.get("header_icon") or "cash_advance"
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
