# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
<<<<<<< HEAD
=======
from datetime import datetime
>>>>>>> origin/develop
from typing import Any

import frappe
from frappe import _
from frappe.model.workflow import get_workflow_name, get_workflow_state_field, has_approval_access
from frappe.permissions import has_permission
<<<<<<< HEAD
=======
from frappe.query_builder import DocType
>>>>>>> origin/develop
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
	"""Return every doctype that has an active workflow (no hardcoded allowlist)."""
	return frappe.get_all(
		"Workflow",
		filters={"is_active": 1},
		pluck="document_type",
		distinct=True,
	)


<<<<<<< HEAD
def get_user_roles(user: str | None = None) -> set[str]:
	user = user or frappe.session.user
	return set(frappe.get_roles(user))


def _get_permitted_roles(workflow_action_name: str) -> list[str]:
	return frappe.get_all(
		"Workflow Action Permitted Role",
		filters={"parent": workflow_action_name},
		pluck="role",
	)


def _user_can_see_action(user: str, permitted_roles: list[str], role_filter: str | None) -> bool:
	"""Match Frappe Workflow Action visibility, with optional queue filter."""
	if role_filter:
		return role_filter in permitted_roles

	if user == "Administrator":
		return True

	user_roles = get_user_roles(user)
	return bool(user_roles.intersection(permitted_roles))
=======
def get_user_roles(user: str | None = None, role_filter: str | None = None) -> set[str]:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if role_filter:
		roles = roles.intersection({role_filter})
	return roles
>>>>>>> origin/develop


def get_open_workflow_actions(
	user: str | None = None,
	role_filter: str | None = None,
	limit: int = 500,
) -> list[dict[str, Any]]:
<<<<<<< HEAD
	"""Return open Workflow Action rows visible to the user, across all doctypes."""
	user = user or frappe.session.user

	# Use frappe.get_all so Workflow Action permission_query_conditions apply
	# (Administrator sees all open actions; others see role-matched actions).
	rows = frappe.get_all(
		"Workflow Action",
		filters={"status": "Open"},
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"workflow_state",
			"creation",
			"modified",
			"user",
		],
		order_by="modified desc",
		limit_page_length=cint(limit) or 500,
		ignore_permissions=False,
	)

	deduped: list[dict[str, Any]] = []
	seen: set[tuple[str, str]] = set()
	for row in rows:
		permitted_roles = _get_permitted_roles(row.name)
		if not _user_can_see_action(user, permitted_roles, role_filter):
			continue

=======
	"""Return open Workflow Action rows the user can act on, across all doctypes."""
	user = user or frappe.session.user
	roles = get_user_roles(user, role_filter)
	if not roles:
		return []

	WorkflowAction = DocType("Workflow Action")
	WorkflowActionPermittedRole = DocType("Workflow Action Permitted Role")

	rows = (
		frappe.qb.from_(WorkflowAction)
		.join(WorkflowActionPermittedRole)
		.on(WorkflowAction.name == WorkflowActionPermittedRole.parent)
		.select(
			WorkflowAction.name.as_("workflow_action"),
			WorkflowAction.reference_doctype,
			WorkflowAction.reference_name,
			WorkflowAction.workflow_state,
			WorkflowAction.creation,
			WorkflowAction.modified,
			WorkflowActionPermittedRole.role.as_("permitted_role"),
		)
		.where(WorkflowAction.status == "Open")
		.where(WorkflowActionPermittedRole.role.isin(list(roles)))
		.orderby(WorkflowAction.modified, order=frappe.qb.desc)
		.limit(cint(limit) or 500)
	).run(as_dict=True)

	# Deduplicate by (doctype, name) keeping the most recently modified row.
	seen: set[tuple[str, str]] = set()
	deduped: list[dict[str, Any]] = []
	for row in rows:
>>>>>>> origin/develop
		key = (row.reference_doctype, row.reference_name)
		if key in seen:
			continue
		seen.add(key)
