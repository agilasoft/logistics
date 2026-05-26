# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Seed Lifecycle Stage master values (Exhibits + Special Project)."""

from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path


STAGES = (
	("Pre-Show", 1, 0),
	("Logistics", 2, 0),
	("On-Site", 3, 0),
	("Post-Show", 4, 0),
	("Closed", 5, 1),
)


def execute():
	path = frappe.get_app_path(
		"logistics",
		"logistics",
		"doctype",
		"lifecycle_stage",
		"lifecycle_stage.json",
	)
	if frappe.db.exists("DocType", "Lifecycle Stage"):
		import_file_by_path(path, force=True, ignore_version=True, reset_permissions=True)

	for stage, sort_order, is_closed in STAGES:
		if frappe.db.exists("Lifecycle Stage", stage):
			frappe.db.set_value(
				"Lifecycle Stage",
				stage,
				{
					"sort_order": sort_order,
					"is_closed": is_closed,
					"for_exhibits": 1,
					"for_special_project": 1,
				},
				update_modified=False,
			)
			continue
		doc = frappe.new_doc("Lifecycle Stage")
		doc.lifecycle_stage = stage
		doc.sort_order = sort_order
		doc.is_closed = is_closed
		doc.for_exhibits = 1
		doc.for_special_project = 1
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
