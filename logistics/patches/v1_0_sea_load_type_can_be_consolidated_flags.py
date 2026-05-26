# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Set Can be Consolidated on standard sea Load Types (FCL off, LCL on)."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Load Type"):
		return

	flags = {
		"FCL": 0,
		"LCL": 1,
	}
	for load_type_name, can_consolidate in flags.items():
		if not frappe.db.exists("Load Type", load_type_name):
			continue
		frappe.db.set_value(
			"Load Type",
			load_type_name,
			"can_be_consolidated",
			1 if can_consolidate else 0,
			update_modified=False,
		)
