# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Remove Custom Field rows on logistics charge child tables when the fieldname already exists
in the app's DocType JSON.

Charge lines must be defined in DocType JSON only; duplicate Custom Field definitions cause
PRIMARY key conflicts, broken field_order, and scrambled grid layouts.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.utils import cint


def _iter_logistics_charge_doctype_json():
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
		# Child charge rows and *Charges* Qty/Weight Break helpers shipped in this app
		if "Charges" in name or name.endswith(" Charge"):
			yield name, data


def _json_fieldnames(data: dict) -> set[str]:
	return {
		f["fieldname"]
		for f in (data.get("fields") or [])
		if isinstance(f, dict) and f.get("fieldname")
	}


def execute():
	standard_by_dt: dict[str, set[str]] = {}
	for dt, doc_json in _iter_logistics_charge_doctype_json():
		if not frappe.db.exists("DocType", dt):
			continue
		fnames = _json_fieldnames(doc_json)
		if fnames:
			standard_by_dt[dt] = fnames

	if not standard_by_dt:
		return True

	all_cfs = frappe.get_all(
		"Custom Field",
		filters={"dt": ["in", list(standard_by_dt)]},
		fields=["name", "dt", "fieldname"],
	)

	removed = 0
	cleared: set[str] = set()
	for row in all_cfs:
		if row.fieldname in standard_by_dt.get(row.dt, ()):
			frappe.delete_doc("Custom Field", row.name, force=True, ignore_permissions=True)
			removed += 1
			cleared.add(row.dt)
			print(f"Removed duplicate charge-table Custom Field: {row.name}")

	if cleared:
		frappe.db.commit()
		for dt in cleared:
			frappe.clear_cache(doctype=dt)
	if removed:
		print(f"Removed {removed} duplicate Custom Field(s) on charge child tables")
	return True
