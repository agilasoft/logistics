# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Event family → Exhibit / Exhibits module (reverse of exhibits→events migration)."""

from __future__ import annotations

import frappe
from frappe.model.utils.rename_field import rename_field

_DOCTYPE_RENAMES = (
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

_FIELD_RENAMES = (
	("Exhibit Order", "event", "exhibit"),
	("Exhibit Job", "event", "exhibit"),
	("Exhibit Plan", "event", "exhibit"),
	("Sales Quote", "event", "exhibit"),
	("Exhibit", "event_participants", "exhibit_participants"),
	("Exhibit", "event_type", "exhibit_type"),
)

_CHILD_PARENTFIELDS = (
	("Exhibit Participant", "event_participants", "exhibit_participants"),
)

# Logistics programme tables (not Frappe desk ``tabEvent`` / ``tabEvent Participants``).
_TABLE_RENAMES = (
	("tabEvent Participant", "tabExhibit Participant"),
	("tabEvent Job Participant", "tabExhibit Job Participant"),
	("tabEvent Job Resource", "tabExhibit Job Resource"),
	("tabEvent Milestone", "tabExhibit Milestone"),
	("tabEvent Billing", "tabExhibit Billing"),
	("tabEvent Delivery", "tabExhibit Delivery"),
	("tabEvent Scoping Activity", "tabExhibit Scoping Activity"),
	("tabEvent Charges", "tabExhibit Charges"),
	("tabEvent Service Activity", "tabExhibit Service Activity"),
	("tabEvent Job", "tabExhibit Job"),
	("tabEvent Order", "tabExhibit Order"),
	("tabEvent Plan", "tabExhibit Plan"),
	("tabEvent Type", "tabExhibit Type"),
	("tabEvent Settings", "tabExhibit Settings"),
	("tabEvent", "tabExhibit"),
)


def execute():
	frappe.flags.in_patch = True
	frappe.flags.ignore_links = True
	try:
		_rename_module_def()
		_set_events_module_to_exhibits()
		_remove_duplicate_exhibit_doctypes()
		_cleanup_duplicate_event_exhibit_tables()
		_rename_logistics_event_tables()
		_rename_doctypes()
		_rename_fields()
		_rename_event_order_field()
		_update_child_parenttypes()
		_update_child_parentfields()
		_backfill_main_service()
		_rename_workspace_and_icons()
	finally:
		frappe.flags.in_patch = False
		frappe.flags.ignore_links = False
	frappe.db.commit()
	frappe.clear_cache()


def _rename_module_def():
	if frappe.db.exists("Module Def", "Events") and not frappe.db.exists("Module Def", "Exhibits"):
		frappe.db.sql(
			"""
			UPDATE `tabModule Def`
			SET name = 'Exhibits', module_name = 'Exhibits'
			WHERE name = 'Events'
			"""
		)
	elif frappe.db.exists("Module Def", "Events"):
		frappe.db.sql("DELETE FROM `tabModule Def` WHERE name = 'Events'")

	for table in ("DocType", "Report", "Workspace", "Page"):
		if frappe.db.table_exists(f"tab{table}"):
			frappe.db.sql(
				f"UPDATE `tab{table}` SET module = 'Exhibits' WHERE module = 'Events'"
			)


def _set_events_module_to_exhibits():
	for table in ("DocType", "Report", "Workspace", "Page", "Dashboard", "Number Card"):
		if frappe.db.table_exists(f"tab{table}") and frappe.db.has_column(table, "module"):
			frappe.db.sql(
				f"UPDATE `tab{table}` SET module = 'Exhibits' WHERE module = 'Events'"
			)
	if frappe.db.table_exists("tabDesktop Icon") and frappe.db.has_column("Desktop Icon", "module"):
		frappe.db.sql(
			"UPDATE `tabDesktop Icon` SET module = 'Exhibits' WHERE module = 'Events'"
		)


def _remove_duplicate_exhibit_doctypes():
	"""Drop partial Exhibit* rows created if migrate synced JSON before DB rename."""
	for old_name, new_name in _DOCTYPE_RENAMES:
		if old_name == "Event":
			continue
		if frappe.db.exists("DocType", old_name) and frappe.db.exists("DocType", new_name):
			frappe.delete_doc("DocType", new_name, force=True, ignore_missing=True)


def _drop_orphan_exhibit_table(old_name: str, new_name: str) -> None:
	"""Drop premature ``tabExhibit*`` table so DocType rename can RENAME TABLE."""
	if not frappe.db.table_exists(new_name) or not frappe.db.table_exists(old_name):
		return
	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{new_name}`")


def _cleanup_duplicate_event_exhibit_tables() -> None:
	"""Resolve partial renames where both ``tabEvent*`` and ``tabExhibit*`` exist."""
	for old_name, new_name in _DOCTYPE_RENAMES:
		if old_name == "Event":
			continue
		if not frappe.db.table_exists(old_name) or not frappe.db.table_exists(new_name):
			continue
		if not frappe.db.exists("DocType", old_name) and frappe.db.exists("DocType", new_name):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{old_name}`")
		elif frappe.db.exists("DocType", old_name):
			_drop_orphan_exhibit_table(old_name, new_name)


def _rename_logistics_event_tables():
	"""Move logistics programme SQL tables off ``tabEvent`` so desk calendar Event can use it."""
	if not frappe.db.table_exists("tabEvent") or not frappe.db.has_column("Event", "project_name"):
		return
	for old_table, new_table in _TABLE_RENAMES:
		old_name = old_table.replace("tab", "", 1)
		new_name = new_table.replace("tab", "", 1)
		if not frappe.db.table_exists(old_name):
			continue
		if frappe.db.table_exists(new_name):
			continue
		frappe.db.sql(f"RENAME TABLE `{old_table}` TO `{new_table}`")


def _rename_doctypes():
	frappe.flags.ignore_links = True
	for old_name, new_name in _DOCTYPE_RENAMES:
		if old_name == "Event":
			continue
		if not frappe.db.exists("DocType", old_name):
			continue
		if frappe.db.exists("DocType", new_name):
			continue
		_drop_orphan_exhibit_table(old_name, new_name)
		frappe.rename_doc("DocType", old_name, new_name, force=True, merge=False)
	frappe.flags.ignore_links = False

	if frappe.db.exists("Desktop Icon", "Events") and not frappe.db.exists("Desktop Icon", "Exhibits"):
		frappe.rename_doc("Desktop Icon", "Events", "Exhibits", force=True, merge=False)
	elif frappe.db.exists("Desktop Icon", "Events"):
		frappe.delete_doc("Desktop Icon", "Events", force=True, ignore_missing=True)

	if frappe.db.exists("Workspace Sidebar", "Events") and not frappe.db.exists(
		"Workspace Sidebar", "Exhibits"
	):
		frappe.rename_doc("Workspace Sidebar", "Events", "Exhibits", force=True, merge=False)
	elif frappe.db.exists("Workspace Sidebar", "Events"):
		frappe.delete_doc("Workspace Sidebar", "Events", force=True, ignore_missing=True)

	if frappe.db.exists("Workspace", "Events") and not frappe.db.exists("Workspace", "Exhibits"):
		frappe.rename_doc("Workspace", "Events", "Exhibits", force=True, merge=False)
	elif frappe.db.exists("Workspace", "Events"):
		frappe.delete_doc("Workspace", "Events", force=True, ignore_missing=True)


def _rename_fields():
	for doctype, old_field, new_field in _FIELD_RENAMES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.db.table_exists(f"tab{doctype}"):
			continue
		if not frappe.db.has_column(doctype, old_field):
			continue
		if frappe.db.has_column(doctype, new_field):
			continue
		rename_field(doctype, old_field, new_field)


def _rename_event_order_field():
	if not frappe.db.table_exists("tabExhibit Job"):
		return
	if frappe.db.has_column("Exhibit Job", "event_order") and not frappe.db.has_column(
		"Exhibit Job", "exhibit_order"
	):
		rename_field("Exhibit Job", "event_order", "exhibit_order")


def _update_child_parenttypes():
	pairs = (
		("Event", "Exhibit"),
		("Event Order", "Exhibit Order"),
		("Event Job", "Exhibit Job"),
		("Event Plan", "Exhibit Plan"),
	)
	children = (
		"Exhibit Charges",
		"Exhibit Milestone",
		"Exhibit Billing",
		"Exhibit Delivery",
		"Exhibit Scoping Activity",
		"Exhibit Service Activity",
		"Exhibit Participant",
		"Exhibit Job Participant",
	)
	for old_parent, new_parent in pairs:
		for child in children:
			if frappe.db.table_exists(f"tab{child}"):
				frappe.db.sql(
					f"UPDATE `tab{child}` SET parenttype = %s WHERE parenttype = %s",
					(new_parent, old_parent),
				)


def _update_child_parentfields():
	for child, old_field, new_field in _CHILD_PARENTFIELDS:
		if not frappe.db.table_exists(f"tab{child}"):
			continue
		if frappe.db.has_column(child, "parentfield"):
			frappe.db.sql(
				f"UPDATE `tab{child}` SET parentfield = %s WHERE parentfield = %s",
				(new_field, old_field),
			)


def _backfill_main_service():
	if frappe.db.has_column("Sales Quote", "main_service"):
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET main_service = 'Exhibits'
			WHERE main_service = 'Events'
			"""
		)
	if frappe.db.has_column("Internal Job Detail", "service_type"):
		frappe.db.sql(
			"""
			UPDATE `tabInternal Job Detail`
			SET service_type = 'Exhibits'
			WHERE service_type = 'Events'
			"""
		)


def _rename_workspace_and_icons():
	for doctype, name, updates in (
		("Desktop Icon", "Exhibits", {"label": "Exhibits", "link_to": "Exhibits"}),
		("Workspace Sidebar", "Exhibits", {"title": "Exhibits", "module": "Exhibits"}),
		("Workspace", "Exhibits", {"title": "Exhibits", "label": "Exhibits", "module": "Exhibits"}),
	):
		if frappe.db.exists(doctype, name):
			frappe.db.set_value(doctype, name, updates, update_modified=False)
