# Migrate Sea Shipment transport_mode and house_type to align with Sea Booking options
from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("Sea Shipment"):
		return

	# transport_mode: "Sea" -> "FCL" (Sea Shipment now uses FCL/LCL/Break Bulk like Sea Booking)
	frappe.db.sql("""
		UPDATE `tabSea Shipment`
		SET transport_mode = 'FCL'
		WHERE transport_mode = 'Sea' OR transport_mode IS NULL OR transport_mode = ''
	""")

	# house_type: keep original values (Standard House, Co-load Master, etc.) per HOUSE_TYPE_DESIGN.md
	# Only normalize Break-Bulk -> Break Bulk
	frappe.db.sql("""
		UPDATE `tabSea Shipment`
		SET house_type = 'Break Bulk'
		WHERE house_type = 'Break-Bulk'
	""")

	frappe.db.commit()
