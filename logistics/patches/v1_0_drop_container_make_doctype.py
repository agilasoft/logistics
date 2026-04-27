# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""Remove unused Container Make DocType."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Container Make"):
		return
	frappe.delete_doc("DocType", "Container Make", force=True, ignore_permissions=True)
