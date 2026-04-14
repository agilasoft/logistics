# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shared logistics Job Status (same options as Transport Job) for charge reopen and cross-module consistency."""

from __future__ import unicode_literals

import frappe
from frappe import _

# Keep identical to Select "options" on job_status / Transport Job status fields
JOB_STATUS_SELECT_OPTIONS = "Draft\nSubmitted\nIn Progress\nCompleted\nClosed\nReopened\nCancelled"

ALLOWED_JOB_STATUS_VALUES = frozenset(
	line.strip() for line in JOB_STATUS_SELECT_OPTIONS.split("\n") if line.strip()
)

CHARGE_LOCKED_STATUSES = frozenset({"Completed", "Closed"})
JOB_STATUS_REOPENED = "Reopened"
JOB_STATUS_CLOSED = "Closed"


def sync_sea_shipment_job_status(doc):
	"""Derive job_status from shipping_status; preserve Reopened/Closed from charge reopen workflow."""
	if getattr(doc.flags, "skip_job_status_sync", False):
		return
	docstatus = getattr(doc, "docstatus", 0) or 0
	cur = (getattr(doc, "job_status", None) or "").strip()
	if docstatus == 0:
		if not cur:
			doc.job_status = "Draft"
		return
	if cur in ("Reopened", "Closed"):
		return
	ss = (getattr(doc, "shipping_status", None) or "").strip()
	if ss == "Closed":
		doc.job_status = "Closed"
		return
	if ss in ("Delivered", "Empty Container Returned"):
		doc.job_status = "Completed"
		return
	if not cur or cur == "Draft":
		doc.job_status = "Submitted"


def sync_air_shipment_job_status(doc):
	"""Derive job_status from tracking_status (Delivered -> Completed)."""
	if getattr(doc.flags, "skip_job_status_sync", False):
		return
	docstatus = getattr(doc, "docstatus", 0) or 0
	cur = (getattr(doc, "job_status", None) or "").strip()
	if docstatus == 0:
		if not cur:
			doc.job_status = "Draft"
		return
	if cur in ("Reopened", "Closed"):
		return
	ts = (getattr(doc, "tracking_status", None) or "").strip()
	if ts == "Delivered":
		doc.job_status = "Completed"
		return
	if not cur or cur == "Draft":
		doc.job_status = "Submitted"


def sync_declaration_job_status(doc):
	"""Align billing job_status with customs status (separate field `status`)."""
	if getattr(doc.flags, "skip_job_status_sync", False):
		return
	docstatus = getattr(doc, "docstatus", 0) or 0
	cur = (getattr(doc, "job_status", None) or "").strip()
	if docstatus == 0:
		if not cur:
			doc.job_status = "Draft"
		return
	if cur in ("Reopened", "Closed"):
		return
	cs = (getattr(doc, "status", None) or "").strip()
	if cs in ("Cancelled", "Rejected"):
		doc.job_status = "Cancelled"
		return
	if cs in ("Cleared", "Released"):
		doc.job_status = "Completed"
		return
	if cs == "Under Review":
		doc.job_status = "In Progress"
		return
	if cs == "Submitted":
		doc.job_status = "Submitted"
		return
	if cs == "Draft":
		doc.job_status = "Draft"
		return
	if not cur or cur == "Draft":
		doc.job_status = "Submitted"


def validate_job_status_field(doc, fieldname="job_status"):
	"""Ensure job_status (or equivalent) is one of the standard options."""
	val = (getattr(doc, fieldname, None) or "").strip()
	if not val:
		return
	if val not in ALLOWED_JOB_STATUS_VALUES:
		frappe.throw(
			_("Invalid {0}: {1}").format(frappe.unscrub(fieldname), val),
			title=_("Invalid Job Status"),
		)


def validate_warehouse_job_defaults(doc):
	"""Default job lifecycle on Warehouse Job (editable Job Status for Completed/Closed)."""
	docstatus = getattr(doc, "docstatus", 0) or 0
	cur = (getattr(doc, "job_status", None) or "").strip()
	if docstatus == 0:
		if not cur:
			doc.job_status = "Draft"
		return
	if not cur or cur == "Draft":
		doc.job_status = "Submitted"
