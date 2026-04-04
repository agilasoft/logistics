# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Before schema sync: snapshot legacy Change Request Charge columns for migration."""
	if not frappe.db.has_table("tabChange Request Charge"):
		return
	cols = {r[0] for r in frappe.db.sql("SHOW COLUMNS FROM `tabChange Request Charge`")}
	if "quantity" not in cols:
		return
	if frappe.db.has_table("_cr_charge_legacy_backup"):
		frappe.db.sql("DROP TABLE IF EXISTS `_cr_charge_legacy_backup`")
	frappe.db.sql(
		"""
		CREATE TABLE `_cr_charge_legacy_backup` AS
		SELECT name, quantity, unit_cost, currency, uom, amount, remarks
		FROM `tabChange Request Charge`
		"""
	)
	frappe.db.commit()
