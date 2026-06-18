# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Restore Pricing workspace removed from app JSON; desktop icon needs it for routing."""

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(
		app_path, "pricing_center", "workspace", "pricing", "pricing.json"
	)
	if not os.path.exists(workspace_path):
		return

	if import_file_by_path(workspace_path, force=True):
		frappe.db.commit()
		frappe.cache.delete_key("desktop_icons")
		frappe.cache.delete_key("bootinfo")
		frappe.clear_cache()
		print("Restored Pricing workspace for desktop icon routing.")
