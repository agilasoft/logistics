# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.model.workflow import get_workflow_name, get_workflow_state_field
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, time_diff_in_seconds


def _parse_filters(filters: dict | str | None) -> dict[str, Any]:
	if not filters:
		return {}
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except json.JSONDecodeError:
			return {}
	return filters or {}


def get_active_workflow_doctypes() -> list[str]:
	return frappe.get_all(
		"Workflow",
		filters={"is_active": 1},
		pluck="document_type",
		distinct=True,
	)


def get_user_roles(user: str | None = None) -> set[str]:
	user = user or frappe.session.user
	return set(frappe.get_roles(user))


def _get_permitted_roles(workflow_action_name: str) -> list[str]:
	return frappe.get_all(
		"Workflow Action Permitted Role",
		filters={"parent": workflow_action_name},
		pluck="role",
	)


def _matches_role_filter(permitted_roles: list[str], role_filter: str | None, user: str) -> bool:
	if not role_filter:
		return True
	if role_filter in permitted_roles:
		return True
	# Allow queue view even when child roles are missing but user holds the filter role.
	return user == "Administrator" or role_filter in get_user_roles(user)


def get_open_workflow_actions(
	user: str | None = None,
	role_filter: str | None = None,
	limit: int = 500,
) -> list[dict[str, Any]]:
	"""Return open Workflow Action rows across all doctypes."""
	user = user or frappe.session.user
	limit = cint(limit) or 500

	# Direct SQL is more reliable than role joins and matches the Workflow Action list.
	rows = frappe.db.sql(
		"""
		SELECT
			name,
			reference_doctype,
			reference_name,
			workflow_state,
			creation,
			modified,
			user
		FROM `tabWorkflow Action`
		WHERE status = 'Open'
		ORDER BY modified DESC
		LIMIT %(limit)s
		""",
		{"limit": limit},
		as_dict=True,
	)

	results: list[dict[str, Any]] = []
	seen: set[tuple[str, str]] = set()
	for row in rows:
		permitted_roles = _get_permitted_roles(row.name)
		if not _matches_role_filter(permitted_roles, role_filter, user):
			continue

		if user != "Administrator":
			user_roles = get_user_roles(user)
			if permitted_roles and not user_roles.intersection(permitted_roles):
				continue

		key = (row.reference_doctype, row.reference_name)
		if key in seen:
			continue
		seen.add(key)

		results.append(
			{
				"workflow_action": row.name,
				"reference_doctype": row.reference_doctype,
				"reference_name": row.reference_name,
				"workflow_state": row.workflow_state,
				"creation": row.creation,
				"modified": row.modified,
				"permitted_role": permitted_roles[0] if permitted_roles else None,
				"permitted_roles": permitted_roles,
				"assigned_user": row.user,
			}
		)

	return results


def _matches_dimension_filters(doc, filters: dict[str, Any]) -> bool:
	meta = frappe.get_meta(doc.doctype)
	for field in ("company", "branch", "cost_center", "profit_center"):
		value = (filters.get(field) or "").strip()
		if not value:
			continue
		if not meta.has_field(field):
			continue
		if (doc.get(field) or "") != value:
			return False
	return True


def _get_transition_actions(doctype: str, workflow_state: str, permitted_roles: list[str]) -> list[str]:
	workflow = get_workflow_name(doctype)
	if not workflow or not workflow_state:
		return []
	filters = {"parent": workflow, "state": workflow_state}
	if permitted_roles:
		filters["allowed"] = ["in", permitted_roles]
	return frappe.get_all("Workflow Transition", filters=filters, pluck="action", distinct=True)


def _get_sla_config(workflow_state: str) -> dict[str, Any]:
	row = frappe.db.get_value(
		"Workflow State",
		workflow_state,
		["wc_sla_enabled", "wc_sla_unit", "wc_sla_value"],
		as_dict=True,
	)
	if not row or not row.get("wc_sla_enabled"):
		return {"enabled": False}
	return {
		"enabled": True,
		"unit": row.get("wc_sla_unit") or "Hours",
		"value": flt(row.get("wc_sla_value")),
	}


def _allowed_seconds(sla: dict[str, Any]) -> int | None:
	if not sla.get("enabled") or not sla.get("value"):
		return None
	if sla.get("unit") == "Days":
		return int(sla["value"] * 86400)
	return int(sla["value"] * 3600)


