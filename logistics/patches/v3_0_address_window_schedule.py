# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Add Address Pick / Drop Windows schedule table; hide legacy day checkboxes and default windows."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

LEGACY_HIDE_FIELDS = (
	"custom_pick_window",
	"custom_pick_monday",
	"custom_pick_tuesday",
	"custom_pick_wednesday",
	"custom_pick_thursday",
	"custom_pick_friday",
	"custom_pick_saturday",
	"custom_pick_sunday",
	"custom_pickup_window_start",
	"custom_pickup_window_end",
	"custom_column_break_dtwx6",
	"custom_drop_monday",
	"custom_drop_tuesday",
	"custom_drop_wednesday",
	"custom_drop_thursday",
	"custom_drop_friday",
	"custom_drop_saturday",
	"custom_drop_sunday",
	"custom_drop_window_start",
	"custom_drop_windows_end",
)


def execute():
	_ensure_schedule_fields()
	_hide_legacy_fields()
	frappe.clear_cache(doctype="Address")


def _ensure_schedule_fields():
	create_custom_fields(
		{
			"Address": [
				{
					"fieldname": "custom_window_schedule_section",
					"fieldtype": "Section Break",
					"label": "Pick / Drop Windows",
					"insert_after": "custom_address_map",
					"description": (
						"Add one row per allowed day and operation. "
						"A row means that day/operation is available with those times. "
						"No row means not available."
					),
					"module": "Transport",
				},
				{
					"fieldname": "custom_window_schedule",
					"label": "Pick / Drop Windows",
					"fieldtype": "Table",
					"options": "Address Window Schedule",
					"insert_after": "custom_window_schedule_section",
					"module": "Transport",
				},
			]
		},
		update=True,
	)
	# Keep hidden legacy day/window block after the new table (not above it)
	pick = frappe.db.get_value(
		"Custom Field", {"dt": "Address", "fieldname": "custom_pick_window"}, "name"
	)
	if pick:
		frappe.db.set_value(
			"Custom Field", pick, "insert_after", "custom_window_schedule", update_modified=False
		)


def _hide_legacy_fields():
	for fieldname in LEGACY_HIDE_FIELDS:
		name = frappe.db.get_value(
			"Custom Field", {"dt": "Address", "fieldname": fieldname}, "name"
		)
		if not name:
			continue
		frappe.db.set_value("Custom Field", name, "hidden", 1, update_modified=False)
