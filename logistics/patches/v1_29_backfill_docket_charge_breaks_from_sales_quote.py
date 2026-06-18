# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Backfill Weight/Qty Break rows onto Docket charge lines from linked Sales Quotes.

Dockets created before the forward-fix only received scalar charge fields; tier
rows remained on Sales Quote Charge. Re-runnable: copy_charge_breaks_for_reference
replaces existing target breaks before insert.
"""

from __future__ import annotations

import frappe

from logistics.utils.sales_quote_programme_charges import (
	copy_sales_quote_charge_breaks_to_programme_parent,
)


def execute():
	if not frappe.db.table_exists("Docket"):
		return
	if not frappe.db.table_exists("Sales Quote"):
		return

	dockets = frappe.get_all(
		"Docket",
		filters={"sales_quote": ["is", "set"], "docstatus": ["<", 2]},
		fields=["name", "sales_quote"],
	)
	updated = 0
	copied_total = 0
	for row in dockets:
		sq_name = (row.sales_quote or "").strip()
		if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
			continue
		try:
			doc = frappe.get_doc("Docket", row.name)
			if not doc.get("charges"):
				continue
			copied = copy_sales_quote_charge_breaks_to_programme_parent(doc, sq_name)
			if copied:
				updated += 1
				copied_total += copied
		except Exception:
			frappe.log_error(
				title="v1_29_backfill_docket_charge_breaks_from_sales_quote",
				message=frappe.get_traceback(),
			)

	if updated:
		frappe.db.commit()
		print(
			f"[v1_29_backfill_docket_charge_breaks_from_sales_quote] "
			f"updated {updated} docket(s), copied {copied_total} break row(s)"
		)
