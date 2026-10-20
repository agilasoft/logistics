# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Whitelisted Permission Studio endpoints. Each one checks System Manager."""

import frappe

from logistics.permissions.studio_api import (
	bulk_apply,
	bulk_preview,
	check_access,
	create_group_from_template,
	delete_group,
	delete_template,
	export_groups,
	get_dashboard,
	get_group,
	get_matrix,
	get_settings,
	get_user_access,
	list_activity,
	list_groups,
	list_templates,
	list_users,
	preview_sync,
	run_health_check,
	save_group,
	save_group_as_template,
	save_settings,
	save_template,
	search_documents,
	search_users,
	set_enabled,
	sync_groups,
)


@frappe.whitelist()
def dashboard():
	return get_dashboard()


@frappe.whitelist()
def groups(search="", status="", category="", enabled=None, sort="modified", page=1, page_size=None):
	return list_groups(search, status, category, enabled, sort, page, page_size)


@frappe.whitelist()
def group(name):
	return get_group(name)


@frappe.whitelist()
def save(payload):
	return save_group(payload)


@frappe.whitelist()
def delete(name):
	return delete_group(name)


@frappe.whitelist()
def enabled(name, enabled):
	return set_enabled(name, enabled)


@frappe.whitelist()
def sync_preview(names=None):
	return preview_sync(names)


@frappe.whitelist()
def sync(names=None):
	return sync_groups(names)


@frappe.whitelist()
def users(search="", assignment="all", page=1, page_size=20):
	return list_users(search, assignment, page, page_size)


@frappe.whitelist()
def user_access(user):
	return get_user_access(user)


@frappe.whitelist()
def access_check(user, doctype, document=None, action="read"):
	return check_access(user, doctype, document, action)


@frappe.whitelist()
def matrix(groups=None, field="", applicable="", search=""):
	return get_matrix(groups, field, applicable, search)


@frappe.whitelist()
def health():
	return run_health_check()


@frappe.whitelist()
def templates():
	return list_templates()


@frappe.whitelist()
def save_template_doc(payload):
	return save_template(payload)


@frappe.whitelist()
def delete_template_doc(name):
	return delete_template(name)


@frappe.whitelist()
def group_to_template(group, template_name):
	return save_group_as_template(group, template_name)


@frappe.whitelist()
def template_to_group(template, group_name, values=None, include_members=0):
	return create_group_from_template(template, group_name, values, include_members)


@frappe.whitelist()
def activity(query="", action="", actor="", date_from="", date_to="", group="", limit=200):
	return list_activity(query, action, actor, date_from, date_to, group, limit)


@frappe.whitelist()
def documents(allow, txt="", start=0, page_len=None, include_tagged=1):
	return search_documents(allow, txt, start, page_len, include_tagged)


@frappe.whitelist()
def user_search(txt="", start=0, page_len=None):
	return search_users(txt, start, page_len)


@frappe.whitelist()
def bulk_plan(operation, payload=None):
	return bulk_preview(operation, payload)


@frappe.whitelist()
def bulk_run(operation, payload=None, confirmed=0):
	return bulk_apply(operation, payload, confirmed)


@frappe.whitelist()
def export(names=None):
	return export_groups(names)


@frappe.whitelist()
def settings():
	return get_settings()


@frappe.whitelist()
def save_studio_settings(list_page_size=10, picker_page_size=25):
	return save_settings(list_page_size, picker_page_size)