def _severity(elapsed_seconds: float, allowed_seconds: int | None, sla: dict[str, Any]) -> str:
	if not sla.get("enabled") or not allowed_seconds:
		return "ok"
	ratio = elapsed_seconds / allowed_seconds
	if ratio > 1:
		return "overdue"
	try:
		settings = frappe.get_single("Workflow Center Settings")
		critical = flt(getattr(settings, "critical_percent", None) or 90) / 100
		warning = flt(getattr(settings, "warning_percent", None) or 75) / 100
		info = flt(getattr(settings, "info_percent", None) or 50) / 100
	except Exception:
		critical, warning, info = 0.9, 0.75, 0.5
	if ratio >= critical:
		return "critical"
	if ratio >= warning:
		return "warning"
	if ratio >= info:
		return "info"
	return "ok"


def _classify_item(item: dict[str, Any]) -> str:
	severity = item.get("severity") or "ok"
	if severity in ("critical", "warning", "info"):
		return "at_risk"
	if severity == "overdue":
		return "delay_risk"
	if item.get("sla_breach_penalty"):
		return "penalty_risk"
	creation = get_datetime(item.get("creation"))
	if creation and getdate(creation) == getdate():
		return "todays_tasks"
	if not item.get("sla_enabled"):
		return "compliance_gaps"
	return "open_actions"


def enrich_workflow_action(row: dict[str, Any], user: str, filters: dict[str, Any]) -> dict[str, Any] | None:
	doctype = row.get("reference_doctype")
	name = row.get("reference_name")
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None

	doc = frappe.get_doc(doctype, name)

	if user != "Administrator" and not frappe.has_permission(doctype, "read", doc=doc, user=user):
		return None

	if not _matches_dimension_filters(doc, filters):
		return None

	workflow = get_workflow_name(doctype)
	state_field = get_workflow_state_field(workflow) if workflow else "workflow_state"
	current_state = doc.get(state_field) or row.get("workflow_state")
	permitted_roles = row.get("permitted_roles") or []

	entered_at = get_datetime(row.get("modified") or row.get("creation"))
	elapsed = time_diff_in_seconds(now_datetime(), entered_at) if entered_at else 0
	sla = _get_sla_config(current_state)
	allowed = _allowed_seconds(sla)
	severity = _severity(elapsed, allowed, sla)
	actions = _get_transition_actions(doctype, current_state, permitted_roles)

	title = doc.get("title") or doc.get("supplier_name") or doc.get("customer_name") or name
	item = {
		"workflow_action": row.get("workflow_action"),
		"reference_doctype": doctype,
		"reference_name": name,
		"title": title,
		"workflow": workflow,
		"workflow_state": current_state,
		"permitted_role": row.get("permitted_role"),
		"permitted_roles": permitted_roles,
		"available_actions": actions,
		"company": doc.get("company"),
		"branch": doc.get("branch"),
		"cost_center": doc.get("cost_center"),
		"profit_center": doc.get("profit_center"),
		"docstatus": doc.docstatus,
		"owner": doc.get("owner"),
		"modified": str(doc.modified),
		"creation": str(row.get("creation")),
		"state_entered_at": str(entered_at) if entered_at else None,
		"elapsed_seconds": elapsed,
		"allowed_seconds": allowed,
		"severity": severity,
		"sla_enabled": sla.get("enabled"),
		"sla_breach_penalty": False,
	}
	item["segment"] = _classify_item(item)
	return item


def get_dashboard_items(
	filters: dict | str | None = None,
	user: str | None = None,
	segment: str | None = None,
) -> list[dict[str, Any]]:
	filters = _parse_filters(filters)
	user = user or frappe.session.user
	role_filter = (filters.get("role") or "").strip() or None

	items = [
		item
		for row in get_open_workflow_actions(user=user, role_filter=role_filter)
		if (item := enrich_workflow_action(row, user, filters))
	]

	if not segment or segment == "open_actions":
		return items
	return [item for item in items if item.get("segment") == segment]


def get_dashboard_summary(filters: dict | str | None = None, user: str | None = None) -> dict[str, Any]:
	filters = _parse_filters(filters)
	user = user or frappe.session.user
	items = get_dashboard_items(filters=filters, user=user)
	counts = {
		"at_risk": 0,
		"delay_risk": 0,
		"penalty_risk": 0,
		"todays_tasks": 0,
		"compliance_gaps": 0,
		"open_actions": len(items),
	}
	for item in items:
		seg = item.get("segment") or "open_actions"
		if seg in counts and seg != "open_actions":
			counts[seg] += 1

	return {
		"counts": counts,
		"workflow_doctypes": get_active_workflow_doctypes(),
		"user": user,
		"roles": sorted(get_user_roles(user)),
		"filters": filters,
	}
