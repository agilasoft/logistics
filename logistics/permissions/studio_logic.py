# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Pure Permission Studio rules.

Synchronization planning, health checks, the document picker, and access
explanations live here so they can be tested without a site. The Frappe layer
is the only place that reads or writes User Permission.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

PICKER_PAGE_SIZE = 25
LIST_PAGE_SIZE = 10

STATUSES = ("In Sync", "Changes Pending", "Sync Failed", "Syncing")
CATEGORIES = ("", "Accounting", "Sales", "Operations", "Management", "Custom")
PALETTE = ("#2563eb", "#16a34a", "#7c3aed", "#d97706", "#db2777", "#0891b2")

PERMISSION_ACTIONS = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"import",
	"export",
	"print",
	"email",
	"share",
)

SEVERITY_ORDER = {"Critical": 0, "Warning": 1, "Information": 2}


def clean(value) -> str:
	return " ".join(str(value or "").split())


def truthy(value) -> bool:
	return value in (1, True, "1", "Yes", "true", "True")


def abbreviation(name: str, explicit: str | None = None) -> str:
	chosen = clean(explicit).upper()
	if chosen:
		return chosen[:3]
	words = [word for word in re.split(r"[^A-Za-z0-9]+", clean(name)) if word]
	if len(words) >= 2:
		return (words[0][0] + words[1][0]).upper()
	compact = re.sub(r"[^A-Za-z0-9]", "", clean(name))
	return (compact[:2] or "PG").upper()


def palette_color(name: str) -> str:
	digest = hashlib.sha256(clean(name).encode()).hexdigest()
	return PALETTE[int(digest[:2], 16) % len(PALETTE)]


def permission_key(row: dict) -> tuple:
	return (
		clean(row.get("user")),
		clean(row.get("allow")),
		clean(row.get("for_value")),
		clean(row.get("applicable_for")),
	)


def signature(row: dict) -> str:
	parts = [
		clean(row.get("user")),
		clean(row.get("allow")),
		clean(row.get("for_value")),
		clean(row.get("applicable_for")),
		"1" if truthy(row.get("is_default")) else "0",
		"1" if truthy(row.get("hide_descendants")) else "0",
	]
	return "|".join(parts)


def value_key(row: dict) -> tuple:
	return (
		clean(row.get("allow")),
		clean(row.get("for_value")),
		clean(row.get("applicable_for")),
	)


def desired_permissions(enabled, members, values) -> list[dict]:
	"""User Permission rows a group should own. Disabled groups own nothing."""
	if not truthy(enabled):
		return []
	rows = []
	seen = set()
	for user in members or []:
		user_name = clean(user if isinstance(user, str) else (user or {}).get("user"))
		if not user_name:
			continue
		for value in values or []:
			allow = clean(value.get("allow"))
			for_value = clean(value.get("for_value"))
			if not allow or not for_value:
				continue
			row = {
				"user": user_name,
				"allow": allow,
				"for_value": for_value,
				"applicable_for": clean(value.get("applicable_for")),
				"apply_to_all_doctypes": 0 if clean(value.get("applicable_for")) else 1,
				"is_default": 1 if truthy(value.get("is_default")) else 0,
				"hide_descendants": 1 if truthy(value.get("hide_descendants")) else 0,
			}
			row["signature"] = signature(row)
			key = permission_key(row)
			if key in seen:
				continue
			seen.add(key)
			rows.append(row)
	return rows


def config_hash(enabled, members, values) -> str:
	rows = desired_permissions(enabled, members, values)
	payload = "\n".join(sorted(row["signature"] for row in rows))
	return hashlib.sha256(payload.encode()).hexdigest()[:16]


def stored_status(sync_status: str, config_hash_value: str, synced_hash: str, last_error: str) -> str:
	if sync_status == "Syncing":
		return "Syncing"
	if (config_hash_value or "") != (synced_hash or ""):
		if last_error and sync_status == "Sync Failed":
			return "Sync Failed"
		return "Changes Pending"
	return "In Sync"


