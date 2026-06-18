# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Retire the standalone Job 360 Page + Dashboard in favour of Script Reports.

Before this patch the Job Management workspace exposed:

* ``Job 360 Explorer`` — a custom **Page** at ``/app/job-360-explorer``
  (HTML + JS dashboard with KPI tiles, charts, paginated table).
* ``Job Management 360`` — a Frappe **Dashboard** with 10 Charts + 10
  Number Cards.
* ``Job 360 Cross Module Report`` — a Script Report that already exposed
  the same per-job data the Page did, with a chart and Report Summary
  tiles.

The Page and the Dashboard duplicated work and added a maintenance burden
(custom JS, custom CSS, parallel KPI math). This patch consolidates both
into two Script Reports that live alongside the existing reports:

* ``Job Explorer 360`` — renamed in DB from ``Job 360 Cross Module Report``
  so the existing report record (filters, role grants, saved views) is
  preserved and simply re-labelled.
* ``Job Management 360`` — a brand new Script Report. The existing
  ``Job Management 360`` Dashboard record is deleted; the dashboard's 10
  Number Cards are independent doctype records and stay pinned on the
  Job Management workspace.

The retired Page and Dashboard records are deleted from the DB so the
sidebar / search index do not surface them anymore.

Idempotent — safe to re-run.
"""

from __future__ import annotations

import os

import frappe
from frappe.modules.import_file import import_file_by_path


OLD_REPORT = "Job 360 Cross Module Report"
NEW_EXPLORER_REPORT = "Job Explorer 360"
NEW_MANAGEMENT_REPORT = "Job Management 360"
OLD_PAGE = "job-360-explorer"
OLD_DASHBOARD = "Job Management 360"


def execute() -> None:
	_rename_explorer_report()
	_install_management_report()
	_delete_old_page()
	_delete_old_dashboard()


def _rename_explorer_report() -> None:
	"""Rename the existing ``Job 360 Cross Module Report`` to ``Job Explorer 360``.

	Renaming (instead of delete + create) preserves any role grants, saved
	views, or custom filters that users may have added to the original
	report record.
	"""
	if not frappe.db.table_exists("Report"):
		return
	if not frappe.db.exists("Report", OLD_REPORT):
		return
	if frappe.db.exists("Report", NEW_EXPLORER_REPORT):
		# Already renamed in a prior run; drop the old shell if it somehow lingered.
		frappe.delete_doc("Report", OLD_REPORT, force=1, ignore_permissions=True)
		return
	frappe.rename_doc("Report", OLD_REPORT, NEW_EXPLORER_REPORT, force=True)
	frappe.db.commit()


def _install_management_report() -> None:
	"""Force-load the new ``Job Management 360`` Report doc from disk.

	``bench migrate`` would pick this up too, but we run it here so the
	patch leaves the site fully usable without waiting for the next sync.
	"""
	if not frappe.db.table_exists("Report"):
		return
	if frappe.db.exists("Report", NEW_MANAGEMENT_REPORT):
		return
	path = frappe.get_app_path(
		"logistics",
		"job_management",
		"report",
		"job_management_360",
		"job_management_360.json",
	)
	if not os.path.exists(path):
		return
	import_file_by_path(path, force=True, ignore_version=True)
	frappe.db.commit()


def _delete_old_page() -> None:
	if not frappe.db.table_exists("Page"):
		return
	if not frappe.db.exists("Page", OLD_PAGE):
		return
	frappe.delete_doc("Page", OLD_PAGE, force=1, ignore_permissions=True)
	frappe.db.commit()


def _delete_old_dashboard() -> None:
	"""Delete the retired ``Job Management 360`` Dashboard record.

	The 10 underlying Number Cards and Dashboard Charts are independent
	doctype records and are left in place — they continue to be pinned on
	the Job Management workspace and to be reusable from any dashboard.
	"""
	if not frappe.db.table_exists("Dashboard"):
		return
	if not frappe.db.exists("Dashboard", OLD_DASHBOARD):
		return
	frappe.delete_doc("Dashboard", OLD_DASHBOARD, force=1, ignore_permissions=True)
	frappe.db.commit()
