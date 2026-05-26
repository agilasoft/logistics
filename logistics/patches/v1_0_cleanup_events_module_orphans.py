# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop orphan Event*/legacy Exhibit* tables and fix stale module references after Exhibits rename."""

from __future__ import annotations

import frappe

# Logistics programme tables superseded by Exhibit* (Desk ``Event`` / ``tabEvent`` kept).
_ORPHAN_LOGISTICS_TABLES = (
	"Event Billing",
	"Event Charges",
	"Event Delivery",
	"Event Job",
	"Event Job Participant",
	"Event Job Resource",
	"Event Milestone",
	"Event Order",
	"Event Participant",
	"Event Plan",
	"Event Scoping Activity",
	"Event Service Activity",
	"Event Type",
	"Event Venue",
	"Exhibit Service Activity",
	"Exhibit Scoping Activity",
	"Exhibit Statement of Work",
	"Exhibit Lifecycle Stage",
)

_DOCTYPE_OPTION_RENAMES = (
	("Event Job Resource", "Exhibit Job Resource"),
	("Event Milestone", "Exhibit Milestone"),
	("Event Billing", "Exhibit Billing"),
	("Event Delivery", "Exhibit Delivery"),
	("Event Scoping Activity", "Exhibit Scoping Activity"),
	("Event Charges", "Exhibit Charges"),
	("Event Service Activity", "Exhibit Service Activity"),
	("Event Job Participant", "Exhibit Job Participant"),
	("Event Participant", "Exhibit Participant"),
	("Event Job", "Exhibit Job"),
	("Event Order", "Exhibit Order"),
	("Event Plan", "Exhibit Plan"),
	("Event Type", "Exhibit Type"),
	("Event Settings", "Exhibit Settings"),
	("Event Pipeline Report", "Exhibit Pipeline Report"),
	("Event Activity Status Report", "Exhibit Activity Status Report"),
	("Event Billing Status Report", "Exhibit Billing Status Report"),
	("Event", "Exhibit"),
)

_CHILD_PARENTTYPE_PAIRS = (
	("Event", "Exhibit"),
	("Event Order", "Exhibit Order"),
	("Event Job", "Exhibit Job"),
	("Event Plan", "Exhibit Plan"),
)


def execute():
	frappe.flags.in_patch = True
	try:
		_remove_logistics_rows_from_desk_event_table()
		_drop_orphan_logistics_tables()
		_update_child_parenttypes()
		_update_doctype_link_options()
		_remove_events_module_artifacts()
	finally:
		frappe.flags.in_patch = False
	frappe.db.commit()
	frappe.clear_cache()


def _remove_logistics_rows_from_desk_event_table():
	"""Programme rows were copied to ``tabExhibit``; remove legacy rows from shared ``tabEvent``."""
	if not frappe.db.table_exists("Event"):
		return
	if not frappe.db.has_column("Event", "project_name"):
		return
	frappe.db.sql(
		"""
		DELETE FROM `tabEvent`
		WHERE IFNULL(project_name, '') != ''
		"""
	)


def _drop_orphan_logistics_tables():
	for name in _ORPHAN_LOGISTICS_TABLES:
		if frappe.db.table_exists(name):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{name}`")


def _update_child_parenttypes():
	for child in (
		"Exhibit Charges",
		"Exhibit Milestone",
		"Exhibit Billing",
		"Exhibit Delivery",
		"Exhibit Participant",
		"Exhibit Job Participant",
		"Exhibit Job Resource",
	):
		if not frappe.db.table_exists(child):
			continue
		for old_parent, new_parent in _CHILD_PARENTTYPE_PAIRS:
			frappe.db.sql(
				f"UPDATE `tab{child}` SET parenttype = %s WHERE parenttype = %s",
				(new_parent, old_parent),
			)


def _update_doctype_link_options():
	for old, new in _DOCTYPE_OPTION_RENAMES:
		for parent in ("DocField", "Custom Field"):
			if not frappe.db.table_exists(f"tab{parent}"):
				continue
			frappe.db.sql(
				f"""
				UPDATE `tab{parent}`
				SET options = REPLACE(options, %s, %s)
				WHERE options LIKE %s
				""",
				(old, new, f"%{old}%"),
			)
		if frappe.db.table_exists("tabProperty Setter"):
			frappe.db.sql(
				"""
				UPDATE `tabProperty Setter`
				SET value = REPLACE(value, %s, %s)
				WHERE property = 'options' AND value LIKE %s
				""",
				(old, new, f"%{old}%"),
			)


def _remove_events_module_artifacts():
	if frappe.db.exists("Module Def", "Events") and frappe.db.exists("Module Def", "Exhibits"):
		frappe.delete_doc("Module Def", "Events", force=True, ignore_missing=True)

	for doctype in ("Desktop Icon", "Workspace Sidebar", "Workspace"):
		if frappe.db.exists(doctype, "Events") and frappe.db.exists(doctype, "Exhibits"):
			frappe.delete_doc(doctype, "Events", force=True, ignore_missing=True)

	for table in ("DocType", "Report", "Workspace", "Page", "Dashboard", "Number Card"):
		if frappe.db.table_exists(f"tab{table}") and frappe.db.has_column(table, "module"):
			frappe.db.sql(
				f"UPDATE `tab{table}` SET module = 'Exhibits' WHERE module = 'Events'"
			)

	# Orphan logistics DocType rows (JSON now under exhibits/)
	for old_name, new_name in _DOCTYPE_OPTION_RENAMES:
		if old_name == "Event":
			continue
		if frappe.db.exists("DocType", old_name) and frappe.db.exists("DocType", new_name):
			frappe.delete_doc("DocType", old_name, force=True, ignore_missing=True)
