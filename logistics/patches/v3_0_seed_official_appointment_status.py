# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed default Official Appointment Status options for MICE Project."""

from __future__ import annotations

import frappe

OFFICIAL_APPOINTMENT_STATUSES = (
	"Sole Appointment",
	"1 of 2 Appointment",
	"1 of 3 Appointment",
	"Not Appointed",
	"No Appointed Official",
	"On Process",
)


def execute():
	if not frappe.db.exists("DocType", "Official Appointment Status"):
		return

	for label in OFFICIAL_APPOINTMENT_STATUSES:
		if frappe.db.exists("Official Appointment Status", label):
			frappe.db.set_value(
				"Official Appointment Status",
				label,
				"is_active",
				1,
				update_modified=False,
			)
			continue
		doc = frappe.new_doc("Official Appointment Status")
		doc.official_appointment_status = label
		doc.is_active = 1
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
