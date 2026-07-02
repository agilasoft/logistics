# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move service parameters and operational links from Lifecycle Job to Programme Service."""

from __future__ import annotations

import frappe

_SERVICE_COLUMNS = (
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


def execute():
	frappe.reload_doc("special_projects", "doctype", "programme_service", force=True)

	if not frappe.db.table_exists("tabProgramme Service"):
		return
	if not _column_exists("tabLifecycle Job", "service_type"):
		return

	existing = frappe.db.sql(
		"""
		SELECT parent FROM `tabProgramme Service`
		WHERE parenttype = 'Special Project'
		LIMIT 1
		"""
	)
	if existing:
		return

	lifecycle_cols = {
		row[0]
		for row in frappe.db.sql(
			"""
			SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabLifecycle Job'
			"""
		)
	}
	copy_cols = [c for c in _SERVICE_COLUMNS if c in lifecycle_cols]
	if not copy_cols:
		return

	rows = frappe.db.sql(
		"""
		SELECT name, parent, idx, lifecycle_job_line, {cols}
		FROM `tabLifecycle Job`
		WHERE parenttype = 'Special Project' AND parentfield = 'lifecycle_jobs'
		ORDER BY parent, idx
		""".format(cols=", ".join(f"`{c}`" for c in copy_cols)),
		as_dict=True,
	)

	planning_map: dict[str, str] = {}
	for row in rows:
		if (row.get("lifecycle_job_line") or "").strip():
			continue
		service_type = (row.get("service_type") or "").strip()
		if not service_type:
			continue
		ps = frappe.new_doc("Programme Service")
		ps.update(
			{
				"parent": row.parent,
				"parenttype": "Special Project",
				"parentfield": "programme_services",
				"idx": row.idx,
				"lifecycle_job_line": row.name,
				**{c: row.get(c) for c in copy_cols},
			}
		)
		ps.db_insert()
		planning_map[row.name] = ps.name

	for row in rows:
		source = (row.get("lifecycle_job_line") or "").strip()
		if not source or source not in planning_map:
			continue
		service_type = (row.get("service_type") or "").strip()
		if not service_type:
			continue
		planning_service = planning_map[source]
		lifecycle_stage = frappe.db.get_value(
			"Programme Service", planning_service, "lifecycle_job_line"
		)
		ps = frappe.new_doc("Programme Service")
		ps.update(
			{
				"parent": row.parent,
				"parenttype": "Special Project",
				"parentfield": "programme_services",
				"idx": row.idx,
				"lifecycle_job_line": lifecycle_stage,
				"programme_service_line": planning_service,
				**{c: row.get(c) for c in copy_cols},
			}
		)
		ps.db_insert()

	if frappe.db.has_column("Special Project Charges", "programme_service_line"):
		for sp_name in {r.parent for r in rows}:
			charges = frappe.get_all(
				"Special Project Charges",
				filters={"parent": sp_name, "parenttype": "Special Project"},
				fields=["name", "lifecycle_job_line", "programme_service_line"],
			)
			for ch in charges:
				lifecycle_line = (ch.lifecycle_job_line or "").strip()
				if not lifecycle_line or (ch.programme_service_line or "").strip():
					continue
				service_name = planning_map.get(lifecycle_line)
				if service_name:
					frappe.db.set_value(
						"Special Project Charges",
						ch.name,
						"programme_service_line",
						service_name,
						update_modified=False,
					)
