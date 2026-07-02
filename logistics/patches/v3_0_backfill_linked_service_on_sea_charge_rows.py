# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill ``linked_service`` on Sea charge rows scoped Linked with an empty link."""

from __future__ import unicode_literals

import frappe

from logistics.utils.linked_service_compat import linked_service_record_exists

_CHARGE_PARENTS = (
	("Sea Booking Charges", "Sea Booking", "internal_job_details"),
	("Sea Shipment Charges", "Sea Shipment", "internal_job_details"),
)


def _detail_link_column(detail_dt: str) -> str | None:
	meta = frappe.get_meta(detail_dt)
	if meta.has_field("linked_service"):
		return "linked_service"
	if meta.has_field("internal_job"):
		return "internal_job"
	return None


def _service_type_map(parent: str, parenttype: str, parentfield: str, detail_dt: str) -> dict[str, str]:
	link_col = _detail_link_column(detail_dt)
	if not link_col:
		return {}
	rows = frappe.get_all(
		detail_dt,
		filters={"parent": parent, "parenttype": parenttype, "parentfield": parentfield},
		fields=["service_type", link_col],
	)
	out: dict[str, str] = {}
	for row in rows:
		st = (row.get("service_type") or "").strip()
		ls = (row.get(link_col) or "").strip()
		if st and ls:
			out[st] = ls
	return out


def execute():
	for charge_dt, parent_dt, parentfield in _CHARGE_PARENTS:
		if not frappe.db.exists("DocType", charge_dt):
			continue
		if not frappe.db.table_exists(f"tab{charge_dt}"):
			continue
		charge_meta = frappe.get_meta(charge_dt)
		if not charge_meta.has_field("linked_service") or not charge_meta.has_field("charge_scope"):
			continue
		detail_df = frappe.get_meta(parent_dt).get_field(parentfield)
		if not detail_df:
			continue
		detail_dt = (detail_df.options or "").strip()
		if not detail_dt:
			continue

		orphans = frappe.db.sql(
			f"""
			SELECT name, parent, service_type
			FROM `tab{charge_dt}`
			WHERE charge_scope = 'Linked'
			  AND IFNULL(linked_service, '') = ''
			""",
			as_dict=True,
		)
		for row in orphans:
			parent_name = row.get("parent")
			if not parent_name:
				continue
			by_service = _service_type_map(parent_name, parent_dt, parentfield, detail_dt)
			service_type = (row.get("service_type") or "").strip()
			replacement = by_service.get(service_type) if service_type else None
			if replacement and linked_service_record_exists(replacement):
				frappe.db.set_value(
					charge_dt,
					row.name,
					"linked_service",
					replacement,
					update_modified=False,
				)
			else:
				frappe.db.set_value(
					charge_dt,
					row.name,
					{"charge_scope": "Main", "linked_service": None},
					update_modified=False,
				)

	frappe.db.commit()
