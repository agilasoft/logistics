# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Scheduled monitoring for Time Sensitive cases."""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from logistics.time_sensitive.notifications import notify_case_event, users_with_role
from logistics.time_sensitive.sla import compute_sla_status, get_at_risk_hours_for_case


def monitor_time_sensitive_cases():
	"""Five-minute monitor: refresh SLA, fire at-risk / breach / unacked alerts."""
	try:
		cases = frappe.get_all(
			"Time Sensitive Case",
			filters={
				"status": ["in", ["Triage", "Activated", "In Execution", "On Hold"]],
				"docstatus": ["<", 2],
			},
			fields=[
				"name",
				"status",
				"sla_status",
				"critical_deadline",
				"next_checkpoint",
				"activated_on",
				"acknowledged_on",
				"response_due_on",
				"coordinator",
				"escalation_contact",
				"case_type",
				"case_type_name",
				"at_risk_hours",
				"breach_grace_minutes",
				"last_alert_key",
			],
			limit=500,
		)
		now = now_datetime()
		updated = 0
		for row in cases:
			try:
				updated += _process_case_row(row, now)
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f"time_sensitive.monitor:{row.name}",
				)
		if updated:
			frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "time_sensitive.monitor_time_sensitive_cases")


def _process_case_row(row, now) -> int:
	at_risk = get_at_risk_hours_for_case(frappe._dict(row))
	grace = cint(row.breach_grace_minutes or 0)
	new_sla = compute_sla_status(
		row.critical_deadline,
		at_risk_hours=at_risk,
		breach_grace_minutes=grace,
		now=now,
	)
	changed = 0
	if new_sla != row.sla_status:
		frappe.db.set_value(
			"Time Sensitive Case", row.name, "sla_status", new_sla, update_modified=False
		)
		changed = 1
		case_proxy = frappe._dict(row)
		case_proxy.sla_status = new_sla
		if new_sla == "At Risk":
			notify_case_event(
				case_proxy,
				event_type="At Risk",
				subject=_("At Risk: {0}").format(row.name),
				message=_("Case {0} is at risk of missing deadline {1}.").format(
					row.name, row.critical_deadline
				),
				severity="impending",
				bucket=new_sla,
			)
		elif new_sla == "Breached":
			recipients = _escalation_recipients(row)
			notify_case_event(
				case_proxy,
				event_type="Deadline Breach",
				subject=_("BREACHED: {0}").format(row.name),
				message=_("Case {0} has breached critical deadline {1}.").format(
					row.name, row.critical_deadline
				),
				severity="critical",
				recipients=recipients,
				bucket=new_sla,
			)

	# Unacknowledged after response_due_on
	if (
		row.activated_on
		and not row.acknowledged_on
		and row.response_due_on
		and get_datetime(row.response_due_on) < now
	):
		case_proxy = frappe._dict(row)
		notify_case_event(
			case_proxy,
			event_type="Unacknowledged",
			subject=_("Unacknowledged: {0}").format(row.name),
			message=_("Case {0} was not acknowledged by {1}.").format(
				row.name, row.response_due_on
			),
			severity="critical",
			bucket="unacked",
		)

	# Missed checkpoint
	if row.next_checkpoint and get_datetime(row.next_checkpoint) < now:
		case_proxy = frappe._dict(row)
		notify_case_event(
			case_proxy,
			event_type="Checkpoint Missed",
			subject=_("Checkpoint missed: {0}").format(row.name),
			message=_("Next checkpoint {0} was missed.").format(row.next_checkpoint),
			severity="impending",
			bucket=f"checkpoint:{row.next_checkpoint}",
		)

	return changed


def _escalation_recipients(row) -> list[str]:
	users = []
	if row.coordinator:
		users.append(row.coordinator)
	if row.escalation_contact:
		users.append(row.escalation_contact)
	rules = frappe.get_all(
		"Time Sensitive Escalation Rule",
		filters={"enabled": 1, "trigger_event": "Deadline Breach"},
		fields=["escalate_to_user", "escalate_to_role", "case_type"],
		limit=50,
	)
	rules = [r for r in rules if not r.case_type or r.case_type == row.case_type]
	for r in rules or []:
		if r.escalate_to_user:
			users.append(r.escalate_to_user)
		if r.escalate_to_role:
			users.extend(users_with_role(r.escalate_to_role))
	return list({u for u in users if u})
