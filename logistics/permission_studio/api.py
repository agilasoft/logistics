# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from logistics.permission_studio.flags import as_flag, clean_text, parse_payload
from logistics.permission_studio.logic import (
	BLOCKED_USERS,
	collect_grants,
	coverage_rows,
	default_conflicts,
	group_matches,
	matrix_for,
	requested_group_name,
)
from logistics.permission_studio.sync import reconcile

SYSTEM_DOCTYPES = {
	"DocType",
	"DocField",
	"DocPerm",
	"Custom Field",
	"Patch Log",
	"Error Log",
	"Activity Log",
	"Access Log",
	"View Log",
	"Version",
	"Scheduled Job Log",
	"Module Def",
}


@frappe.whitelist()
def get_studio_state(filters: str | dict | None = None) -> dict:
	"""Groups, coverage, conflicts, and the users who are not in any enabled group."""
	frappe.only_for("System Manager")
	filters = parse_payload(filters, {})
	groups = [_serialize_group(doc) for doc in _all_groups()]
	_attach_roles(groups)
	grants, hide_conflicts = collect_grants(groups)
	conflicts = default_conflicts(grants)
	conflicted = set()
	for conflict in conflicts:
		for grant in conflict["grants"]:
			conflicted.update(grant["groups"])
	for item in hide_conflicts:
		conflicted.update(item["groups"])

	visible = []
	for group in groups:
		if group_matches(group, filters, conflicted):
			group["matrix"] = matrix_for(group)
			visible.append(group)

	grouped_users = {
		member["user"]
		for group in groups
		if as_flag(group.get("enabled", 1))
		for member in group["members"]
	}
	ungrouped = _ungrouped_users(filters, grouped_users)
	enabled_users = _enabled_user_count()
	return {
		"groups": visible,
		"group_total": len(groups),
		"messages": _conflict_messages(conflicts, hide_conflicts),
		"ungrouped_users": ungrouped["rows"],
		"ungrouped_total": ungrouped["total"],
		"stats": {
			"groups": len(groups),
			"enabled_groups": sum(1 for group in groups if as_flag(group.get("enabled", 1))),
			"grouped_users": len(grouped_users),
			"ungrouped_users": max(enabled_users - len(grouped_users), 0),
			"rules": sum(len(group["rules"]) for group in groups if as_flag(group.get("enabled", 1))),
			"grants": len(grants),
		},
		"filter_options": {
			"roles": sorted({role for group in groups for member in group["members"] for role in member.get("roles") or []}),
			"doctypes": sorted(
				{
					clean_text(rule.get("reference_doctype"))
					for group in groups
					for rule in group["rules"]
					if clean_text(rule.get("reference_doctype"))
				}
			),
		},
	}


@frappe.whitelist()
def create_group(
	group_name: str,
	description: str | None = None,
	color: str | None = None,
	enabled: int | str = 1,
) -> dict:
	frappe.only_for("System Manager")
	doc = frappe.get_doc(
		{
			"doctype": "Hero Permission Group",
			"group_name": clean_text(group_name),
			"description": description or "",
			"color": color or "#2490ef",
			"enabled": as_flag(enabled),
		}
	)
	doc.insert()
	return {"name": doc.name}


@frappe.whitelist()
def update_group(
	name: str,
	description: str | None = None,
	color: str | None = None,
	enabled: int | str = 1,
	group_name: str | None = None,
) -> dict:
	"""Update the group's description, color, and enabled flag.

	``group_name``, when sent, renames the document. The name is the primary
	key, so links such as reviews, shares, and managed User Permissions follow it.
	"""
	frappe.only_for("System Manager")
	current = clean_text(name)
	target = requested_group_name(current, group_name)
	if target == "":
		frappe.throw(_("Group name is required."), title=_("Check the permission group"))
	if target:
		current = frappe.rename_doc("Hero Permission Group", current, target, show_alert=False)
	doc = frappe.get_doc("Hero Permission Group", current)
	doc.description = description or ""
	doc.color = color or doc.color
	doc.enabled = as_flag(enabled)
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def delete_group(name: str) -> dict:
	frappe.only_for("System Manager")
	frappe.delete_doc("Hero Permission Group", name)
	return {"name": name}


