# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Frappe integration for Permission Studio.

User Permission remains the authorization record. This module only creates,
updates, and deletes rows that carry the Permission Group ownership field.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_first_day, now, nowdate

from logistics.permissions.studio_logic import (
	LIST_PAGE_SIZE,
	PERMISSION_ACTIONS,
	PICKER_PAGE_SIZE,
	access_summary,
	analyze_health,
	bulk_member_plan,
	build_matrix,
	clean,
	config_hash,
	copy_values,
	dashboard_cards,
	desired_permissions,
	effective_access_groups,
	explain_access,
	filter_activity,
	filter_groups,
	group_from_template,
	plan_sync,
	removal_is_managed,
	template_from_group,
	user_permission_blocks,
)

OWNERSHIP_FIELDS = {
	"User Permission": [
		{
			"fieldname": "ps_group",
			"label": "Permission Group",
			"fieldtype": "Link",
			"options": "Permission Group",
			"insert_after": "apply_to_all_doctypes",
			"read_only": 1,
			"no_copy": 1,
			"search_index": 1,
			"description": "Set when Permission Studio owns this User Permission. Blank rows are never changed by sync.",
		},
		{
			"fieldname": "ps_signature",
			"label": "Permission Studio Signature",
			"fieldtype": "Data",
			"insert_after": "ps_group",
			"read_only": 1,
			"hidden": 1,
			"no_copy": 1,
		},
	]
}


def require_manager():
	frappe.only_for("System Manager")


def ensure_ownership_fields() -> bool:
	if not frappe.db.table_exists("User Permission"):
		return False
	if frappe.db.has_column("User Permission", "ps_group") and frappe.db.has_column(
		"User Permission", "ps_signature"
	):
		return True
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(OWNERSHIP_FIELDS, update=True)
	frappe.clear_cache(doctype="User Permission")
	return bool(frappe.db.has_column("User Permission", "ps_group"))


def get_settings() -> dict:
	require_manager()
	return _settings()


def save_settings(list_page_size=LIST_PAGE_SIZE, picker_page_size=PICKER_PAGE_SIZE):
	require_manager()
	doc = frappe.get_single("Permission Studio Settings")
	doc.list_page_size = cint(list_page_size) or LIST_PAGE_SIZE
	doc.picker_page_size = cint(picker_page_size) or PICKER_PAGE_SIZE
	doc.save(ignore_permissions=True)
	return _settings()


def get_dashboard():
	require_manager()
	stats = _stats()
	previous, earlier = _previous_snapshot()
	cards = dashboard_cards(stats, previous, earlier)
	_record_snapshot(stats)
	return {"cards": cards, "generated": now(), "stats": stats}


def list_groups(search="", status="", category="", enabled=None, sort="modified", page=1, page_size=None):
	require_manager()
	groups = _group_rows()
	enabled_filter = None if enabled in (None, "", "all") else cint(enabled)
	size = cint(page_size) or _settings()["list_page_size"]
	return filter_groups(
		groups,
		search=search or "",
		status=status or "",
		category=category or "",
		enabled=enabled_filter,
		sort=sort or "modified",
		page=cint(page) or 1,
		page_size=size,
	)


def get_group(name: str):
	require_manager()
	doc = frappe.get_doc("Permission Group", name)
	group = _public_group(doc)
	group["activity"] = list_activity(group=name, limit=30)
	group["summary"] = access_summary(group["members"], group["permitted_values"])
	group["sync_preview"] = preview_sync([name])["groups"][0]
	return group


def save_group(payload):
	require_manager()
	data = _payload(payload)
	name = clean(data.get("name") or data.get("group_name"))
	exists = bool(name and frappe.db.exists("Permission Group", name))
	previous = _public_group(frappe.get_doc("Permission Group", name)) if exists else None
	doc = frappe.get_doc("Permission Group", name) if exists else frappe.new_doc("Permission Group")
	if not exists:
		doc.group_name = clean(data.get("group_name") or name)
	elif clean(data.get("group_name")) and clean(data.get("group_name")) != doc.group_name:
		frappe.throw(_("Group name stays as {0}. Create a new group to use another name.").format(doc.group_name))
	for field in ("description", "category", "color", "abbreviation"):
		if field in data:
			doc.set(field, data.get(field))
	if "enabled" in data:
		doc.enabled = 1 if cint(data.get("enabled")) else 0
	if "members" in data:
		doc.set("members", [])
		for user in data.get("members") or []:
			user_name = clean(user if isinstance(user, str) else (user or {}).get("user"))
			if user_name:
				doc.append("members", {"user": user_name})
	if "permitted_values" in data or "values" in data:
		doc.set("permitted_values", [])
		for value in data.get("permitted_values") or data.get("values") or []:
			doc.append("permitted_values", _value_row(value))
	doc.save(ignore_permissions=True)
	log_activity(
		"Group Updated" if exists else "Group Created",
		group=doc.name,
		previous=previous,
		new=_public_group(doc),
		result="Success",
	)
	return _public_group(doc)


