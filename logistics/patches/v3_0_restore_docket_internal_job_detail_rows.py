# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Restore persisted ``Internal Job Detail`` rows on Docket.

``Docket.internal_jobs`` was briefly a virtual ``Linked Service Detail`` grid, which
hid Add Row and dropped child-table rows on save. Existing line data may still live
in ``tabLinked Service Detail`` (pre-virtual) and/or as ``Linked Service`` documents
parented to the Docket.
"""

from __future__ import annotations

import frappe

from logistics.utils.linked_service_compat import (
	linked_service_doctype,
	row_linked_service_link,
	set_row_linked_service_link,
)


_SKIP_CHILD_KEYS = frozenset(
	{
		"name",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"docstatus",
		"doctype",
		"parent",
		"parenttype",
		"parentfield",
		"idx",
		"linked_service",
	}
)


def execute():
	if not frappe.db.table_exists("Docket"):
		return
	if not frappe.db.table_exists("tabInternal Job Detail"):
		return

	restored_from_lsd = _restore_from_linked_service_detail_rows()
	restored_from_ls = _restore_from_linked_service_documents()
	if restored_from_lsd or restored_from_ls:
		frappe.db.commit()


def _restore_from_linked_service_detail_rows() -> int:
	table = "tabLinked Service Detail"
	if not frappe.db.table_exists(table):
		return 0
	if not frappe.db.has_column("Linked Service Detail", "parenttype"):
		return 0

	rows = frappe.db.sql(
		f"""
		SELECT *
		FROM `{table}`
		WHERE parenttype = %s AND parentfield = %s
		ORDER BY parent ASC, idx ASC
		""",
		("Docket", "internal_jobs"),
		as_dict=True,
	)
	count = 0
	for row in rows:
		parent = (row.get("parent") or "").strip()
		if not parent or not frappe.db.exists("Docket", parent):
			continue
		if _ijd_row_exists(parent, row):
			continue
		payload = {
			k: v
			for k, v in row.items()
			if k not in _SKIP_CHILD_KEYS and v is not None
		}
		ls_link = row_linked_service_link(row)
		if ls_link:
			set_row_linked_service_link(payload, ls_link)
		try:
			child = frappe.new_doc("Internal Job Detail")
			child.update(payload)
			child.parent = parent
			child.parenttype = "Docket"
			child.parentfield = "internal_jobs"
			child.idx = row.get("idx") or 1
			child.flags.ignore_links = True
			child.insert(ignore_permissions=True)
			count += 1
		except Exception:
			frappe.log_error(
				title=f"Docket IJ backfill failed for {parent}",
				message=frappe.get_traceback(),
			)
	return count


def _restore_from_linked_service_documents() -> int:
	ls_dt = linked_service_doctype()
	if not ls_dt or not frappe.db.table_exists(f"tab{ls_dt}"):
		return 0

	ls_rows = frappe.get_all(
		ls_dt,
		filters={"parent_booking_type": "Docket"},
		fields=["name", "parent_booking_name"],
		order_by="parent_booking_name asc, creation asc",
	)
	count = 0
	for row in ls_rows:
		parent = (row.get("parent_booking_name") or "").strip()
		ls_name = (row.get("name") or "").strip()
		if not parent or not ls_name or not frappe.db.exists("Docket", parent):
			continue
		if frappe.db.exists(
			"Internal Job Detail",
			{"parent": parent, "parenttype": "Docket", "parentfield": "internal_jobs", "internal_job": ls_name},
		):
			continue
		try:
			ls_doc = frappe.get_doc(ls_dt, ls_name)
		except frappe.DoesNotExistError:
			continue
		child = frappe.new_doc("Internal Job Detail")
		child.parent = parent
		child.parenttype = "Docket"
		child.parentfield = "internal_jobs"
		set_row_linked_service_link(child, ls_name)
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
		child.flags.ignore_links = True
		child.insert(ignore_permissions=True)
		count += 1
	return count


def _ijd_row_exists(parent: str, lsd_row: dict) -> bool:
	idx = lsd_row.get("idx")
	if idx and frappe.db.exists(
		"Internal Job Detail",
		{"parent": parent, "parenttype": "Docket", "parentfield": "internal_jobs", "idx": idx},
	):
		return True
	ls_link = row_linked_service_link(lsd_row)
	if ls_link and frappe.db.exists(
		"Internal Job Detail",
		{
			"parent": parent,
			"parenttype": "Docket",
			"parentfield": "internal_jobs",
			"internal_job": ls_link,
		},
	):
		return True
	job_no = (lsd_row.get("job_no") or "").strip()
	service_type = (lsd_row.get("service_type") or "").strip()
	if job_no:
		return bool(
			frappe.db.exists(
				"Internal Job Detail",
				{
					"parent": parent,
					"parenttype": "Docket",
					"parentfield": "internal_jobs",
					"job_no": job_no,
				},
			)
		)
	if service_type:
		return bool(
			frappe.db.exists(
				"Internal Job Detail",
				{
					"parent": parent,
					"parenttype": "Docket",
					"parentfield": "internal_jobs",
					"service_type": service_type,
					"job_no": ["in", ("", None)],
				},
			)
		)
	return False
