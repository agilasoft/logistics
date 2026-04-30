# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""Migrate standalone Container Charge rows into Container.charge_lines, then remove old DocTypes."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe


def _migrate_container_charge_rows():
	if not frappe.db.table_exists("tabContainer Charge"):
		return
	try:
		rows = frappe.db.sql(
			"""
			SELECT container, charge_type, revenue_calculation_method, quantity, unit_rate,
				currency, total_amount, reference_doctype, reference_name, invoice_status,
				sales_invoice, purchase_invoice
			FROM `tabContainer Charge`
			WHERE IFNULL(docstatus, 0) != 2
			""",
			as_dict=True,
		)
	except Exception:
		return
	if not rows:
		return
	by_parent = defaultdict(list)
	for r in rows:
		c = r.get("container")
		if c and frappe.db.exists("Container", c):
			by_parent[c].append(r)
	for parent, child_rows in by_parent.items():
		try:
			doc = frappe.get_doc("Container", parent)
			for r in child_rows:
				doc.append(
					"charge_lines",
					{
						"charge_type": r.get("charge_type"),
						"revenue_calculation_method": r.get("revenue_calculation_method"),
						"quantity": r.get("quantity"),
						"unit_rate": r.get("unit_rate"),
						"currency": r.get("currency"),
						"total_amount": r.get("total_amount"),
						"reference_doctype": r.get("reference_doctype"),
						"reference_name": r.get("reference_name"),
						"invoice_status": r.get("invoice_status"),
						"sales_invoice": r.get("sales_invoice"),
						"purchase_invoice": r.get("purchase_invoice"),
					},
				)
			doc.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="Container Charge migration to charge_lines",
				message=frappe.get_traceback(),
			)


def execute():
	_migrate_container_charge_rows()
	for dt in ("Container Transaction", "Container Charge"):
		if frappe.db.exists("DocType", dt):
			frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)
