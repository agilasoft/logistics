# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Restore the 14 Oct Frappe Hero Permission Studio.

User Permission rows stay. The logistics-only studio DocTypes and the
ps_group / ps_signature columns are removed. Ownership for this studio is
hero_managed, hero_permission_group, and hero_source_groups.
"""

from __future__ import unicode_literals

import frappe

from logistics.permission_studio.fields import ensure_custom_fields


LOGISTICS_STUDIO_DOCTYPES = (
	"Permission Studio Settings",
	"Permission Studio Activity",
	"Permission Template",
	"Permission Group",
	"Permission Group Member",
	"Permission Group Value",
)
REPLACED_FIELDS = ("ps_group", "ps_signature")


def execute():
	frappe.flags.in_patch = True
	ensure_custom_fields()
	_drop_replaced_fields()
	_delete_logistics_studio_doctypes()
	frappe.clear_cache()


def _drop_replaced_fields():
	"""Drop the logistics studio columns without deleting User Permission rows."""
	if not frappe.db.table_exists("User Permission"):
		return
	if frappe.db.table_exists("Custom Field"):
		for fieldname in REPLACED_FIELDS:
			name = frappe.db.get_value(
				"Custom Field", {"dt": "User Permission", "fieldname": fieldname}, "name"
			)
			if name:
				frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
	if frappe.db.table_exists("Property Setter"):
		for fieldname in REPLACED_FIELDS:
			for name in frappe.get_all(
				"Property Setter",
				filters={"doc_type": "User Permission", "field_name": fieldname},
				pluck="name",
			):
				frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)
	frappe.db.commit()
	for fieldname in REPLACED_FIELDS:
		if frappe.db.has_column("User Permission", fieldname):
			frappe.db.sql_ddl(f"ALTER TABLE `tabUser Permission` DROP COLUMN `{fieldname}`")
	frappe.db.commit()
	frappe.clear_cache(doctype="User Permission")


def _delete_logistics_studio_doctypes():
	for name in LOGISTICS_STUDIO_DOCTYPES:
		if frappe.db.exists("DocType", name):
			frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
	frappe.db.commit()
	if frappe.db.table_exists("Singles"):
		frappe.db.delete("Singles", {"doctype": "Permission Studio Settings"})
	for name in LOGISTICS_STUDIO_DOCTYPES:
		if frappe.db.table_exists(name):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{name}`")
	frappe.db.commit()
