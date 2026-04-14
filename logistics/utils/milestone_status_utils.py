# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared utilities for milestone status auto-update."""

from __future__ import unicode_literals

import frappe
from frappe.utils import get_datetime, now_datetime

from logistics.utils.validation_user_messages import (
	milestone_actual_end_without_start_message,
	milestone_actual_range_invalid_message,
	milestone_completed_before_planned_start_message,
	milestone_date_validation_title,
	milestone_planned_range_invalid_message,
)


def _is_strict_milestone_schedule_validation_enabled():
	"""Use strict mode by default; admins can relax it from Logistics Settings."""
	try:
		value = frappe.db.get_single_value("Logistics Settings", "strict_milestone_schedule_validation")
		if value in (None, ""):
			return True
		return bool(int(value))
	except Exception:
		return True


def _show_non_blocking_schedule_warning(message):
	"""Show at most one identical warning per request to avoid repetitive popups."""
	cache = getattr(frappe.flags, "_milestone_schedule_warnings_shown", None)
	if cache is None:
		cache = set()
		frappe.flags._milestone_schedule_warnings_shown = cache
	if message in cache:
		return
	cache.add(message)
	frappe.msgprint(message, title=milestone_date_validation_title(), indicator="orange", alert=True)


def validate_milestone_date_ranges(milestone_doc):
	"""
	Ensure planned/actual intervals are not inverted.
	Planned Start and Actual Start must be on or before their respective end (same timestamp allowed).
	"""
	if not milestone_doc:
		return

	# Parent date sync / automation may set actual_end without actual_start; treat as same instant.
	_end = milestone_doc.get("actual_end")
	_start = milestone_doc.get("actual_start")
	if _end and (_start is None or _start == ""):
		milestone_doc.actual_start = _end

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

	if actual_end and not actual_start:
		frappe.throw(
			milestone_actual_end_without_start_message(),
			title=milestone_date_validation_title(),
		)

	if actual_start and actual_end and actual_start > actual_end:
		frappe.throw(
			milestone_actual_range_invalid_message(),
			title=milestone_date_validation_title(),
		)

	if planned_start and actual_end and actual_end < planned_start:
		message = milestone_completed_before_planned_start_message()
		if _is_strict_milestone_schedule_validation_enabled():
			frappe.throw(
				message,
				title=milestone_date_validation_title(),
			)
		else:
			_show_non_blocking_schedule_warning(message)


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

	# No actual dates and planned window not overdue — always reset to Planned (e.g. after clearing actual_end)
	milestone_doc.status = "Planned"
