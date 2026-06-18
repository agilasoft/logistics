# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Index the ``GL Entry.job_number`` custom field.

The WIP / accrual reversal queries in ``logistics/invoice_integration``
filter ``tabGL Entry`` by ``job_number`` (a logistics-only custom field).
With no index, every reversal call full-scans the table and the site
degrades as GL volume grows.

This patch:

1. Marks the ``job_number`` Custom Field with ``search_index = 1`` so
   future ``bench migrate`` runs maintain a single-column index
   automatically (belt-and-braces).
2. Ensures the composite index
   ``(job_number, company, account, docstatus)`` exists right now via
   :func:`logistics.invoice_integration.install.ensure_gl_entry_job_number_index`.
   The composite covers all WHERE clauses used by the reversal queries
   and turns full-scans into single-row lookups.

Idempotent — safe to re-run.
"""

from __future__ import annotations

import frappe

from logistics.invoice_integration.install import ensure_gl_entry_job_number_index


def execute() -> None:
	_mark_job_number_custom_field_as_search_index()
	ensure_gl_entry_job_number_index()


def _mark_job_number_custom_field_as_search_index() -> None:
	if not frappe.db.table_exists("Custom Field"):
		return

	cf_name = frappe.db.get_value(
		"Custom Field",
		{"dt": "GL Entry", "fieldname": "job_number"},
		"name",
	)
	if not cf_name:
		return

	cf = frappe.get_doc("Custom Field", cf_name)
	if cf.search_index:
		return

	cf.search_index = 1
	cf.save(ignore_permissions=True)
	frappe.db.commit()