def duplicate_names(names) -> list[str]:
	seen = set()
	duplicates = []
	for name in names:
		cleaned = clean(name)
		if not cleaned:
			continue
		if cleaned in seen and cleaned not in duplicates:
			duplicates.append(cleaned)
		seen.add(cleaned)
	return duplicates


def duplicate_values(values) -> list[dict]:
	seen = set()
	duplicates = []
	for value in values or []:
		key = value_key(value)
		if not key[0] or not key[1]:
			continue
		if key in seen:
			duplicates.append(value)
		seen.add(key)
	return duplicates


def _comparable(row: dict) -> tuple:
	return (
		clean(row.get("applicable_for")),
		1 if truthy(row.get("is_default")) else 0,
		1 if truthy(row.get("hide_descendants")) else 0,
		0 if clean(row.get("applicable_for")) else 1,
	)


def plan_sync(desired, managed, manual=None) -> dict:
	"""Plan User Permission writes.

	``managed`` rows are owned by this group and may be updated or removed.
	``manual`` rows are never removed or claimed. A manual row that already
	matches a desired permission is left in place instead of creating a copy.
	"""
	desired_by_key = {}
	for row in desired or []:
		desired_by_key[permission_key(row)] = row

	managed_by_key = defaultdict(list)
	for row in managed or []:
		managed_by_key[permission_key(row)].append(row)

	manual_keys = {permission_key(row) for row in (manual or [])}

	create, update, remove, unchanged, kept_manual = [], [], [], [], []
	for key, want in desired_by_key.items():
		owned = managed_by_key.get(key) or []
		if owned:
			primary = owned[0]
			if _comparable(primary) != _comparable(want) or clean(primary.get("signature")) != clean(
				want.get("signature")
			):
				update.append({**want, "name": primary.get("name")})
			else:
				unchanged.append({**want, "name": primary.get("name")})
			for extra in owned[1:]:
				remove.append(extra)
			continue
		if key in manual_keys:
			kept_manual.append(want)
			continue
		create.append(want)

	for key, owned in managed_by_key.items():
		if key in desired_by_key:
			continue
		remove.extend(owned)

	return {
		"create": create,
		"update": update,
		"remove": remove,
		"unchanged": unchanged,
		"kept_manual": kept_manual,
		"users": sorted({row.get("user") for row in create + update + remove if row.get("user")}),
	}


def removal_is_managed(row: dict, group: str) -> bool:
	"""A delete is allowed only when the row is explicitly owned by this group."""
	return bool(clean(row.get("name"))) and clean(row.get("ps_group")) == clean(group)


def filter_groups(groups, search="", status="", category="", enabled=None, sort="modified", page=1, page_size=LIST_PAGE_SIZE):
	query = clean(search).casefold()
	status = clean(status)
	category = clean(category)
	rows = []
	for group in groups or []:
		if status and clean(group.get("sync_status")) != status:
			continue
		if category and clean(group.get("category")) != category:
			continue
		if enabled is not None and truthy(group.get("enabled")) != truthy(enabled):
			continue
		if query:
			hay = " ".join(
				[
					clean(group.get("name")),
					clean(group.get("group_name")),
					clean(group.get("description")),
					clean(group.get("abbreviation")),
				]
			).casefold()
			if query not in hay:
				continue
		rows.append(group)

	def sort_key(group):
		if sort in ("name", "group_name"):
			return (clean(group.get("group_name") or group.get("name")).casefold(),)
		if sort == "members":
			return (-int(group.get("member_count") or 0), clean(group.get("group_name")).casefold())
		return (clean(group.get("modified")), clean(group.get("name")))

	reverse = sort not in ("name", "group_name")
	if sort == "members":
		reverse = False
	rows.sort(key=sort_key, reverse=reverse)

	size = page_size if isinstance(page_size, int) and page_size > 0 else LIST_PAGE_SIZE
	current = page if isinstance(page, int) and page > 0 else 1
	start = (current - 1) * size
	return {
		"rows": rows[start : start + size],
		"total": len(rows),
		"page": current,
		"page_size": size,
		"from": start + 1 if rows else 0,
		"to": min(start + size, len(rows)),
	}


