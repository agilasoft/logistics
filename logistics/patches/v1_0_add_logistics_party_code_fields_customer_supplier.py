# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
"""Custom fields on ERPNext Customer / Supplier: Default UNLOCO + logistics party Code (9-char generator)."""

import frappe


def _ensure_field(dt: str, fieldname: str, properties: dict):
	if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
		return
	doc = frappe.get_doc({"doctype": "Custom Field", "dt": dt, "fieldname": fieldname, **properties})
	doc.insert(ignore_permissions=True)


def execute():
	if not frappe.db.exists("DocType", "UNLOCO"):
		return

	# Customer
	if frappe.db.exists("DocType", "Customer"):
		_ensure_field(
			"Customer",
			"logistics_default_unloco",
			{
				"fieldtype": "Link",
				"label": "Default UNLOCO",
				"options": "UNLOCO",
				"description": "Used with Customer Name to suggest the logistics party Code.",
				"insert_after": "customer_name",
				"link_filters": "[[\"UNLOCO\", \"is_active\", \"=\", 1]]",
			},
		)
		_ensure_field(
			"Customer",
			"logistics_party_code",
			{
				"fieldtype": "Data",
				"label": "Code",
				"description": "Nine-character code (auto-filled from name + Default UNLOCO when empty).",
				"insert_after": "logistics_default_unloco",
				"unique": 1,
			},
		)

	# Supplier
	if frappe.db.exists("DocType", "Supplier"):
		_ensure_field(
			"Supplier",
			"logistics_default_unloco",
			{
				"fieldtype": "Link",
				"label": "Default UNLOCO",
				"options": "UNLOCO",
				"description": "Used with Supplier Name to suggest the logistics party Code.",
				"insert_after": "supplier_name",
				"link_filters": "[[\"UNLOCO\", \"is_active\", \"=\", 1]]",
			},
		)
		_ensure_field(
			"Supplier",
			"logistics_party_code",
			{
				"fieldtype": "Data",
				"label": "Code",
				"description": "Nine-character code (auto-filled from name + Default UNLOCO when empty).",
				"insert_after": "logistics_default_unloco",
				"unique": 1,
			},
		)

	frappe.db.commit()
	frappe.clear_cache(doctype="Customer")
	frappe.clear_cache(doctype="Supplier")