def delete_group(name: str):
	require_manager()
	if not frappe.db.exists("Permission Group", name):
		frappe.throw(_("Permission Group {0} does not exist.").format(name))
	previous = _public_group(frappe.get_doc("Permission Group", name))
	removal = remove_managed_permissions(name)
	if removal.get("errors"):
		frappe.throw(
			_("Could not remove managed User Permissions: {0}").format(
				"; ".join(item["error"] for item in removal["errors"])
			)
		)
	frappe.delete_doc("Permission Group", name, ignore_permissions=True, force=True)
	log_activity(
		"Group Deleted",
		affected=name,
		previous=previous,
		new={"removed_user_permissions": removal.get("removed") or []},
		result="Success",
	)
	return {"deleted": name, "removed_user_permissions": removal.get("removed") or []}


def set_enabled(name: str, enabled: int):
	require_manager()
	doc = frappe.get_doc("Permission Group", name)
	previous = doc.enabled
	doc.enabled = 1 if cint(enabled) else 0
	doc.save(ignore_permissions=True)
	log_activity(
		"Group Enabled" if doc.enabled else "Group Disabled",
		group=doc.name,
		previous={"enabled": previous},
		new={"enabled": doc.enabled},
	)
	return _public_group(doc)


def preview_sync(names=None):
	require_manager()
	ensure_ownership_fields()
	selected = _group_names(names)
	groups = []
	for name in selected:
		doc = frappe.get_doc("Permission Group", name)
		plan = _plan_for_doc(doc)
		groups.append(
			{
				"group": name,
				"create": len(plan["create"]),
				"update": len(plan["update"]),
				"remove": len(plan["remove"]),
				"unchanged": len(plan["unchanged"]),
				"kept_manual": plan["kept_manual"],
				"users": plan["users"],
				"status": doc.sync_status,
			}
		)
	return {
		"groups": groups,
		"create": sum(item["create"] for item in groups),
		"update": sum(item["update"] for item in groups),
		"remove": sum(item["remove"] for item in groups),
		"users": sorted({user for item in groups for user in item["users"]}),
	}


def sync_groups(names=None):
	require_manager()
	if not ensure_ownership_fields():
		frappe.throw(_("User Permission ownership fields could not be created, so nothing was synchronized."))
	results = []
	for name in _group_names(names):
		results.append(sync_group(name))
	failed = [item for item in results if not item.get("ok")]
	return {
		"results": results,
		"ok": not failed,
		"failed": [item.get("group") for item in failed],
	}


def sync_group(name: str) -> dict:
	require_manager()
	doc = frappe.get_doc("Permission Group", name)
	expected_hash = doc.config_hash or config_hash(doc.enabled, _member_names(doc), _value_dicts(doc))
	frappe.db.set_value("Permission Group", name, "sync_status", "Syncing", update_modified=False)
	log_activity("Sync Started", group=name, result="Information")
	plan = _plan_for_doc(doc)
	errors = []
	created, updated, removed = [], [], []
	for row in plan["create"]:
		try:
			created.append(_create_user_permission(row, name))
		except Exception as exc:
			errors.append({"operation": "create", "record": _record_label(row), "error": _error_text(exc)})
	for row in plan["update"]:
		try:
			updated.append(_update_user_permission(row, name))
		except Exception as exc:
			errors.append({"operation": "update", "record": row.get("name") or _record_label(row), "error": _error_text(exc)})
	for row in plan["remove"]:
		try:
			removed.append(_delete_user_permission(row, name))
		except Exception as exc:
			errors.append({"operation": "remove", "record": row.get("name"), "error": _error_text(exc)})
	current_hash = frappe.db.get_value("Permission Group", name, "config_hash")
	if errors:
		message = "; ".join(f"{item['operation']}: {item['record']}: {item['error']}" for item in errors)[:1000]
		frappe.db.set_value(
			"Permission Group",
			name,
			{"sync_status": "Sync Failed", "last_sync_error": message, "last_sync": now(), "last_sync_by": frappe.session.user},
			update_modified=False,
		)
		log_activity("Sync Failed", group=name, new=errors, result="Failed", details=message)
		return {"ok": False, "group": name, "errors": errors, "created": created, "updated": updated, "removed": removed}
	status = "In Sync" if current_hash == expected_hash else "Changes Pending"
	values = {
		"sync_status": status,
		"last_sync_error": "",
		"last_sync": now(),
		"last_sync_by": frappe.session.user,
	}
	if status == "In Sync":
		values["synced_hash"] = expected_hash
	frappe.db.set_value("Permission Group", name, values, update_modified=False)
	log_activity(
		"Sync Succeeded",
		group=name,
		new={"created": created, "updated": updated, "removed": removed, "kept_manual": len(plan["kept_manual"])},
		result="Success",
	)
	return {
		"ok": True,
		"group": name,
		"created": created,
		"updated": updated,
		"removed": removed,
		"kept_manual": plan["kept_manual"],
		"status": status,
	}


def remove_managed_permissions(group: str) -> dict:
	"""Delete User Permissions owned by this group. Manual rows are not read."""
	if not frappe.db.table_exists("User Permission") or not frappe.db.has_column("User Permission", "ps_group"):
		return {"removed": [], "errors": []}
	names = frappe.get_all("User Permission", filters={"ps_group": group}, pluck="name", limit_page_length=0)
	removed, errors = [], []
	for name in names:
		owner = frappe.db.get_value("User Permission", name, "ps_group")
		row = {"name": name, "ps_group": owner}
		if not removal_is_managed(row, group):
			continue
		try:
			frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)
			removed.append(name)
		except Exception as exc:
			errors.append({"name": name, "error": _error_text(exc)})
	return {"removed": removed, "errors": errors}


