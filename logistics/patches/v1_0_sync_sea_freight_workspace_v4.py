# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Force sync Sea Freight Workspace so "Analytics and Insights" card and all 3 report groups show.

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	"""Re-import Sea Freight workspace from app so all three report cards appear."""
	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(
		app_path, "sea_freight", "workspace", "sea_freight", "sea_freight.json"
	)
	if not os.path.exists(workspace_path):
		return
	imported = import_file_by_path(workspace_path, force=True)
	if imported:
		frappe.db.commit()
		print("Sea Freight Workspace synced from app (v4 - Analytics and Insights card).")
