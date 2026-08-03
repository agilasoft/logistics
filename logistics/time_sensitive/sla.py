# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""SLA helpers for Time Sensitive cases."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

import frappe
from frappe.utils import cint, get_datetime, now_datetime


def compute_sla_status(
	deadline,
	*,
	at_risk_hours: int = 4,
	breach_grace_minutes: int = 0,
	now=None,
) -> str:
	"""Return On Track / At Risk / Breached for a critical deadline."""
	if not deadline:
		return "On Track"
	now = get_datetime(now or now_datetime())
	target = get_datetime(deadline)
	if now > target + timedelta(minutes=cint(breach_grace_minutes) or 0):
		return "Breached"
	if now >= target - timedelta(hours=cint(at_risk_hours) or 4):
		return "At Risk"
	return "On Track"


def get_at_risk_hours_for_case(case) -> int:
	"""Resolve at-risk window from case, case type, or Logistics Service Level."""
	if cint(getattr(case, "at_risk_hours", 0)):
		return cint(case.at_risk_hours)

	case_type = getattr(case, "case_type", None)
	if case_type:
		hours = frappe.db.get_value("Time Sensitive Case Type", case_type, "default_at_risk_hours")
		if cint(hours):
			return cint(hours)

	# Prefer Logistics Service Level Module row for Time Sensitive when configured
	try:
		from logistics.logistics.doctype.logistics_service_level.logistics_service_level import (
			get_sla_settings_for_module,
		)

		sl_name = frappe.db.get_value(
			"Logistics Service Level Module",
			{"module": "Time Sensitive", "enabled": 1},
			"parent",
		)
		if sl_name:
			settings = get_sla_settings_for_module(sl_name, "Time Sensitive")
			if settings and cint(settings.get("sla_at_risk_hours_before")):
				return cint(settings.get("sla_at_risk_hours_before"))
	except Exception:
		pass

	return 4


def seconds_until_deadline(deadline, now=None) -> Optional[int]:
	"""Positive = remaining; negative = overdue seconds. None if no deadline."""
	if not deadline:
		return None
	now = get_datetime(now or now_datetime())
	target = get_datetime(deadline)
	return int((target - now).total_seconds())


def format_countdown(seconds: Optional[int]) -> str:
	"""Human-readable Dd HHh MMm SSs or OVERDUE …."""
	if seconds is None:
		return ""
	overdue = seconds < 0
	secs = abs(int(seconds))
	days, rem = divmod(secs, 86400)
	hours, rem = divmod(rem, 3600)
	mins, secs = divmod(rem, 60)
	parts = []
	if days:
		parts.append(f"{days}d")
	parts.append(f"{hours:02d}h")
	parts.append(f"{mins:02d}m")
	parts.append(f"{secs:02d}s")
	label = " ".join(parts)
	return f"OVERDUE {label}" if overdue else label
