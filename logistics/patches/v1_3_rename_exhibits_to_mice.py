# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Exhibits module + Exhibit family doctypes to MICE / MICE Project.

Mapping
-------
Module:
    ``Exhibits`` -> ``MICE``

Non-child doctypes (use ``MICE`` prefix):
    ``Exhibit``           -> ``MICE Project``  (main DocType, was the rebranded show/programme)
    ``Exhibit Type``      -> ``MICE Type``
    ``Exhibit Job``       -> ``MICE Job``
    ``Exhibit Order``     -> ``MICE Order``
    ``Exhibit Settings``  -> ``MICE Settings``

Child tables (use ``MICE Project`` prefix, except ``Exhibit Job Resource`` which
is a child of ``MICE Job``):
    ``Exhibit Billing``                -> ``MICE Project Billing``
    ``Exhibit Charges``                -> ``MICE Project Charges``
    ``Exhibit Consolidation Charges``  -> ``MICE Project Consolidation Charges``
    ``Exhibit Cost Allocation``        -> ``MICE Project Cost Allocation``
    ``Exhibit Delivery``               -> ``MICE Project Delivery``
    ``Exhibit Docket``                 -> ``MICE Project Docket``
    ``Exhibit Milestone``              -> ``MICE Project Milestone``
    ``Exhibit Job Resource``           -> ``MICE Job Resource``

Reports (use ``MICE`` prefix):
    ``Exhibit Pipeline Report``         -> ``MICE Pipeline Report``
    ``Exhibit Activity Status Report``  -> ``MICE Activity Status Report``
    ``Exhibit Billing Status Report``   -> ``MICE Billing Status Report``

Workspace / Desktop Icon / Workspace Sidebar:
    ``Exhibits`` -> ``MICE``

