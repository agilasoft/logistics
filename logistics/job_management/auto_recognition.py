# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""
Automatic WIP and Accrual recognition.

Posts when Recognition Policy Settings has Auto Recognize enabled and the
policy recognition date is known and not in the future. Triggered on job
submit, after-submit updates (ATA/ATD, charges), and a daily catch-up.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import cint, getdate, nowdate

from logistics.job_management.recognition_engine import (
	RecognitionEngine,
	get_recognition_settings,
	sync_job_recognition_fields_from_policy,
)

RECOGNITION_JOB_TYPES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Declaration",
	"General Job",
	"Project Job",
	"Special Project",
	"Docket",
)

CLOSED_STATUSES = ("Closed", "Completed", "Cancelled")


def company_auto_recognize_enabled(company):
	"""True when the company policy is enabled and Auto Recognize is on."""
	if not company:
		return False
	return bool(
		frappe.db.exists(
			"Recognition Policy Settings",
			{"company": company, "enabled": 1, "auto_recognize": 1},
		)
	)


def enqueue_auto_recognize(doc, method=None):
	"""Queue auto-recognition after commit. Safe to call from doc events."""
	if getattr(frappe.flags, "in_auto_recognition", False):
		return
	if cint(getattr(doc, "docstatus", 0)) != 1:
		return
	if not getattr(doc, "doctype", None) or not getattr(doc, "name", None):
		return
	company = doc.get("company") if hasattr(doc, "get") else getattr(doc, "company", None)
	if not company_auto_recognize_enabled(company):
		return

	frappe.enqueue(
		"logistics.job_management.auto_recognition.auto_recognize_job",
		queue="short",
		doctype=doc.doctype,
		name=doc.name,
		enqueue_after_commit=True,
		job_id="auto_recognize|{0}|{1}".format(doc.doctype, doc.name),
		deduplicate=True,
	)


def _job_is_closed(job):
	status = (job.get("status") or job.get("job_status") or "").strip()
	return status in CLOSED_STATUSES


def _recognition_fully_closed(job):
	return cint(job.get("wip_closed")) and cint(job.get("accrual_closed"))


def auto_recognize_job(doctype, name):
	"""
	Post WIP then accrual for one submitted job when the recognition date is ready.

	Does not throw: missing dates, drafts, and posting errors are skipped or logged.
	"""
	if not doctype or not name:
		return
	if not frappe.db.exists(doctype, name):
		return

	job = frappe.get_doc(doctype, name)
	if cint(job.docstatus) != 1:
		return
	if _job_is_closed(job) or _recognition_fully_closed(job):
		return

	sync_job_recognition_fields_from_policy(job)
	settings = get_recognition_settings(job)
	if not settings.get("auto_recognize"):
		return
	if not settings.get("enable_wip_recognition") and not settings.get("enable_accrual_recognition"):
		return

	engine = RecognitionEngine(job)
	rec_date = engine.get_recognition_date()
	if not rec_date:
		return
	if getdate(rec_date) > getdate(nowdate()):
		return

	prev_in_auto = getattr(frappe.flags, "in_auto_recognition", False)
	frappe.flags.in_auto_recognition = True
	try:
		if settings.get("enable_wip_recognition") and engine.has_pending_wip_recognition():
			try:
				engine.recognize_wip()
			except Exception:
				frappe.log_error(
					title="Auto WIP recognition failed: {0} {1}".format(doctype, name),
					message=frappe.get_traceback(),
				)

		job.reload()
		engine = RecognitionEngine(job)
		if settings.get("enable_accrual_recognition") and engine.has_pending_accrual_recognition():
			try:
				engine.recognize_accruals()
			except Exception:
				frappe.log_error(
					title="Auto accrual recognition failed: {0} {1}".format(doctype, name),
					message=frappe.get_traceback(),
				)
	finally:
		frappe.flags.in_auto_recognition = prev_in_auto


def _pending_job_names(job_type, company):
	if not frappe.db.exists("DocType", job_type):
		return []
	meta = frappe.get_meta(job_type)
	if not meta.has_field("wip_amount") and not meta.has_field("accrual_amount"):
		return []

	conditions = ["company = %(company)s", "docstatus = 1"]
	if meta.has_field("job_status"):
		conditions.append(
			"IFNULL(job_status, '') NOT IN ('Closed', 'Completed', 'Cancelled')"
		)
	elif meta.has_field("status"):
		conditions.append(
			"IFNULL(status, '') NOT IN ('Closed', 'Completed', 'Cancelled')"
		)
	if meta.has_field("wip_closed") and meta.has_field("accrual_closed"):
		conditions.append(
			"NOT (IFNULL(wip_closed, 0) = 1 AND IFNULL(accrual_closed, 0) = 1)"
		)

	pending = []
	if meta.has_field("estimated_revenue") and meta.has_field("wip_amount"):
		pending.append("IFNULL(estimated_revenue, 0) > IFNULL(wip_amount, 0)")
	if meta.has_field("estimated_costs") and meta.has_field("accrual_amount"):
		pending.append("IFNULL(estimated_costs, 0) > IFNULL(accrual_amount, 0)")
	if not pending:
		return []
	conditions.append("(" + " OR ".join(pending) + ")")

	sql = "SELECT name FROM `tab{0}` WHERE {1}".format(job_type, " AND ".join(conditions))
	return frappe.db.sql_list(sql, {"company": company}) or []


def process_auto_recognition():
	"""Daily catch-up: enqueue jobs whose estimates still exceed posted WIP/accrual."""
	companies = frappe.get_all(
		"Recognition Policy Settings",
		filters={"enabled": 1, "auto_recognize": 1},
		pluck="company",
	)
	for company in companies:
		for job_type in RECOGNITION_JOB_TYPES:
			try:
				for job_name in _pending_job_names(job_type, company):
					enqueue_auto_recognize(
						frappe._dict(
							doctype=job_type,
							name=job_name,
							docstatus=1,
							company=company,
						)
					)
			except Exception:
				frappe.log_error(
					title="Auto recognition catch-up failed: {0} {1}".format(
						company, job_type
					),
					message=frappe.get_traceback(),
				)
