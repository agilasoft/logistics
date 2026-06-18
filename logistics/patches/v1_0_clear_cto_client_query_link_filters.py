# Copyright (c) 2026, www.agilasoft.com and contributors
"""Clear Cargo Terminal Operator link_filters on fields that use custom set_query in JS.

Frappe link.js apply_link_field_filters() replaces set_query and merges its filters
(e.g. shipping_line, port) into a standard search_link on Cargo Terminal Operator,
which raises PermissionError because CTO has no shipping_line field.
"""

import frappe

# Keep in sync with logistics/tools/merge_master_link_filters.py
CTO_CLIENT_QUERY_FIELDS = [
	("Master Bill", "origin_cto"),
	("Master Bill", "destination_cto"),
	("Sea Booking", "origin_cto"),
	("Sea Booking", "destination_cto"),
	("Sea Shipment", "origin_cto"),
	("Sea Shipment", "destination_cto"),
	("Shipping Line CTO", "sea_cto"),
]


def execute():
	cleared = []
	for parent, fieldname in CTO_CLIENT_QUERY_FIELDS:
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
			"Cleared CTO link_filters on: %s", ", ".join(cleared)
		)
