# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute():
	"""After schema sync: map legacy Change Request Charge rows to Sales Quote–aligned cost fields."""
	if not frappe.db.has_table("_cr_charge_legacy_backup"):
		return
	rows = frappe.db.sql("SELECT * FROM `_cr_charge_legacy_backup`", as_dict=True)
	for r in rows:
		if not frappe.db.exists("Change Request Charge", r.get("name")):
			continue
		remarks = (r.get("remarks") or "").strip()
		frappe.db.set_value(
			"Change Request Charge",
			r["name"],
			{
				"cost_calculation_method": "Per Unit",
				"cost_quantity": flt(r.get("quantity")) or 1,
				"cost_currency": r.get("currency"),
				"unit_cost": r.get("unit_cost"),
				"cost_uom": r.get("uom"),
				"estimated_cost": r.get("amount"),
				"cost_calc_notes": (remarks[:140] if remarks else None),
			},
			update_modified=False,
		)
	frappe.db.sql("DROP TABLE IF EXISTS `_cr_charge_legacy_backup`")
	frappe.db.commit()
