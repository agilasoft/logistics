# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Resolve Address pick/drop windows from the Pick / Drop Windows schedule table."""

from __future__ import annotations

from typing import Any, Optional, Tuple

import frappe
from frappe.utils import getdate

SCHEDULE_FIELD = "custom_window_schedule"
SCHEDULE_DOCTYPE = "Address Window Schedule"

_OPERATION_MAP = {
	"pick": "Pick",
	"drop": "Drop",
	"Pick": "Pick",
	"Drop": "Drop",
}


def normalize_operation(operation: str) -> Optional[str]:
	"""Return canonical Select value Pick/Drop, or None if unknown."""
	if not operation:
		return None
	return _OPERATION_MAP.get(str(operation).strip()) or _OPERATION_MAP.get(
		str(operation).strip().lower()
	)


def weekday_name(on_date) -> Optional[str]:
	"""Return English weekday name (Monday…Sunday) for a date-like value."""
	if not on_date:
		return None
	return getdate(on_date).strftime("%A")


def get_schedule_rows(address_name: str) -> list[dict[str, Any]]:
	"""Return schedule child rows for an Address (empty if none / missing)."""
	if not address_name or not frappe.db.exists("DocType", SCHEDULE_DOCTYPE):
		return []
	if not frappe.db.exists("Address", address_name):
		return []
	return frappe.get_all(
		SCHEDULE_DOCTYPE,
		filters={"parent": address_name, "parenttype": "Address", "parentfield": SCHEDULE_FIELD},
		fields=["day", "operation", "window_start", "window_end", "remarks", "name"],
		order_by="idx asc",
	)


def resolve_address_window(
	address_name: str,
	operation: str,
	on_date,
) -> Optional[Tuple[Any, Any]]:
	"""
	Look up pick/drop window for address + weekday + operation from the schedule table.

	Returns (window_start, window_end) or None when no matching row (not available).
	Does not fall back to legacy default window fields.
	"""
	if not address_name or not on_date:
		return None

	op = normalize_operation(operation)
	day = weekday_name(on_date)
	if not op or not day:
		return None

	for row in get_schedule_rows(address_name):
		if row.get("day") == day and normalize_operation(row.get("operation") or "") == op:
			return row.get("window_start"), row.get("window_end")
	return None


def is_operation_allowed(address_name: str, operation: str, on_date) -> bool:
	"""True when a schedule row exists for that weekday and operation."""
	return resolve_address_window(address_name, operation, on_date) is not None


def validate_address_window_schedule(doc, method=None):
	"""Validate Address Pick / Drop Windows table: end after start, unique day+operation."""
	rows = doc.get(SCHEDULE_FIELD) or []
	if not rows:
		return

	from frappe import _
	from frappe.utils import get_time
	from datetime import time as time_type
	from datetime import timedelta

	seen: set[tuple[str, str]] = set()
	for row in rows:
		day = (row.get("day") or "").strip()
		op = normalize_operation(row.get("operation") or "")
		if not day or not op:
			continue

		key = (day, op)
		if key in seen:
			frappe.throw(
				_("Duplicate Pick / Drop Windows row for {0} / {1}. Each day and operation may appear only once.").format(
					day, op
				),
				title=_("Invalid Window Schedule"),
			)
		seen.add(key)

		start = row.get("window_start")
		end = row.get("window_end")
		if not start or not end:
			continue

		start_t = get_time(start)
		end_t = get_time(end)
		# get_time may return timedelta
		if isinstance(start_t, timedelta):
			start_secs = int(start_t.total_seconds())
		elif isinstance(start_t, time_type):
			start_secs = start_t.hour * 3600 + start_t.minute * 60 + start_t.second
		else:
			continue
		if isinstance(end_t, timedelta):
			end_secs = int(end_t.total_seconds())
		elif isinstance(end_t, time_type):
			end_secs = end_t.hour * 3600 + end_t.minute * 60 + end_t.second
		else:
			continue

		if end_secs <= start_secs:
			frappe.throw(
				_("Window End must be after Window Start for {0} / {1}.").format(day, op),
				title=_("Invalid Window Schedule"),
			)
