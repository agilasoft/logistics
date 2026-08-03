# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Deduplicated notifications and realtime alerts for Time Sensitive cases."""

from __future__ import annotations

from typing import Iterable, Optional

import frappe
from frappe import _
from frappe.utils import cint, now_datetime


SEVERITY_INDICATOR = {
	"critical": "red",
	"impending": "orange",
	"informational": "blue",
}


def _alert_key(case_name: str, event_type: str, bucket: str = "") -> str:
	return f"{case_name}|{event_type}|{bucket}"


def notify_case_event(
	case,
	*,
	event_type: str,
	subject: str,
	message: str,
	severity: str = "informational",
	recipients: Optional[Iterable[str]] = None,
	bucket: str = "",
	force: bool = False,
) -> int:
	"""Create Notification Logs + optional ToDos; publish realtime toast.

	Deduplicates by case + event_type + bucket using ``last_alert_key`` on the case.
	Returns number of recipient notifications enqueued.
	"""
	case_name = case.name if hasattr(case, "name") else case
	key = _alert_key(case_name, event_type, bucket or severity)
	last_key = None
	if hasattr(case, "last_alert_key"):
		last_key = case.last_alert_key
	elif case_name:
		last_key = frappe.db.get_value("Time Sensitive Case", case_name, "last_alert_key")

	if not force and last_key == key:
		return 0

	users = list(_resolve_recipients(case, recipients))
	if not users:
		users = [frappe.session.user]

	sent = 0
	try:
		from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

		enqueue_create_notification(
			users,
			{
				"subject": subject,
				"type": "Alert",
				"document_type": "Time Sensitive Case",
				"document_name": case_name,
				"from_user": frappe.session.user,
				"email_content": message,
			},
		)
		sent = len(users)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "time_sensitive.notify_case_event")

	# Assignment / ToDo for coordinator on critical events
	if severity == "critical":
		for user in users:
			try:
				frappe.get_doc(
					{
						"doctype": "ToDo",
						"allocated_to": user,
						"description": f"{subject}\n\n{message}",
						"reference_type": "Time Sensitive Case",
						"reference_name": case_name,
						"priority": "High",
						"status": "Open",
						"date": now_datetime().date(),
					}
				).insert(ignore_permissions=True)
			except Exception:
				pass

	# Live desk toast for open sessions
	try:
		frappe.publish_realtime(
			"time_sensitive_alert",
			{
				"case": case_name,
				"event_type": event_type,
				"subject": subject,
				"message": message,
				"severity": severity,
				"indicator": SEVERITY_INDICATOR.get(severity, "blue"),
			},
			after_commit=True,
		)
	except Exception:
		pass

	if case_name:
		try:
			frappe.db.set_value(
				"Time Sensitive Case", case_name, "last_alert_key", key, update_modified=False
			)
			if hasattr(case, "last_alert_key"):
				case.last_alert_key = key
		except Exception:
			pass

	return sent


def _resolve_recipients(case, recipients: Optional[Iterable[str]]) -> set[str]:
	users: set[str] = set()
	if recipients:
		users.update([u for u in recipients if u and u != "Guest"])
	for field in ("coordinator", "escalation_contact"):
		val = getattr(case, field, None)
		if val:
			users.add(val)
	# Role-based fallback from escalation rules is handled by the monitor
	return {u for u in users if u and u != "Guest"}


def users_with_role(role: str) -> list[str]:
	if not role:
		return []
	return frappe.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User"},
		pluck="parent",
	)
