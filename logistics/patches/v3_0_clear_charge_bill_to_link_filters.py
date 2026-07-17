# Copyright (c) 2026, Agilasoft and contributors
"""Clear Customer.disabled link_filters on charge Bill To fields (#1266).

Static link_filters on bill_to (Customer.disabled) trigger a permlevel-0 field
permission check (Customer.0) for roles that can edit jobs but cannot read base
Customer fields. Bill To filtering is handled by charge_bill_to.js set_query and
get_eligible_bill_to_customers on the server instead.
"""

import frappe

# Keep in sync with logistics/tools/merge_master_link_filters.py
CHARGE_BILL_TO_FIELDS = [
	("Air Booking Charges", "bill_to"),
	("Air Shipment Charges", "bill_to"),
	("Change Request Charge", "bill_to"),
	("Declaration Charges", "bill_to"),
	("Declaration Order Charges", "bill_to"),
	("Exhibit Charges", "bill_to"),
	("MICE Project Charges", "bill_to"),
	("Sales Quote Air Freight", "bill_to"),
	("Sales Quote Charge", "bill_to"),
	("Sales Quote Customs", "bill_to"),
	("Sales Quote Sea Freight", "bill_to"),
	("Sales Quote Transport", "bill_to"),
	("Sea Booking Charges", "bill_to"),
	("Sea Shipment Charges", "bill_to"),
	("Special Project Charges", "bill_to"),
	("Tariff Charge", "bill_to"),
	("Transport Job Charges", "bill_to"),
	("Transport Order Charges", "bill_to"),
]


def execute():
	cleared = []
	for parent, fieldname in CHARGE_BILL_TO_FIELDS:
		if not frappe.db.exists("DocField", {"parent": parent, "fieldname": fieldname}):
			continue
		if not frappe.db.get_value("DocField", {"parent": parent, "fieldname": fieldname}, "link_filters"):
			continue
		frappe.db.set_value(
			"DocField",
			{"parent": parent, "fieldname": fieldname},
			"link_filters",
			None,
		)
		cleared.append(f"{parent}.{fieldname}")

	if cleared:
		frappe.clear_cache()
		frappe.logger().info(
			"Cleared charge bill_to link_filters on: %s", ", ".join(cleared)
		)
