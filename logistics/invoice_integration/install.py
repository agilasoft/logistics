# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Install / migrate hooks for the ``invoice_integration`` module.

Owns DB indexes that back the WIP/accrual reversal queries in
``wip_reversal.py`` and ``accrual_reversal.py``. Those queries filter
``tabGL Entry`` by the logistics-only custom field ``job_number``, which
Frappe schema sync does not index on its own. Without the composite index
below, every reversal call full-scans ``tabGL Entry`` and the site degrades
as GL volume grows.
"""

from __future__ import annotations

import frappe


GL_ENTRY_JOB_INDEX = "job_number_company_account_index"
GL_ENTRY_JOB_INDEX_COLUMNS = ("job_number", "company", "account", "docstatus")


def after_migrate() -> None:
	"""Registered in ``hooks.after_migrate``. Idempotent, safe to re-run."""
	ensure_gl_entry_job_number_index()


def ensure_gl_entry_job_number_index() -> None:
	"""Create the composite index on ``tabGL Entry`` if missing.

	Skipped on sites that don't have the GL Entry doctype (no ERPNext) or
	don't have the ``job_number`` custom field installed.
	"""
	if not frappe.db.table_exists("GL Entry"):
		return
	if not frappe.db.has_column("GL Entry", "job_number"):
		return

	existing = frappe.db.sql(
		"SHOW INDEX FROM `tabGL Entry` WHERE Key_name = %s",
		GL_ENTRY_JOB_INDEX,
	)
	if existing:
		return

	cols = ", ".join(f"`{c}`" for c in GL_ENTRY_JOB_INDEX_COLUMNS)
	ddl = (
		f"ALTER TABLE `tabGL Entry` "
		f"ADD INDEX `{GL_ENTRY_JOB_INDEX}` ({cols}), "
		f"ALGORITHM=INPLACE, LOCK=NONE"
	)
	try:
		frappe.db.sql_ddl(ddl)
	except Exception:
		# Older MariaDB / unsupported online DDL — retry with a plain CREATE INDEX
		# which briefly locks the table but never leaves the index missing.
		frappe.db.sql_ddl(
			f"CREATE INDEX `{GL_ENTRY_JOB_INDEX}` "
			f"ON `tabGL Entry` ({cols})"
		)
