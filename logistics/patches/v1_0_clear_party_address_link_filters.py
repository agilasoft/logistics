# Copyright (c) 2026, www.agilasoft.com and contributors
"""Clear Address link_filters on party shipper/consignee address fields.

JSON link_filters on these fields drop logistics.address.query_for_link (address_query)
and cause PermissionError on Address.link_doctype when opening the link picker.
"""

import frappe

PARTY_ADDRESS_FIELDS = [
	("MICE Order", "shipper_address"),
	("MICE Order", "consignee_address"),
	("MICE Job", "shipper_address"),
	("MICE Job", "consignee_address"),
	("Exhibit Job", "shipper_address"),
	("Exhibit Job", "consignee_address"),
	("Project Job", "shipper_address"),
	("Project Job", "consignee_address"),
]


def execute():
	cleared = []
	for parent, fieldname in PARTY_ADDRESS_FIELDS:
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
			"Cleared party Address link_filters on: %s", ", ".join(cleared)
		)
