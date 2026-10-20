# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Write Permission Studio groups into Frappe User Permissions.

The group is the source of truth. Each enabled member combined with each rule
becomes one User Permission. Rows this app created are updated or removed when
the groups change. Rows a person created by hand are left alone, and the group
is marked Needs Attention so the overlap is visible.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.exceptions import DuplicateEntryError

from logistics.permission_studio.logic import (
	blocked_defaults,
	collect_grants,
	default_conflicts,
	diff_permissions,
)

PERMISSION_FIELDS = [
	"name",
	"user",
	"allow",
	"for_value",
	"apply_to_all_doctypes",
	"applicable_for",
	"is_default",
	"hide_descendants",
	"hero_managed",
	"hero_permission_group",
	"hero_source_groups",
]


def reconcile(exclude_groups: set[str] | None = None) -> dict:
	"""Rebuild managed User Permissions from every permission group."""
	_require_fields()
	exclude_groups = set(exclude_groups or [])
	group_docs = _load_groups(exclude_groups)
	payloads = [_group_dict(doc) for doc in group_docs]
	grants, hide_conflicts = collect_grants(payloads)
	if hide_conflicts or default_conflicts(grants):
		frappe.throw(
			_("Fix the default and Hide Descendants conflicts before syncing."),
			title=_("Permission groups disagree"),
		)

	manual_rows = _permission_rows(managed=0)
	managed_rows = _permission_rows(managed=1)
	manual_defaults = [row for row in manual_rows if row.get("is_default")]
	for grant in blocked_defaults(grants, manual_defaults):
		grant["is_default"] = 0
		grant["default_blocked"] = 1

	diff = diff_permissions(grants, managed_rows, manual_rows)
	_apply(diff)

	attention = _attention(diff, grants)
	for doc in group_docs:
		_write_status(doc, grants, attention)
	return {"grants": len(grants), "diff": {key: len(diff[key]) for key in diff}}


def _require_fields():
	if frappe.get_meta("User Permission").has_field("hero_managed"):
		return
	frappe.throw(
		_("Run bench migrate so Permission Studio can mark the User Permissions it owns."),
		title=_("Migrate required"),
	)


def _load_groups(exclude_groups: set[str]):
	names = frappe.get_all("Hero Permission Group", pluck="name")
	docs = []
	for name in names:
		if name in exclude_groups:
			continue
		docs.append(frappe.get_doc("Hero Permission Group", name))
	return docs


def _group_dict(doc) -> dict:
	return {
		"name": doc.name,
		"group_name": doc.group_name,
		"enabled": doc.enabled,
		"members": [{"user": row.user, "full_name": row.full_name} for row in doc.members if row.user],
		"rules": [
			{
				"reference_doctype": row.reference_doctype,
				"for_value": row.for_value,
				"apply_to_all_doctypes": row.apply_to_all_doctypes,
				"applicable_for": row.applicable_for,
				"is_default": row.is_default,
				"hide_descendants": row.hide_descendants,
			}
			for row in doc.rules
			if row.reference_doctype and row.for_value
		],
	}


def _permission_rows(managed: int) -> list[dict]:
	# A newly added checkbox can be NULL on existing rows. Those are manual.
	if managed:
		filters = {"hero_managed": 1}
		or_filters = None
	else:
		filters = None
		or_filters = [{"hero_managed": 0}, {"hero_managed": ["is", "not set"]}]
	return frappe.get_all(
		"User Permission",
		filters=filters,
		or_filters=or_filters,
		fields=PERMISSION_FIELDS,
		limit_page_length=0,
		ignore_permissions=True,
	)


def _apply(diff: dict):
	early = []
	middle = []
	late = []
	for item in diff["to_update"]:
		if item["changes"].get("is_default") == 0:
			early.append(item)
		elif item["changes"].get("is_default") == 1:
			late.append(item)
		else:
			middle.append(item)

	for item in early:
		_update_permission(item)
	for name in diff["to_delete"]:
		_delete_permission(name)
	for item in middle:
		_update_permission(item)
	for grant in diff["to_create"]:
		if not grant.get("is_default"):
			_create_permission(grant)
	for grant in diff["to_create"]:
		if grant.get("is_default"):
			_create_permission(grant)
	for item in late:
		_update_permission(item)


def _create_permission(grant: dict):
	doc = frappe.new_doc("User Permission")
	doc.flags.hero_sync = True
	doc.user = grant["user"]
	doc.allow = grant["allow"]
	doc.for_value = grant["for_value"]
	doc.apply_to_all_doctypes = grant["apply_to_all_doctypes"]
	doc.applicable_for = None if grant["apply_to_all_doctypes"] else grant["applicable_for"]
	doc.is_default = grant["is_default"]
	doc.hide_descendants = grant["hide_descendants"]
	doc.hero_managed = 1
	doc.hero_permission_group = grant["groups"][0]
	doc.hero_source_groups = ", ".join(grant["groups"])
	try:
		doc.insert(ignore_permissions=True)
	except DuplicateEntryError:
		grant["duplicate"] = 1


def _update_permission(item: dict):
	doc = frappe.get_doc("User Permission", item["name"])
	doc.flags.hero_sync = True
	for fieldname, value in item["changes"].items():
		doc.set(fieldname, value)
	doc.save(ignore_permissions=True)


def _delete_permission(name: str):
	if frappe.db.exists("User Permission", name):
		frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)


def _attention(diff: dict, grants: dict) -> dict:
	notes = defaultdict(list)
	overlaps = defaultdict(int)
	blocked = defaultdict(int)
	duplicates = defaultdict(int)
	for grant in diff["manual_overlaps"]:
		for name in grant["groups"]:
			overlaps[name] += 1
	for grant in diff["to_create"]:
		if grant.get("duplicate"):
			for name in grant["groups"]:
				duplicates[name] += 1
	for grant in grants.values():
		if grant.get("default_blocked"):
			for name in grant["groups"]:
				blocked[name] += 1
	for name, count in overlaps.items():
		notes[name].append(
			_("{0} permission(s) already exist as manual User Permissions and were left unchanged.").format(count)
		)
	for name, count in duplicates.items():
		notes[name].append(
			_("{0} permission(s) already existed and were not created again.").format(count)
		)
	for name, count in blocked.items():
		notes[name].append(
			_("{0} default(s) were not applied because another default is already set.").format(count)
		)
	return notes


def _write_status(doc, grants: dict, attention: dict):
	owned = sum(1 for grant in grants.values() if doc.name in grant["groups"])
	messages = list(attention.get(doc.name) or [])
	if not doc.enabled:
		summary = _("Disabled. This group does not grant any User Permissions.")
		status = "Needs Attention" if messages else "In Sync"
	elif messages:
		summary = " ".join(messages)
		status = "Needs Attention"
	else:
		summary = _("In sync. {0} User Permission(s) come from this group.").format(owned)
		status = "In Sync"
	if messages and doc.enabled:
		summary = _("{0} User Permission(s) come from this group. {1}").format(owned, " ".join(messages))
	frappe.db.set_value(
		"Hero Permission Group",
		doc.name,
		{
			"sync_status": status,
			"sync_summary": summary,
			"last_synced": frappe.utils.now(),
		},
		update_modified=False,
	)

