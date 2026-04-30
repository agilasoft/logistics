# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Remove every Custom Field on logistics charge child tables.

Charge fields are owned by DocType JSON in this app; Custom Field rows on these tables are removed
regardless of fieldname (including site-only additions).
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.utils import cint


def _iter_logistics_charge_table_doctype_names():
	root = Path(frappe.get_app_path("logistics")) / "logistics"
	if not root.is_dir():
		return
	for path in root.rglob("*.json"):
		if "doctype" not in path.parts:
			continue
		try:
			data = json.loads(path.read_text(encoding="utf-8"))
		except (OSError, UnicodeDecodeError, json.JSONDecodeError):
			continue
		if data.get("doctype") != "DocType":
			continue
		if not cint(data.get("istable")):
			continue
		name = (data.get("name") or "").strip()
		if not name:
			continue
		if "Charges" in name or name.endswith(" Charge"):
			yield name


def execute():
	charge_dts = [dt for dt in _iter_logistics_charge_table_doctype_names() if frappe.db.exists("DocType", dt)]
	if not charge_dts:
		return True

	all_cfs = frappe.get_all(
		"Custom Field",
		filters={"dt": ["in", charge_dts]},
		fields=["name", "dt"],
	)

	removed = 0
	cleared: set[str] = set()
	for row in all_cfs:
		frappe.delete_doc("Custom Field", row.name, force=True, ignore_permissions=True)
		removed += 1
		cleared.add(row.dt)
		print(f"Removed charge-table Custom Field: {row.name}")

	if cleared:
		frappe.db.commit()
		for dt in cleared:
			frappe.clear_cache(doctype=dt)
	if removed:
		print(f"Removed {removed} Custom Field(s) on charge child tables")
	return True
