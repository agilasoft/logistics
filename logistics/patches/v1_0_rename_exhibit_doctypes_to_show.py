# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Events doctypes to align with Special Projects naming.

Event = programme (was Exhibit Program). Event Job / Event Order = task job / order.
Child tables use Event * prefix where Special Project uses Special Project *.
"""

from __future__ import annotations

import frappe

# Child tables and leaf doctypes first, then parents, then reports.
_RENAMES = (
	("Exhibit Phase Job Resource", "Event Job Resource"),
	("Exhibit Program Milestone", "Event Milestone"),
	("Exhibit Program Billing", "Event Billing"),
	("Exhibit Program Delivery", "Event Delivery"),
	("Exhibit Scoping Activity", "Event Scoping Activity"),
	("Exhibit Program Charges", "Event Charges"),
	("Exhibit Service Activity", "Event Service Activity"),
	("Exhibit Phase Job", "Event Job"),
	("Exhibit Phase Order", "Event Order"),
	("Exhibit Program", "Event"),
	("Exhibit Settings", "Event Settings"),
	("Exhibit Pipeline Report", "Event Pipeline Report"),
	("Exhibit Activity Status Report", "Event Activity Status Report"),
	("Exhibit Billing Status Report", "Event Billing Status Report"),
)


def execute():
	frappe.flags.in_patch = True
	try:
		for old_name, new_name in _RENAMES:
			if not frappe.db.exists("DocType", old_name):
				continue
			if frappe.db.exists("DocType", new_name):
				continue
			frappe.rename_doc(
				"DocType",
				old_name,
				new_name,
				force=True,
				merge=False,
			)
	finally:
		frappe.flags.in_patch = False
