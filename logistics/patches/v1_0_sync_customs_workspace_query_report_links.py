# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Re-import Customs + Pricing Center workspaces so Script Report links use is_query_report=1
# (routes to query-report/… — charts render like Sea Freight).

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	"""Workspace card links must set is_query_report for Script Reports or Frappe opens DocType Report view (no chart)."""
	app_path = frappe.get_app_path("logistics")
	paths = [
		os.path.join(app_path, "customs", "workspace", "customs", "customs.json"),
		os.path.join(app_path, "pricing_center", "workspace", "pricing", "pricing.json"),
	]
	synced = 0
	for workspace_path in paths:
		if os.path.exists(workspace_path) and import_file_by_path(workspace_path, force=True):
			synced += 1
	if synced:
		frappe.db.commit()
		print(f"Synced {synced} workspace(s): Customs / Pricing query-report links.")
