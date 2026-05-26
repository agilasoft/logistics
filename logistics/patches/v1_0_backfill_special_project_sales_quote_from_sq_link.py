# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Before dropping Sales Quote.special_project, copy link to Special Project.sales_quote when empty."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Sales Quote", "special_project"):
		return
	rows = frappe.get_all(
		"Sales Quote",
		filters={"special_project": ["is", "set"]},
		fields=["name", "special_project"],
	)
	for row in rows:
		sp = (row.special_project or "").strip()
		if not sp or not frappe.db.exists("Special Project", sp):
			continue
		if frappe.db.get_value("Special Project", sp, "sales_quote"):
			continue
		frappe.db.set_value(
			"Special Project",
			sp,
			"sales_quote",
			row.name,
			update_modified=False,
		)
	frappe.db.commit()