def list_users(search="", assignment="all", page=1, page_size=20):
	require_manager()
	users = frappe.get_all(
		"User",
		filters={"name": ["!=", "Guest"]},
		fields=["name", "full_name", "email", "enabled", "user_type"],
		order_by="full_name asc",
		limit_page_length=0,
	)
	membership = {}
	if frappe.db.table_exists("Permission Group Member"):
		for row in frappe.get_all(
			"Permission Group Member", fields=["user", "parent"], limit_page_length=0
		):
			membership.setdefault(row.user, []).append(row.parent)
	query = clean(search).casefold()
	rows = []
	for user in users:
		groups = sorted(set(membership.get(user.name) or []))
		if assignment == "grouped" and not groups:
			continue
		if assignment == "ungrouped" and (groups or not user.enabled):
			continue
		if query and query not in " ".join([user.name or "", user.full_name or "", user.email or ""]).casefold():
			continue
		rows.append(
			{
				"name": user.name,
				"full_name": user.full_name,
				"email": user.email,
				"enabled": user.enabled,
				"user_type": user.user_type,
				"groups": groups,
			}
		)
	size = cint(page_size) or 20
	current = cint(page) or 1
	start = (current - 1) * size
	page_rows = rows[start : start + size]
	_attach_permission_counts(page_rows)
	return {"rows": page_rows, "total": len(rows), "page": current, "page_size": size}


def get_user_access(user: str):
	require_manager()
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} does not exist.").format(user))
	info = frappe.db.get_value(
		"User", user, ["name", "full_name", "email", "enabled", "user_type"], as_dict=True
	)
	groups = []
	if frappe.db.table_exists("Permission Group Member"):
		groups = frappe.get_all("Permission Group Member", filters={"user": user}, pluck="parent")
	permissions = _user_permissions(user)
	for perm in permissions:
		perm["source"] = perm.get("ps_group") or "Manual"
	return {
		"user": info,
		"roles": frappe.get_roles(user),
		"groups": sorted(set(groups)),
		"direct": [perm for perm in permissions if not perm.get("ps_group")],
		"managed": [perm for perm in permissions if perm.get("ps_group")],
		"summary": effective_access_groups(permissions),
		"note": "Grouped values are User Permission restrictions and their source. They are not role grants.",
	}


def check_access(user: str, doctype: str, document: str | None = None, action: str = "read"):
	require_manager()
	action = clean(action) or "read"
	if action not in PERMISSION_ACTIONS:
		frappe.throw(_("Unsupported permission action."))
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} does not exist.").format(user))
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("Document type {0} does not exist.").format(doctype))
	user_enabled = bool(frappe.db.get_value("User", user, "enabled"))
	document_exists = None
	doc = None
	if clean(document):
		document_exists = bool(frappe.db.exists(doctype, document))
		if document_exists:
			doc = frappe.get_doc(doctype, document)
	meta = frappe.get_meta(doctype)
	roles = set(frappe.get_roles(user))
	role_permissions = []
	role_has_right = False
	for rule in meta.permissions or []:
		if rule.role not in roles:
			continue
		granted = bool(rule.get(action))
		role_permissions.append(
			{
				"role": rule.role,
				"permlevel": rule.permlevel,
				"if_owner": rule.if_owner,
				"granted": granted,
			}
		)
		if granted and not cint(rule.if_owner) and cint(rule.permlevel) == 0:
			role_has_right = True
	allowed = None
	try:
		if doc is not None:
			allowed = bool(frappe.has_permission(doctype, ptype=action, doc=doc, user=user))
		else:
			allowed = bool(frappe.has_permission(doctype, ptype=action, user=user))
	except Exception:
		allowed = None
	permissions = _user_permissions(user)
	doc_links = {}
	if doc is not None:
		for field in meta.fields:
			if field.fieldtype == "Link" and field.options:
				doc_links[field.fieldname] = {"doctype": field.options, "value": doc.get(field.fieldname)}
	blocks = user_permission_blocks(doctype, doc_links, permissions) if doc is not None else []
	facts = {
		"allowed": allowed,
		"user": user,
		"doctype": doctype,
		"document": document,
		"action": action,
		"user_enabled": user_enabled,
		"document_exists": document_exists,
		"role_has_right": role_has_right,
		"role_permissions": role_permissions,
		"user_permissions": [
			{
				"allow": perm.get("allow"),
				"for_value": perm.get("for_value"),
				"applicable_for": perm.get("applicable_for"),
				"source": perm.get("ps_group") or "Manual",
			}
			for perm in permissions
		],
		"blocking_user_permissions": blocks,
		"user_permissions_evaluated": doc is not None,
		"has_direct_user_permissions": any(not perm.get("ps_group") for perm in permissions),
		"has_managed_user_permissions": any(perm.get("ps_group") for perm in permissions),
	}
	result = explain_access(facts)
	result["action"] = action
	result["doctype"] = doctype
	result["document"] = document or ""
	result["user"] = user
	return result


def get_matrix(groups=None, field="", applicable="", search=""):
	require_manager()
	selected = _group_names(groups)
	payload = []
	for name in selected:
		doc = frappe.get_doc("Permission Group", name)
		payload.append({"name": doc.name, "permitted_values": _value_dicts(doc)})
	return build_matrix(payload, field=field or "", applicable=applicable or "", search=search or "")


