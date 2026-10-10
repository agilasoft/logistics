# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop Client Credit Line and keep limits on Customer Credit Limit.

Each Client Credit Line with a customer, company, and limit is copied onto
that Customer when the company does not already have a credit-limit row.
Existing Customer credit rows are left as they are. Credit term days are not
copied; payment terms stay on the Customer. Exposure is calculated from the
ledger, not stored on the credit row.
"""

from __future__ import unicode_literals

import frappe


def execute():
	_copy_limits_onto_customers()
	_retarget_workspace_links()
	_retarget_exposure_card()
	if frappe.db.exists("DocType", "Client Credit Line"):
		frappe.delete_doc("DocType", "Client Credit Line", force=True, ignore_permissions=True)


def _copy_limits_onto_customers():
	if not frappe.db.table_exists("Client Credit Line"):
		return
	if not frappe.db.table_exists("Customer Credit Limit"):
		return
	if not frappe.db.exists("DocType", "Customer"):
		return
	rows = frappe.db.sql(
		"""
		SELECT customer, company, credit_limit
		FROM `tabClient Credit Line`
		WHERE IFNULL(customer, '') != ''
		  AND IFNULL(company, '') != ''
		  AND IFNULL(credit_limit, 0) > 0
		""",
		as_dict=True,
	)
	for row in rows:
		if not frappe.db.exists("Customer", row.customer):
			continue
		if not frappe.db.exists("Company", row.company):
			continue
		if frappe.db.exists(
			"Customer Credit Limit",
			{"parent": row.customer, "parenttype": "Customer", "company": row.company},
		):
			continue
		_insert_customer_credit_limit(row.customer, row.company, row.credit_limit)


def _insert_customer_credit_limit(customer, company, credit_limit):
	idx = frappe.db.sql(
		"""
		SELECT IFNULL(MAX(idx), 0) + 1
		FROM `tabCustomer Credit Limit`
		WHERE parent = %s AND parenttype = 'Customer' AND parentfield = 'credit_limits'
		""",
		customer,
	)[0][0]
	frappe.get_doc(
		{
			"doctype": "Customer Credit Limit",
			"parent": customer,
			"parenttype": "Customer",
			"parentfield": "credit_limits",
			"idx": idx,
			"company": company,
			"credit_limit": credit_limit,
		}
	).insert(ignore_permissions=True)


def _retarget_exposure_card():
	if not frappe.db.exists("Number Card", "Credit Exposure (PHP)"):
		return
	from logistics.control_tower.install import _retarget_credit_exposure_card

	_retarget_credit_exposure_card(
		"Credit Exposure (PHP)",
		"Accounting & Finance",
		"credit_lines_exposure",
		{"currency": "PHP"},
	)


def _retarget_workspace_links():
	if not frappe.db.table_exists("Workspace Link"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Link`
		SET link_to = 'Customer Credit Limit', label = 'Customer Credit Limit'
		WHERE link_to = 'Client Credit Line'
		"""
	)
