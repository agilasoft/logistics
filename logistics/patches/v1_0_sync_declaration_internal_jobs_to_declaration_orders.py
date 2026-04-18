# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe

from logistics.utils.internal_job_detail_copy import (
	sync_internal_job_details_from_declaration_to_declaration_order,
)


def execute():
	"""Align Declaration Order Internal Jobs child table with linked Declarations (one-time backfill)."""
	if not frappe.db.table_exists("Declaration"):
		return

	names = frappe.get_all(
		"Declaration",
		filters={"docstatus": ["<", 2], "declaration_order": ["!=", ""]},
		pluck="name",
	)
	for name in names:
		try:
			doc = frappe.get_doc("Declaration", name)
			sync_internal_job_details_from_declaration_to_declaration_order(doc)
		except Exception:
			frappe.log_error(
				title="Declaration internal jobs sync patch",
				message=frappe.get_traceback(),
			)
