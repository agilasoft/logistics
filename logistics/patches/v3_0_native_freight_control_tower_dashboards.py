# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Install Air and Sea Control Tower dashboards and retarget desk links.

The custom control tower pages stay as routes that redirect to the native
dashboard view. Sidebar and workspace shortcuts open the Dashboard directly.
"""

from __future__ import unicode_literals

import frappe


DASHBOARDS = {
	"Air Freight": "Air Freight Control Tower",
	"Sea Freight": "Sea Freight Control Tower",
}

REPORTS = {
	"air_freight": ("afct_module_snapshot",),
	"sea_freight": ("sfct_module_snapshot",),
}


def execute():
	frappe.flags.in_patch = True
	for module, names in REPORTS.items():
		for name in names:
			frappe.reload_doc(module, "report", name, force=True)
	_sync_dashboard_assets()
	_retarget_links()
	frappe.clear_cache(doctype="Page")
	frappe.clear_cache()


def _sync_dashboard_assets():
	"""Import standard Number Cards, Dashboard Charts, and Dashboards."""
	from frappe.utils.dashboard import sync_dashboards

	sync_dashboards(app="logistics")


def _retarget_links():
	for parent, dashboard in DASHBOARDS.items():
		if frappe.db.table_exists("Workspace Shortcut"):
			frappe.db.sql(
				"""
				UPDATE `tabWorkspace Shortcut`
				SET link_to = %s, type = 'Dashboard', doc_view = ''
				WHERE parent = %s AND label = 'Control Tower'
				""",
				(dashboard, parent),
			)
		if frappe.db.table_exists("Sidebar Item"):
			frappe.db.sql(
				"""
				UPDATE `tabSidebar Item`
				SET link_to = %s, link_type = 'Dashboard'
				WHERE parent = %s AND label = 'Control Tower'
				""",
				(dashboard, parent),
			)
	frappe.db.commit()
