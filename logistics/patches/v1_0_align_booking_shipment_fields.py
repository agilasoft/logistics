# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Align Booking and Shipment field names: goods_value, chargeable, notify_party."""

import frappe


def execute():
	# Sea Booking: good_value -> goods_value, chargeable_weight -> chargeable,
	# notify_to_party -> notify_party, notify_to_address -> notify_party_address
	_rename_column_if_exists("Sea Booking", "good_value", "goods_value")
	_rename_column_if_exists("Sea Booking", "chargeable_weight", "chargeable")
	_rename_column_if_exists("Sea Booking", "notify_to_party", "notify_party")
	_rename_column_if_exists("Sea Booking", "notify_to_address", "notify_party_address")

	# Sea Shipment: good_value -> goods_value, notify_to_* -> notify_*
	_rename_column_if_exists("Sea Shipment", "good_value", "goods_value")
	_rename_column_if_exists("Sea Shipment", "notify_to_party", "notify_party")
	_rename_column_if_exists("Sea Shipment", "notify_to_address", "notify_party_address")

	frappe.db.commit()


def _rename_column_if_exists(doctype: str, old_name: str, new_name: str) -> None:
	if not frappe.db.exists("DocType", doctype):
		return
	table = "tab" + doctype.replace(" ", " ")
	try:
		columns = frappe.db.sql("SHOW COLUMNS FROM `{0}`".format(table), as_dict=True)
		col_names = [c.get("Field") for c in columns]
		if old_name not in col_names or new_name in col_names:
			return
		old_col = next((c for c in columns if c.get("Field") == old_name), None)
		if not old_col:
			return
		col_type = old_col.get("Type") or "TEXT"
		frappe.db.sql(
			"ALTER TABLE `{0}` CHANGE COLUMN `{1}` `{2}` {3}".format(
				table, old_name, new_name, col_type
			)
		)
	except Exception as e:
		frappe.log_error("align_booking_shipment_fields: " + str(e), "Patch align_booking_shipment_fields")
