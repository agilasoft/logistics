# Copyright (c) 2026, www.agilasoft.com and contributors
"""Clear Address link_filters on fields that use logistics.address.query_for_* in JS.

Frappe link.js apply_link_field_filters() replaces set_query and drops the custom
address_query when JSON link_filters are present. Merged link_doctype filters then
hit search_link on Address directly and raise PermissionError on Address.link_doctype.
"""

import frappe

# Keep in sync with logistics/tools/merge_master_link_filters.py
ADDRESS_CLIENT_QUERY_FIELDS = [
	("Docket", "site"),
	("MICE Order", "site"),
	("Exhibit Order", "site"),
	("MICE Job", "site"),
	("Exhibit Job", "site"),
	("Project Order", "site"),
	("Project Job", "site"),
	("Lifecycle Job", "sp_site"),
	("Sea Booking", "shipper_address"),
	("Sea Booking", "consignee_address"),
	("Sea Shipment", "shipper_address"),
	("Sea Shipment", "consignee_address"),
	("Air Booking", "shipper_address"),
	("Air Booking", "consignee_address"),
	("Air Shipment", "shipper_address"),
	("Air Shipment", "consignee_address"),
	("MICE Order", "shipper_address"),
	("MICE Order", "consignee_address"),
	("MICE Job", "shipper_address"),
	("MICE Job", "consignee_address"),
	("Exhibit Job", "shipper_address"),
	("Exhibit Job", "consignee_address"),
	("Project Job", "shipper_address"),
	("Project Job", "consignee_address"),
	("Warehouse Settings", "warehouse_contract_address"),
	# Legacy names before exhibits rebrand (orphan DocField rows).
	("Event Plan", "site"),
	("Event Order", "site"),
	("Event Job", "site"),
	("Event Job", "shipper_address"),
	("Event Job", "consignee_address"),
]


def execute():
	cleared = []
	for parent, fieldname in ADDRESS_CLIENT_QUERY_FIELDS:
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
			"Cleared Address link_filters on: %s", ", ".join(cleared)
		)
