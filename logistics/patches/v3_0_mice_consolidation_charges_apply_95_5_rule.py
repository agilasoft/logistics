# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


DOCTYPE = "MICE Project Consolidation Charges"


def execute():
	"""Backfill Taxes-section gate on MICE Project Consolidation Charges."""
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	if not frappe.db.has_column("Charge Category", "apply_95_5_rule"):
		return
	if not frappe.db.has_column(DOCTYPE, "category_apply_95_5_rule"):
		return

	table = f"tab{DOCTYPE}"
	frappe.db.sql(
		f"""
		UPDATE `{table}` ch
		LEFT JOIN `tabCharge Category` cc ON cc.name = ch.charge_category
		SET ch.category_apply_95_5_rule = IFNULL(cc.apply_95_5_rule, 0)
		"""
	)
