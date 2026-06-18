# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate inline charge lifecycle tag child rows to standalone SPCLT documents."""

from __future__ import annotations

import frappe
from frappe.utils import cint


def execute():
	table = "Special Project Charge Lifecycle Tag"
	if not frappe.db.table_exists(f"tab{table}"):
		return
	if not frappe.db.has_column(table, "parent"):
		return

	legacy_rows = frappe.db.sql(
		f"""
		SELECT *
		FROM `tab{table}`
		WHERE parenttype = 'Special Project'
			AND parentfield = 'charge_lifecycle_tags'
			AND IFNULL(parent, '') != ''
		""",
		as_dict=True,
	)
	if not legacy_rows:
		return

	by_parent: dict[str, list[dict]] = {}
	for row in legacy_rows:
		parent = row.get("parent")
		if parent:
			by_parent.setdefault(parent, []).append(row)

	for sp_name, rows in by_parent.items():
		if not frappe.db.exists("Special Project", sp_name):
			continue
		sp = frappe.get_doc("Special Project", sp_name)
		sp.set("charge_lifecycle_tags", [])
		for row in rows:
			tag = frappe.new_doc("Special Project Charge Lifecycle Tag")
			tag.naming_series = "SPCLT-.#####"
			tag.special_project = sp_name
			tag.charge_row = cint(row.get("charge_row") or 0)
			tag.programme_lifecycle_job = row.get("programme_lifecycle_job")
			tag.lifecycle_jobs_idx = cint(row.get("lifecycle_jobs_idx") or 0)
			tag.cost_allocation_percentage = row.get("cost_allocation_percentage")
			tag.allocated_cost = row.get("allocated_cost")
			tag.allocated_revenue = row.get("allocated_revenue")
			tag.is_primary = cint(row.get("is_primary") or 0)
			tag.insert(ignore_permissions=True)
			sp.append("charge_lifecycle_tags", {"charge_lifecycle_tag": tag.name})

		frappe.db.delete(
			table,
			{
				"parent": sp_name,
				"parenttype": "Special Project",
				"parentfield": "charge_lifecycle_tags",
			},
		)
		sp.flags.ignore_links = True
		sp.save(ignore_permissions=True)

	frappe.db.commit()
