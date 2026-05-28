# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Merge legacy ``Special Project Cargo Package`` rows into ``Special Project Site Material``.

The Programme Cargo concept is folded into Site Materials. Each row on the merged grid
carries an ``include_on_create`` flag that decides whether it is a tracked requirement
or an always-along package template (hidden from the Shipment Lines dialog,
auto-appended to every booking, excluded from receipts and balances).

Logic:

1. For every legacy ``tabSpecial Project Cargo Package`` row:
   - If ``site_material_row`` points at an existing requirement row on the same parent,
     merge package fields (HS code, dimensions, weight, volume, DG flag, no_of_packs,
     reference_no) into that row, only filling fields that are currently empty. Force
     ``include_on_create = 0`` on the merged row (it remains a tracked requirement).
   - Otherwise append a new requirement row to the same parent's child table with
     ``include_on_create = 1``, ``qty_required = max(quantity, no_of_packs, 1)``, and
     all package fields copied. The new row gets ``commodity`` / ``warehouse_item`` /
     ``description`` from the source cargo row.
2. Drop the now-empty ``tabSpecial Project Cargo Package`` table.
3. Delete the ``Special Project Cargo Package`` DocType document if still present.
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

LEGACY_DOCTYPE = "Special Project Cargo Package"
LEGACY_TABLE = f"tab{LEGACY_DOCTYPE}"
# Site Material was renamed to Package in v1_1; this historical patch picks whichever
# table exists at the time it runs (on fresh installs, only the new one exists; on
# already-migrated installs neither will be missing the Site Material table because the
# rename was completed by v1_1_rename_special_project_site_material_to_package).
_TARGET_DOCTYPE_NEW = "Special Project Package"
_TARGET_DOCTYPE_OLD = "Special Project Site Material"

PACKAGE_FIELDS = (
	"hs_code",
	"reference_no",
	"no_of_packs",
	"length",
	"width",
	"height",
	"dimension_uom",
	"weight",
	"weight_uom",
	"volume",
	"volume_uom",
	"contains_dangerous_goods",
)


def _resolve_target_doctype() -> tuple[str | None, str | None]:
	for dt in (_TARGET_DOCTYPE_NEW, _TARGET_DOCTYPE_OLD):
		tab = f"tab{dt}"
		if frappe.db.table_exists(tab):
			return dt, tab
	return None, None


def execute():
	if not frappe.db.table_exists(LEGACY_TABLE):
		return
	target_doctype, target_table = _resolve_target_doctype()
	if not target_doctype:
		return

	cargo_rows = frappe.db.sql(
		f"""
		SELECT
			name, parent, parenttype, parentfield, idx,
			site_material_row, commodity, warehouse_item, description,
			hs_code, reference_no, quantity, no_of_packs, uom,
			length, width, height, dimension_uom,
			weight, weight_uom, volume, volume_uom,
			contains_dangerous_goods, include_on_create
		FROM `{LEGACY_TABLE}`
		ORDER BY parent, idx
		""",
		as_dict=True,
	)

	merged_into_existing = 0
	appended_as_new = 0

	for cargo in cargo_rows:
		parent = cargo.get("parent")
		if not parent:
			continue

		mat_row = _existing_site_material_row(parent, cargo.get("site_material_row"), target_table)
		if mat_row:
			_merge_package_fields(mat_row, cargo, target_doctype)
			merged_into_existing += 1
		else:
			_append_always_along_row(parent, cargo, target_doctype, target_table)
			appended_as_new += 1

	frappe.db.commit()

	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{LEGACY_TABLE}`")

	if frappe.db.exists("DocType", LEGACY_DOCTYPE):
		frappe.delete_doc("DocType", LEGACY_DOCTYPE, ignore_missing=True, force=True)

	frappe.db.commit()

	frappe.logger().info(
		"merge_programme_cargo_into_site_materials: merged=%s, appended=%s",
		merged_into_existing,
		appended_as_new,
	)


def _existing_site_material_row(parent: str, idx_value, target_table: str) -> dict | None:
	try:
		idx = int(idx_value or 0)
	except (TypeError, ValueError):
		idx = 0
	if idx < 1:
		return None
	rows = frappe.db.sql(
		f"""
		SELECT name, idx, hs_code, reference_no, no_of_packs,
			length, width, height, dimension_uom,
			weight, weight_uom, volume, volume_uom,
			contains_dangerous_goods
		FROM `{target_table}`
		WHERE parent = %s AND idx = %s
		LIMIT 1
		""",
		(parent, idx),
		as_dict=True,
	)
	return rows[0] if rows else None


def _merge_package_fields(mat_row: dict, cargo: dict, target_doctype: str) -> None:
	updates: dict[str, object] = {"include_on_create": 0}
	for fn in PACKAGE_FIELDS:
		current = mat_row.get(fn)
		if current not in (None, "", 0, 0.0):
			continue
		new_value = cargo.get(fn)
		if new_value in (None, "", 0, 0.0):
			continue
		updates[fn] = new_value
	frappe.db.set_value(target_doctype, mat_row["name"], updates, update_modified=False)


def _append_always_along_row(parent: str, cargo: dict, target_doctype: str, target_table: str) -> None:
	parent_row = frappe.db.sql(
		f"""
		SELECT parenttype, parentfield FROM `{target_table}`
		WHERE parent = %s LIMIT 1
		""",
		(parent,),
		as_dict=True,
	)
	if parent_row:
		parenttype = parent_row[0]["parenttype"]
		parentfield = parent_row[0]["parentfield"]
	else:
		parenttype = "Special Project"
		# Prefer the new field name when targeting the renamed doctype.
		parentfield = "packages" if target_doctype == _TARGET_DOCTYPE_NEW else "site_materials"

	max_idx = (
		frappe.db.sql(
			f"SELECT COALESCE(MAX(idx), 0) FROM `{target_table}` WHERE parent = %s",
			(parent,),
		)[0][0]
		or 0
	)
	next_idx = int(max_idx) + 1

	qty_required = max(
		flt(cargo.get("quantity")), flt(cargo.get("no_of_packs")), 1.0
	)

	doc = frappe.get_doc(
		{
			"doctype": target_doctype,
			"parent": parent,
			"parenttype": parenttype,
			"parentfield": parentfield,
			"idx": next_idx,
			"include_on_create": 1,
			"commodity": cargo.get("commodity"),
			"warehouse_item": cargo.get("warehouse_item"),
			"description": cargo.get("description"),
			"qty_required": qty_required,
			"uom": cargo.get("uom"),
			"hs_code": cargo.get("hs_code"),
			"reference_no": cargo.get("reference_no"),
			"no_of_packs": cargo.get("no_of_packs"),
			"length": cargo.get("length"),
			"width": cargo.get("width"),
			"height": cargo.get("height"),
			"dimension_uom": cargo.get("dimension_uom"),
			"weight": cargo.get("weight"),
			"weight_uom": cargo.get("weight_uom"),
			"volume": cargo.get("volume"),
			"volume_uom": cargo.get("volume_uom"),
			"contains_dangerous_goods": cargo.get("contains_dangerous_goods") or 0,
		}
	)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	doc.db_insert()
