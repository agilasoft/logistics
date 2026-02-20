# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Restore Route Cost Analysis report if it was removed as orphan during migrate.
Re-imports the report from app JSON so it is available in the database and
the Transport workspace link works.
"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	"""Re-import Route Cost Analysis report from app."""
	app_path = frappe.get_app_path("logistics")
	report_path = os.path.join(
		app_path, "transport", "report", "route_cost_analysis", "route_cost_analysis.json"
	)
	if not os.path.exists(report_path):
		return
	imported = import_file_by_path(report_path, force=True)
	if imported:
		frappe.db.commit()
		print("Route Cost Analysis report restored from app.")
