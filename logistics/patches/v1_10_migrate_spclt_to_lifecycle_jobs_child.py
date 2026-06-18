# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate standalone charge lifecycle tags to Lifecycle Jobs child rows on Special Project."""

from __future__ import annotations

import frappe
from frappe.utils import cint


def _lifecycle_line_for_plj(sp, plj_name: str) -> str | None:
	"""Resolve Programme Lifecycle Job child name to Lifecycle Job line name."""
	if not plj_name:
		return None
	plj_idx = frappe.db.get_value("Programme Lifecycle Job", plj_name, "lifecycle_jobs_idx")
	if plj_idx is None:
		return None
	for lj in sp.get("lifecycle_jobs") or []:
		if cint(getattr(lj, "idx", 0) or 0) == cint(plj_idx):
			return (getattr(lj, "name", None) or "").strip() or None
	return None


def _lifecycle_line_for_idx(sp, lifecycle_jobs_idx: int) -> str | None:
	for lj in sp.get("lifecycle_jobs") or []:
		if cint(getattr(lj, "idx", 0) or 0) == cint(lifecycle_jobs_idx):
			return (getattr(lj, "name", None) or "").strip() or None
	return None


def _migrate_standalone_tags(sp_name: str) -> bool:
	table = "Special Project Charge Lifecycle Tag"
	if not frappe.db.table_exists(f"tab{table}"):
		return False
	if not frappe.db.has_column(table, "special_project"):
		return False

	tags = frappe.get_all(
		table,
		filters={"special_project": sp_name},
		fields=[
			"name",
			"charge_row",
			"programme_lifecycle_job",
			"lifecycle_jobs_idx",
			"cost_allocation_percentage",
			"allocated_cost",
			"allocated_revenue",
			"is_primary",
		],
		order_by="charge_row asc, creation asc",
	)
	if not tags:
		return False

	sp = frappe.get_doc("Special Project", sp_name)
	existing = {
		(cint(r.charge_row), (r.lifecycle_job_line or "").strip())
		for r in sp.get("lifecycle_job_allocations") or []
	}
	changed = False
	for tag in tags:
		line = _lifecycle_line_for_plj(sp, (tag.get("programme_lifecycle_job") or "").strip())
		if not line:
			line = _lifecycle_line_for_idx(sp, cint(tag.get("lifecycle_jobs_idx") or 0))
		if not line:
			continue
		key = (cint(tag.get("charge_row") or 0), line)
		if key in existing:
			continue
		sp.append(
			"lifecycle_job_allocations",
			{
				"charge_row": cint(tag.get("charge_row") or 0),
				"lifecycle_job_line": line,
				"cost_allocation_percentage": tag.get("cost_allocation_percentage"),
				"allocated_cost": tag.get("allocated_cost"),
				"allocated_revenue": tag.get("allocated_revenue"),
				"is_primary": cint(tag.get("is_primary") or 0),
			},
		)
		existing.add(key)
		changed = True

	if changed:
		sp.flags.ignore_validate = True
		sp.save(ignore_permissions=True)

	for tag in tags:
		frappe.delete_doc(table, tag.name, force=1, ignore_permissions=True)

	return changed


def _migrate_wrapper_inline_tags(sp_name: str) -> bool:
	"""Legacy inline rows on charge_lifecycle_tags before v1_7 standalone migration."""
	table = "Special Project Charge Lifecycle Tag"
	if not frappe.db.table_exists(f"tab{table}"):
		return False
	if not frappe.db.has_column(table, "parent"):
		return False

	legacy_rows = frappe.db.sql(
		f"""
		SELECT *
		FROM `tab{table}`
		WHERE parent = %s
			AND parenttype = 'Special Project'
			AND parentfield = 'charge_lifecycle_tags'
		""",
		sp_name,
		as_dict=True,
	)
	if not legacy_rows:
		return False

	sp = frappe.get_doc("Special Project", sp_name)
	changed = False
	for row in legacy_rows:
		line = _lifecycle_line_for_plj(sp, (row.get("programme_lifecycle_job") or "").strip())
		if not line:
			line = _lifecycle_line_for_idx(sp, cint(row.get("lifecycle_jobs_idx") or 0))
		if not line:
			continue
		sp.append(
			"lifecycle_job_allocations",
			{
				"charge_row": cint(row.get("charge_row") or 0),
				"lifecycle_job_line": line,
				"cost_allocation_percentage": row.get("cost_allocation_percentage"),
				"allocated_cost": row.get("allocated_cost"),
				"allocated_revenue": row.get("allocated_revenue"),
				"is_primary": cint(row.get("is_primary") or 0),
			},
		)
		changed = True

	if changed:
		sp.flags.ignore_validate = True
		sp.save(ignore_permissions=True)

	frappe.db.delete(
		table,
		{"parent": sp_name, "parenttype": "Special Project", "parentfield": "charge_lifecycle_tags"},
	)
	return changed


def _backfill_from_lifecycle_job_row(sp_name: str) -> bool:
	if not frappe.db.has_column("Special Project Charges", "lifecycle_job_row"):
		return False
	sp = frappe.get_doc("Special Project", sp_name)
	existing_charges = {
		cint(r.charge_row)
		for r in sp.get("lifecycle_job_allocations") or []
		if cint(getattr(r, "charge_row", 0) or 0)
	}
	changed = False
	for charge in sp.get("charges") or []:
		ch_idx = cint(getattr(charge, "idx", 0) or 0)
		if not ch_idx or ch_idx in existing_charges:
			continue
		lj_idx = cint(getattr(charge, "lifecycle_job_row", 0) or 0)
		if not lj_idx:
			continue
		line = _lifecycle_line_for_idx(sp, lj_idx)
		if not line:
			continue
		sp.append(
			"lifecycle_job_allocations",
			{
				"charge_row": ch_idx,
				"lifecycle_job_line": line,
				"cost_allocation_percentage": 100,
				"is_primary": 1,
			},
		)
		existing_charges.add(ch_idx)
		changed = True
	if changed:
		sp.flags.ignore_validate = True
		sp.save(ignore_permissions=True)
	return changed


def execute():
	if not frappe.db.table_exists("tabSpecial Project"):
		return

	for sp_name in frappe.get_all("Special Project", pluck="name"):
		_migrate_wrapper_inline_tags(sp_name)
		_migrate_standalone_tags(sp_name)
		_backfill_from_lifecycle_job_row(sp_name)

	frappe.db.commit()
