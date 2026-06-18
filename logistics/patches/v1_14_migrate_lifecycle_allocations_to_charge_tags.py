# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate lifecycle_job_allocations to charges.lifecycle_job_line; backfill execution rows."""

from __future__ import annotations

import frappe
from frappe.utils import cint

_LIFECYCLE_JOB_COPY_FIELDS = (
	"lifecycle_stage",
	"activity_code",
	"activity_name",
	"lifecycle_activity_status",
	"service_type",
	"job_description",
	"transport_template",
	"vehicle_type",
	"load_type",
	"direction",
	"air_house_type",
	"sea_house_type",
	"origin_port",
	"destination_port",
	"container_type",
	"container_no",
	"location_type",
	"location_from",
	"location_to",
	"pick_mode",
	"drop_mode",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
	"sp_site",
	"sp_manpower",
	"sp_skilled",
	"sp_equipment_type",
	"sp_handling",
	"sp_resource_notes",
	"airline",
	"freight_agent",
	"freight_agent_sea",
	"shipping_line",
	"transport_mode",
)


def _norm(value) -> str:
	return (value or "").strip()


def _charge_by_idx(sp, charge_row: int):
	for ch in sp.get("charges") or []:
		if cint(getattr(ch, "idx", 0) or 0) == cint(charge_row):
			return ch
	return None


def _legacy_allocations(sp_name: str) -> list[dict]:
	if not frappe.db.table_exists("tabLifecycle Jobs"):
		return []
	return frappe.get_all(
		"Lifecycle Jobs",
		filters={
			"parent": sp_name,
			"parenttype": "Special Project",
			"parentfield": "lifecycle_job_allocations",
		},
		fields=[
			"charge_row",
			"lifecycle_job_line",
			"is_primary",
		],
		order_by="charge_row asc, creation asc",
	)


def _migrate_allocations_to_charge_tags(sp) -> bool:
	if not frappe.get_meta("Special Project Charges").has_field("lifecycle_job_line"):
		return False

	allocs = _legacy_allocations(sp.name)
	if not allocs:
		return False

	by_charge: dict[int, list] = {}
	for alloc in allocs:
		ch_idx = cint(alloc.get("charge_row") or 0)
		if not ch_idx:
			continue
		by_charge.setdefault(ch_idx, []).append(alloc)

	changed = False
	for ch_idx, rows in by_charge.items():
		charge = _charge_by_idx(sp, ch_idx)
		if not charge:
			continue
		if _norm(getattr(charge, "lifecycle_job_line", None)):
			continue
		primary = next(
			(a for a in rows if cint(a.get("is_primary") or 0)),
			rows[0],
		)
		line = _norm(primary.get("lifecycle_job_line"))
		if not line:
			continue
		charge.lifecycle_job_line = line
		changed = True

	return changed


def _backfill_execution_rows(sp) -> bool:
	changed = False
	execution_by_planning: dict[str, str] = {}

	for row in list(sp.get("lifecycle_jobs") or []):
		planning_name = _norm(getattr(row, "name", None))
		if not planning_name:
			continue
		if _norm(getattr(row, "lifecycle_job_line", None)):
			continue
		job_no = _norm(getattr(row, "job_no", None))
		job_type = _norm(getattr(row, "job_type", None))
		if not job_no or not job_type:
			continue

		exec_row = sp.append("lifecycle_jobs", {})
		for fn in _LIFECYCLE_JOB_COPY_FIELDS:
			if hasattr(row, fn):
				exec_row.set(fn, getattr(row, fn, None))
		exec_row.job_type = job_type
		exec_row.job_no = job_no
		exec_row.lifecycle_job_line = planning_name
		execution_by_planning[planning_name] = exec_row.name

		row.job_type = None
		row.job_no = None
		changed = True

	if not changed:
		return False

	for charge in sp.get("charges") or []:
		tag = _norm(getattr(charge, "lifecycle_job_line", None))
		if tag in execution_by_planning:
			charge.lifecycle_job_line = execution_by_planning[tag]

	return True


def _migrate_special_project(sp_name: str) -> None:
	sp = frappe.get_doc("Special Project", sp_name)
	changed = _migrate_allocations_to_charge_tags(sp)
	changed = _backfill_execution_rows(sp) or changed
	if changed:
		sp.flags.ignore_validate = True
		sp.save(ignore_permissions=True)


def execute():
	if not frappe.db.table_exists("tabSpecial Project"):
		return

	for sp_name in frappe.get_all("Special Project", pluck="name"):
		_migrate_special_project(sp_name)

	if frappe.db.table_exists("tabLifecycle Jobs"):
		frappe.db.delete("Lifecycle Jobs", {"parenttype": "Special Project"})

	if frappe.db.exists("DocType", "Lifecycle Jobs"):
		frappe.delete_doc("DocType", "Lifecycle Jobs", force=1, ignore_permissions=True)

	frappe.db.commit()