<<<<<<< HEAD

		deduped.append(
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
=======
		deduped.append(row)
>>>>>>> origin/develop

	return deduped


def _get_doc_meta_fields(doctype: str) -> dict[str, bool]:
	meta = frappe.get_meta(doctype)
	return {
		"company": meta.has_field("company"),
		"branch": meta.has_field("branch"),
		"cost_center": meta.has_field("cost_center"),
		"profit_center": meta.has_field("profit_center"),
	}


def _matches_dimension_filters(doc: frappe.model.document.Document, filters: dict[str, Any]) -> bool:
	meta_fields = _get_doc_meta_fields(doc.doctype)
	for field in ("company", "branch", "cost_center", "profit_center"):
		value = filters.get(field)
		if not value:
			continue
		if not meta_fields.get(field):
			continue
		if doc.get(field) != value:
			return False
	return True


<<<<<<< HEAD
def _get_available_actions(
	doc: frappe.model.document.Document,
	workflow_state: str,
	user: str,
	permitted_roles: list[str] | None = None,
) -> list[str]:
=======
def _get_available_actions(doc: frappe.model.document.Document, workflow_state: str, user: str) -> list[str]:
>>>>>>> origin/develop
	workflow = get_workflow_name(doc.doctype)
	if not workflow:
		return []

	roles = set(frappe.get_roles(user))
<<<<<<< HEAD
	if user == "Administrator":
		roles.add("Administrator")

=======
>>>>>>> origin/develop
	actions: list[str] = []
	for transition in frappe.get_all(
		"Workflow Transition",
		filters={"parent": workflow, "state": workflow_state},
		fields=["action", "allowed", "allow_self_approval", "condition"],
	):
<<<<<<< HEAD
		if permitted_roles and transition.allowed not in permitted_roles:
			# Still allow if user has the transition role directly.
			if transition.allowed not in roles:
				continue
		elif transition.allowed not in roles and user != "Administrator":
			continue

		if user != "Administrator" and not has_approval_access(user, doc, transition):
			continue
		actions.append(transition.action)

	if not actions and permitted_roles:
		# Fall back to transition labels for the open action's permitted roles.
		actions = frappe.get_all(
			"Workflow Transition",
			filters={"parent": workflow, "state": workflow_state, "allowed": ["in", permitted_roles]},
			pluck="action",
		)

=======
		if transition.allowed not in roles:
			continue
		if not has_approval_access(user, doc, transition):
			continue
		actions.append(transition.action)
>>>>>>> origin/develop
	return sorted(set(actions))


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
	"""Map an enriched item to a dashboard segment."""
	severity = item.get("severity") or "ok"
	if severity in ("critical", "warning", "info"):
		return "at_risk"
	if severity == "overdue":
		return "delay_risk"
	if item.get("sla_breach_penalty"):
		return "penalty_risk"
<<<<<<< HEAD
	creation = get_datetime(item.get("creation"))
	if creation and getdate(creation) == getdate():
		return "todays_tasks"
	if not item.get("sla_enabled"):
		return "compliance_gaps"
=======
	if not item.get("sla_enabled"):
		return "compliance_gaps"
	creation = get_datetime(item.get("creation"))
	if creation and getdate(creation) == getdate():
		return "todays_tasks"
>>>>>>> origin/develop
	return "open_actions"


def enrich_workflow_action(row: dict[str, Any], user: str, filters: dict[str, Any]) -> dict[str, Any] | None:
	doctype = row.get("reference_doctype")
	name = row.get("reference_name")
	if not doctype or not name:
		return None
	if not frappe.db.exists(doctype, name):
		return None
	if not has_permission(doctype, "read", name, user=user):
		return None

	doc = frappe.get_doc(doctype, name)
	if not _matches_dimension_filters(doc, filters):
		return None

	workflow = get_workflow_name(doctype)
	state_field = get_workflow_state_field(workflow) if workflow else "workflow_state"
	current_state = doc.get(state_field) or row.get("workflow_state")
<<<<<<< HEAD
	permitted_roles = row.get("permitted_roles") or (
		[row.get("permitted_role")] if row.get("permitted_role") else []
	)

	# Prefer the document's live workflow state; only skip if the open action is
	# clearly for a different state than the document currently holds.
	action_state = row.get("workflow_state")
	if action_state and current_state and action_state != current_state:
=======
	if current_state != row.get("workflow_state"):
		# Stale action — document moved on; skip from dashboard.
>>>>>>> origin/develop
		return None

	sla = _get_sla_config(current_state)
	allowed = _allowed_seconds(sla)
	entered_at = get_datetime(row.get("modified") or row.get("creation"))
	elapsed = time_diff_in_seconds(now_datetime(), entered_at) if entered_at else 0
	severity = _severity(elapsed, allowed, sla)
<<<<<<< HEAD
	actions = _get_available_actions(doc, current_state, user, permitted_roles=permitted_roles)
=======
	actions = _get_available_actions(doc, current_state, user)
	if not actions:
		return None
>>>>>>> origin/develop

	title = doc.get("title") or doc.get("supplier_name") or doc.get("customer_name") or name
	item = {
		"workflow_action": row.get("workflow_action"),
		"reference_doctype": doctype,
		"reference_name": name,
		"title": title,
		"workflow": workflow,
		"workflow_state": current_state,
		"permitted_role": row.get("permitted_role"),
<<<<<<< HEAD
		"permitted_roles": permitted_roles,
=======
>>>>>>> origin/develop
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
		"segment": "open_actions",
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
	role_filter = filters.get("role")

	raw_actions = get_open_workflow_actions(user=user, role_filter=role_filter)
	items: list[dict[str, Any]] = []
	for row in raw_actions:
		item = enrich_workflow_action(row, user, filters)
		if not item:
			continue
		items.append(item)

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
<<<<<<< HEAD
		"roles": sorted(get_user_roles(user)),
=======
		"roles": sorted(get_user_roles(user, filters.get("role"))),
>>>>>>> origin/develop
		"filters": filters,
	}
