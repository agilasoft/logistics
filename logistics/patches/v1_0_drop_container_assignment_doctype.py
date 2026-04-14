# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""Remove superseded Container Assignment DocType (logic lives on Container)."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Container Assignment"):
		return
	frappe.delete_doc("DocType", "Container Assignment", force=True, ignore_permissions=True)