def access_summary(members, values) -> dict:
	fields = defaultdict(int)
	applicable = set()
	for value in values or []:
		allow = clean(value.get("allow"))
		if not allow:
			continue
		fields[allow] += 1
		applicable.add(clean(value.get("applicable_for")) or allow)
	return {
		"members": len([member for member in (members or []) if clean(member if isinstance(member, str) else member.get("user"))]),
		"permitted_values": len([value for value in (values or []) if clean(value.get("allow")) and clean(value.get("for_value"))]),
		"applicable_doctypes": sorted(name for name in applicable if name),
		"fields": dict(sorted(fields.items())),
		"note": (
			"These figures describe configured User Permission restrictions. "
			"They do not grant access to the listed document types."
		),
	}


def _issue(severity, code, title, detail, records=None, action=None):
	return {
		"severity": severity,
		"code": code,
		"title": title,
		"detail": detail,
		"records": records or [],
		"action": action or "",
	}


def analyze_health(groups, managed, manual, enabled_users, invalid_values, orphan_groups) -> dict:
	issues = []
	group_names = {clean(group.get("name")) for group in groups or []}

	seen = defaultdict(list)
	for row in list(managed or []) + list(manual or []):
		seen[permission_key(row)].append(row)
	duplicates = [rows for rows in seen.values() if len(rows) > 1]
	if duplicates:
		issues.append(
			_issue(
				"Warning",
				"duplicate_permissions",
				"Duplicate permissions",
				"The same user, document type, value, and applicable document type is assigned more than once.",
				records=[permission_key(rows[0]) for rows in duplicates],
			)
		)

	if invalid_values:
		issues.append(
			_issue(
				"Critical",
				"invalid_values",
				"Invalid permitted values",
				"A permitted value points at a document that does not exist.",
				records=invalid_values,
				action="open",
			)
		)

	pending = [group for group in groups or [] if clean(group.get("sync_status")) == "Changes Pending"]
	if pending:
		issues.append(
			_issue(
				"Warning",
				"unsynchronized",
				"Unsynchronized groups",
				"These groups have changes that are not written to User Permission yet.",
				records=[group.get("name") for group in pending],
				action="sync",
			)
		)

	failed = [group for group in groups or [] if clean(group.get("sync_status")) == "Sync Failed"]
	if failed:
		issues.append(
			_issue(
				"Critical",
				"sync_failed",
				"Synchronization failures",
				"The last synchronization attempt for these groups failed.",
				records=[group.get("name") for group in failed],
				action="retry",
			)
		)

	empty = [group for group in groups or [] if not (group.get("members") or [])]
	if empty:
		issues.append(
			_issue(
				"Warning",
				"empty_groups",
				"Empty permission groups",
				"These groups have no assigned users.",
				records=[group.get("name") for group in empty],
				action="open",
			)
		)

	grouped_users = set()
	for group in groups or []:
		for member in group.get("members") or []:
			name = clean(member if isinstance(member, str) else member.get("user"))
			if name:
				grouped_users.add(name)
	without = [user for user in (enabled_users or []) if clean(user) and clean(user) not in grouped_users and clean(user) != "Guest"]
	if without:
		issues.append(
			_issue(
				"Information",
				"users_without_groups",
				"Users without groups",
				"Enabled users who are not members of a permission group.",
				records=without,
				action="users",
			)
		)

	orphans = []
	for row in managed or []:
		owner = clean(row.get("ps_group"))
		if owner and owner not in group_names:
			orphans.append(row.get("name") or permission_key(row))
	for name in orphan_groups or []:
		if clean(name) and clean(name) not in group_names and clean(name) not in orphans:
			orphans.append(clean(name))
	if orphans:
		issues.append(
			_issue(
				"Warning",
				"orphaned",
				"Orphaned managed permissions",
				"These User Permissions are marked as Permission Studio records, but the group no longer exists. They were not changed.",
				records=orphans,
				action="open",
			)
		)

	allow_by_user = defaultdict(lambda: defaultdict(set))
	for group in groups or []:
		for member in group.get("members") or []:
			user = clean(member if isinstance(member, str) else member.get("user"))
			if not user:
				continue
			for value in group.get("permitted_values") or group.get("values") or []:
				allow = clean(value.get("allow"))
				if allow:
					allow_by_user[user][allow].add(group.get("name"))
	overlaps = []
	for user, allows in allow_by_user.items():
		for allow, owners in allows.items():
			if len(owners) > 1:
				overlaps.append({"user": user, "allow": allow, "groups": sorted(owners)})
	if overlaps:
		issues.append(
			_issue(
				"Information",
				"overlapping",
				"Overlapping assignments",
				"These users receive the same permission field from more than one group. This is informational unless another issue flags a conflict.",
				records=overlaps,
			)
		)

	issues.sort(key=lambda issue: (SEVERITY_ORDER.get(issue["severity"], 9), issue["title"]))
	counts = defaultdict(int)
	for issue in issues:
		counts[issue["severity"]] += 1
	return {
		"issues": issues,
		"groups_analyzed": len(groups or []),
		"managed_checked": len(managed or []),
		"issue_count": len(issues),
		"by_severity": {
			"Critical": counts["Critical"],
			"Warning": counts["Warning"],
			"Information": counts["Information"],
		},
	}


