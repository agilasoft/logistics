# Copyright (c) 2026, Agilasoft and contributors
"""Replace the Beginning Jobs page with Legacy Job on the existing files.

Reload Job Management Settings, copy is_beginning_job onto is_legacy_job,
drop the page from the Job Management workspace, and refresh the sidebar.
"""

from __future__ import annotations

import json

import frappe

from logistics.patches.v3_0_sync_job_management_sidebar import execute as sync_sidebar


PAGE = "beginning-jobs"
WORKSPACE = "Job Management"
FILES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Declaration",
	"Warehouse Job",
)


def execute():
	frappe.flags.in_patch = True
	if frappe.db.exists("DocType", "Job Management Settings"):
		frappe.reload_doc("job_management", "doctype", "job_management_settings", force=True)
	for doctype in FILES:
		if frappe.db.exists("DocType", doctype):
			frappe.reload_doc(*_module_path(doctype), force=True)
			_copy_beginning_flag(doctype)
	_remove_workspace_shortcut()
	if frappe.db.exists("Page", PAGE):
		frappe.delete_doc("Page", PAGE, force=True, ignore_permissions=True)
	sync_sidebar()
	frappe.clear_cache()


def _module_path(doctype):
	return {
		"Air Shipment": ("air_freight", "doctype", "air_shipment"),
		"Sea Shipment": ("sea_freight", "doctype", "sea_shipment"),
		"Transport Job": ("transport", "doctype", "transport_job"),
		"Declaration": ("customs", "doctype", "declaration"),
		"Warehouse Job": ("warehousing", "doctype", "warehouse_job"),
	}[doctype]


def _copy_beginning_flag(doctype):
	if not frappe.db.has_column(doctype, "is_beginning_job"):
		return
	if not frappe.db.has_column(doctype, "is_legacy_job"):
		return
	table = f"tab{doctype}"
	frappe.db.sql(
		f"""
		update `{table}`
		set is_legacy_job = 1
		where ifnull(is_beginning_job, 0) = 1 and ifnull(is_legacy_job, 0) = 0
		"""
	)


def _remove_workspace_shortcut():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	doc = frappe.get_doc("Workspace", WORKSPACE)
	changed = False
	kept = [row for row in (doc.shortcuts or []) if row.link_to != PAGE]
	if len(kept) != len(doc.shortcuts or []):
		doc.set("shortcuts", [])
		for row in kept:
			doc.append("shortcuts", row.as_dict())
		changed = True
	if not any(row.link_to == "Job Management Settings" for row in (doc.shortcuts or [])):
		doc.append(
			"shortcuts",
			{
				"type": "DocType",
				"link_to": "Job Management Settings",
				"label": "Job Management Settings",
				"color": "Grey",
				"doc_view": "",
			},
		)
		changed = True
	content = _load_content(doc.content)
	filtered = [
		block
		for block in content
		if not (
			block.get("id") == "bjShortcut01"
			or (
				block.get("type") == "shortcut"
				and (block.get("data") or {}).get("shortcut_name") == "Beginning Jobs"
			)
		)
	]
	if filtered != content:
		doc.content = json.dumps(filtered, separators=(",", ":"), ensure_ascii=False)
		changed = True
	if not changed:
		return
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)


def _load_content(raw):
	if not raw:
		return []
	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		return []
	return data if isinstance(data, list) else []
