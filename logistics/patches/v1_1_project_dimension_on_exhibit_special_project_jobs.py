# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""
Backfill the ``project`` field on Docket and on every logistics job linked to a
Special Project / Exhibit so the new Project-level Profitability tab and the
Project accounting dimension on GL Entry both have something to roll up.

The patch is idempotent — it only writes when the destination value is currently
empty/blank.
"""

import frappe


def execute():
	_backfill_docket_project_from_exhibit()
	_backfill_internal_job_project_from_special_project()
	_backfill_internal_job_project_from_exhibit()


def _backfill_docket_project_from_exhibit() -> None:
	"""Every Docket inherits its parent Exhibit's ``project`` (Exhibit creates one on insert)."""
	if not frappe.db.table_exists("Docket"):
		return
	if not frappe.get_meta("Docket").get_field("project"):
		# DocType JSON not yet synced — nothing to backfill.
		return
	rows = frappe.db.sql(
		"""
		SELECT dk.name AS docket, ex.project AS project
		FROM `tabDocket` dk
		INNER JOIN `tabExhibit` ex ON ex.name = dk.exhibit
		WHERE IFNULL(dk.project, '') = ''
		AND IFNULL(ex.project, '') != ''
		""",
		as_dict=True,
	)
	for r in rows:
		try:
			frappe.db.set_value(
				"Docket", r["docket"], "project", r["project"], update_modified=False
			)
		except Exception:
			frappe.log_error(
				title="Project backfill: Docket.project from Exhibit failed",
				message=frappe.get_traceback(),
			)


_JOB_DOCTYPES_WITH_PROJECT = (
	"Air Booking",
	"Sea Booking",
	"Air Shipment",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Transfer Order",
	"VAS Order",
	"Project Job",
)


def _backfill_internal_job_project_from_special_project() -> None:
	"""Walk Special Project lifecycle_jobs and pin project on every linked operational job."""
	if not frappe.db.table_exists("Special Project"):
		return
	rows = frappe.db.sql(
		"""
		SELECT
			lj.job_type AS job_type,
			lj.job_no AS job_no,
			sp.project AS project
		FROM `tabLifecycle Job` lj
		INNER JOIN `tabSpecial Project` sp ON sp.name = lj.parent
		WHERE lj.parenttype = 'Special Project'
		AND lj.parentfield = 'lifecycle_jobs'
		AND IFNULL(lj.job_no, '') != ''
		AND IFNULL(lj.job_type, '') != ''
		AND IFNULL(sp.project, '') != ''
		""",
		as_dict=True,
	)
	_apply_project_to_job_refs(rows)


def _backfill_internal_job_project_from_exhibit() -> None:
	"""Walk Exhibit lifecycle_jobs and pin project on every linked operational job."""
	if not frappe.db.table_exists("Exhibit"):
		return
	rows = frappe.db.sql(
		"""
		SELECT
			lj.job_type AS job_type,
			lj.job_no AS job_no,
			ex.project AS project
		FROM `tabLifecycle Job` lj
		INNER JOIN `tabExhibit` ex ON ex.name = lj.parent
		WHERE lj.parenttype = 'Exhibit'
		AND lj.parentfield = 'lifecycle_jobs'
		AND IFNULL(lj.job_no, '') != ''
		AND IFNULL(lj.job_type, '') != ''
		AND IFNULL(ex.project, '') != ''
		""",
		as_dict=True,
	)
	_apply_project_to_job_refs(rows)


def _apply_project_to_job_refs(rows) -> None:
	for r in rows:
		jt = (r.get("job_type") or "").strip()
		jn = (r.get("job_no") or "").strip()
		project = (r.get("project") or "").strip()
		if not jt or not jn or not project:
			continue
		if jt not in _JOB_DOCTYPES_WITH_PROJECT:
			continue
		if not frappe.db.exists(jt, jn):
			continue
		try:
			if not frappe.get_meta(jt).get_field("project"):
				continue
		except Exception:
			continue
		current = (frappe.db.get_value(jt, jn, "project") or "").strip()
		if current:
			continue
		try:
			frappe.db.set_value(jt, jn, "project", project, update_modified=False)
		except Exception:
			frappe.log_error(
				title="Project backfill: {0}.project from parent failed".format(jt),
				message=frappe.get_traceback(),
			)
