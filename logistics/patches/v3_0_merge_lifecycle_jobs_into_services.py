# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Merge Special Project lifecycle_jobs into special_project_services; add applicable lifecycle stages."""

from __future__ import annotations

import frappe

_LIFECYCLE_JOB_COPY_COLUMNS = (
	"lifecycle_stage",
	"activity_code",
	"activity_name",
	"lifecycle_activity_status",
	"lifecycle_row_label",
	"service_type",
	"job_type",
	"order_no",
	"job_no",
	"job_description",
	"air_house_type",
	"airline",
	"freight_agent",
	"sea_house_type",
	"freight_agent_sea",
	"shipping_line",
	"transport_mode",
	"load_type",
	"direction",
	"origin_port",
	"destination_port",
	"transport_template",
	"vehicle_type",
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
	"planned_cost",
	"planned_revenue",
	"actual_cost",
	"actual_revenue",
)


def _column_exists(table: str, column: str) -> bool:
	return bool(
		frappe.db.sql(
			"""
			SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
			""",
			(table, column),
		)
	)


def _lifecycle_job_cols() -> set[str]:
	if not frappe.db.table_exists("tabLifecycle Job"):
		return set()
	return {
		row[0]
		for row in frappe.db.sql(
			"""
			SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabLifecycle Job'
			"""
		)
	}


