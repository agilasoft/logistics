# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
"""Issue #1458: Country on Consignee, Customer, and Freight Agent list views (Supplier parity)."""

from __future__ import unicode_literals

import frappe


_LIST_VIEW_COUNTRY = (
	"Consignee",
	"Customer",
	"Freight Agent",
	"Supplier",
)


def execute():
	for doctype in ("Consignee", "Freight Agent"):
		if frappe.db.exists("DocType", doctype):
			frappe.reload_doc(
				"logistics",
				"doctype",
				doctype.lower().replace(" ", "_"),
				force=True,
			)

	for doctype in _LIST_VIEW_COUNTRY:
		if frappe.db.exists("DocType", doctype):
			_ensure_country_in_list_view(doctype)

	_backfill_country_from_unloco("Consignee")
	_backfill_country_from_unloco("Freight Agent")
	_backfill_customer_country_from_primary_address()

	frappe.db.commit()
	for doctype in _LIST_VIEW_COUNTRY:
		frappe.clear_cache(doctype=doctype)


def _has_country_column(doctype):
	# has_column() takes a DocType name and prefixes "tab" itself.
	if not frappe.db.table_exists(doctype):
		return False
	return frappe.db.has_column(doctype, "country")


def _ensure_country_in_list_view(doctype):
	if not _has_country_column(doctype):
		return
	row_name = frappe.db.get_value(
		"DocField",
		{"parent": doctype, "fieldname": "country"},
		"name",
	)
	if not row_name:
		return
	frappe.db.set_value("DocField", row_name, "in_list_view", 1, update_modified=False)


def _backfill_country_from_unloco(doctype):
	if not _has_country_column(doctype):
		return
	table = f"tab{doctype}"
	frappe.db.sql(
		f"""
		UPDATE `{table}` p
		INNER JOIN `tabUNLOCO` u ON u.name = p.default_unloco
		SET p.country = u.country
		WHERE IFNULL(p.country, '') = ''
		  AND IFNULL(u.country, '') != ''
		"""
	)


def _backfill_customer_country_from_primary_address():
	if not _has_country_column("Customer"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabCustomer` c
		INNER JOIN `tabAddress` a ON a.name = c.customer_primary_address
		SET c.country = a.country
		WHERE IFNULL(c.country, '') = ''
		  AND IFNULL(a.country, '') != ''
		"""
	)
