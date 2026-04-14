# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Remove legacy Custom Fields on Air Shipment that duplicate fields now defined in
`air_shipment.json` (Revenue & Cost Recognition + related amounts/JEs).

Duplicate fieldnames in Meta.fields break Frappe's sort_fields() fast path
(len(field_order) == len(self.fields)), which scrambles layout (single column,
wrong field order vs DocType Form builder).
"""

import frappe

# Must match standard DocType JSON + old split basis fields from install_recognition_fields
_AIR_SHIPMENT_DUPLICATE_FIELDNAMES = (
	"recognition_section",
	"wip_recognition_enabled",
	"wip_recognition_date_basis",
	"accrual_recognition_enabled",
	"accrual_recognition_date_basis",
	"recognition_date",
	"column_break_recognition",
	"estimated_revenue",
	"wip_amount",
	"recognized_revenue",
	"wip_journal_entry",
	"wip_adjustment_journal_entry",
	"wip_closed",
	"column_break_accrual",
	"estimated_costs",
	"accrual_amount",
	"recognized_costs",
	"accrual_journal_entry",
	"accrual_adjustment_journal_entry",
	"accrual_closed",
)


def execute():
	removed = 0
	for fn in _AIR_SHIPMENT_DUPLICATE_FIELDNAMES:
		names = frappe.get_all(
			"Custom Field",
			filters={"dt": "Air Shipment", "fieldname": fn},
			pluck="name",
		)
		for name in names:
			frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
			removed += 1
			print(f"Removed duplicate Air Shipment Custom Field: {name}")

	if removed:
		frappe.clear_cache(doctype="Air Shipment")
		print(f"Removed {removed} Air Shipment recognition duplicate Custom Field(s)")
	return True