def execute():
	frappe.reload_doc("special_projects", "doctype", "special_project_lifecycle_stage", force=True)
	frappe.reload_doc("special_projects", "doctype", "special_project_service", force=True)
	frappe.reload_doc("special_projects", "doctype", "special_project", force=True)

	if not frappe.db.table_exists("tabLifecycle Job"):
		return

	lifecycle_cols = _lifecycle_job_cols()
	if not lifecycle_cols:
		return

	copy_cols = [c for c in _LIFECYCLE_JOB_COPY_COLUMNS if c in lifecycle_cols]

	rows = frappe.db.sql(
		"""
		SELECT name, parent, idx, lifecycle_job_line, {cols}
		FROM `tabLifecycle Job`
		WHERE parenttype = 'Special Project' AND parentfield = 'lifecycle_jobs'
		ORDER BY parent, idx
		""".format(cols=", ".join(f"`{c}`" for c in copy_cols) if copy_cols else "name"),
		as_dict=True,
	)

	lifecycle_to_stage: dict[str, str] = {}
	for row in rows:
		stage = (row.get("lifecycle_stage") or "").strip()
		if stage:
			lifecycle_to_stage[row.name] = stage

	if _column_exists("tabSpecial Project Service", "lifecycle_job_line"):
		ps_rows = frappe.db.sql(
			"""
			SELECT name, lifecycle_job_line, lifecycle_stage
			FROM `tabSpecial Project Service`
			WHERE parenttype = 'Special Project' AND parentfield = 'special_project_services'
			""",
			as_dict=True,
		)
		for ps in ps_rows:
			stage = (ps.get("lifecycle_stage") or "").strip()
			if stage:
				continue
			line = (ps.get("lifecycle_job_line") or "").strip()
			if not line:
				continue
			resolved = lifecycle_to_stage.get(line)
			if not resolved and frappe.db.exists("Lifecycle Job", line):
				resolved = (
					frappe.db.get_value("Lifecycle Job", line, "lifecycle_stage") or ""
				).strip()
			if resolved:
				frappe.db.set_value(
					"Special Project Service",
					ps.name,
					"lifecycle_stage",
					resolved,
					update_modified=False,
				)

	if copy_cols:
		existing_parents = {
			row.parent
			for row in frappe.db.sql(
				"""
				SELECT DISTINCT parent FROM `tabSpecial Project Service`
				WHERE parenttype = 'Special Project' AND parentfield = 'special_project_services'
				""",
				as_dict=True,
			)
		}
		planning_map: dict[str, str] = {}
		for row in rows:
			parent = row.parent
			if parent in existing_parents:
				continue
			if (row.get("lifecycle_job_line") or "").strip():
				continue
			service_type = (row.get("service_type") or "").strip()
			if not service_type:
				continue
			ps = frappe.new_doc("Special Project Service")
			ps.update(
				{
					"parent": parent,
					"parenttype": "Special Project",
					"parentfield": "special_project_services",
					"idx": row.idx,
					**{c: row.get(c) for c in copy_cols},
				}
			)
			ps.db_insert()
			planning_map[row.name] = ps.name

		for row in rows:
			parent = row.parent
			if parent in existing_parents:
				continue
			source = (row.get("lifecycle_job_line") or "").strip()
			if not source or source not in planning_map:
				continue
			service_type = (row.get("service_type") or "").strip()
			if not service_type:
				continue
			planning_service = planning_map[source]
			stage = lifecycle_to_stage.get(source) or frappe.db.get_value(
				"Lifecycle Job", source, "lifecycle_stage"
			)
			ps = frappe.new_doc("Special Project Service")
			ps.update(
				{
					"parent": parent,
					"parenttype": "Special Project",
					"parentfield": "special_project_services",
					"idx": row.idx,
					"lifecycle_stage": stage,
					"special_project_service_line": planning_service,
					**{c: row.get(c) for c in copy_cols if c != "lifecycle_stage"},
				}
			)
			ps.db_insert()

	if frappe.db.table_exists("tabSpecial Project Lifecycle Stage"):
		parent_names = {r.parent for r in rows}
		parent_names.update(frappe.get_all("Special Project", pluck="name"))
		for sp_name in parent_names:
			stages: set[str] = set()
			for stage in frappe.get_all(
				"Special Project Service",
				filters={
					"parent": sp_name,
					"parenttype": "Special Project",
					"parentfield": "special_project_services",
				},
				pluck="lifecycle_stage",
			):
				if (stage or "").strip():
					stages.add(stage.strip())
			for stage in frappe.get_all(
				"Lifecycle Job",
				filters={
					"parent": sp_name,
					"parenttype": "Special Project",
					"parentfield": "lifecycle_jobs",
				},
				pluck="lifecycle_stage",
			):
				if (stage or "").strip():
					stages.add(stage.strip())
			existing = set(
				frappe.get_all(
					"Special Project Lifecycle Stage",
					filters={
						"parent": sp_name,
						"parenttype": "Special Project",
						"parentfield": "applicable_lifecycle_stages",
					},
					pluck="lifecycle_stage",
				)
			)
			idx = 1
			for stage in sorted(stages):
				if stage in existing:
					continue
				child = frappe.new_doc("Special Project Lifecycle Stage")
				child.update(
					{
						"parent": sp_name,
						"parenttype": "Special Project",
						"parentfield": "applicable_lifecycle_stages",
						"idx": idx,
						"lifecycle_stage": stage,
					}
				)
				child.db_insert()
				idx += 1

	if _column_exists("tabSpecial Project Charges", "lifecycle_job_line"):
		charges = frappe.db.sql(
			"""
			SELECT name, lifecycle_job_line, lifecycle_stage
			FROM `tabSpecial Project Charges`
			WHERE parenttype = 'Special Project'
			""",
			as_dict=True,
		)
		for ch in charges:
			stage = (ch.get("lifecycle_stage") or "").strip()
			if stage:
				continue
			line = (ch.get("lifecycle_job_line") or "").strip()
			if not line:
				continue
			resolved = lifecycle_to_stage.get(line)
			if not resolved and frappe.db.exists("Lifecycle Job", line):
				resolved = (
					frappe.db.get_value("Lifecycle Job", line, "lifecycle_stage") or ""
				).strip()
			if resolved:
				frappe.db.set_value(
					"Special Project Charges",
					ch.name,
					"lifecycle_stage",
					resolved,
					update_modified=False,
				)

	if _column_exists("tabSpecial Project Charge Execution Log", "lifecycle_job_line"):
		logs = frappe.db.sql(
			"""
			SELECT name, lifecycle_job_line, lifecycle_stage
			FROM `tabSpecial Project Charge Execution Log`
			WHERE parenttype = 'Special Project'
			""",
			as_dict=True,
		)
		for log in logs:
			stage = (log.get("lifecycle_stage") or "").strip()
			if stage:
				continue
			line = (log.get("lifecycle_job_line") or "").strip()
			if not line:
				continue
			resolved = lifecycle_to_stage.get(line)
			if not resolved and frappe.db.exists("Lifecycle Job", line):
				resolved = (
					frappe.db.get_value("Lifecycle Job", line, "lifecycle_stage") or ""
				).strip()
			if resolved:
				frappe.db.set_value(
					"Special Project Charge Execution Log",
					log.name,
					"lifecycle_stage",
					resolved,
					update_modified=False,
				)

	frappe.db.sql(
		"""
		DELETE FROM `tabLifecycle Job`
		WHERE parenttype = 'Special Project' AND parentfield = 'lifecycle_jobs'
		"""
	)
