# Copyright (c) 2026, logistics.agilasoft.com and contributors
"""Create one Sea Freight Settings per Company from legacy Single backup or leftover row."""

import json
import os

import frappe


def execute():
	path = frappe.get_site_path("private", "files", "sea_freight_settings_single_backup.json")
	data = None
	if os.path.exists(path):
		with open(path) as f:
			data = json.load(f)
		try:
			os.remove(path)
		except OSError:
			pass

	if not data and frappe.db.table_exists("tabSea Freight Settings"):
		legacy = frappe.db.sql(
			"SELECT * FROM `tabSea Freight Settings` WHERE name=%s LIMIT 1",
			("Sea Freight Settings",),
			as_dict=True,
		)
		if legacy:
			data = legacy[0]

	if not data:
		return

	companies = frappe.get_all("Company", pluck="name")
	if not companies:
		return

	skip_keys = {
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"default_company",
		"company",
	}

	for company in companies:
		if frappe.db.exists("Sea Freight Settings", company):
			continue
		doc = frappe.new_doc("Sea Freight Settings")
		doc.company = company
		for k, v in data.items():
			if k in skip_keys:
				continue
			if doc.meta.has_field(k):
				doc.set(k, v)
		doc.flags.ignore_validate = True
		try:
			doc.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Sea Freight Settings per-company migration")

	frappe.db.commit()

	if frappe.db.table_exists("tabSea Freight Settings"):
		frappe.db.sql(
			"DELETE FROM `tabSea Freight Settings` WHERE name=%s",
			("Sea Freight Settings",),
		)
		frappe.db.commit()
