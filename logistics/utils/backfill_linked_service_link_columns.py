# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""One-off backfill: mirror ``linked_service`` / ``internal_job`` on child rows and Docket grids."""

from __future__ import annotations

from typing import Any

import frappe

from logistics.utils.linked_service_compat import (
	linked_service_doctype,
	row_linked_service_link,
	set_row_linked_service_link,
)


def debug_counts() -> dict:
	ls_dt = linked_service_doctype()
	rows = frappe.db.sql(
		"""
		SELECT name, linked_service AS src
		FROM `tabLinked Service Detail`
		WHERE IFNULL(linked_service, '') != ''
		  AND IFNULL(internal_job, '') = ''
		""",
		as_dict=True,
	)
	ok = sum(1 for r in rows if frappe.db.exists(ls_dt, (r.get("src") or "").strip()))
	return {
		"ls_dt": ls_dt,
		"lsd_table": frappe.db.table_exists("Linked Service Detail"),
		"ijd_table": frappe.db.table_exists("Internal Job Detail"),
		"candidate_rows": len(rows),
		"exists_ok": ok,
		"docket_ls": len(
			frappe.get_all(
				ls_dt, filters={"parent_booking_type": "Docket"}, pluck="name"
			)
		),
	}


def run(dry_run: bool = False) -> dict:
	"""Backfill link columns and Docket ``Internal Job Detail`` rows from ``Linked Service`` docs."""
	stats = {
		"lsd_internal_job_backfilled": 0,
		"lsd_linked_service_backfilled": 0,
		"docket_ijd_rows_created": 0,
		"docket_ijd_rows_updated": 0,
		"orphan_child_links_cleared": 0,
	}

	if frappe.db.table_exists("Linked Service Detail"):
		stats["lsd_internal_job_backfilled"] = _backfill_lsd_column(
			source="linked_service", target="internal_job", dry_run=dry_run
		)
		stats["lsd_linked_service_backfilled"] = _backfill_lsd_column(
			source="internal_job", target="linked_service", dry_run=dry_run
		)
		stats["orphan_child_links_cleared"] = _clear_orphan_lsd_links(dry_run=dry_run)

	if frappe.db.table_exists("Internal Job Detail"):
		created, updated = _sync_docket_internal_job_detail_from_linked_services(dry_run=dry_run)
		stats["docket_ijd_rows_created"] = created
		stats["docket_ijd_rows_updated"] = updated

	if not dry_run:
		frappe.db.commit()
	return stats


def _backfill_lsd_column(*, source: str, target: str, dry_run: bool) -> int:
	if not frappe.db.has_column("Linked Service Detail", source):
		return 0
	if not frappe.db.has_column("Linked Service Detail", target):
		return 0
	rows = frappe.db.sql(
		f"""
		SELECT name, `{source}` AS src
		FROM `tabLinked Service Detail`
		WHERE IFNULL(`{source}`, '') != ''
		  AND IFNULL(`{target}`, '') = ''
		""",
		as_dict=True,
	)
	count = 0
	ls_dt = linked_service_doctype()
	for row in rows:
		src = (row.get("src") or "").strip()
		if not src or not frappe.db.exists(ls_dt, src):
			continue
		count += 1
		if not dry_run:
			frappe.db.set_value(
				"Linked Service Detail",
				row["name"],
				target,
				src,
				update_modified=False,
			)
	return count


def _clear_orphan_lsd_links(dry_run: bool) -> int:
	ls_dt = linked_service_doctype()
	rows = frappe.db.sql(
		"""
		SELECT name, internal_job, linked_service
		FROM `tabLinked Service Detail`
		WHERE IFNULL(internal_job, '') != '' OR IFNULL(linked_service, '') != ''
		""",
		as_dict=True,
	)
	count = 0
	for row in rows:
		link = row_linked_service_link(row)
		if not link or frappe.db.exists(ls_dt, link):
			continue
		count += 1
		if not dry_run:
			frappe.db.set_value(
				"Linked Service Detail",
				row["name"],
				{"internal_job": None, "linked_service": None},
				update_modified=False,
			)
	return count


def _sync_docket_internal_job_detail_from_linked_services(
	dry_run: bool,
) -> tuple[int, int]:
	ls_dt = linked_service_doctype()
	ls_rows = frappe.get_all(
		ls_dt,
		filters={"parent_booking_type": "Docket"},
		fields=["name", "parent_booking_name"],
		order_by="parent_booking_name asc, creation asc",
	)
	created = 0
	updated = 0
	for row in ls_rows:
		parent = (row.get("parent_booking_name") or "").strip()
		ls_name = (row.get("name") or "").strip()
		if not parent or not ls_name or not frappe.db.exists("Docket", parent):
			continue
		existing = frappe.db.get_value(
			"Internal Job Detail",
			{
				"parent": parent,
				"parenttype": "Docket",
				"parentfield": "internal_jobs",
				"internal_job": ls_name,
			},
			"name",
		)
		if existing:
			if not dry_run:
				_copy_ls_params_to_ijd(ls_name, existing)
			updated += 1
			continue
		if dry_run:
			created += 1
			continue
		ls_doc = frappe.get_doc(ls_dt, ls_name)
		child = frappe.new_doc("Internal Job Detail")
		child.parent = parent
		child.parenttype = "Docket"
		child.parentfield = "internal_jobs"
		set_row_linked_service_link(child, ls_name)
		_copy_ls_doc_fields(ls_doc, child)
		child.flags.ignore_links = True
		child.insert(ignore_permissions=True)
		created += 1
	return created, updated


def _copy_ls_params_to_ijd(ls_name: str, ijd_name: str) -> None:
	ls_doc = frappe.get_doc(linked_service_doctype(), ls_name)
	child = frappe.get_doc("Internal Job Detail", ijd_name)
	_copy_ls_doc_fields(ls_doc, child)
	set_row_linked_service_link(child, ls_name)
	child.flags.ignore_links = True
	child.save(ignore_permissions=True)


def _copy_ls_doc_fields(ls_doc: Any, child: Any) -> None:
	for fn in (
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
	):
		if hasattr(ls_doc, fn):
			child.set(fn, getattr(ls_doc, fn, None))
