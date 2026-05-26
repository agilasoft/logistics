# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop legacy Special Project Milestone rows after child table matches Sea Shipment Milestone (milestone link, not job_milestone)."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Special Project Milestone"):
		return
	try:
		frappe.db.sql("DELETE FROM `tabSpecial Project Milestone` WHERE IFNULL(`milestone`, '') = ''")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Special Project Milestone cleanup")
