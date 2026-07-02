# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill is_active on Official Appointment Status records created before the field was added."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Official Appointment Status"):
		return

	# Avoid frappe.db.set_value with "is not set" on Check/tinyint — MariaDB can error on ''.
	frappe.db.sql(
		"""
		UPDATE `tabOfficial Appointment Status`
		SET is_active = 1
		WHERE is_active IS NULL
		"""
	)
	frappe.db.commit()
