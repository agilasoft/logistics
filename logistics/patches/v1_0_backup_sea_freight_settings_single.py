# Copyright (c) 2026, logistics.agilasoft.com and contributors
"""Backup legacy Single Sea Freight Settings row before DocType is migrated to per-company."""

import json
import os

import frappe


def execute():
	if not frappe.db.table_exists("tabSea Freight Settings"):
		return
	try:
		meta = frappe.get_meta("Sea Freight Settings")
	except Exception:
		return
	if not getattr(meta, "issingle", 0):
		return
	row = frappe.db.sql(
		"SELECT * FROM `tabSea Freight Settings` WHERE name=%s LIMIT 1",
		("Sea Freight Settings",),
		as_dict=True,
	)
	if not row:
		return
	path = frappe.get_site_path("private", "files", "sea_freight_settings_single_backup.json")
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w") as f:
		json.dump(row[0], f, default=str)
