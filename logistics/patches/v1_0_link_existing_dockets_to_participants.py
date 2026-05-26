# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill `docket` link on existing Exhibit Participant rows.

The Dockets table and the Participants table on the Exhibit form have been merged into
a single grid (Exhibit.exhibit_participants). The child DocType `Exhibit Participant`
now carries a `docket` Link field pointing at the matching Docket so the merged grid
can show / open it directly.

For each existing Docket, this patch finds the matching Exhibit Participant row
(same exhibit + customer + role=Exhibitor) and writes the docket name into its
`docket` field. Re-runnable: it only updates rows whose docket value differs.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("Docket"):
		return
	if not frappe.db.table_exists("Exhibit Participant"):
		return
	if not frappe.db.has_column("Exhibit Participant", "docket"):
		# Schema sync should have added the column; nothing we can do otherwise.
		return

	dockets = frappe.db.sql(
		"""
		SELECT name, exhibit, exhibitor
		FROM `tabDocket`
		WHERE IFNULL(exhibit, '') != '' AND IFNULL(exhibitor, '') != ''
		""",
		as_dict=True,
	)
	updated = 0
	for d in dockets:
		try:
			rows = frappe.db.sql(
				"""
				SELECT name, IFNULL(docket, '') AS docket
				FROM `tabExhibit Participant`
				WHERE parent = %(exhibit)s
				  AND parenttype = 'Exhibit'
				  AND parentfield = 'exhibit_participants'
				  AND customer = %(customer)s
				  AND participant_role = 'Exhibitor'
				""",
				{"exhibit": d["exhibit"], "customer": d["exhibitor"]},
				as_dict=True,
			)
		except Exception:
			rows = []
		for row in rows:
			if row.get("docket") == d["name"]:
				continue
			try:
				frappe.db.set_value(
					"Exhibit Participant",
					row["name"],
					"docket",
					d["name"],
					update_modified=False,
				)
				updated += 1
			except Exception:
				frappe.log_error(
					title="Docket-participant backfill failed",
					message=frappe.get_traceback(),
				)

	if updated:
		frappe.db.commit()
