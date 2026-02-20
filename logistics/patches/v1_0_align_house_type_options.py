# Revert to original House Type values per HOUSE_TYPE_DESIGN.md
# Reverts v1_0_align_sea_shipment_fields: Direct->Standard House, Consolidation->Co-load Master
# Also normalizes Break-Bulk -> Break Bulk
from __future__ import unicode_literals

import frappe


def execute():
	# Revert simplified values to original industry values
	revert_map = {
		"Direct": "Standard House",
		"Consolidation": "Co-load Master",
	}
	for doctype, fieldname in [
		("Sea Booking", "house_type"),
		("Sea Shipment", "house_type"),
		("Air Booking", "house_type"),
		("Air Shipment", "house_type"),
		("Sales Quote Air Freight", "air_house_type"),
		("Sales Quote Sea Freight", "sea_house_type"),
		("One-Off Quote", "air_house_type"),
	]:
		_migrate_doctype(doctype, fieldname, revert_map)

	# Normalize Break-Bulk -> Break Bulk
	for doctype, fieldname in [
		("Sea Booking", "house_type"),
		("Sea Shipment", "house_type"),
		("Air Booking", "house_type"),
		("Air Shipment", "house_type"),
		("Sales Quote Air Freight", "air_house_type"),
		("Sales Quote Sea Freight", "sea_house_type"),
		("One-Off Quote", "air_house_type"),
	]:
		_normalize_break_bulk(doctype, fieldname)

	# Single doctypes
	_migrate_single("Air Freight Settings", "default_house_type", revert_map)
	try:
		_migrate_single("Sea Freight Settings", "default_house_type", revert_map)
	except Exception:
		pass

	frappe.db.commit()


def _migrate_doctype(doctype, fieldname, revert_map):
	if not frappe.db.table_exists(doctype):
		return
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	for old_val, new_val in revert_map.items():
		frappe.db.sql(
			"UPDATE `tab{0}` SET `{1}` = %(new_val)s WHERE `{1}` = %(old_val)s".format(
				doctype, fieldname
			),
			{"old_val": old_val, "new_val": new_val},
		)


def _normalize_break_bulk(doctype, fieldname):
	if not frappe.db.table_exists(doctype):
		return
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	frappe.db.sql(
		"UPDATE `tab{0}` SET `{1}` = 'Break Bulk' WHERE `{1}` = 'Break-Bulk'".format(
			doctype, fieldname
		)
	)


def _migrate_single(doctype, fieldname, revert_map):
	if not frappe.db.table_exists(doctype):
		return
	if not frappe.get_meta(doctype).has_field(fieldname):
		return
	try:
		val = frappe.db.get_single_value(doctype, fieldname)
		if val in revert_map:
			frappe.db.set_value(doctype, doctype, fieldname, revert_map[val])
		elif val == "Break-Bulk":
			frappe.db.set_value(doctype, doctype, fieldname, "Break Bulk")
	except Exception:
		pass