def build_matrix(groups, field="", applicable="", search="") -> dict:
	field_query = clean(field).casefold()
	applicable_query = clean(applicable).casefold()
	text = clean(search).casefold()
	columns = [clean(group.get("name")) for group in groups or []]
	by_field = {}
	for group in groups or []:
		name = clean(group.get("name"))
		for value in group.get("permitted_values") or group.get("values") or []:
			allow = clean(value.get("allow"))
			if not allow:
				continue
			if field_query and field_query not in allow.casefold():
				continue
			applicable_for = clean(value.get("applicable_for"))
			if applicable_query and applicable_query not in applicable_for.casefold() and applicable_query not in "all document types":
				continue
			for_value = clean(value.get("for_value"))
			if text and text not in for_value.casefold() and text not in allow.casefold() and text not in applicable_for.casefold():
				continue
			cell = by_field.setdefault(allow, {}).setdefault(
				name, {"configured": False, "values": []}
			)
			cell["configured"] = True
			cell["values"].append(
				{
					"for_value": for_value,
					"applicable_for": applicable_for,
					"group": name,
				}
			)
	rows = []
	for allow in sorted(by_field):
		cells = {}
		configured_flags = []
		for column in columns:
			cell = by_field[allow].get(column) or {"configured": False, "values": []}
			cells[column] = cell
			configured_flags.append(bool(cell["configured"]))
		rows.append(
			{
				"field": allow,
				"cells": cells,
				"different": len(set(configured_flags)) > 1,
			}
		)
	return {
		"columns": columns,
		"rows": rows,
		"note": (
			"A configured cell means the group stores a User Permission restriction for that field. "
			"It is not a role permission and it does not grant access to the document type."
		),
	}


