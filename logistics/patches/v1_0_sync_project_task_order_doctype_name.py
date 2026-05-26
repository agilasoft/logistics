# Copyright (c) 2026, Agilasoft and contributors
"""Fix Project Task Order JSON shipped as Special Project Order; sync schema (sales_quote, etc.).

Superseded by the rename of Project Task Order → Project Order: kept as a no-op for fresh installs
where the legacy DocType never existed, and as a safety net for installs where the rename has
already moved the JSON file out of ``project_task_order/``.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	# Orphan DocType created when project_task_order.json had name "Special Project Order".
	if frappe.db.exists("DocType", "Special Project Order") and frappe.db.exists(
		"DocType", "Project Task Order"
	):
		if not frappe.db.count("Special Project Order"):
			frappe.delete_doc("DocType", "Special Project Order", force=True)
		else:
			frappe.throw(
				"Cannot remove DocType Special Project Order: it has data. "
				"Migrate rows to Project Task Order, then re-run patch."
			)

	# Skip on installs where the legacy JSON was renamed alongside the DocType.
	if not frappe.db.exists("DocType", "Project Task Order"):
		return

	path = frappe.get_app_path(
		"logistics",
		"special_projects",
		"doctype",
		"project_task_order",
		"project_task_order.json",
	)
	if not os.path.exists(path):
		return

	import_file_by_path(path, force=True, ignore_version=True)

	doc = frappe.get_doc("DocType", "Project Task Order")
	doc.run_module_method("on_update")
	frappe.db.commit()