def run_health_check():
	require_manager()
	report = _health_report()
	log_activity(
		"Health Check",
		new={"issue_count": report["issue_count"], "by_severity": report["by_severity"]},
		result="Information",
	)
	return report


def list_templates():
	require_manager()
	names = frappe.get_all("Permission Template", pluck="name", order_by="template_name asc", limit_page_length=0)
	return [_public_template(frappe.get_doc("Permission Template", name)) for name in names]


def save_template(payload):
	require_manager()
	data = _payload(payload)
	name = clean(data.get("name") or data.get("template_name"))
	exists = bool(name and frappe.db.exists("Permission Template", name))
	doc = frappe.get_doc("Permission Template", name) if exists else frappe.new_doc("Permission Template")
	if not exists:
		doc.template_name = clean(data.get("template_name") or name)
	for field in ("description", "category", "color"):
		if field in data:
			doc.set(field, data.get(field))
	if "permitted_values" in data or "values" in data:
		doc.set("permitted_values", [])
		for value in data.get("permitted_values") or data.get("values") or []:
			doc.append("permitted_values", _value_row(value))
	doc.save(ignore_permissions=True)
	log_activity("Template Updated" if exists else "Template Created", affected=doc.name, result="Success")
	return _public_template(doc)


def delete_template(name: str):
	require_manager()
	frappe.delete_doc("Permission Template", name, ignore_permissions=True)
	log_activity("Template Deleted", affected=name, result="Success")
	return {"deleted": name}


def save_group_as_template(group: str, template_name: str):
	require_manager()
	doc = frappe.get_doc("Permission Group", group)
	payload = template_from_group(_public_group(doc), template_name)
	if frappe.db.exists("Permission Template", payload["template_name"]):
		frappe.throw(_("Template {0} already exists.").format(payload["template_name"]))
	return save_template(payload)


def create_group_from_template(template: str, group_name: str, values=None, include_members=0):
	require_manager()
	source = frappe.get_doc("Permission Template", template)
	payload = group_from_template(
		_public_template(source), group_name, include_members=bool(cint(include_members))
	)
	if values is not None:
		payload["permitted_values"] = _payload(values)
	created = save_group(payload)
	log_activity("Template Applied", group=created["name"], affected=template, result="Success")
	return created


def list_activity(query="", action="", actor="", date_from="", date_to="", group="", limit=200):
	require_manager()
	filters = {}
	if clean(group):
		filters["permission_group"] = group
	rows = frappe.get_all(
		"Permission Studio Activity",
		filters=filters,
		fields=[
			"name",
			"action",
			"result",
			"permission_group",
			"affected_record",
			"details",
			"previous_state",
			"new_state",
			"owner",
			"creation",
		],
		order_by="creation desc",
		limit_page_length=cint(limit) or 200,
	)
	actors = {row.owner for row in rows if row.owner}
	labels = {}
	for actor_name in actors:
		labels[actor_name] = frappe.db.get_value("User", actor_name, "full_name") or actor_name
	materialized = []
	for row in rows:
		item = dict(row)
		item["actor"] = labels.get(row.owner) or row.owner
		materialized.append(item)
	return filter_activity(
		materialized,
		query=query or "",
		action=action or "",
		actor=actor or "",
		date_from=date_from or "",
		date_to=date_to or "",
	)


def search_documents(allow: str, txt: str = "", start=0, page_len=None, include_tagged=1):
	require_manager()
	allow = clean(allow)
	if not allow or not frappe.db.exists("DocType", allow):
		frappe.throw(_("Select a document type."))
	meta = frappe.get_meta(allow)
	if meta.istable:
		frappe.throw(_("Select a document type that is not a child table."))
	title_field = meta.get_title_field() or "name"
	fields = ["name"]
	if title_field != "name" and meta.has_field(title_field):
		fields.append(title_field)
	or_filters = None
	text = clean(txt)
	if text:
		or_filters = {"name": ["like", f"%{text}%"]}
		if title_field != "name":
			or_filters = [{"name": ["like", f"%{text}%"]}, {title_field: ["like", f"%{text}%"]}]
	page_length = cint(page_len) or _settings()["picker_page_size"]
	rows = frappe.get_all(
		allow,
		or_filters=or_filters,
		fields=fields,
		start=cint(start),
		page_length=page_length,
		order_by="modified desc",
	)
	documents = [
		{"name": row.name, "label": row.get(title_field) or row.name, "tags": []}
		for row in rows
	]
	tagged = tagged_documents(allow) if cint(include_tagged) else []
	return {
		"documents": documents,
		"tagged": tagged,
		"start": cint(start),
		"page_size": page_length,
		"viewport_rows": page_length,
	}


