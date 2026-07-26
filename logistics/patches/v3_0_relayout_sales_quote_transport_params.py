# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Relayout Sales Quote Transport params into their own Section Break.

Transport fields previously sat after ``column_break_params``. That Column Break
had its own depends_on; on some deployed sites the second column stayed hidden
even though DocField depends_on for location_type etc. was correct. Move
Transport fields under ``transport_params_section`` so visibility does not
depend on the Air/Sea column break.
"""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Sales Quote"):
		return

	# Drop Property Setters that could pin old column / depends_on layout.
	for name in frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": "Sales Quote",
			"field_name": [
				"in",
				[
					"column_break_params",
					"location_type",
					"location_from",
					"location_to",
					"transport_template",
					"vehicle_type",
					"container_type",
					"container_no",
					"pick_mode",
					"drop_mode",
					"transport_params_section",
					"column_break_transport_params",
				],
			],
			"property": [
				"in",
				[
					"depends_on",
					"mandatory_depends_on",
					"hidden",
					"insert_after",
				],
			],
		},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", name, force=1, ignore_permissions=True)

	frappe.reload_doc("pricing_center", "doctype", "sales_quote", force=True)
	frappe.clear_cache(doctype="Sales Quote")
	frappe.db.commit()
