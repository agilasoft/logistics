# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Event Venue master and drop link column on Event if present."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("DocType", "Event Venue"):
		frappe.delete_doc("DocType", "Event Venue", force=True, ignore_missing=True)

	if frappe.db.table_exists("tabEvent") and frappe.db.has_column("Event", "event_venue"):
		frappe.db.sql("ALTER TABLE `tabEvent` DROP COLUMN `event_venue`")

	if frappe.db.table_exists("tabSales Quote") and frappe.db.has_column(
		"Sales Quote", "exhibit_event_venue"
	):
		frappe.db.sql("ALTER TABLE `tabSales Quote` DROP COLUMN `exhibit_event_venue`")

	frappe.db.commit()
	frappe.clear_cache()