def tagged_documents(allow: str) -> list[dict]:
	tags = {}
	if frappe.db.table_exists("Permission Group Value"):
		for row in frappe.get_all(
			"Permission Group Value",
			filters={"allow": allow},
			fields=["for_value", "applicable_for", "parent", "parenttype"],
			limit_page_length=0,
		):
			_add_tag(
				tags,
				row.for_value,
				{
					"group": row.parent if row.parenttype == "Permission Group" else "",
					"template": row.parent if row.parenttype == "Permission Template" else "",
					"applicable_for": row.applicable_for or "",
					"source": row.parenttype or "Permission Group",
				},
			)
	if frappe.db.table_exists("User Permission"):
		fields = ["for_value", "applicable_for"]
		if frappe.db.has_column("User Permission", "ps_group"):
			fields.append("ps_group")
		for row in frappe.get_all(
			"User Permission", filters={"allow": allow}, fields=fields, limit_page_length=0
		):
			if not row.applicable_for and not row.get("ps_group"):
				continue
			_add_tag(
				tags,
				row.for_value,
				{
					"group": row.get("ps_group") or "",
					"applicable_for": row.applicable_for or "",
					"source": "User Permission",
				},
			)
	documents = []
	for name, tag_list in sorted(tags.items()):
		if not name or not frappe.db.exists(allow, name):
			continue
		documents.append({"name": name, "label": name, "tags": tag_list})
	return documents


def search_users(txt: str = "", start=0, page_len=None):
	require_manager()
	text = clean(txt)
	or_filters = None
	if text:
		or_filters = [
			{"name": ["like", f"%{text}%"]},
			{"full_name": ["like", f"%{text}%"]},
			{"email": ["like", f"%{text}%"]},
		]
	page_length = cint(page_len) or _settings()["picker_page_size"]
	rows = frappe.get_all(
		"User",
		filters={"name": ["!=", "Guest"], "enabled": 1},
		or_filters=or_filters,
		fields=["name", "full_name", "email"],
		start=cint(start),
		page_length=page_length,
		order_by="full_name asc",
	)
	membership = {}
	if frappe.db.table_exists("Permission Group Member"):
		names = [row.name for row in rows]
		if names:
			for member in frappe.get_all(
				"Permission Group Member",
				filters={"user": ["in", names]},
				fields=["user", "parent"],
				limit_page_length=0,
			):
				membership.setdefault(member.user, []).append(member.parent)
	return {
		"documents": [
			{
				"name": row.name,
				"label": row.full_name or row.name,
				"description": row.email or row.name,
				"tags": [{"group": group, "source": "Permission Group"} for group in membership.get(row.name, [])],
			}
			for row in rows
		],
		"page_size": page_length,
		"start": cint(start),
	}


def bulk_preview(operation: str, payload=None):
	require_manager()
	return _bulk(operation, payload, apply=False)


def bulk_apply(operation: str, payload=None, confirmed=0):
	require_manager()
	if operation in ("remove_members", "remove_values", "delete_groups") and not cint(confirmed):
		frappe.throw(_("Confirm this bulk operation before applying it."))
	result = _bulk(operation, payload, apply=True)
	log_activity(
		"Bulk Operation",
		new={"operation": operation, "applied": result.get("applied"), "errors": result.get("errors")},
		result="Partial" if result.get("errors") else "Success",
		details=operation,
	)
	return result


def export_groups(names=None):
	require_manager()
	selected = _group_names(names)
	return {"groups": [_public_group(frappe.get_doc("Permission Group", name)) for name in selected]}


def _bulk(operation: str, payload, apply: bool) -> dict:
	data = _payload(payload or {})
	if operation == "sync":
		names = data.get("groups") or []
		preview = preview_sync(names)
		if not apply:
			return {"operation": operation, "preview": preview, "applied": [], "errors": []}
		result = sync_groups(names)
		return {"operation": operation, "preview": preview, "applied": result["results"], "errors": result["failed"]}
	if operation == "export":
		exported = export_groups(data.get("groups"))
		return {"operation": operation, "preview": exported, "applied": exported["groups"], "errors": []}
	if operation == "copy_values":
		return _bulk_copy(data, apply)
	if operation in ("add_members", "remove_members"):
		return _bulk_members(operation, data, apply)
	if operation in ("add_values", "remove_values"):
		return _bulk_values(operation, data, apply)
	if operation == "delete_groups":
		return _bulk_delete(data, apply)
	frappe.throw(_("Unsupported bulk operation."))


def _bulk_members(operation, data, apply: bool) -> dict:
	group = data.get("group")
	doc = frappe.get_doc("Permission Group", group)
	plan = bulk_member_plan(_member_names(doc), data.get("users") or [], operation)
	if not apply:
		return {"operation": operation, "preview": plan, "applied": [], "errors": []}
	applied, errors = [], []
	for user in plan["add"] if operation == "add_members" else plan["remove"]:
		try:
			current = frappe.get_doc("Permission Group", group)
			if operation == "add_members":
				current.append("members", {"user": user})
			else:
				current.set("members", [row for row in current.members if row.user != user])
			current.save(ignore_permissions=True)
			applied.append(user)
		except Exception as exc:
			errors.append({"record": user, "error": _error_text(exc)})
	return {"operation": operation, "preview": plan, "applied": applied, "errors": errors}


