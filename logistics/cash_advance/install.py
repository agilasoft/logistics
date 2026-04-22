# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

import frappe


def after_migrate():
	if frappe.flags.in_install:
		return
	if not frappe.db.exists("DocType", "Cash Advance Settings"):
		return
	if frappe.db.exists("Cash Advance Settings", "Cash Advance Settings"):
		return
	doc = frappe.new_doc("Cash Advance Settings")
	doc.insert(ignore_permissions=True)
