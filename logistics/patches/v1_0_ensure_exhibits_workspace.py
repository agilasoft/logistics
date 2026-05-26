# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Import Exhibits workspace when missing (desk tile route depends on it)."""

from __future__ import annotations

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	if frappe.db.exists("Workspace", "Exhibits"):
		return

	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(app_path, "exhibits", "workspace", "exhibits", "exhibits.json")
	if not os.path.exists(workspace_path):
		return

	import_file_by_path(workspace_path, force=True)
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()
