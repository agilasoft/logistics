# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Use DYNAMIC row format on `tabAir Shipment` so InnoDB can store wide rows (many
VARCHAR columns) using off-page storage. Reduces OperationalError 1118 during
`bench migrate` on sites with a near-limit table definition.
"""

import frappe


def execute():
	if not frappe.db.has_table("tabAir Shipment"):
		return True
	try:
		row = frappe.db.sql("SHOW TABLE STATUS LIKE %s", ("tabAir Shipment",), as_dict=True)
		if row and row[0].get("Row_format", "").lower() == "dynamic":
			return True
	except Exception:
		pass
	try:
		frappe.db.sql_ddl("ALTER TABLE `tabAir Shipment` ROW_FORMAT=DYNAMIC")
		print("Set tabAir Shipment ROW_FORMAT=DYNAMIC")
	except Exception as e:
		print(f"Could not set tabAir Shipment ROW_FORMAT=DYNAMIC (non-fatal): {e}")
	return True
