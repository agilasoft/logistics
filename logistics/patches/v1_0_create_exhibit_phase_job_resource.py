# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create child DocType Event Job Resource (Resources tab on Event Job)."""

from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	path = frappe.get_app_path(
		"logistics",
		"events",
		"doctype",
		"event_job_resource",
		"event_job_resource.json",
	)
	import_file_by_path(path, force=True, ignore_version=True, reset_permissions=True)
	frappe.db.commit()
	frappe.clear_cache(doctype="Event Job")