``Docket`` and ``Activity Code`` stay (only their ``module`` field flips to
``MICE``).
"""

from __future__ import annotations

import frappe

# Ordered longest-first so child / compound names rename before the parent
# ``Exhibit`` -> ``MICE Project`` swap fires.
_DOCTYPE_RENAMES = (
	# Reports
	("Exhibit Pipeline Report", "MICE Pipeline Report"),
	("Exhibit Activity Status Report", "MICE Activity Status Report"),
	("Exhibit Billing Status Report", "MICE Billing Status Report"),
	# Child tables
	("Exhibit Consolidation Charges", "MICE Project Consolidation Charges"),
	("Exhibit Cost Allocation", "MICE Project Cost Allocation"),
	("Exhibit Job Resource", "MICE Job Resource"),
	("Exhibit Milestone", "MICE Project Milestone"),
	("Exhibit Delivery", "MICE Project Delivery"),
	("Exhibit Billing", "MICE Project Billing"),
	("Exhibit Charges", "MICE Project Charges"),
	("Exhibit Docket", "MICE Project Docket"),
	# Non-child doctypes
	("Exhibit Settings", "MICE Settings"),
	("Exhibit Type", "MICE Type"),
	("Exhibit Order", "MICE Order"),
	("Exhibit Job", "MICE Job"),
	("Exhibit", "MICE Project"),
)

# Parent doctypes whose ``parenttype`` column on child tables needs flipping.
_PARENT_RENAMES = (
	("Exhibit", "MICE Project"),
	("Exhibit Order", "MICE Order"),
	("Exhibit Job", "MICE Job"),
)

# Child tables whose ``parenttype`` column references the renamed parents.
_CHILD_DOCTYPES_FOR_PARENTTYPE = (
	"MICE Project Milestone",
	"MICE Project Billing",
	"MICE Project Charges",
	"MICE Project Delivery",
	"MICE Project Docket",
	"MICE Project Consolidation Charges",
	"MICE Project Cost Allocation",
	"MICE Job Resource",
)


def execute():
	frappe.flags.in_patch = True
	frappe.flags.ignore_links = True
	try:
		_rename_module_def()
		_drop_premature_mice_tables()
		_rename_doctypes()
		_rename_reports()
		_rename_workspace_desktop_sidebar()
		_set_renamed_doctype_module()
		_update_child_parenttypes()
		_migrate_main_service_values()
		_migrate_service_type_values()
		_migrate_cost_allocation_target()
		_migrate_cost_allocation_basis_target()
		_drop_orphan_legacy_tables()
		_repoint_workspace_items_off_mice_event()
	finally:
		frappe.flags.in_patch = False
		frappe.flags.ignore_links = False
	frappe.db.commit()
	frappe.clear_cache()


# ---------------------------------------------------------------------------
# Module Def
# ---------------------------------------------------------------------------


def _rename_module_def():
	if frappe.db.exists("Module Def", "Exhibits") and not frappe.db.exists("Module Def", "MICE"):
		frappe.db.sql(
			"""
			UPDATE `tabModule Def`
			SET name = 'MICE', module_name = 'MICE'
			WHERE name = 'Exhibits'
			"""
		)
	elif frappe.db.exists("Module Def", "Exhibits"):
		frappe.db.sql("DELETE FROM `tabModule Def` WHERE name = 'Exhibits'")


# ---------------------------------------------------------------------------
# DocType renames
# ---------------------------------------------------------------------------


def _drop_premature_mice_tables():
	"""If migrate synced the new JSON before this patch ran, drop the empty
	``tabMICE *`` shells so ``frappe.rename_doc`` can ``RENAME TABLE`` cleanly."""
	for old_name, new_name in _DOCTYPE_RENAMES:
		if not frappe.db.exists("DocType", old_name):
			continue
		if frappe.db.exists("DocType", new_name):
			# Both DocType rows exist - delete the new (empty) shell so rename succeeds.
			frappe.delete_doc("DocType", new_name, force=True, ignore_missing=True)
		# frappe.db.table_exists() takes the DocType name, not the prefixed table.
		if frappe.db.table_exists(new_name) and frappe.db.table_exists(old_name):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{new_name}`")


def _rename_doctypes():
	for old_name, new_name in _DOCTYPE_RENAMES:
		if not frappe.db.exists("DocType", old_name):
			continue
		if frappe.db.exists("DocType", new_name):
			continue
		frappe.rename_doc("DocType", old_name, new_name, force=True, merge=False)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _rename_reports():
	pairs = (
		("Exhibit Pipeline Report", "MICE Pipeline Report"),
		("Exhibit Activity Status Report", "MICE Activity Status Report"),
		("Exhibit Billing Status Report", "MICE Billing Status Report"),
	)
	for old_name, new_name in pairs:
		if frappe.db.exists("Report", old_name) and not frappe.db.exists("Report", new_name):
			frappe.rename_doc("Report", old_name, new_name, force=True, merge=False)
		elif frappe.db.exists("Report", old_name):
			frappe.delete_doc("Report", old_name, force=True, ignore_missing=True)


# ---------------------------------------------------------------------------
# Workspace / Desktop Icon / Workspace Sidebar
# ---------------------------------------------------------------------------


def _rename_workspace_desktop_sidebar():
	for doctype, old_name, new_name in (
		("Workspace", "Exhibits", "MICE"),
		("Workspace Sidebar", "Exhibits", "MICE"),
		("Desktop Icon", "Exhibits", "MICE"),
	):
		if not frappe.db.table_exists(f"tab{doctype}"):
			continue
		if frappe.db.exists(doctype, old_name) and not frappe.db.exists(doctype, new_name):
			frappe.rename_doc(doctype, old_name, new_name, force=True, merge=False)
		elif frappe.db.exists(doctype, old_name):
			frappe.delete_doc(doctype, old_name, force=True, ignore_missing=True)


def _set_renamed_doctype_module():
	"""Ensure every renamed DocType / Report / Workspace / Desktop Icon points at the new module."""
	for tbl in ("DocType", "Report", "Workspace", "Page", "Dashboard", "Number Card"):
		if frappe.db.table_exists(f"tab{tbl}") and frappe.db.has_column(tbl, "module"):
			frappe.db.sql(
				f"UPDATE `tab{tbl}` SET module = 'MICE' WHERE module = 'Exhibits'"
			)
	if frappe.db.table_exists("tabDesktop Icon") and frappe.db.has_column("Desktop Icon", "module"):
		frappe.db.sql(
			"UPDATE `tabDesktop Icon` SET module = 'MICE' WHERE module = 'Exhibits'"
		)


# ---------------------------------------------------------------------------
# Child table parenttype
# ---------------------------------------------------------------------------


def _update_child_parenttypes():
	for child in _CHILD_DOCTYPES_FOR_PARENTTYPE:
		table = f"tab{child}"
		if not frappe.db.table_exists(table):
			continue
		if not frappe.db.has_column(child, "parenttype"):
			continue
		for old_parent, new_parent in _PARENT_RENAMES:
			frappe.db.sql(
				f"UPDATE `{table}` SET parenttype = %s WHERE parenttype = %s",
				(new_parent, old_parent),
			)


# ---------------------------------------------------------------------------
# Stored option values (Select fields) and link values
# ---------------------------------------------------------------------------


def _migrate_main_service_values():
	"""Sales Quote / Internal Job Detail.main_service / service_type ``Exhibits`` -> ``MICE``."""
	for doctype, column in (
		("Sales Quote", "main_service"),
		("Internal Job Detail", "service_type"),
	):
		if frappe.db.table_exists(f"tab{doctype}") and frappe.db.has_column(doctype, column):
			frappe.db.sql(
				f"UPDATE `tab{doctype}` SET {column} = 'MICE' WHERE {column} = 'Exhibits'"
			)


def _migrate_service_type_values():
	"""Charge child tables carry ``service_type`` Select with ``Exhibits`` option."""
	charge_tables = (
		"Sales Quote Charge",
		"Change Request Charge",
		"Special Project Charges",
		"MICE Project Charges",
		"Lifecycle Template Activity",
		"Lifecycle Job",
	)
	for tbl in charge_tables:
		if frappe.db.table_exists(f"tab{tbl}") and frappe.db.has_column(tbl, "service_type"):
			frappe.db.sql(
				f"UPDATE `tab{tbl}` SET service_type = 'MICE' WHERE service_type = 'Exhibits'"
			)


def _migrate_cost_allocation_target():
	"""MICE Project.cost_allocation_target Select option ``Exhibit Jobs`` -> ``MICE Jobs``."""
	if frappe.db.table_exists("tabMICE Project") and frappe.db.has_column(
		"MICE Project", "cost_allocation_target"
	):
		frappe.db.sql(
			"""
			UPDATE `tabMICE Project`
			SET cost_allocation_target = 'MICE Jobs'
			WHERE cost_allocation_target = 'Exhibit Jobs'
			"""
		)
	if frappe.db.table_exists("tabMICE Project Cost Allocation") and frappe.db.has_column(
		"MICE Project Cost Allocation", "target_type"
	):
		frappe.db.sql(
			"""
			UPDATE `tabMICE Project Cost Allocation`
			SET target_type = 'MICE Job'
			WHERE target_type = 'Exhibit Job'
			"""
		)


def _migrate_cost_allocation_basis_target():
	"""MICE Project Consolidation Charges.allocation_basis Select option."""
	tbl = "tabMICE Project Consolidation Charges"
	if frappe.db.table_exists(tbl) and frappe.db.has_column(
		"MICE Project Consolidation Charges", "allocation_basis"
	):
		frappe.db.sql(
			f"""
			UPDATE `{tbl}`
			SET allocation_basis = 'MICE Job'
			WHERE allocation_basis = 'Exhibit Job'
			"""
		)


def _drop_orphan_legacy_tables():
	"""Drop SQL tables that have no matching DocType row.

	Two sources of orphan tables on a site that has been through multiple
	renames (Event -> Exhibit -> MICE / MICE Event -> MICE Project):

	1. Old Exhibit-era tables removed long ago in code but still present in
	   the DB because schema sync only adds tables, it never drops them
	   (``tabExhibit Docket``, ``tabExhibit Phase Job``,
	   ``tabExhibit Phase Order``, ``tabExhibit Program``,
	   ``tabExhibit Program Order``).
	2. ``tabMICE Event`` — created by schema sync during the brief
	   intermediate naming phase where the main DocType JSON was named
	   ``MICE Event`` before the final rename to ``MICE Project``. Left
	   behind as an empty shell once the JSON flipped to ``MICE Project``.

	Tables are only dropped when (a) the matching DocType row is gone and
	(b) the table is empty, to avoid silently destroying data on a site
	that somehow has rows on the orphan name.
	"""
	candidates = (
		"MICE Event",
		"Exhibit Docket",
		"Exhibit Phase Job",
		"Exhibit Phase Order",
		"Exhibit Program",
		"Exhibit Program Order",
	)
	for dt in candidates:
		# frappe.db.table_exists() expects the DocType name (it prepends ``tab`` itself).
		if not frappe.db.table_exists(dt):
			continue
		if frappe.db.exists("DocType", dt):
			# Real DocType still present - leave the table alone.
			continue
		table = f"tab{dt}"
		row_count = frappe.db.sql(f"SELECT COUNT(*) FROM `{table}`")[0][0]
		if row_count:
			# Has data - refuse to drop. Surface for manual review.
			frappe.log_error(
				message=(
					f"Orphan table `{table}` has {row_count} row(s) but no DocType. "
					"Refusing to drop in v1_3_rename_exhibits_to_mice."
				),
				title="MICE rename: orphan table retained",
			)
			continue
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{table}`")


# ---------------------------------------------------------------------------
# Workspace cleanup
# ---------------------------------------------------------------------------


_WORKSPACE_LINK_REMAP = {
	"MICE Event": "MICE Project",
	"MICE Event Billing": "MICE Project Billing",
	"MICE Event Charges": "MICE Project Charges",
	"MICE Event Delivery": "MICE Project Delivery",
	"MICE Event Milestone": "MICE Project Milestone",
	"MICE Event Docket": "MICE Project Docket",
	"MICE Event Consolidation Charges": "MICE Project Consolidation Charges",
	"MICE Event Cost Allocation": "MICE Project Cost Allocation",
	"Exhibit": "MICE Project",
	"Exhibit Type": "MICE Type",
	"Exhibit Job": "MICE Job",
	"Exhibit Order": "MICE Order",
	"Exhibit Settings": "MICE Settings",
}


def _repoint_workspace_items_off_mice_event():
	"""Re-point Workspace Link / Workspace Sidebar Item / Workspace Shortcut /
	Workspace.content rows that still reference the intermediate ``MICE Event``
	naming (or any other legacy ``Exhibit`` name).

	frappe.rename_doc updates link references for live DocTypes, but the
	short-lived ``MICE Event`` rename was never persisted as a real DocType,
	so any user-customized workspace row that latched onto it stays stale
	forever and causes ``DocType MICE Event not found`` on every page load.
	"""
	for child_table, link_col in (
		("Workspace Link", "link_to"),
		("Workspace Sidebar Item", "link_to"),
		("Workspace Shortcut", "link_to"),
	):
		if not frappe.db.table_exists(child_table):
			continue
		if not frappe.db.has_column(child_table, link_col):
			continue
		table = f"tab{child_table}"
		for old_name, new_name in _WORKSPACE_LINK_REMAP.items():
			frappe.db.sql(
				f"UPDATE `{table}` SET `{link_col}` = %s WHERE `{link_col}` = %s",
				(new_name, old_name),
			)
			if frappe.db.has_column(child_table, "label"):
				frappe.db.sql(
					f"UPDATE `{table}` SET label = %s WHERE label = %s",
					(new_name, old_name),
				)

	if not frappe.db.table_exists("Workspace") or not frappe.db.has_column("Workspace", "content"):
		return
	for old_name, new_name in _WORKSPACE_LINK_REMAP.items():
		# Workspace.content is a JSON blob with double-quoted names.
		quoted_old = f'"{old_name}"'
		quoted_new = f'"{new_name}"'
		frappe.db.sql(
			"UPDATE `tabWorkspace` SET content = REPLACE(content, %s, %s) "
			"WHERE content LIKE %s",
			(quoted_old, quoted_new, f"%{quoted_old}%"),
		)