def _bulk_values(operation, data, apply: bool) -> dict:
	group = data.get("group")
	incoming = [_value_row(value) for value in data.get("values") or []]
	doc = frappe.get_doc("Permission Group", group)
	if operation == "add_values":
		plan = copy_values(incoming, _value_dicts(doc))
		targets = plan["add"]
	else:
		wanted = {(row["allow"], row["for_value"], row.get("applicable_for") or "") for row in incoming}
		targets = [
			row
			for row in _value_dicts(doc)
			if (row["allow"], row["for_value"], row.get("applicable_for") or "") in wanted
		]
		plan = {"remove": targets}
	if not apply:
		return {"operation": operation, "preview": plan, "applied": [], "errors": []}
	applied, errors = [], []
	for row in targets:
		try:
			current = frappe.get_doc("Permission Group", group)
			key = (row["allow"], row["for_value"], row.get("applicable_for") or "")
			if operation == "add_values":
				current.append("permitted_values", row)
			else:
				current.set(
					"permitted_values",
					[
						existing
						for existing in current.permitted_values
						if (existing.allow, existing.for_value, existing.applicable_for or "") != key
					],
				)
			current.save(ignore_permissions=True)
			applied.append(row)
		except Exception as exc:
			errors.append({"record": f"{row.get('allow')} / {row.get('for_value')}", "error": _error_text(exc)})
	return {"operation": operation, "preview": plan, "applied": applied, "errors": errors}


def _bulk_copy(data, apply: bool) -> dict:
	source = frappe.get_doc("Permission Group", data.get("source"))
	source_values = _value_dicts(source)
	preview = []
	applied, errors = [], []
	for target in data.get("targets") or []:
		if target == source.name or not frappe.db.exists("Permission Group", target):
			errors.append({"record": target, "error": _("Target group is not available.")})
			continue
		doc = frappe.get_doc("Permission Group", target)
		plan = copy_values(source_values, _value_dicts(doc))
		preview.append({"group": target, **plan})
		if not apply:
			continue
		for row in plan["add"]:
			try:
				current = frappe.get_doc("Permission Group", target)
				current.append("permitted_values", _value_row(row))
				current.save(ignore_permissions=True)
				applied.append({"group": target, **row})
			except Exception as exc:
				errors.append({"record": f"{target}: {row.get('for_value')}", "error": _error_text(exc)})
	return {"operation": "copy_values", "preview": preview, "applied": applied, "errors": errors}


def _bulk_delete(data, apply: bool) -> dict:
	names = [name for name in data.get("groups") or [] if frappe.db.exists("Permission Group", name)]
	if not apply:
		return {"operation": "delete_groups", "preview": {"groups": names}, "applied": [], "errors": []}
	applied, errors = [], []
	for name in names:
		try:
			delete_group(name)
			applied.append(name)
		except Exception as exc:
			errors.append({"record": name, "error": _error_text(exc)})
	return {"operation": "delete_groups", "preview": {"groups": names}, "applied": applied, "errors": errors}


def _plan_for_doc(doc) -> dict:
	desired = desired_permissions(doc.enabled, _member_names(doc), _value_dicts(doc))
	managed = _managed_rows(doc.name)
	users = sorted({row["user"] for row in desired} | {row.get("user") for row in managed if row.get("user")})
	manual = _manual_rows(users) if users else []
	return plan_sync(desired, managed, manual)


def _managed_rows(group: str) -> list[dict]:
	if not frappe.db.has_column("User Permission", "ps_group"):
		return []
	return [
		dict(row)
		for row in frappe.get_all(
			"User Permission",
			filters={"ps_group": group},
			fields=_up_fields(),
			limit_page_length=0,
		)
	]


def _manual_rows(users: list[str]) -> list[dict]:
	if not users:
		return []
	rows = frappe.get_all(
		"User Permission",
		filters={"user": ["in", users]},
		fields=_up_fields(),
		limit_page_length=0,
	)
	return [dict(row) for row in rows if not row.get("ps_group")]


def _user_permissions(user: str) -> list[dict]:
	if not frappe.db.table_exists("User Permission"):
		return []
	return [
		dict(row)
		for row in frappe.get_all(
			"User Permission",
			filters={"user": user},
			fields=_up_fields(),
			limit_page_length=0,
		)
	]


def _up_fields() -> list[str]:
	fields = ["name", "user", "allow", "for_value", "applicable_for", "is_default", "apply_to_all_doctypes"]
	for extra in ("hide_descendants", "ps_group", "ps_signature"):
		if frappe.db.has_column("User Permission", extra):
			fields.append(extra)
	return fields


def _create_user_permission(row: dict, group: str) -> str:
	payload = {
		"doctype": "User Permission",
		"user": row["user"],
		"allow": row["allow"],
		"for_value": row["for_value"],
		"applicable_for": row.get("applicable_for") or None,
		"apply_to_all_doctypes": 0 if row.get("applicable_for") else 1,
		"is_default": row.get("is_default") or 0,
		"ps_group": group,
		"ps_signature": row.get("signature"),
	}
	if frappe.get_meta("User Permission").has_field("hide_descendants"):
		payload["hide_descendants"] = row.get("hide_descendants") or 0
	doc = frappe.get_doc(payload)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


def _update_user_permission(row: dict, group: str) -> str:
	current = frappe.db.get_value("User Permission", row.get("name"), ["ps_group"], as_dict=True)
	if not current or current.ps_group != group:
		raise frappe.ValidationError(_("Refusing to update a User Permission this group does not own."))
	doc = frappe.get_doc("User Permission", row.get("name"))
	doc.applicable_for = row.get("applicable_for") or None
	doc.apply_to_all_doctypes = 0 if row.get("applicable_for") else 1
	doc.is_default = row.get("is_default") or 0
	if doc.meta.has_field("hide_descendants"):
		doc.hide_descendants = row.get("hide_descendants") or 0
	doc.ps_signature = row.get("signature")
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	return doc.name


