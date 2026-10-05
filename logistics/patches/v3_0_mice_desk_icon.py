# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Show MICE on the desk. Remove the Exhibits tile once MICE is present."""

from __future__ import annotations

import json

import frappe

from logistics.mice.desk_icon import EXHIBITS_LABEL, MICE_LABEL, relabel_desk_layout

_DESK_DOCTYPES = ("Desktop Icon", "Workspace Sidebar", "Workspace", "Sidebar")


def execute():
	_drop_exhibits_desk_rows()
	_relabel_saved_layouts()
	frappe.clear_cache()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")


def _drop_exhibits_desk_rows():
	for doctype in _DESK_DOCTYPES:
		if not frappe.db.table_exists(f"tab{doctype}"):
			continue
		if not frappe.db.exists(doctype, EXHIBITS_LABEL):
			continue
		if frappe.db.exists(doctype, MICE_LABEL):
			frappe.delete_doc(doctype, EXHIBITS_LABEL, force=True, ignore_permissions=True)
			continue
		frappe.rename_doc(doctype, EXHIBITS_LABEL, MICE_LABEL, force=True, merge=False)
		_point_renamed_row_at_mice(doctype)


def _point_renamed_row_at_mice(doctype):
	values = {}
	meta = frappe.get_meta(doctype)
	if meta.has_field("label"):
		values["label"] = MICE_LABEL
	if meta.has_field("title"):
		values["title"] = MICE_LABEL
	if meta.has_field("link_to"):
		current = frappe.db.get_value(doctype, MICE_LABEL, "link_to")
		if current == EXHIBITS_LABEL:
			values["link_to"] = MICE_LABEL
	if meta.has_field("module"):
		current = frappe.db.get_value(doctype, MICE_LABEL, "module")
		if current == EXHIBITS_LABEL:
			values["module"] = MICE_LABEL
	if values:
		frappe.db.set_value(doctype, MICE_LABEL, values, update_modified=False)


def _relabel_saved_layouts():
	if not frappe.db.table_exists("tabDesktop Layout"):
		return
	for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
		if not row.layout:
			continue
		try:
			layout = json.loads(row.layout)
		except Exception:
			continue
		updated = relabel_desk_layout(layout)
		if updated == layout:
			continue
		frappe.db.set_value(
			"Desktop Layout",
			row.name,
			"layout",
			json.dumps(updated),
			update_modified=False,
		)
