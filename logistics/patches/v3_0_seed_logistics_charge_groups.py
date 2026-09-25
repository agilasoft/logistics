# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Seed Logistics Charge Group rows matching charge row Select options."""

import frappe

DEFAULT_GROUPS = (
	"Origin",
	"Destination",
	"Freight",
	"Customs",
	"Documentation",
	"Storage",
	"Insurance",
	"Other",
)


def execute():
	if not frappe.db.exists("DocType", "Logistics Charge Group"):
		return
	for name in DEFAULT_GROUPS:
		if frappe.db.exists("Logistics Charge Group", name):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Logistics Charge Group",
				"group_name": name,
			}
		)
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
