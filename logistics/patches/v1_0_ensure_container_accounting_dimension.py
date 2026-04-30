# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Ensure Accounting Dimension for logistics Container exists (GL / PI / JE dimensions)."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Accounting Dimension"):
		return
	if not frappe.db.exists("DocType", "Container"):
		return
	if frappe.db.exists("Accounting Dimension", "Container"):
		return
	if frappe.db.get_value("Accounting Dimension", {"document_type": "Container"}, "name"):
		return

	doc = frappe.new_doc("Accounting Dimension")
	doc.document_type = "Container"
	doc.label = "Container"
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
