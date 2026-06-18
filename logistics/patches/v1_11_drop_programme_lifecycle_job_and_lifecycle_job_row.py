# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Programme Lifecycle Job registry and legacy lifecycle_job_row on charges."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.table_exists("tabProgramme Lifecycle Job"):
		frappe.db.delete("Programme Lifecycle Job", {"parenttype": "Special Project"})

	for obsolete in (
		"Special Project Charge Lifecycle Tag Link",
		"Programme Lifecycle Job",
		"Special Project Charge Lifecycle Tag",
	):
		if frappe.db.exists("DocType", obsolete):
			frappe.delete_doc("DocType", obsolete, force=1, ignore_permissions=True)

	if frappe.db.has_column("Special Project Charges", "lifecycle_job_row"):
		frappe.db.sql_ddl(
			"ALTER TABLE `tabSpecial Project Charges` DROP COLUMN `lifecycle_job_row`"
		)
