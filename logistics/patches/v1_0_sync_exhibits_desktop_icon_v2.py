# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Import Events workspace, sidebar, and desktop icon from app JSON (force).

Sites can have a Desktop Icon named Events while Workspace / Workspace Sidebar
are missing (early patch exit + reload_doc path mismatch). That breaks desk setup
and causes "Desktop Icon Events already exists" when adding the tile from UI.
"""

from __future__ import annotations

import os

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


def execute():
	app = "logistics"
	app_path = frappe.get_app_path(app)
	paths = [
		os.path.join(app_path, "exhibits", "workspace", "exhibits", "exhibits.json"),
		os.path.join(get_app_level_directory_path("workspace_sidebar", app), "exhibits.json"),
		os.path.join(get_app_level_directory_path("desktop_icon", app), "exhibits.json"),
	]
	for path in paths:
		if os.path.exists(path):
			import_file_by_path(path, force=True)

	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.db.commit()