def _delete_user_permission(row: dict, group: str) -> str:
	if not removal_is_managed(row, group):
		raise frappe.ValidationError(_("Refusing to delete a User Permission this group does not own."))
	frappe.delete_doc("User Permission", row["name"], ignore_permissions=True, force=True)
	return row["name"]


def _group_names(names) -> list[str]:
	if isinstance(names, str):
		names = _payload(names)
	if not names:
		return frappe.get_all("Permission Group", pluck="name", limit_page_length=0)
	return [clean(name) for name in names if clean(name) and frappe.db.exists("Permission Group", name)]


def _group_rows() -> list[dict]:
	records = frappe.get_all(
		"Permission Group",
		fields=[
			"name",
			"group_name",
			"abbreviation",
			"description",
			"enabled",
			"category",
			"color",
			"sync_status",
			"modified",
			"modified_by",
			"last_sync_error",
		],
		limit_page_length=0,
	)
	member_counts = _child_counts("Permission Group Member")
	value_counts = _child_counts("Permission Group Value")
	modifiers = {}
	for row in records:
		if row.modified_by and row.modified_by not in modifiers:
			modifiers[row.modified_by] = frappe.db.get_value("User", row.modified_by, "full_name") or row.modified_by
	rows = []
	for row in records:
		item = dict(row)
		item["member_count"] = member_counts.get(row.name, 0)
		item["value_count"] = value_counts.get(row.name, 0)
		item["modified_by_name"] = modifiers.get(row.modified_by) or row.modified_by
		rows.append(item)
	return rows


def _child_counts(doctype: str) -> dict:
	if not frappe.db.table_exists(doctype):
		return {}
	counts = {}
	for row in frappe.get_all(doctype, fields=["parent"], limit_page_length=0):
		if row.parent:
			counts[row.parent] = counts.get(row.parent, 0) + 1
	return counts


def _public_group(doc) -> dict:
	members = []
	user_names = [row.user for row in doc.members if row.user]
	labels = _user_labels(user_names)
	for row in doc.members:
		if not row.user:
			continue
		info = labels.get(row.user, {})
		members.append(
			{
				"name": row.name,
				"user": row.user,
				"full_name": info.get("full_name") or row.user,
				"email": info.get("email") or row.user,
				"enabled": info.get("enabled"),
			}
		)
	values = _value_dicts(doc)
	return {
		"name": doc.name,
		"group_name": doc.group_name,
		"abbreviation": doc.abbreviation,
		"description": doc.description,
		"enabled": doc.enabled,
		"category": doc.category,
		"color": doc.color,
		"sync_status": doc.sync_status,
		"last_sync": doc.last_sync,
		"last_sync_by": doc.last_sync_by,
		"last_sync_error": doc.last_sync_error,
		"modified": doc.modified,
		"modified_by": doc.modified_by,
		"creation": doc.creation,
		"owner": doc.owner,
		"members": members,
		"permitted_values": values,
		"member_count": len(members),
		"value_count": len(values),
		"summary": access_summary(members, values),
	}


def _public_template(doc) -> dict:
	return {
		"name": doc.name,
		"template_name": doc.template_name,
		"description": doc.description,
		"category": doc.category,
		"color": doc.color,
		"permitted_values": [
			{
				"allow": row.allow,
				"for_value": row.for_value,
				"applicable_for": row.applicable_for or "",
				"is_default": row.is_default,
				"hide_descendants": row.hide_descendants,
			}
			for row in doc.permitted_values
		],
	}


def _value_dicts(doc) -> list[dict]:
	return [
		{
			"name": row.name,
			"allow": row.allow,
			"for_value": row.for_value,
			"applicable_for": row.applicable_for or "",
			"is_default": row.is_default,
			"hide_descendants": row.hide_descendants,
		}
		for row in doc.permitted_values
		if row.allow and row.for_value
	]


def _value_row(value: dict) -> dict:
	applicable = clean(value.get("applicable_for"))
	return {
		"allow": clean(value.get("allow")),
		"for_value": clean(value.get("for_value")),
		"applicable_for": applicable,
		"is_default": 1 if cint(value.get("is_default")) else 0,
		"hide_descendants": 1 if cint(value.get("hide_descendants")) else 0,
	}


def _member_names(doc) -> list[str]:
	return [row.user for row in doc.members if row.user]


