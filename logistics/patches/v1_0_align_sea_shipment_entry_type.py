# Migrate entry_type to industry-standard options: Direct, Transit, Transshipment, ATA Carnet
# Applies to: Sea Shipment, Air Booking, Air Shipment, Air Freight Settings
from __future__ import unicode_literals

import frappe

ENTRY_TYPE_MAP = {
	"Customs Permit": "Direct",
	"ATA Carnet": "ATA Carnet",  # Already correct
	"Break-Bulk": "Direct",
}


def execute():
	# Sea Shipment
	if frappe.db.table_exists("Sea Shipment"):
		for old_val, new_val in ENTRY_TYPE_MAP.items():
			if old_val != new_val:
				frappe.db.sql(
					"UPDATE `tabSea Shipment` SET entry_type = %(new_val)s WHERE entry_type = %(old_val)s",
					{"old_val": old_val, "new_val": new_val},
				)

	# Air Booking
	if frappe.db.table_exists("Air Booking"):
		for old_val, new_val in ENTRY_TYPE_MAP.items():
			if old_val != new_val:
				frappe.db.sql(
					"UPDATE `tabAir Booking` SET entry_type = %(new_val)s WHERE entry_type = %(old_val)s",
					{"old_val": old_val, "new_val": new_val},
				)

	# Air Shipment
	if frappe.db.table_exists("Air Shipment"):
		for old_val, new_val in ENTRY_TYPE_MAP.items():
			if old_val != new_val:
				frappe.db.sql(
					"UPDATE `tabAir Shipment` SET entry_type = %(new_val)s WHERE entry_type = %(old_val)s",
					{"old_val": old_val, "new_val": new_val},
				)

	# Air Freight Settings - default_entry_type
	if frappe.db.table_exists("Air Freight Settings"):
		frappe.db.sql(
			"UPDATE `tabAir Freight Settings` SET default_entry_type = 'Direct' WHERE default_entry_type = 'Break-Bulk'"
		)

	frappe.db.commit()
