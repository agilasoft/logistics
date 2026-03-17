# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Re-import Workspace Sidebars and Desktop Icons from app JSON so custom menus
# (Orders, Bookings, Shipments, Jobs) are shown in the sidebar.

import os

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


def execute():
	"""Re-import Workspace Sidebars and Desktop Icons from app so DB reflects app JSON."""
	app_name = "logistics"
	synced = 0

	# Sync Workspace Sidebars
	sidebar_path = get_app_level_directory_path("workspace_sidebar", app_name)
	if os.path.exists(sidebar_path):
		for fname in os.listdir(sidebar_path):
			if fname.endswith(".json"):
				doc_path = os.path.join(sidebar_path, fname)
				if import_file_by_path(doc_path, force=True):
					synced += 1
					print(f"  Synced Workspace Sidebar: {fname}")

	# Sync Desktop Icons
	icon_path = get_app_level_directory_path("desktop_icon", app_name)
	if os.path.exists(icon_path):
		for fname in os.listdir(icon_path):
			if fname.endswith(".json"):
				doc_path = os.path.join(icon_path, fname)
				if import_file_by_path(doc_path, force=True):
					synced += 1
					print(f"  Synced Desktop Icon: {fname}")

	if synced:
		frappe.db.commit()
		print(f"Synced {synced} workspace sidebars and desktop icons for {app_name}.")