def explain_access(facts: dict) -> dict:
	"""Explain a Frappe permission result without inventing a denial reason."""
	allowed = facts.get("allowed")
	doctype = clean(facts.get("doctype"))
	action = clean(facts.get("action")) or "read"
	user = clean(facts.get("user"))
	reliable = []
	suggestions = []
	evaluated = []

	if facts.get("user_enabled") is False:
		reliable.append(f"{user or 'The user'} is disabled.")
		suggestions.append("Enable the user before expecting this action to succeed.")
	elif facts.get("user_enabled") is True:
		evaluated.append("The user account is enabled.")

	if facts.get("document_exists") is False:
		reliable.append(f"{doctype} {clean(facts.get('document'))} does not exist.")
		suggestions.append("Choose a document that exists.")

	if facts.get("role_has_right") is False:
		reliable.append(f"None of the user's roles grant {action} on {doctype}.")
		suggestions.append("Grant the right in Role Permission Matrix or Role Permissions Manager.")
	elif facts.get("role_has_right") is True:
		evaluated.append(f"At least one role grants {action} on {doctype}.")

	blocks = facts.get("blocking_user_permissions") or []
	if blocks:
		for block in blocks:
			permitted = ", ".join(block.get("permitted") or []) or "none"
			reliable.append(
				f"User Permission restricts {block.get('allow')} and this document's {block.get('field')} "
				f"is {block.get('document_value')}, which is outside the permitted values ({permitted})."
			)
		suggestions.append(
			"Add the document value to a permission group for this user, or review the User Permission restriction."
		)
	elif facts.get("user_permissions_evaluated"):
		evaluated.append("Applicable User Permission restrictions were compared with the document.")

	if facts.get("has_direct_user_permissions"):
		evaluated.append("The user has User Permissions that are not managed by a group.")
	if facts.get("has_managed_user_permissions"):
		evaluated.append("The user has User Permissions managed by Permission Studio.")

	if allowed is True:
		status = "Access Allowed"
		summary = "Frappe allowed this action."
		if blocks or any(reason.startswith("None of the user's roles") for reason in reliable):
			summary = (
				"Frappe allowed this action. Role and User Permission checks were evaluated "
				"and did not deny this check."
			)
		reliable = []
	elif allowed is False:
		status = "Access Denied"
		if reliable:
			summary = " ".join(reliable)
		else:
			summary = (
				"Frappe denied this action. The checks that can be evaluated reliably "
				"did not identify a single denial reason."
			)
			suggestions.append("Review the user's roles, User Permissions, and document shares.")
	else:
		status = "Could not evaluate"
		summary = "Frappe did not return a permission result for this check."

	return {
		"status": status,
		"allowed": allowed,
		"summary": summary,
		"reliable_reasons": reliable,
		"evaluated": evaluated,
		"suggestions": _unique(suggestions),
		"role_permissions": facts.get("role_permissions") or [],
		"user_permissions": facts.get("user_permissions") or [],
	}


def user_permission_blocks(doctype, doc_links, user_permissions) -> list[dict]:
	"""Return restrictions that exclude this document.

	``doc_links`` maps a document field to ``{"doctype": link_doctype, "value": name}``.
	A restriction applies when its applicable document type is blank or matches
	``doctype``. Empty document values are not treated as a denial.
	"""
	applicable = []
	for perm in user_permissions or []:
		target = clean(perm.get("applicable_for"))
		if target:
			applies = target == clean(doctype)
		else:
			applies = truthy(perm.get("apply_to_all_doctypes", 1))
		if applies and clean(perm.get("allow")) and clean(perm.get("for_value")):
			applicable.append(perm)

	by_allow = defaultdict(set)
	for perm in applicable:
		by_allow[clean(perm.get("allow"))].add(clean(perm.get("for_value")))

	blocks = []
	for field, link in (doc_links or {}).items():
		allow = clean((link or {}).get("doctype"))
		value = clean((link or {}).get("value"))
		if allow not in by_allow or not value:
			continue
		if value not in by_allow[allow]:
			blocks.append(
				{
					"field": field,
					"allow": allow,
					"document_value": value,
					"permitted": sorted(by_allow[allow]),
				}
			)
	return blocks


def group_from_template(template: dict, group_name: str, include_members: bool = False) -> dict:
	values = []
	for value in template.get("permitted_values") or template.get("values") or []:
		if not clean(value.get("allow")) or not clean(value.get("for_value")):
			continue
		values.append(
			{
				"allow": clean(value.get("allow")),
				"for_value": clean(value.get("for_value")),
				"applicable_for": clean(value.get("applicable_for")),
				"is_default": 1 if truthy(value.get("is_default")) else 0,
				"hide_descendants": 1 if truthy(value.get("hide_descendants")) else 0,
			}
		)
	return {
		"group_name": clean(group_name),
		"description": clean(template.get("description")),
		"category": clean(template.get("category")),
		"color": clean(template.get("color")),
		"enabled": 1,
		"members": list(template.get("members") or []) if include_members else [],
		"permitted_values": values,
	}