def _user_labels(names: list[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(
		"User",
		filters={"name": ["in", names]},
		fields=["name", "full_name", "email", "enabled"],
		limit_page_length=0,
	)
	return {row.name: row for row in rows}


def _attach_permission_counts(rows: list[dict]):
	names = [row["name"] for row in rows]
	if not names or not frappe.db.table_exists("User Permission"):
		for row in rows:
			row["direct_permissions"] = 0
			row["managed_permissions"] = 0
		return
	counts = {name: {"direct": 0, "managed": 0} for name in names}
	fields = ["user"]
	if frappe.db.has_column("User Permission", "ps_group"):
		fields.append("ps_group")
	for perm in frappe.get_all(
		"User Permission", filters={"user": ["in", names]}, fields=fields, limit_page_length=0
	):
		bucket = counts.setdefault(perm.user, {"direct": 0, "managed": 0})
		if perm.get("ps_group"):
			bucket["managed"] += 1
		else:
			bucket["direct"] += 1
	for row in rows:
		bucket = counts.get(row["name"], {"direct": 0, "managed": 0})
		row["direct_permissions"] = bucket["direct"]
		row["managed_permissions"] = bucket["managed"]


def _stats() -> dict:
	groups = frappe.get_all("Permission Group", pluck="name", limit_page_length=0) if frappe.db.table_exists("Permission Group") else []
	members = []
	if frappe.db.table_exists("Permission Group Member"):
		members = frappe.get_all("Permission Group Member", pluck="user", limit_page_length=0)
	users_in = {user for user in members if user}
	enabled = frappe.get_all("User", filters={"enabled": 1, "name": ["!=", "Guest"]}, pluck="name")
	managed = 0
	if frappe.db.table_exists("User Permission") and frappe.db.has_column("User Permission", "ps_group"):
		managed = frappe.db.count("User Permission", {"ps_group": ["is", "set"]})
	report = _health_report()
	return {
		"groups": len(groups),
		"users_in_groups": len(users_in),
		"users_without_groups": len([user for user in enabled if user not in users_in]),
		"managed_permissions": managed,
		"issues": report["issue_count"],
	}


def _health_report() -> dict:
	groups = []
	if frappe.db.table_exists("Permission Group"):
		for name in frappe.get_all("Permission Group", pluck="name", limit_page_length=0):
			doc = frappe.get_doc("Permission Group", name)
			groups.append(
				{
					"name": doc.name,
					"sync_status": doc.sync_status,
					"members": _member_names(doc),
					"permitted_values": _value_dicts(doc),
				}
			)
	managed = []
	manual = []
	if frappe.db.table_exists("User Permission"):
		for row in frappe.get_all("User Permission", fields=_up_fields(), limit_page_length=0):
			item = dict(row)
			if item.get("ps_group"):
				managed.append(item)
			else:
				manual.append(item)
	enabled = frappe.get_all("User", filters={"enabled": 1, "name": ["!=", "Guest"]}, pluck="name")
	invalid = []
	for group in groups:
		for value in group["permitted_values"]:
			if not frappe.db.exists("DocType", value["allow"]) or not frappe.db.exists(value["allow"], value["for_value"]):
				invalid.append({"group": group["name"], **value})
	group_names = {group["name"] for group in groups}
	orphan_groups = sorted({row.get("ps_group") for row in managed if row.get("ps_group") and row.get("ps_group") not in group_names})
	return analyze_health(groups, managed, manual, enabled, invalid, orphan_groups)


def _previous_snapshot():
	if not frappe.db.table_exists("Permission Studio Activity"):
		return None, False
	today = nowdate()
	month_start = str(get_first_day(today))
	rows = frappe.get_all(
		"Permission Studio Activity",
		filters={"action": "Snapshot", "creation": ["between", [month_start, f"{today} 00:00:00"]]},
		fields=["new_state", "creation"],
		order_by="creation asc",
		limit_page_length=1,
	)
	if not rows:
		return None, False
	try:
		return frappe.parse_json(rows[0].new_state), True
	except Exception:
		return None, False


def _record_snapshot(stats: dict):
	if not frappe.db.table_exists("Permission Studio Activity"):
		return
	today = nowdate()
	existing = frappe.get_all(
		"Permission Studio Activity",
		filters={"action": "Snapshot", "creation": [">=", today]},
		limit_page_length=1,
	)
	if existing:
		return
	log_activity("Snapshot", new=stats, result="Information", details=today)


def log_activity(action, group=None, affected="", previous=None, new=None, result="Success", details=""):
	if not frappe.db.table_exists("Permission Studio Activity"):
		return None
	group_name = group if group and frappe.db.exists("Permission Group", group) else None
	doc = frappe.get_doc(
		{
			"doctype": "Permission Studio Activity",
			"action": action,
			"permission_group": group_name,
			"affected_record": clean(affected)[:140],
			"previous_state": previous if isinstance(previous, str) else frappe.as_json(previous or {}),
			"new_state": new if isinstance(new, str) else frappe.as_json(new or {}),
			"result": result,
			"details": clean(details)[:140],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _settings() -> dict:
	if not frappe.db.exists("DocType", "Permission Studio Settings"):
		return {"list_page_size": LIST_PAGE_SIZE, "picker_page_size": PICKER_PAGE_SIZE}
	doc = frappe.get_single("Permission Studio Settings")
	return {
		"list_page_size": cint(doc.list_page_size) or LIST_PAGE_SIZE,
		"picker_page_size": cint(doc.picker_page_size) or PICKER_PAGE_SIZE,
	}


def _payload(value):
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return {}
		return frappe.parse_json(value)
	return value or {}


def _add_tag(tags: dict, name: str, tag: dict):
	name = clean(name)
	if not name:
		return
	bucket = tags.setdefault(name, [])
	if tag not in bucket:
		bucket.append(tag)


def _record_label(row: dict) -> str:
	return " / ".join(
		part for part in (row.get("user"), row.get("allow"), row.get("for_value"), row.get("applicable_for")) if part
	)


def _error_text(exc) -> str:
	message = getattr(exc, "message", None) or exc
	return clean(message)[:500]
