# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Reassign charge execution logs to the correct programme charge row and rebuild qty."""

from __future__ import annotations

import frappe

from logistics.special_projects.special_project_charge_execution import (
	reconcile_programme_charge_qty_from_execution_logs,
)


def execute():
	if not frappe.db.table_exists("tabSpecial Project"):
		return

	for row in frappe.get_all("Special Project", pluck="name"):
		sp_doc = frappe.get_doc("Special Project", row)
		if not sp_doc.get("charge_execution_logs"):
			continue
		reconcile_programme_charge_qty_from_execution_logs(sp_doc)
		sp_doc.flags.ignore_validate = True
		sp_doc.flags.ignore_charges_sync = True
		sp_doc.save(ignore_permissions=True)

	frappe.db.commit()
