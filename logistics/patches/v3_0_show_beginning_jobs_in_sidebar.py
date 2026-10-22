# Copyright (c) 2026, Agilasoft and contributors
"""Show Beginning Jobs on sites whose Job Management sidebar was already synced.

The earlier sidebar patches already ran, and the workspace file is older than
the row stored on the site, so migrate leaves both documents as they were.
Reload the page, replace the sidebar from the app file, and add the shortcut
when the workspace does not have it yet.
"""

from __future__ import annotations

import json
import os

import frappe

from logistics.patches.v3_0_sync_job_management_sidebar import execute as sync_sidebar


PAGE = "beginning-jobs"
WORKSPACE = "Job Management"
SHORTCUT_ID = "bjShortcut01"


def execute():
	frappe.flags.in_patch = True
	page_path = frappe.get_app_path("logistics", "job_management", "page", "beginning_jobs")
	if frappe.db.exists("DocType", "Page") and os.path.isdir(page_path):
		frappe.reload_doc("job_management", "page", "beginning_jobs", force=True)
	sync_sidebar()
	_ensure_workspace_shortcut()
	frappe.clear_cache()


def _ensure_workspace_shortcut():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	doc = frappe.get_doc("Workspace", WORKSPACE)
	changed = False
	if not any(row.link_to == PAGE for row in (doc.shortcuts or [])):
		doc.append(
			"shortcuts",
			{
				"type": "Page",
				"link_to": PAGE,
				"label": "Beginning Jobs",
				"color": "Blue",
				"doc_view": "",
			},
		)
		changed = True

	content = _load_content(doc.content)
	has_block = any(
		block.get("id") == SHORTCUT_ID
		or (
			block.get("type") == "shortcut"
			and (block.get("data") or {}).get("shortcut_name") == "Beginning Jobs"
		)
		for block in content
	)
	if not has_block:
		block = {
			"id": SHORTCUT_ID,
			"type": "shortcut",
			"data": {"shortcut_name": "Beginning Jobs", "col": 3},
		}
		insert_at = len(content)
		for index, row in enumerate(content):
			data = row.get("data") or {}
			if row.get("type") == "shortcut" and data.get("shortcut_name") == "Job Number":
				insert_at = index + 1
				break
		content.insert(insert_at, block)
		doc.content = json.dumps(content, separators=(",", ":"), ensure_ascii=False)
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
