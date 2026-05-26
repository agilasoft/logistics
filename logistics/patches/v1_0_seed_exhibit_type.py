# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Seed Exhibit Type master values."""

from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	path = frappe.get_app_path(
		"logistics", "exhibits", "doctype", "exhibit_type", "exhibit_type.json"
	)
	if frappe.db.exists("DocType", "Exhibit Type"):
		import_file_by_path(path, force=True, ignore_version=True, reset_permissions=True)

	for name in ("Show", "Exhibit", "Fair", "Expo", "Others"):
		if frappe.db.exists("Exhibit Type", name):
			continue
		doc = frappe.new_doc("Exhibit Type")
		doc.exhibit_type = name
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