@frappe.whitelist()
def add_members(group: str, users: str | list) -> dict:
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Hero Permission Group", group)
	present = {row.user.casefold() for row in doc.members if row.user}
	added = 0
	for user in _user_list(users):
		if user.casefold() in present or user in BLOCKED_USERS:
			continue
		doc.append("members", {"user": user})
		present.add(user.casefold())
		added += 1
	if added:
		doc.save()
	return {"name": doc.name, "added": added}


@frappe.whitelist()
def remove_member(group: str, user: str) -> dict:
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Hero Permission Group", group)
	target = clean_text(user).casefold()
	for row in list(doc.members):
		if clean_text(row.user).casefold() == target:
			doc.remove(row)
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def add_rules(group: str, rules: str | list) -> dict:
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Hero Permission Group", group)
	for rule in parse_payload(rules, []):
		doc.append(
			"rules",
			{
				"reference_doctype": clean_text(rule.get("reference_doctype")),
				"for_value": clean_text(rule.get("for_value")),
				"apply_to_all_doctypes": as_flag(rule.get("apply_to_all_doctypes", 1)),
				"applicable_for": clean_text(rule.get("applicable_for")) or None,
				"is_default": as_flag(rule.get("is_default")),
				"hide_descendants": as_flag(rule.get("hide_descendants")),
			},
		)
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def remove_rule(group: str, rule_name: str) -> dict:
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Hero Permission Group", group)
	for row in list(doc.rules):
		if row.name == rule_name:
			doc.remove(row)
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def sync_all() -> dict:
	frappe.only_for("System Manager")
	return reconcile()


@frappe.whitelist()
def search_users(
	txt: str | None = None,
	role: str | None = None,
	user_type: str | None = None,
	enabled_only: int | str = 1,
) -> list:
	frappe.only_for("System Manager")
	filters = {"name": ["not in", sorted(BLOCKED_USERS)]}
	if as_flag(enabled_only):
		filters["enabled"] = 1
	if clean_text(user_type):
		filters["user_type"] = clean_text(user_type)
	if clean_text(role):
		with_role = frappe.get_all(
			"Has Role",
			filters={"role": clean_text(role), "parenttype": "User"},
			pluck="parent",
			limit_page_length=0,
			ignore_permissions=True,
		)
		allowed = [user for user in with_role if user not in BLOCKED_USERS]
		filters["name"] = ["in", allowed or ["__none__"]]
	or_filters = None
	query = clean_text(txt)
	if query:
		like = f"%{query}%"
		or_filters = [
			{"name": ["like", like]},
			{"full_name": ["like", like]},
			{"email": ["like", like]},
		]
	rows = frappe.get_all(
		"User",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "full_name", "user_type", "enabled"],
		order_by="full_name asc",
		limit_page_length=40,
		ignore_permissions=True,
	)
	_attach_role_rows(rows)
	return rows


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def permitted_doctype_query(doctype, txt, searchfield, start, page_len, filters):
	frappe.only_for("System Manager")
	del searchfield, filters
	if doctype and doctype != "DocType":
		return []
	query_filters = {"istable": 0, "issingle": 0, "name": ["not in", sorted(SYSTEM_DOCTYPES)]}
	meta = frappe.get_meta("DocType")
	if meta.has_field("is_virtual"):
		query_filters["is_virtual"] = 0
	or_filters = None
	if txt:
		or_filters = [{"name": ["like", f"%{txt}%"]}]
	return frappe.get_all(
		"DocType",
		filters=query_filters,
		or_filters=or_filters,
		fields=["name"],
		order_by="name asc",
		start=start,
		page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
def search_documents(doctype: str, txt: str | None = None) -> list:
	frappe.only_for("System Manager")
	doctype = clean_text(doctype)
	if doctype in SYSTEM_DOCTYPES or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("Choose a document type that can be used in a User Permission."))
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle:
		frappe.throw(_("{0} cannot be used in a User Permission.").format(doctype))
	fields = ["name"]
	title_field = meta.get_title_field() if hasattr(meta, "get_title_field") else (meta.title_field or "name")
	if title_field and title_field != "name" and meta.has_field(title_field):
		fields.append(title_field)
	or_filters = None
	query = clean_text(txt)
	if query:
		like = f"%{query}%"
		or_filters = [{"name": ["like", like]}]
		if title_field and title_field != "name":
			or_filters.append({title_field: ["like", like]})
	rows = frappe.get_all(
		doctype,
		or_filters=or_filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=40,
		ignore_permissions=True,
	)
	results = []
	for row in rows:
		label = row.get(title_field) if title_field and title_field != "name" else row.name
		results.append({"name": row.name, "label": label or row.name})
	return results


