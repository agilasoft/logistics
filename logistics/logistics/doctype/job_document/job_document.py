# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today
from frappe import _
from logistics.utils.document_date_validation import throw_if_not_past_date


def apply_job_document_status_updates(row):
	"""Apply activity-based status updates to a Job Document row. Call from parent before_save
	since child table rows do not run their controller validate/before_save when parent is saved."""
	if not row or getattr(row, "doctype", None) != "Job Document":
		return
	# Set defaults
	if not row.get("source"):
		row.source = "Manual"
	if not row.get("created_at"):
		row.created_at = frappe.utils.now()
	_realign_job_document_status_from_dates(row)
	_downgrade_uploaded_when_no_attachment(row)
	_apply_activity_based_status_updates(row)
	_update_overdue_status(row)


def _downgrade_uploaded_when_no_attachment(row):
	"""If attachment was cleared, Uploaded is no longer valid — use Pending so save is not blocked."""
	if row.get("status") == "Uploaded" and not row.get("attachment"):
		row.status = "Pending"


def _realign_job_document_status_from_dates(row):
	"""When dates are corrected on save, drop stale Overdue/Expired so status matches the new dates."""
	status = row.get("status")
	if status not in ("Overdue", "Expired"):
		return
	today_date = getdate(today())

	if status == "Expired":
		exp = row.get("expiry_date")
		if not exp or getdate(exp) >= today_date:
			row.status = "Pending"
			if row.get("overdue_days"):
				row.overdue_days = 0
		return

	# Overdue: deadline removed or moved to today / future
	if status == "Overdue":
		dr = row.get("date_required")
		if not dr or getdate(dr) >= today_date:
			row.status = "Pending"
			if row.get("overdue_days"):
				row.overdue_days = 0


def _apply_activity_based_status_updates(row):
	"""Vice versa: when fields are set, update status accordingly."""
	today_date = getdate(today())

	# Attachment + date_received set -> Received (check first; includes Overdue)
	if row.get("attachment") and row.get("date_received") and row.status in ("Pending", "Uploaded", "Overdue"):
		row.status = "Received"
		if row.get("overdue_days"):
			row.overdue_days = 0
	# Attachment uploaded -> Uploaded (including when Overdue - document now provided)
	elif row.get("attachment") and row.status in ("Pending", "Overdue"):
		row.status = "Uploaded"
		if row.get("overdue_days"):
			row.overdue_days = 0

	# Verified By entered -> Verified
	if row.get("verified_by") and row.status not in ("Verified", "Done"):
		row.date_verified = today_date
		row.is_verified = 1
		row.status = "Verified"
	# is_verified checked -> Verified (alternative path)
	elif row.get("is_verified") and row.status not in ("Verified", "Done"):
		row.date_verified = today_date
		row.status = "Verified"


def _update_overdue_status(row):
	"""Update overdue_days and status when date_required or expiry_date has passed."""
	today_date = getdate(today())

	# Expired: expiry_date passed
	if row.expiry_date and getdate(row.expiry_date) < today_date:
		row.status = "Expired"
		return

	# Overdue: date_required passed, required document not received
	if row.date_required:
		required = getdate(row.date_required)
		# Include Overdue so overdue_days is recomputed each save; otherwise the branch below
		# (`elif row.overdue_days`) clears days whenever status is already Overdue.
		if required < today_date and row.status in ("Pending", "Uploaded", "Overdue"):
			row.overdue_days = date_diff(today_date, required)
			if row.status == "Pending":
				row.status = "Overdue"
		elif row.overdue_days:
			row.overdue_days = 0


def validate_job_document_status_aligned(row):
	"""Ensure status is consistent with dates and required fields. Call from parent before_save."""
	if not row or getattr(row, "doctype", None) != "Job Document":
		return
	_realign_job_document_status_from_dates(row)
	_downgrade_uploaded_when_no_attachment(row)
	status = row.get("status")
	if not status:
		return

	if status == "Overdue":
		throw_if_not_past_date(
			row.date_required,
			status_label="Overdue",
			date_label="Date Required",
			title=_("Invalid Status"),
		)

	elif status == "Expired":
		throw_if_not_past_date(
			row.expiry_date,
			status_label="Expired",
			date_label="Expiry Date",
			title=_("Invalid Status"),
		)

	elif status in ("Received", "Done", "Uploaded"):
		if not row.get("attachment"):
			frappe.throw(
				_("Status '{0}' requires an attachment to be uploaded.").format(status),
				title=_("Invalid Status"),
			)

	elif status == "Verified":
		if not row.get("verified_by"):
			frappe.throw(
				_("Status 'Verified' requires Verified By to be entered."),
				title=_("Invalid Status"),
			)


class JobDocument(Document):
	"""Child table for document tracking on Bookings, Jobs, Shipments."""

	def validate(self):
		validate_job_document_status_aligned(self)

	def before_save(self):
		apply_job_document_status_updates(self)