def template_from_group(group: dict, template_name: str) -> dict:
	payload = group_from_template(
		{**group, "permitted_values": group.get("permitted_values") or group.get("values") or []},
		group.get("group_name") or "",
		include_members=False,
	)
	payload["template_name"] = clean(template_name)
	payload.pop("group_name", None)
	payload.pop("enabled", None)
	payload.pop("members", None)
	return payload


def copy_values(source_values, target_values) -> dict:
	existing = {value_key(value) for value in target_values or []}
	add = []
	skipped = []
	for value in source_values or []:
		key = value_key(value)
		if not key[0] or not key[1]:
			continue
		row = {
			"allow": key[0],
			"for_value": key[1],
			"applicable_for": key[2],
			"is_default": 1 if truthy(value.get("is_default")) else 0,
			"hide_descendants": 1 if truthy(value.get("hide_descendants")) else 0,
		}
		if key in existing:
			skipped.append(row)
			continue
		existing.add(key)
		add.append(row)
	return {"add": add, "skipped": skipped}


def bulk_member_plan(current_members, users, operation: str) -> dict:
	current = [clean(member if isinstance(member, str) else member.get("user")) for member in current_members or []]
	current = [name for name in current if name]
	wanted = [clean(user) for user in users or [] if clean(user)]
	if operation == "add_members":
		add = [user for user in wanted if user not in current]
		return {"add": add, "remove": [], "unchanged": [user for user in wanted if user in current]}
	if operation == "remove_members":
		remove = [user for user in wanted if user in current]
		missing = [user for user in wanted if user not in current]
		return {"add": [], "remove": remove, "unchanged": missing}
	raise ValueError(f"Unsupported member operation: {operation}")


def dashboard_cards(stats: dict, previous: dict | None, previous_is_earlier_day: bool) -> list[dict]:
	definitions = (
		("groups", "Permission Groups", "groups", "Open permission groups"),
		("users_in_groups", "Users in a Group", "users", "Open users assigned to a group"),
		("users_without_groups", "Users without a Group", "users_without", "Open users who have no group"),
		("managed_permissions", "User Permissions from Groups", "groups", "Open permission groups"),
		("issues", "Permission Issues", "health", "Open the health check"),
	)
	cards = []
	for key, label, target, description in definitions:
		card = {
			"key": key,
			"label": label,
			"value": int(stats.get(key) or 0),
			"target": target,
			"description": description,
		}
		if previous_is_earlier_day and previous and key in previous:
			delta = int(stats.get(key) or 0) - int(previous.get(key) or 0)
			card["delta"] = delta
		cards.append(card)
	return cards


def filter_activity(rows, query="", action="", actor="", date_from="", date_to="") -> list[dict]:
	text = clean(query).casefold()
	action = clean(action)
	actor = clean(actor).casefold()
	start = clean(date_from)
	end = clean(date_to)
	matched = []
	for row in rows or []:
		if action and clean(row.get("action")) != action:
			continue
		if actor and actor not in clean(row.get("owner") or row.get("actor")).casefold():
			continue
		created = clean(row.get("creation"))
		if start and created < start:
			continue
		if end and created[:10] > end:
			continue
		if text:
			hay = " ".join(
				[
					clean(row.get("action")),
					clean(row.get("permission_group")),
					clean(row.get("affected_record")),
					clean(row.get("details")),
					clean(row.get("previous_state")),
					clean(row.get("new_state")),
					clean(row.get("owner")),
				]
			).casefold()
			if text not in hay:
				continue
		matched.append(row)
	return matched


def _doc_name(doc) -> str:
	if isinstance(doc, str):
		return clean(doc)
	return clean((doc or {}).get("name"))


def _doc_label(doc) -> str:
	if isinstance(doc, str):
		return clean(doc)
	return clean((doc or {}).get("label") or (doc or {}).get("name"))


def _matches_query(doc: dict, query: str) -> bool:
	if not query:
		return True
	hay = " ".join(
		[
			clean(doc.get("name")),
			clean(doc.get("label")),
			clean(doc.get("description")),
		]
	).casefold()
	return query in hay


