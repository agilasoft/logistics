# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove obsolete DocType Special Project Activity (replaced by Internal Job Detail on Special Project)."""

from __future__ import unicode_literals

import frappe


def execute():
	name = "Special Project Activity"
	if not frappe.db.exists("DocType", name):
		return
	frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
	frappe.db.commit()
