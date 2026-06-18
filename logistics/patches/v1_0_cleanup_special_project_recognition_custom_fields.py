# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Remove legacy Custom Fields on Special Project that duplicate fields now defined in
``special_project.json`` (Revenue & Cost Recognition + invoice lifecycle).

Mirrors the cleanup already done for Air Shipment in
``v1_0_cleanup_air_shipment_recognition_custom_fields``: duplicate fieldnames in
``Meta.fields`` break Frappe's ``sort_fields()`` fast path
(``len(field_order) == len(self.fields)``), which scrambles the form layout.
"""

import frappe

_SPECIAL_PROJECT_DUPLICATE_FIELDNAMES = (
	# Revenue & Cost Recognition section
	"recognition_section",
	"wip_recognition_enabled",
	"accrual_recognition_enabled",
	"recognition_policy_reference",
	"recognition_date_basis",
	"wip_recognition_date_basis",
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
	# Invoice lifecycle section
	"invoice_section",
	"sales_invoice",
	"date_sales_invoice_requested",
	"date_sales_invoice_submitted",
	"column_break_invoice",
	"purchase_invoice",
	"date_purchase_invoice_requested",
	"date_purchase_invoice_submitted",
	"column_break_invoice_lifecycle",
	"fully_invoiced",
	"date_fully_invoiced",
	"fully_paid",
	"date_fully_paid",
	"costs_fully_paid",
	"date_costs_fully_paid",
)


def execute():
	removed = 0
	for fn in _SPECIAL_PROJECT_DUPLICATE_FIELDNAMES:
		names = frappe.get_all(
			"Custom Field",
			filters={"dt": "Special Project", "fieldname": fn},
			pluck="name",
		)
		for name in names:
			frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
			removed += 1
			print(f"Removed duplicate Special Project Custom Field: {name}")

	if removed:
		frappe.clear_cache(doctype="Special Project")
		print(f"Removed {removed} Special Project recognition / invoice duplicate Custom Field(s)")
	return True