def assemble_picker(documents, selected, tagged, query="", page_size=PICKER_PAGE_SIZE) -> dict:
	"""Build the document checklist.

	Checked rows stay checked when the search is cleared because selection is
	passed in separately from the visible search page. The caller shows
	``page_size`` rows at a time and scrolls for the rest. Documents already
	tagged on another document type or group stay in the list with an indicator.
	"""
	query_text = clean(query).casefold()
	selected_docs = []
	selected_names = set()
	for item in selected or []:
		name = _doc_name(item)
		if not name or name in selected_names:
			continue
		selected_names.add(name)
		if isinstance(item, str):
			selected_docs.append({"name": name, "label": name, "tags": []})
		else:
			selected_docs.append(
				{
					"name": name,
					"label": _doc_label(item),
					"description": clean(item.get("description")),
					"tags": list(item.get("tags") or []),
				}
			)

	tags_by_name = {}
	for doc in list(tagged or []) + [doc for doc in (documents or []) if isinstance(doc, dict)]:
		name = _doc_name(doc)
		if name and doc.get("tags"):
			tags_by_name.setdefault(name, [])
			for tag in doc.get("tags") or []:
				if tag not in tags_by_name[name]:
					tags_by_name[name].append(tag)

	rows = []
	seen = set()

	def add(doc, checked, source):
		name = _doc_name(doc)
		if not name or name in seen:
			return
		if source != "selected" and not _matches_query(doc, query_text):
			return
		seen.add(name)
		tags = list(doc.get("tags") or []) if isinstance(doc, dict) else []
		for tag in tags_by_name.get(name) or []:
			if tag not in tags:
				tags.append(tag)
		rows.append(
			{
				"name": name,
				"label": _doc_label(doc) or name,
				"description": clean(doc.get("description")) if isinstance(doc, dict) else "",
				"checked": checked or name in selected_names,
				"tags": tags,
				"source": source,
			}
		)

	for doc in selected_docs:
		add(doc, True, "selected")
	for doc in tagged or []:
		add(doc, doc.get("name") in selected_names if isinstance(doc, dict) else False, "tagged")
	for doc in documents or []:
		add(doc, False, "document")

	size = page_size if isinstance(page_size, int) and page_size > 0 else PICKER_PAGE_SIZE
	return {
		"rows": rows,
		"total": len(rows),
		"selected": [doc["name"] for doc in selected_docs],
		"selected_count": len(selected_docs),
		"page_size": size,
		"viewport_rows": size,
	}


def toggle_selected(selected, document, checked: bool) -> list[dict]:
	name = _doc_name(document)
	kept = []
	seen = set()
	for item in selected or []:
		item_name = _doc_name(item)
		if not item_name or item_name == name or item_name in seen:
			continue
		seen.add(item_name)
		kept.append(item if isinstance(item, dict) else {"name": item_name, "label": item_name, "tags": []})
	if checked and name:
		payload = document if isinstance(document, dict) else {"name": name, "label": name}
		kept.append(
			{
				"name": name,
				"label": _doc_label(payload),
				"description": clean(payload.get("description")),
				"tags": list(payload.get("tags") or []),
			}
		)
	return kept


def effective_access_groups(user_permissions) -> dict:
	"""Group permitted values by the permission field for the access summary."""
	grouped = defaultdict(list)
	for perm in user_permissions or []:
		allow = clean(perm.get("allow")) or "Other"
		grouped[allow].append(
			{
				"for_value": clean(perm.get("for_value")),
				"applicable_for": clean(perm.get("applicable_for")),
				"source": clean(perm.get("source")) or ("Manual" if not clean(perm.get("ps_group")) else clean(perm.get("ps_group"))),
				"group": clean(perm.get("ps_group")),
				"managed": bool(clean(perm.get("ps_group"))),
			}
		)
	order = ["Company", "Branch", "Profit Center", "Warehouse", "Cost Center"]
	keys = [key for key in order if key in grouped]
	keys.extend(sorted(key for key in grouped if key not in order))
	return {key: grouped[key] for key in keys}


def _unique(values):
	seen = set()
	out = []
	for value in values:
		if value in seen:
			continue
		seen.add(value)
		out.append(value)
	return out
