# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Promote `Internal Job Detail` rows to standalone `Internal Job` records.

The `Internal Job Detail` child table used to store service parameters directly. After this
migration the child row is a thin pointer (`internal_job` Link) and the parameters live on a
top-level `Internal Job` doctype. Each existing child row is mapped 1:1 to a new Internal Job
carrying the same parameters plus a back-link (`parent_booking_type`/`parent_booking_name`).

Idempotent: rows that already have `internal_job` set are skipped.
"""

from __future__ import unicode_literals

import frappe


# Parameter columns to copy from `Internal Job Detail` -> `Internal Job`.
_PARAM_COLUMNS: tuple[str, ...] = (
	"service_type",
	"job_type",
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
	"planned_cost",
	"actual_cost",
	"planned_revenue",
	"actual_revenue",
)


def _existing_columns(table: str, columns: tuple[str, ...]) -> list[str]:
	"""Subset of *columns* that actually exist on *table* (defensive against schema drift)."""
	desc = frappe.db.sql(f"DESC `{table}`")
	have = {r[0] for r in desc}
	return [c for c in columns if c in have]


def execute():
	if not frappe.db.table_exists("Internal Job Detail"):
		return
	if not frappe.db.table_exists("Internal Job"):
		# Internal Job doctype hasn't been migrated yet; defer (this patch runs post_model_sync).
		return

	param_cols = _existing_columns("tabInternal Job Detail", _PARAM_COLUMNS)
	if not param_cols:
		return

	select_cols = ["name", "parenttype", "parent"] + param_cols
	select_sql = ", ".join(f"`{c}`" for c in select_cols)

	# Only rows that haven't been migrated yet (internal_job blank/null).
	internal_job_filter = ""
	desc = frappe.db.sql("DESC `tabInternal Job Detail`")
	have_cols = {r[0] for r in desc}
	if "internal_job" in have_cols:
		internal_job_filter = "AND (`internal_job` IS NULL OR `internal_job` = '')"

	rows = frappe.db.sql(
		f"""
		SELECT {select_sql}
		FROM `tabInternal Job Detail`
		WHERE COALESCE(parenttype, '') != ''
			AND COALESCE(parent, '') != ''
			{internal_job_filter}
		ORDER BY parenttype, parent, idx
		""",
		as_dict=True,
	)
	if not rows:
		return

	migrated = 0
	for r in rows:
		ijd_name = r.get("name")
		parent_type = (r.get("parenttype") or "").strip()
		parent_name = (r.get("parent") or "").strip()
		if not ijd_name or not parent_type or not parent_name:
			continue

		payload = {
			"doctype": "Internal Job",
			"parent_booking_type": parent_type,
			"parent_booking_name": parent_name,
		}
		for col in param_cols:
			val = r.get(col)
			if val is None:
				continue
			payload[col] = val

		try:
			ij = frappe.get_doc(payload)
			ij.flags.ignore_validate = False
			ij.flags.ignore_permissions = True
			ij.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="Internal Job migration failed",
				message=f"IJD {ijd_name} on {parent_type}/{parent_name}: {frappe.get_traceback()}",
			)
			continue

		frappe.db.set_value(
			"Internal Job Detail",
			ijd_name,
			"internal_job",
			ij.name,
			update_modified=False,
		)
		migrated += 1

	frappe.db.commit()
	if migrated:
		print(f"Migrated {migrated} Internal Job Detail rows to Internal Job records.")
