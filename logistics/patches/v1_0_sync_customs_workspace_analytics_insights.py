# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Re-import Customs Workspace and Customs Workspace Sidebar after Analytics & Insights card/links change.

import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	app_path = frappe.get_app_path("logistics")
	paths = [
		os.path.join(app_path, "customs", "workspace", "customs", "customs.json"),
		os.path.join(app_path, "workspace_sidebar", "customs.json"),
	]
	synced = 0
	for p in paths:
		if os.path.exists(p) and import_file_by_path(p, force=True):
			synced += 1
	if synced:
		frappe.db.commit()
		print(f"Synced Customs workspace + sidebar ({synced} file(s)).")
