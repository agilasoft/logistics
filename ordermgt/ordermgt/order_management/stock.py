# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Available-to-sell from the logistics warehouse stock ledger."""

from __future__ import annotations

import frappe

from ordermgt.order_management.decisions import available_to_sell


def on_hand_by_item(customer, company, branch=None) -> dict:
	params = {"customer": customer, "company": company}
	branch_sql = ""
	if branch:
		branch_sql = "AND COALESCE(hu.branch, sl.branch) = %(branch)s"
		params["branch"] = branch
	rows = frappe.db.sql(
		f"""
		SELECT wsl.item AS item,
			SUM(COALESCE(wsl.quantity, wsl.end_qty - wsl.beg_quantity, 0)) AS qty
		FROM `tabWarehouse Stock Ledger` wsl
		LEFT JOIN `tabStorage Location` sl ON sl.name = wsl.storage_location
		LEFT JOIN `tabHandling Unit` hu ON hu.name = wsl.handling_unit
		LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
		WHERE wi.customer = %(customer)s
			AND COALESCE(hu.company, sl.company) = %(company)s
			{branch_sql}
		GROUP BY wsl.item
		""",
		params,
		as_dict=True,
	)
	return {row.item: float(row.qty or 0) for row in rows}


def allocated_by_item(customer, company, branch=None) -> dict:
	"""Release quantities whose pick has not been posted to the ledger yet."""
	params = {"customer": customer, "company": company}
	branch_sql = ""
	if branch:
		branch_sql = "AND ro.branch = %(branch)s"
		params["branch"] = branch
	rows = frappe.db.sql(
		f"""
		SELECT roi.item AS item, SUM(roi.quantity) AS qty
		FROM `tabRelease Order Item` roi
		INNER JOIN `tabRelease Order` ro ON ro.name = roi.parent
		WHERE ro.customer = %(customer)s
			AND ro.company = %(company)s
			AND ro.docstatus < 2
			{branch_sql}
			AND NOT EXISTS (
				SELECT 1 FROM `tabWarehouse Job` wj
				WHERE wj.reference_order_type = 'Release Order'
					AND wj.reference_order = ro.name
					AND wj.type = 'Pick'
					AND wj.docstatus = 1
			)
		GROUP BY roi.item
		""",
		params,
		as_dict=True,
	)
	return {row.item: float(row.qty or 0) for row in rows}


def available_map(customer, company, branch=None, safety=0) -> dict:
	on_hand = on_hand_by_item(customer, company, branch)
	allocated = allocated_by_item(customer, company, branch)
	items = set(on_hand) | set(allocated)
	return {
		item: available_to_sell(on_hand.get(item, 0), allocated.get(item, 0), safety)
		for item in items
	}


def pick_is_posted(release_order) -> bool:
	if not release_order:
		return False
	return bool(
		frappe.db.exists(
			"Warehouse Job",
			{
				"reference_order_type": "Release Order",
				"reference_order": release_order,
				"type": "Pick",
				"docstatus": 1,
			},
		)
	)
