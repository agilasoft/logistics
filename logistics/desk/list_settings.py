# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Let selected roles edit document-list columns without System Manager.

Frappe only shows List Settings to System Manager, and saving it also writes
Property Setter rows. Granting that DocType would let the role change any field
property. This path checks the roles on Logistics Settings, then writes only
List View Settings and the in_list_view flag.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.doctype.list_view_settings.list_view_settings import (
	save_listview_settings as _save_listview_settings,
)

from logistics.desk.list_settings_payload import (
	STATUS_FIELD,
	ListSettingsPayloadError,
	sanitize_listview_payload,
	sanitize_removed_fields,
)

_ROLE_TABLE = "Logistics Settings List Settings Role"


def extend_bootinfo(bootinfo) -> None:
	"""Expose the menu flag for the current user. System Manager already sees the menu."""
	if bootinfo is None or getattr(frappe.flags, "in_install", False):
		return
	try:
		bootinfo.can_edit_list_settings = user_has_list_settings_role()
	except Exception:
		bootinfo.can_edit_list_settings = False


def user_has_list_settings_role(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	allowed = set(configured_list_settings_roles())
	if not allowed:
		return False
	return bool(allowed.intersection(frappe.get_roles(user)))


def configured_list_settings_roles() -> list[str]:
	if not frappe.db.table_exists(_ROLE_TABLE):
		return []
	return frappe.get_all(
		_ROLE_TABLE,
		filters={"parent": "Logistics Settings", "parenttype": "Logistics Settings"},
		pluck="role",
	)


@frappe.whitelist()
def save_listview_settings(doctype: str, listview_settings, removed_listview_fields=None):
	"""Save list columns. System Manager keeps Frappe's method. Other roles use the allow-list."""
	if _has_native_list_settings_permission(doctype):
		return _save_listview_settings(doctype, listview_settings, removed_listview_fields)

	if not user_has_list_settings_role():
		frappe.throw(_("Not permitted to edit list settings."), frappe.PermissionError)
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("Document type {0} was not found.").format(doctype), frappe.DoesNotExistError)

	meta = frappe.get_meta(doctype)
	if meta.istable:
		frappe.throw(_("List settings do not apply to a child table."))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(
			_("You need read access on {0} before changing its list.").format(_(doctype)),
			frappe.PermissionError,
		)

	try:
		settings = frappe.parse_json(listview_settings) if isinstance(listview_settings, str) else listview_settings
		removed = (
			frappe.parse_json(removed_listview_fields)
			if isinstance(removed_listview_fields, str)
			else removed_listview_fields
		)
		payload = sanitize_listview_payload(settings, _fieldnames(meta))
		removed_names = sanitize_removed_fields(removed, _fieldnames(meta))
	except ListSettingsPayloadError as exc:
		frappe.throw(str(exc), frappe.ValidationError)

	doc = _upsert_list_view_settings(doctype, payload)
	if "fields" in payload:
		_apply_in_list_view(doctype, meta, payload.get("fields"), removed_names)
	return {"meta": frappe.get_meta(doctype, False), "listview_settings": doc}


def _has_native_list_settings_permission(doctype: str) -> bool:
	if frappe.db.exists("List View Settings", doctype):
		return bool(frappe.has_permission("List View Settings", "write"))
	return bool(frappe.has_permission("List View Settings", "create"))


def _fieldnames(meta) -> set[str]:
	names = {df.fieldname for df in (meta.fields or []) if getattr(df, "fieldname", None)}
	for fieldname in (
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"_user_tags",
		"_liked_by",
		"_assign",
		"_comments",
	):
		if meta.get_field(fieldname):
			names.add(fieldname)
	names.add(STATUS_FIELD)
	return names


def _upsert_list_view_settings(doctype: str, payload: dict):
	if frappe.db.exists("List View Settings", doctype):
		doc = frappe.get_doc("List View Settings", doctype)
		doc.flags.ignore_permissions = True
		doc.update(payload)
		doc.save(ignore_permissions=True)
		return doc

	doc = frappe.new_doc("List View Settings")
	doc.flags.ignore_permissions = True
	doc.name = doctype
	doc.update(payload)
	doc.insert(ignore_permissions=True)
	return doc


def _apply_in_list_view(doctype: str, meta, fields_json: str | None, removed_names: list[str]) -> None:
	selected = []
	for row in frappe.parse_json(fields_json) or []:
		fieldname = row.get("fieldname") if isinstance(row, dict) else None
		if fieldname and fieldname != STATUS_FIELD:
			selected.append(fieldname)

	for fieldname in removed_names:
		_set_in_list_view(doctype, meta, fieldname, "0")
	for fieldname in selected:
		_set_in_list_view(doctype, meta, fieldname, "1")


def _set_in_list_view(doctype: str, meta, fieldname: str, value: str) -> None:
	if not fieldname or fieldname == STATUS_FIELD:
		return
	field = meta.get_field(fieldname)
	if not field:
		return

	existing = frappe.db.get_value(
		"Property Setter",
		{"doc_type": doctype, "field_name": fieldname, "property": "in_list_view"},
		"name",
	)
	if existing:
		setter = frappe.get_doc("Property Setter", existing)
		setter.flags.ignore_permissions = True
		setter.flags.ignore_validate = True
		setter.flags.validate_fields_for_doctype = False
		setter.value = value
		setter.save(ignore_permissions=True)
		return

	setter = frappe.get_doc(
		{
			"doctype": "Property Setter",
			"doctype_or_field": "DocField",
			"doc_type": doctype,
			"field_name": fieldname,
			"property": "in_list_view",
			"value": value,
			"property_type": "Check",
			"is_system_generated": 1,
		}
	)
	setter.flags.ignore_permissions = True
	setter.flags.ignore_validate = True
	setter.flags.validate_fields_for_doctype = False
	setter.insert(ignore_permissions=True)
