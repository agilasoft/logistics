# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Scope of Work (and legacy Statement of Work) after doctype files are deleted."""

from __future__ import annotations

import json

import frappe

_DOCTYPE_NAMES = ("Scope of Work", "Statement of Work")

_CHILD_TABLES = (
	"Special Project Charges",
	"Special Project Milestone",
	"Operational Exchange Rate",
	"Job Document",
)


def execute():
	if not any(frappe.db.exists("DocType", name) for name in _DOCTYPE_NAMES):
		_cleanup_workspace_links()
		frappe.db.commit()
		frappe.clear_cache()
		return

	frappe.flags.in_patch = True
	try:
		_cleanup_workspace_links()
		_delete_child_rows()
		_delete_documents()
		for name in _DOCTYPE_NAMES:
			if frappe.db.exists("DocType", name):
				frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
		_update_link_field_options()
	finally:
		frappe.flags.in_patch = False
	frappe.db.commit()
	frappe.clear_cache()


def _cleanup_workspace_links():
	labels = (
		"Scope of Work",
		"Scope Of Work",
		"Statement of Work",
		"Statement Of Work",
	)
	if frappe.db.table_exists("Workspace Shortcut"):
		frappe.db.sql(
			"""
			DELETE FROM `tabWorkspace Shortcut`
			WHERE link_to IN %s OR label IN %s
			""",
			(_DOCTYPE_NAMES, labels),
		)
	if frappe.db.table_exists("Workspace Link"):
		frappe.db.sql(
			"""
			DELETE FROM `tabWorkspace Link`
			WHERE link_to IN %s OR label IN %s
			""",
			(_DOCTYPE_NAMES, labels),
		)
	if frappe.db.table_exists("Workspace Sidebar Item"):
		frappe.db.sql(
			"""
			DELETE FROM `tabWorkspace Sidebar Item`
			WHERE link_to IN %s OR label IN %s
			""",
			(_DOCTYPE_NAMES, labels),
		)
	if frappe.db.has_column("Workspace", "content"):
		rows = frappe.db.sql(
			"""
			SELECT name, content FROM `tabWorkspace`
			WHERE content LIKE %s OR content LIKE %s
			""",
			("%Scope Of Work%", "%Statement Of Work%"),
			as_dict=True,
		)
		for row in rows:
			try:
				blocks = json.loads(row.content or "[]")
			except json.JSONDecodeError:
				continue
			filtered = [
				block
				for block in blocks
				if (block.get("data") or {}).get("shortcut_name")
				not in ("Scope Of Work", "Scope of Work", "Statement Of Work", "Statement Of Work")
			]
			if len(filtered) != len(blocks):
				frappe.db.set_value("Workspace", row.name, "content", json.dumps(filtered))


def _delete_child_rows():
	for child in _CHILD_TABLES:
		if frappe.db.table_exists(child):
			frappe.db.delete(child, {"parenttype": "Scope of Work"})
			frappe.db.delete(child, {"parenttype": "Statement of Work"})


def _delete_documents():
	for doctype in _DOCTYPE_NAMES:
		if not frappe.db.table_exists(doctype):
			continue
		for name in frappe.get_all(doctype, pluck="name"):
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)


def _update_link_field_options():
	for parent in ("DocField", "Custom Field"):
		if not frappe.db.table_exists(f"tab{parent}"):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{parent}`
			SET options = 'Special Project'
			WHERE options IN ('Scope of Work', 'Statement of Work')
			"""
		)
