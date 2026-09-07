# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


CHARGE_CHILD_TABLES = (
	"Sales Quote Charge",
	"Tariff Charge",
	"Air Booking Charges",
	"Air Shipment Charges",
	"Sea Booking Charges",
	"Sea Shipment Charges",
	"Transport Job Charges",
	"Transport Order Charges",
	"Declaration Charges",
	"Declaration Order Charges",
	"Warehouse Job Charges",
	"Special Project Charges",
	"MICE Project Charges",
	"Exhibit Charges",
)


def execute():
	"""Enable Apply 95/5 rule on Freight and backfill charge-row Taxes gates."""
	if not frappe.db.has_column("Charge Category", "apply_95_5_rule"):
		return
	if frappe.db.exists("Charge Category", "Freight"):
		frappe.db.set_value(
			"Charge Category",
			"Freight",
			{"apply_95_5_rule": 1},
			update_modified=False,
		)

	for doctype in CHARGE_CHILD_TABLES:
		if not frappe.db.table_exists(doctype):
			continue
		if not frappe.db.has_column(doctype, "category_apply_95_5_rule"):
			continue
		table = f"tab{doctype}"
		frappe.db.sql(
			f"""
			UPDATE `{table}` ch
			LEFT JOIN `tabCharge Category` cc ON cc.name = ch.charge_category
			SET ch.category_apply_95_5_rule = IFNULL(cc.apply_95_5_rule, 0)
			"""
		)