def permission_coverage_rows(filters: dict | None = None) -> list[dict]:
	frappe.only_for("System Manager")
	filters = filters or {}
	users = frappe.get_all(
		"User",
		filters={"name": ["not in", sorted(BLOCKED_USERS)]},
		fields=["name", "full_name", "enabled"],
		limit_page_length=0,
		ignore_permissions=True,
	)
	role_rows = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "parent": ["not in", sorted(BLOCKED_USERS)]},
		fields=["parent", "role"],
		limit_page_length=0,
		ignore_permissions=True,
	)
	roles = {}
	for row in role_rows:
		roles.setdefault(row.parent, []).append(row.role)
	for user in users:
		user["roles"] = roles.get(user.name, [])

	enabled_groups = set(frappe.get_all("Hero Permission Group", filters={"enabled": 1}, pluck="name"))
	memberships = {}
	for row in frappe.get_all("Hero Permission Member", fields=["parent", "user"], limit_page_length=0):
		if row.parent in enabled_groups and row.user:
			memberships.setdefault(row.user, []).append(row.parent)
	manual_counts = {}
	if frappe.get_meta("User Permission").has_field("hero_managed"):
		for row in frappe.get_all(
			"User Permission",
			or_filters=[{"hero_managed": 0}, {"hero_managed": ["is", "not set"]}],
			fields=["user"],
			limit_page_length=0,
			ignore_permissions=True,
		):
			manual_counts[row.user] = manual_counts.get(row.user, 0) + 1
	return coverage_rows(users, memberships, manual_counts, filters)


def _all_groups():
	names = frappe.get_all("Hero Permission Group", pluck="name", order_by="name asc")
	return [frappe.get_doc("Hero Permission Group", name) for name in names]


def _serialize_group(doc) -> dict:
	return {
		"name": doc.name,
		"group_name": doc.group_name,
		"enabled": as_flag(doc.enabled),
		"color": doc.color or "#2490ef",
		"description": doc.description or "",
		"member_count": doc.member_count or 0,
		"rule_count": doc.rule_count or 0,
		"sync_status": doc.sync_status or "Pending",
		"sync_summary": doc.sync_summary or "",
		"last_synced": doc.last_synced,
		"members": [
			{
				"user": row.user,
				"full_name": row.full_name or row.user,
				"user_type": row.user_type,
				"roles": [],
			}
			for row in doc.members
			if row.user
		],
		"rules": [
			{
				"name": row.name,
				"reference_doctype": row.reference_doctype,
				"for_value": row.for_value,
				"apply_to_all_doctypes": as_flag(row.apply_to_all_doctypes),
				"applicable_for": row.applicable_for or "",
				"is_default": as_flag(row.is_default),
				"hide_descendants": as_flag(row.hide_descendants),
			}
			for row in doc.rules
			if row.reference_doctype
		],
	}


