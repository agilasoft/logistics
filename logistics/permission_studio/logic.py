# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Pure rules for permission groups.

A group is a set of users plus the document values they may access. Saving a
group materializes one Frappe User Permission per user and rule. These
functions decide what that set should be, and how it differs from the User
Permissions that already exist. They do not touch the database.
"""

from logistics.permission_studio.flags import as_flag, clean_text

BLOCKED_USERS = {"Administrator", "Guest"}


def permission_key(user, allow, for_value, apply_to_all, applicable_for) -> tuple:
	apply_all = as_flag(apply_to_all)
	applicable = "" if apply_all else clean_text(applicable_for)
	return (
		clean_text(user),
		clean_text(allow),
		clean_text(for_value),
		apply_all,
		applicable,
	)


def rule_key(rule: dict) -> tuple:
	return permission_key(
		"",
		rule.get("reference_doctype"),
		rule.get("for_value"),
		rule.get("apply_to_all_doctypes", 1),
		rule.get("applicable_for"),
	)[1:]


def scopes_overlap(left: dict, right: dict) -> bool:
	"""Frappe treats two defaults as overlapping when either one applies everywhere."""
	if as_flag(left.get("apply_to_all_doctypes")) or as_flag(right.get("apply_to_all_doctypes")):
		return True
	return clean_text(left.get("applicable_for")) == clean_text(right.get("applicable_for"))


def requested_group_name(current_name, requested_name) -> str | None:
	"""Return the document name a rename should use.

	``None`` means the name stays as it is: the caller omitted a name, or sent
	the name the document already has. An empty string means the request is
	blank and should be rejected.
	"""
	if requested_name is None:
		return None
	requested = clean_text(requested_name)
	if not requested:
		return ""
	if requested == clean_text(current_name):
		return None
	return requested


def validate_group_shape(group: dict) -> list[str]:
	"""Return human-readable problems with a group. An empty list means it can be saved."""
	errors = []
	name = clean_text(group.get("group_name") or group.get("name"))
	if not name:
		errors.append("Group name is required.")

	color = clean_text(group.get("color"))
	if color and not (len(color) == 7 and color.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in color[1:])):
		errors.append("Color must be a hex value like #2490ef.")

	seen_users = set()
	for member in group.get("members") or []:
		user = clean_text(member.get("user"))
		if not user:
			errors.append("Every member needs a user.")
			continue
		if user in BLOCKED_USERS:
			errors.append(f"{user} cannot be added to a permission group.")
			continue
		folded = user.casefold()
		if folded in seen_users:
			errors.append(f"{user} is listed more than once.")
		seen_users.add(folded)

	seen_rules = {}
	for rule in group.get("rules") or []:
		doctype = clean_text(rule.get("reference_doctype"))
		value = clean_text(rule.get("for_value"))
		apply_all = as_flag(rule.get("apply_to_all_doctypes", 1))
		applicable = "" if apply_all else clean_text(rule.get("applicable_for"))
		if not doctype or not value:
			errors.append("Every permission needs a DocType and a value.")
			continue
		if not apply_all and not applicable:
			errors.append(f"{doctype} {value} needs Applicable For, or it should apply to all document types.")
			continue
		key = (doctype, value, apply_all, applicable)
		previous = seen_rules.get(key)
		if previous is not None:
			if as_flag(previous.get("hide_descendants")) != as_flag(rule.get("hide_descendants")):
				errors.append(
					f"Hide descendants disagrees on duplicate permission {doctype} {value}."
				)
			else:
				errors.append(f"Duplicate permission for {doctype} {value}.")
			continue
		seen_rules[key] = rule

	return errors


def collect_grants(groups: list[dict]) -> tuple[dict, list[dict]]:
	"""Build the User Permissions enabled groups ask for.

	Returns ``(grants, hide_conflicts)``. Grants are keyed by
	``(user, doctype, value, apply_all, applicable_for)``.
	"""
	grants = {}
	hide_conflicts = []
	for group in groups:
		if not as_flag(group.get("enabled", 1)):
			continue
		group_name = clean_text(group.get("name") or group.get("group_name"))
		rules = group.get("rules") or []
		for member in group.get("members") or []:
			user = clean_text(member.get("user"))
			if not user or user in BLOCKED_USERS:
				continue
			for rule in rules:
				doctype = clean_text(rule.get("reference_doctype"))
				value = clean_text(rule.get("for_value"))
				if not doctype or not value:
					continue
				apply_all = as_flag(rule.get("apply_to_all_doctypes", 1))
				applicable = "" if apply_all else clean_text(rule.get("applicable_for"))
				if not apply_all and not applicable:
					continue
				key = (user, doctype, value, apply_all, applicable)
				hide = as_flag(rule.get("hide_descendants"))
				default = as_flag(rule.get("is_default"))
				current = grants.get(key)
				if current is None:
					grants[key] = {
						"user": user,
						"allow": doctype,
						"for_value": value,
						"apply_to_all_doctypes": apply_all,
						"applicable_for": applicable or None,
						"is_default": default,
						"hide_descendants": hide,
						"groups": [group_name],
					}
					continue
				if group_name not in current["groups"]:
					current["groups"].append(group_name)
				if current["hide_descendants"] != hide:
					hide_conflicts.append(
						{
							"user": user,
							"allow": doctype,
							"for_value": value,
							"groups": list(current["groups"]),
						}
					)
				current["is_default"] = 1 if current["is_default"] or default else 0

	for grant in grants.values():
		grant["groups"] = sorted(grant["groups"])
	return grants, hide_conflicts


def default_conflicts(grants: dict) -> list[dict]:
	"""More than one default for the same user and DocType, where the scopes overlap."""
	by_user_doctype = {}
	for grant in grants.values():
		if not grant.get("is_default"):
			continue
		by_user_doctype.setdefault((grant["user"], grant["allow"]), []).append(grant)

	conflicts = []
	for (user, allow), items in by_user_doctype.items():
		if len(items) < 2:
			continue
		involved = []
		for item in items:
			if any(other is not item and scopes_overlap(item, other) for other in items):
				involved.append(item)
		# Same value granted twice is one grant already. Different values conflict.
		distinct_values = {(item["for_value"], clean_text(item.get("applicable_for"))) for item in involved}
		if len(distinct_values) > 1:
			conflicts.append(
				{
					"user": user,
					"allow": allow,
					"grants": [
						{
							"for_value": item["for_value"],
							"applicable_for": item.get("applicable_for") or "",
							"groups": list(item["groups"]),
						}
						for item in involved
					],
				}
			)
	conflicts.sort(key=lambda row: (row["user"], row["allow"]))
	return conflicts


def diff_permissions(desired: dict, managed_rows: list[dict], manual_rows: list[dict]) -> dict:
	"""Compare desired grants with User Permission rows.

	Managed rows are the ones Permission Studio created. Manual rows are left in
	place. A desired grant that matches a manual row is reported as an overlap
	and is not created again.
	"""
	managed_by_key = {}
	for row in managed_rows:
		managed_by_key[_row_key(row)] = row
	manual_keys = {_row_key(row) for row in manual_rows}

	to_create = []
	to_update = []
	manual_overlaps = []

	for key, grant in desired.items():
		groups_text = ", ".join(grant["groups"])
		primary = grant["groups"][0] if grant["groups"] else None
		if key in managed_by_key:
			current = managed_by_key[key]
			changes = {}
			if as_flag(current.get("is_default")) != as_flag(grant["is_default"]):
				changes["is_default"] = grant["is_default"]
			if as_flag(current.get("hide_descendants")) != as_flag(grant["hide_descendants"]):
				changes["hide_descendants"] = grant["hide_descendants"]
			if clean_text(current.get("hero_permission_group")) != clean_text(primary):
				changes["hero_permission_group"] = primary
			if clean_text(current.get("hero_source_groups")) != groups_text:
				changes["hero_source_groups"] = groups_text
			if changes:
				to_update.append({"name": current["name"], "changes": changes, "grant": grant})
		elif key in manual_keys:
			manual_overlaps.append(grant)
		else:
			to_create.append(grant)

	to_delete = [
		row["name"] for key, row in managed_by_key.items() if key not in desired and row.get("name")
	]
	return {
		"to_create": to_create,
		"to_update": to_update,
		"to_delete": to_delete,
		"manual_overlaps": manual_overlaps,
	}


def blocked_defaults(grants: dict, existing_defaults: list[dict]) -> list[dict]:
	"""Defaults we must not write because some other User Permission already holds them.

	``existing_defaults`` rows use the same fields as a grant, plus optional ``name``.
	A row whose name is ``existing_name`` on the grant is the grant itself and is ignored.
	"""
	blocked = []
	for grant in grants.values():
		if not grant.get("is_default"):
			continue
		for other in existing_defaults:
			if clean_text(other.get("user")) != grant["user"] or clean_text(other.get("allow")) != grant["allow"]:
				continue
			if other.get("name") and other.get("name") == grant.get("existing_name"):
				continue
			# The same key is this grant's own row, or a manual overlap we will not write.
			if permission_key(
				other.get("user"),
				other.get("allow"),
				other.get("for_value"),
				other.get("apply_to_all_doctypes"),
				other.get("applicable_for"),
			) == permission_key(
				grant["user"],
				grant["allow"],
				grant["for_value"],
				grant["apply_to_all_doctypes"],
				grant.get("applicable_for"),
			):
				continue
			if scopes_overlap(grant, other) and as_flag(other.get("is_default")):
				blocked.append(grant)
				break
	return blocked


def matrix_for(group: dict) -> dict:
	"""Users down the side, DocTypes across the top, permitted values in the cells."""
	doctypes = []
	for rule in group.get("rules") or []:
		doctype = clean_text(rule.get("reference_doctype"))
		if doctype and doctype not in doctypes:
			doctypes.append(doctype)
	rows = []
	for member in group.get("members") or []:
		user = clean_text(member.get("user"))
		cells = {doctype: [] for doctype in doctypes}
		for rule in group.get("rules") or []:
			doctype = clean_text(rule.get("reference_doctype"))
			if doctype not in cells:
				continue
			cells[doctype].append(
				{
					"value": clean_text(rule.get("for_value")),
					"is_default": as_flag(rule.get("is_default")),
					"applicable_for": clean_text(rule.get("applicable_for")),
					"apply_to_all_doctypes": as_flag(rule.get("apply_to_all_doctypes", 1)),
					"hide_descendants": as_flag(rule.get("hide_descendants")),
				}
			)
		rows.append(
			{
				"user": user,
				"full_name": clean_text(member.get("full_name")) or user,
				"cells": cells,
			}
		)
	return {"doctypes": doctypes, "rows": rows}


def group_matches(group: dict, filters: dict, conflicted_names: set[str]) -> bool:
	"""Whether a group card should stay visible for the current filters."""
	filters = filters or {}
	enabled = filters.get("enabled") or "all"
	if enabled == "enabled" and not as_flag(group.get("enabled", 1)):
		return False
	if enabled == "disabled" and as_flag(group.get("enabled", 1)):
		return False
	if as_flag(filters.get("conflicts_only")) and group.get("name") not in conflicted_names:
		return False

	role = clean_text(filters.get("role"))
	if role:
		member_roles = set()
		for member in group.get("members") or []:
			member_roles.update(member.get("roles") or [])
		if role not in member_roles:
			return False

	doctype = clean_text(filters.get("doctype"))
	if doctype:
		rule_doctypes = {clean_text(rule.get("reference_doctype")) for rule in group.get("rules") or []}
		if doctype not in rule_doctypes:
			return False

	query = clean_text(filters.get("search")).casefold()
	if not query:
		return True
	parts = [group.get("name"), group.get("description"), group.get("sync_status")]
	for member in group.get("members") or []:
		parts.extend([member.get("user"), member.get("full_name")])
	for rule in group.get("rules") or []:
		parts.extend(
			[rule.get("reference_doctype"), rule.get("for_value"), rule.get("applicable_for")]
		)
	haystack = " ".join(clean_text(part) for part in parts).casefold()
	return query in haystack


def coverage_rows(users: list[dict], memberships: dict, manual_counts: dict, filters: dict | None = None) -> list[dict]:
	"""Rows for the Permission Coverage report."""
	filters = filters or {}
	role = clean_text(filters.get("role"))
	coverage = clean_text(filters.get("coverage"))
	enabled_only = as_flag(filters.get("enabled_only", 1))
	rows = []
	for user in users:
		name = user.get("name")
		if name in BLOCKED_USERS:
			continue
		if enabled_only and not as_flag(user.get("enabled", 1)):
			continue
		roles = list(user.get("roles") or [])
		if role and role not in roles:
			continue
		groups = list(memberships.get(name) or [])
		manual = int(manual_counts.get(name) or 0)
		in_group = bool(groups)
		if coverage == "In a group" and not in_group:
			continue
		if coverage == "Not in a group" and in_group:
			continue
		if coverage == "Has manual permissions" and manual <= 0:
			continue
		rows.append(
			{
				"user": name,
				"full_name": user.get("full_name") or name,
				"enabled": as_flag(user.get("enabled", 1)),
				"groups": ", ".join(groups),
				"group_count": len(groups),
				"manual_permissions": manual,
				"in_group": "Yes" if in_group else "No",
			}
		)
	rows.sort(key=lambda row: ((row.get("full_name") or "").casefold(), row["user"]))
	return rows


def _row_key(row: dict) -> tuple:
	return permission_key(
		row.get("user"),
		row.get("allow"),
		row.get("for_value"),
		row.get("apply_to_all_doctypes"),
		row.get("applicable_for"),
	)
