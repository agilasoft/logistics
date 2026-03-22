# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared utilities for milestone status auto-update."""

from __future__ import unicode_literals

import frappe
from frappe.utils import get_datetime, now_datetime

from logistics.utils.validation_user_messages import (
	milestone_actual_range_invalid_message,
	milestone_date_validation_title,
	milestone_planned_range_invalid_message,
)


def validate_milestone_date_ranges(milestone_doc):
	"""
	Ensure planned/actual intervals are not inverted.
	Planned Start and Actual Start must be on or before their respective end (same timestamp allowed).
	"""
	if not milestone_doc:
		return

	def _dt(val):
		if val is None or val == "":
			return None
		return get_datetime(val)

	planned_start = _dt(milestone_doc.get("planned_start"))
	planned_end = _dt(milestone_doc.get("planned_end"))

	if planned_start and planned_end and planned_start > planned_end:
		frappe.throw(
			milestone_planned_range_invalid_message(),
			title=milestone_date_validation_title(),
		)

	actual_start = _dt(milestone_doc.get("actual_start"))
	actual_end = _dt(milestone_doc.get("actual_end"))
	if actual_start and actual_end and actual_start > actual_end:
		frappe.throw(
			milestone_actual_range_invalid_message(),
			title=milestone_date_validation_title(),
		)


def update_milestone_status(milestone_doc):
	"""
	Set milestone status from actual dates (Status field is read-only; only system updates it).
	- Actual End set -> Completed
	- Actual Start set (no Actual End) -> Started
	- Planned End passed, no Actual End -> Delayed
	- Else -> Planned
	Call from child milestone doctype before_save.
	"""
	validate_milestone_date_ranges(milestone_doc)

	status = (milestone_doc.status or "").strip().lower()
	if status in ("completed", "finished", "done"):
		return  # Already completed, don't override

	# Actual End entered -> Completed
	if milestone_doc.actual_end:
		milestone_doc.status = "Completed"
		return

	# Actual Start entered -> Started
	if milestone_doc.actual_start:
		milestone_doc.status = "Started"
		return

	# If planned_end passed and no actual_end, status = Delayed
	if milestone_doc.planned_end:
		planned_dt = get_datetime(milestone_doc.planned_end)
		now = now_datetime()
		if planned_dt < now:
			milestone_doc.status = "Delayed"
			return

	# Default: Planned
	if not milestone_doc.status or milestone_doc.status.lower() in ("delayed",):
		milestone_doc.status = "Planned"