def _attach_roles(groups: list[dict]):
	users = sorted({member["user"] for group in groups for member in group["members"]})
	if not users:
		return
	rows = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "parent": ["in", users]},
		fields=["parent", "role"],
		limit_page_length=0,
		ignore_permissions=True,
	)
	enabled = {
		row.name: row.enabled
		for row in frappe.get_all(
			"User",
			filters={"name": ["in", users]},
			fields=["name", "enabled"],
			limit_page_length=0,
			ignore_permissions=True,
		)
	}
	roles = {}
	for row in rows:
		roles.setdefault(row.parent, []).append(row.role)
	for group in groups:
		for member in group["members"]:
			member["roles"] = sorted(roles.get(member["user"], []))
			member["enabled"] = as_flag(enabled.get(member["user"], 1))


def _attach_role_rows(rows: list[dict]):
	if not rows:
		return
	role_rows = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "parent": ["in", [row.name for row in rows]]},
		fields=["parent", "role"],
		limit_page_length=0,
		ignore_permissions=True,
	)
	roles = {}
	for row in role_rows:
		roles.setdefault(row.parent, []).append(row.role)
	grouped = _users_in_enabled_groups()
	for row in rows:
		row["roles"] = sorted(roles.get(row.name, []))
		row["groups"] = sorted(grouped.get(row.name, []))


def _users_in_enabled_groups() -> dict:
	enabled_groups = set(frappe.get_all("Hero Permission Group", filters={"enabled": 1}, pluck="name"))
	grouped = {}
	for row in frappe.get_all("Hero Permission Member", fields=["parent", "user"], limit_page_length=0):
		if row.parent in enabled_groups and row.user:
			grouped.setdefault(row.user, []).append(row.parent)
	return grouped


def _ungrouped_users(filters: dict, grouped_users: set[str]) -> dict:
	if clean_text(filters.get("doctype")) or as_flag(filters.get("conflicts_only")):
		return {"rows": [], "total": 0}
	if clean_text(filters.get("enabled")) == "disabled":
		return {"rows": [], "total": 0}
	role = clean_text(filters.get("role"))
	query = clean_text(filters.get("search")).casefold()
	rows = frappe.get_all(
		"User",
		filters={"enabled": 1, "name": ["not in", sorted(BLOCKED_USERS)]},
		fields=["name", "full_name", "user_type", "enabled"],
		order_by="full_name asc",
		limit_page_length=0,
		ignore_permissions=True,
	)
	role_map = {}
	if rows:
		for role_row in frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "parent": ["in", [row.name for row in rows]]},
			fields=["parent", "role"],
			limit_page_length=0,
			ignore_permissions=True,
		):
			role_map.setdefault(role_row.parent, []).append(role_row.role)
	matched = []
	for row in rows:
		if row.name in grouped_users:
			continue
		roles = sorted(role_map.get(row.name, []))
		if role and role not in roles:
			continue
		haystack = f"{row.name} {row.full_name or ''}".casefold()
		if query and query not in haystack:
			continue
		row["roles"] = roles
		matched.append(row)
	return {"rows": matched[:80], "total": len(matched)}


def _enabled_user_count() -> int:
	return frappe.db.count("User", {"enabled": 1, "name": ["not in", sorted(BLOCKED_USERS)]})


def _user_list(users) -> list[str]:
	payload = parse_payload(users, [])
	if isinstance(payload, str):
		payload = [payload]
	return [clean_text(user) for user in payload if clean_text(user)]


def _conflict_messages(conflicts: list[dict], hide_conflicts: list[dict]) -> list[str]:
	messages = []
	seen_hide = set()
	for conflict in conflicts:
		values = ", ".join(
			_("{0} ({1})").format(item["for_value"], ", ".join(item["groups"])) for item in conflict["grants"]
		)
		messages.append(
			_("{0} has more than one default for {1}: {2}.").format(conflict["user"], conflict["allow"], values)
		)
	for item in hide_conflicts:
		key = (item["user"], item["allow"], item["for_value"])
		if key in seen_hide:
			continue
		seen_hide.add(key)
		messages.append(
			_("{0} has disagreeing Hide Descendants settings for {1} {2}.").format(
				item["user"], item["allow"], item["for_value"]
			)
		)
	return messages
