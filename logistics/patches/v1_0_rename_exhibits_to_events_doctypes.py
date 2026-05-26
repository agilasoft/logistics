# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Show / Exhibit doctypes to Event family and desk Events icon."""

from __future__ import annotations

import frappe

_RENAMES = (
	("Exhibit Job Resource", "Event Job Resource"),
	("Show Milestone", "Event Milestone"),
	("Show Billing", "Event Billing"),
	("Show Delivery", "Event Delivery"),
	("Show Scoping Activity", "Event Scoping Activity"),
	("Show Charges", "Event Charges"),
	("Show Service Activity", "Event Service Activity"),
	("Exhibit Job", "Event Job"),
	("Exhibit Order", "Event Order"),
	("Exhibit Plan", "Event Plan"),
	("Show", "Event"),
	("Show Settings", "Event Settings"),
	("Show Venue", "Event Venue"),
	("Show Pipeline Report", "Event Pipeline Report"),
	("Show Activity Status Report", "Event Activity Status Report"),
	("Show Billing Status Report", "Event Billing Status Report"),
	("Desktop Icon", "Exhibits", "Events"),
)


def execute():
	frappe.flags.in_patch = True
	try:
		for item in _RENAMES:
			if len(item) == 3:
				doctype, old_name, new_name = item
			else:
				old_name, new_name = item
				doctype = "DocType"
			if not frappe.db.exists(doctype, old_name):
				continue
			if frappe.db.exists(doctype, new_name):
				continue
			frappe.rename_doc(doctype, old_name, new_name, force=True, merge=False)
	finally:
		frappe.flags.in_patch = False
