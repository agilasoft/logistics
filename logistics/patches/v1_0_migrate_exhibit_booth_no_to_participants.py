# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move legacy Exhibit.booth_no values into Exhibit Participants child rows."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabExhibit Participant"):
		return
	if not frappe.db.has_column("Exhibit", "booth_no"):
		return

	events = frappe.db.sql(
		"""
		SELECT name, customer, booth_no
		FROM `tabExhibit`
		WHERE IFNULL(booth_no, '') != ''
		""",
		as_dict=True,
	)

	for row in events:
		if frappe.db.exists(
			"Exhibit Participant",
			{"parent": row.name, "parenttype": "Exhibit", "parentfield": "exhibit_participants"},
		):
			continue

		doc = frappe.get_doc("Exhibit", row.name)
		doc.append(
			"exhibit_participants",
			{
				"participant_role": "Exhibitor",
				"customer": row.customer,
				"booth_no": row.booth_no,
			},
		)
		doc.save(ignore_permissions=True)

	frappe.db.commit()
