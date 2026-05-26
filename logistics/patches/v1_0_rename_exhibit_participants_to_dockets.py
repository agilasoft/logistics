# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename the Exhibit child-table fieldname ``exhibit_participants`` -> ``dockets``.

The Dockets tab on the Exhibit form is now exhibitor-only. The child DocType
``Exhibit Participant`` is still used, but it is linked to the parent Exhibit via
``parentfield = 'dockets'`` (was ``'exhibit_participants'``).

This patch also drops any rows whose legacy ``participant_role`` is not "Exhibitor",
because non-exhibitor participants are no longer tracked on the Exhibit.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("Exhibit Participant"):
		return

	# Drop non-Exhibitor rows (we only track exhibitors now).
	if frappe.db.has_column("Exhibit Participant", "participant_role"):
		frappe.db.sql(
			"""
			DELETE FROM `tabExhibit Participant`
			WHERE parenttype = 'Exhibit'
			  AND IFNULL(participant_role, '') NOT IN ('', 'Exhibitor')
			"""
		)

	# Point surviving rows at the new parentfield.
	frappe.db.sql(
		"""
		UPDATE `tabExhibit Participant`
		SET parentfield = 'dockets'
		WHERE parenttype = 'Exhibit'
		  AND parentfield = 'exhibit_participants'
		"""
	)

	frappe.db.commit()
	frappe.clear_cache(doctype="Exhibit")
	frappe.clear_cache(doctype="Exhibit Participant")
