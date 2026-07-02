# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill lifecycle_row_label on existing Lifecycle Job child rows."""

from __future__ import annotations

import frappe

from logistics.special_projects.lifecycle_job_display import lifecycle_job_line_display_label


def execute():
	if not frappe.db.has_column("Lifecycle Job", "lifecycle_row_label"):
		return

	for row in frappe.get_all(
		"Lifecycle Job",
		filters={"lifecycle_row_label": ("in", ("", None))},
		fields=[
			"name",
			"idx",
			"lifecycle_stage",
			"activity_code",
			"activity_name",
			"job_description",
		],
	):
		label = lifecycle_job_line_display_label(frappe._dict(row))
		if label:
			frappe.db.set_value(
				"Lifecycle Job",
				row.name,
				"lifecycle_row_label",
				label,
				update_modified=False,
			)
