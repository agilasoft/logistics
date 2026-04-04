# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""Fix Custom Field rows still using fieldname job_costing_number after column rename."""

import frappe

OLD = "job_costing_number"
NEW = "job_number"


def execute():
	rows = frappe.get_all("Custom Field", filters={"fieldname": OLD}, fields=["name", "dt"])
	if not rows:
		return True
	for cf in rows:
		new_name = f"{cf.dt}-{NEW}"
		if frappe.db.exists("Custom Field", new_name):
			frappe.delete_doc("Custom Field", cf.name, force=True, ignore_permissions=True)
			continue
		frappe.db.sql(
			"""
			UPDATE `tabCustom Field`
			SET name=%s, fieldname=%s, label='Job Number'
			WHERE name=%s
			""",
			(new_name, NEW, cf.name),
		)
	frappe.db.commit()
	frappe.clear_cache()
	return True
