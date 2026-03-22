# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today
from frappe import _


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
	_apply_activity_based_status_updates(row)
	_update_overdue_status(row)


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
		if required < today_date and row.status in ("Pending", "Uploaded"):
			row.overdue_days = date_diff(today_date, required)
			if row.status == "Pending":
				row.status = "Overdue"
		elif row.overdue_days:
			row.overdue_days = 0


def validate_job_document_status_aligned(row):
	"""Ensure status is consistent with dates and required fields. Call from parent before_save."""
	status = row.get("status")
	if not status:
		return

	today_date = getdate(today())

	if status == "Overdue":
		if not row.date_required:
			frappe.throw(
				_("Status 'Overdue' requires Date Required to be set."),
				title=_("Invalid Status"),
			)
		if getdate(row.date_required) >= today_date:
			frappe.throw(
				_("Status 'Overdue' is only valid when Date Required ({0}) has passed.").format(
					row.date_required
				),
				title=_("Invalid Status"),
			)

	elif status == "Expired":
		if not row.expiry_date:
			frappe.throw(
				_("Status 'Expired' requires Expiry Date to be set."),
				title=_("Invalid Status"),
			)
		if getdate(row.expiry_date) >= today_date:
			frappe.throw(
				_("Status 'Expired' is only valid when Expiry Date ({0}) has passed.").format(
					row.expiry_date
				),
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
