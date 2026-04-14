# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Backfill Declaration.payment_status using current auto-status rules."""
	if not frappe.db.table_exists("Declaration"):
		return

	names = frappe.get_all("Declaration", pluck="name", limit_page_length=0)
	if not names:
		return

	updated = 0
	for name in names:
		try:
			doc = frappe.get_doc("Declaration", name)
			old_status = doc.payment_status
			doc.update_payment_status()
			if old_status != doc.payment_status:
				frappe.db.set_value(
					"Declaration",
					name,
					"payment_status",
					doc.payment_status,
					update_modified=False,
				)
				updated += 1
		except Exception:
			frappe.log_error(
				title="Backfill Declaration Payment Status",
				message=frappe.get_traceback(),
			)

	if updated:
		frappe.db.commit()
