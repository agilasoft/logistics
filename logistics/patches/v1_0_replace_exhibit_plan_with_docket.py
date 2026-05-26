# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop the legacy Exhibit Plan DocType after it has been replaced by Docket.

The Exhibits module now uses the Docket DocType (one per exhibitor on an Exhibit),
and the participants table on Exhibit doubles as the dockets table.

This patch:
  1. Re-points any Exhibit Charges rows that were parented to an Exhibit Plan onto the
     underlying Exhibit, so charge history is not lost.
  2. Removes the `tabExhibit Plan` table if it still exists.
  3. Deletes the `DocType` record for Exhibit Plan (so the orphan cleanup will not
     re-create it on subsequent migrations).
  4. Cleans Exhibit Plan references out of Workspace links / shortcuts / sidebars in
     case a customised site has them.
"""

from __future__ import annotations

import frappe


def execute():
	_repoint_exhibit_charges()
	_drop_exhibit_plan_table()
	_delete_doctype_record()
	_clean_workspace_links()
	_clean_workspace_sidebar()
	frappe.db.commit()


def _repoint_exhibit_charges():
	"""Move any Exhibit Charges parented to an Exhibit Plan onto the underlying Exhibit."""
	if not frappe.db.table_exists("Exhibit Plan"):
		return
	try:
		rows = frappe.db.sql(
			"""
			SELECT ec.name AS charge_row, ec.parent AS plan_name, ep.exhibit AS exhibit
			FROM `tabExhibit Charges` ec
			INNER JOIN `tabExhibit Plan` ep ON ep.name = ec.parent
			WHERE ec.parenttype = 'Exhibit Plan'
			""",
			as_dict=True,
		)
	except Exception:
		rows = []
	for row in rows:
		if not row.get("exhibit"):
			continue
		try:
			frappe.db.set_value(
				"Exhibit Charges",
				row["charge_row"],
				{
					"parenttype": "Exhibit",
					"parent": row["exhibit"],
					"parentfield": "charges",
				},
				update_modified=False,
			)
		except Exception:
			frappe.log_error(
				title="Docket migration: repoint charge failed",
				message=frappe.get_traceback(),
			)


def _drop_exhibit_plan_table():
	if frappe.db.table_exists("Exhibit Plan"):
		try:
			frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabExhibit Plan`")
		except Exception:
			frappe.log_error(
				title="Docket migration: drop tabExhibit Plan failed",
				message=frappe.get_traceback(),
			)


def _delete_doctype_record():
	if not frappe.db.exists("DocType", "Exhibit Plan"):
		return
	try:
		frappe.delete_doc("DocType", "Exhibit Plan", ignore_missing=True, force=True)
	except Exception:
		try:
			frappe.db.delete("DocType", {"name": "Exhibit Plan"})
		except Exception:
			frappe.log_error(
				title="Docket migration: delete Exhibit Plan DocType failed",
				message=frappe.get_traceback(),
			)


def _clean_workspace_links():
	"""Remove Exhibit Plan entries from Workspace.links and Workspace.shortcuts."""
	try:
		frappe.db.delete(
			"Workspace Link",
			{"link_to": "Exhibit Plan", "link_type": "DocType"},
		)
	except Exception:
		pass
	try:
		frappe.db.delete(
			"Workspace Shortcut",
			{"link_to": "Exhibit Plan", "type": "DocType"},
		)
	except Exception:
		pass


def _clean_workspace_sidebar():
	"""Remove any Workspace Sidebar Item rows that still reference Exhibit Plan."""
	if not frappe.db.exists("DocType", "Workspace Sidebar Item"):
		return
	try:
		frappe.db.delete(
			"Workspace Sidebar Item",
			{"link_to": "Exhibit Plan", "link_type": "DocType"},
		)
	except Exception:
		pass
