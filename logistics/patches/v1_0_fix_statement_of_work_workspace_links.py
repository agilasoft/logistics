# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Point workspace links from renamed Statement of Work to Scope of Work."""

from __future__ import annotations

import json

import frappe


def execute():
	_fix_workspace_shortcuts()
	_fix_workspace_content()
	_fix_workspace_links()
	_fix_workspace_sidebar_items()
	_fix_doctype_link_options()

	frappe.db.commit()
	frappe.clear_cache()


def _fix_workspace_shortcuts():
	if not frappe.db.table_exists("Workspace Shortcut"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Shortcut`
		SET link_to = 'Scope of Work',
			label = 'Scope Of Work'
		WHERE link_to = 'Statement of Work'
		   OR label IN ('Statement Of Work', 'Statement of Work')
		"""
	)


def _fix_workspace_content():
	if not frappe.db.has_column("Workspace", "content"):
		return
	rows = frappe.db.sql(
		"""
		SELECT name, content FROM `tabWorkspace`
		WHERE content LIKE %s
		""",
		("%Statement Of Work%",),
		as_dict=True,
	)
	for row in rows:
		try:
			blocks = json.loads(row.content or "[]")
		except json.JSONDecodeError:
			continue
		changed = False
		for block in blocks:
			data = block.get("data") or {}
			if data.get("shortcut_name") in ("Statement Of Work", "Statement of Work"):
				data["shortcut_name"] = "Scope Of Work"
				changed = True
		if changed:
			frappe.db.set_value("Workspace", row.name, "content", json.dumps(blocks))


def _fix_workspace_links():
	if not frappe.db.table_exists("Workspace Link"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Link`
		SET link_to = 'Scope of Work',
			label = 'Scope of Work'
		WHERE link_to = 'Statement of Work'
		"""
	)


def _fix_workspace_sidebar_items():
	if not frappe.db.table_exists("Workspace Sidebar Item"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Sidebar Item`
		SET link_to = 'Scope of Work',
			label = 'Scope of Work'
		WHERE link_to = 'Statement of Work'
		   OR label = 'Statement of Work'
		"""
	)


def _fix_doctype_link_options():
	for parent in ("DocField", "Custom Field"):
		if not frappe.db.table_exists(f"tab{parent}"):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{parent}`
			SET options = 'Scope of Work'
			WHERE options = 'Statement of Work'
			"""
		)
