# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Standardized alert, notification and validation utilities.
Uses Logistics Settings > Alerts and Delays Notification tab for configurable day thresholds.
Alert levels: Critical (red), Warning (yellow), Information (blue). Each section (Documents, Milestones, Penalties, Delays)
defines days for Warning and Information; Critical is used for overdue/past/delayed (no day threshold).
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import getdate, get_datetime, now_datetime, date_diff


def get_alert_settings():
	"""Return Logistics Settings (Alerts and Delays Notification tab fields)."""
	return frappe.get_single("Logistics Settings")


def get_indicator_for_severity(severity):
	"""Map severity to Frappe msgprint/show_alert indicator. Critical=red, Warning=orange, Information=blue."""
	return {"critical": "red", "impending": "orange", "informational": "blue"}.get(
		severity, "blue"
	)


def get_document_expiring_soon_days():
	"""Days before document expiry for Warning level (from Logistics Settings > Documents > Warning (Days))."""
	settings = get_alert_settings()
	return int(getattr(settings, "document_expiring_soon_days", None) or 7)


def get_document_informational_days():
	"""Days before document expiry for Information level (from Logistics Settings > Documents > Information (Days))."""
	settings = get_alert_settings()
	return int(getattr(settings, "document_informational_days", None) or 30)


def get_milestone_impending_days():
	"""Days before milestone planned_end for Warning level (from Logistics Settings > Milestones > Warning (Days))."""
	settings = get_alert_settings()
	return int(getattr(settings, "milestone_impending_days", None) or 2)


def get_milestone_informational_days():
	"""Days before milestone planned_end for Information level (from Logistics Settings > Milestones > Information (Days))."""
	settings = get_alert_settings()
	return int(getattr(settings, "milestone_informational_days", None) or 14)


def get_penalty_impending_days():
	"""Days before free time expires for Warning level (from Logistics Settings > Penalties > Warning (Days))."""
	settings = get_alert_settings()
	return int(getattr(settings, "penalty_impending_days", None) or 2)


def get_delay_impending_days():
	"""Days before expected delay for Warning level (from Logistics Settings > Delays > Warning (Days))."""
	settings = get_alert_settings()
	return int(getattr(settings, "delay_impending_days", None) or 1)


def get_severity_for_document_expiring(days_until_expiry):
	"""
	Return severity for a document expiring in N days using Critical / Warning / Information levels.
	Critical = already expired (caller handles). Warning = within document_expiring_soon_days. Information = within document_informational_days.
	Returns: "impending" (Warning), "informational" (Information), or None.
	"""
	if days_until_expiry is None or days_until_expiry < 0:
		return None
	warning_days = get_document_expiring_soon_days()
	information_days = get_document_informational_days()
	if days_until_expiry <= warning_days:
		return "impending"
	if days_until_expiry <= information_days:
		return "informational"
	return None


def get_severity_for_milestone(planned_end, actual_end=None):
	"""
	Return (display_status, severity) for a milestone using Critical / Warning / Information levels.
	display_status: completed, started, delayed, impending, informational, planned
	severity: critical (Critical), impending (Warning), informational (Information), or None.
	Days from Logistics Settings: Milestones > Warning (Days), Information (Days).
	"""
	now = now_datetime()
	if not planned_end:
		return "planned", None
	planned_dt = get_datetime(planned_end)
	if actual_end:
		actual_dt = get_datetime(actual_end)
		if actual_dt > planned_dt:
			return "delayed", "critical"
		# Completed on time or early
		return "completed", None
	# No actual_end yet
	if planned_dt < now:
		return "delayed", "critical"
	days_until = date_diff(planned_dt.date(), getdate(now))
	impending_days = get_milestone_impending_days()
	informational_days = get_milestone_informational_days()
	if days_until <= impending_days:
		return "planned", "impending"
	if days_until <= informational_days:
		return "planned", "informational"
	return "planned", None
