# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""Restore Special Project data from pre_model_sync staging after activity/order refactor."""

from __future__ import unicode_literals

import frappe
from frappe import _

STAGING_TABLES = [
	"_sp_legacy_special_project_job",
	"_sp_legacy_special_project_resource",
	"_sp_legacy_special_project_product",
	"_sp_legacy_special_project_equipment",
	"_sp_legacy_special_project_activity",
	"_sp_legacy_special_project_resource_request",
	"_sp_legacy_special_project_product_request",
	"_sp_legacy_special_project_equipment_request",
]

LEGACY_JOB_SELECT_TO_CATEGORY = {
	"Transport Job": "Transport",
	"Warehouse Job": "Warehousing",
	"Air Shipment": "Air",
	"Sea Shipment": "Sea",
	"Declaration": "Customs",
}

LEGACY_JOB_SELECT_TO_DOCTYPE = {
	"Transport Job": "Transport Job",
	"Warehouse Job": "Warehouse Job",
	"Air Shipment": "Air Shipment",
	"Sea Shipment": "Sea Shipment",
	"Declaration": "Declaration",
}

def _ensure_stub_special_project_job(special_project, title):
	doc = frappe.new_doc("Project Task Job")
	doc.naming_series = "SPJ-.#####"
	doc.title = (title or _("Migrated activity"))[:140]
	doc.special_project = special_project
	doc.insert(ignore_permissions=True)
	return doc.name


def _ij_from_legacy_operational_job(old_jt, old_job):
	"""Map a legacy per-mode job (e.g. Air Shipment) to Internal Job Detail row fields."""
	if not old_jt or not old_job:
		return None
	if old_jt == "Air Shipment":
		bk = frappe.db.get_value("Air Shipment", old_job, "air_booking")
		return {"service_type": "Air", "job_no": bk or old_job}
	if old_jt == "Sea Shipment":
		bk = frappe.db.get_value("Sea Shipment", old_job, "sea_booking")
		return {"service_type": "Sea", "job_no": bk or old_job}
	if old_jt == "Transport Job":
		to = frappe.db.get_value("Transport Job", old_job, "transport_order")
		return {"service_type": "Transport", "job_no": to or old_job}
	if old_jt == "Declaration":
		do = frappe.db.get_value("Declaration", old_job, "declaration_order")
		return {"service_type": "Customs", "job_no": do or old_job}
	if old_jt == "Warehouse Job":
		rt = frappe.db.get_value(
			"Warehouse Job",
			old_job,
			["reference_order_type", "reference_order"],
			as_dict=True,
		)
		out = {
			"service_type": "Warehousing",
			"job_no": (rt or {}).get("reference_order") or old_job,
		}
		jt = (rt or {}).get("reference_order_type") if rt else None
		if jt in ("Inbound Order", "Release Order", "Transfer Order"):
			out["job_type"] = jt
		return out
	return None


def execute():
	if not any(frappe.db.table_exists(t) for t in STAGING_TABLES):
		return

	try:
		if frappe.db.table_exists("tabSpecial Project Activity"):
			frappe.db.sql(
				"""
				UPDATE `tabSpecial Project Activity`
				SET parentfield = 'activity'
				WHERE parenttype = 'Special Project'
				"""
			)

		_migrate_existing_activity_rows_from_staging()
		_migrate_legacy_job_child_rows()
		_migrate_resource_rows()
		_migrate_product_rows()
		_migrate_equipment_rows()
		_migrate_resource_requests()
		_migrate_product_requests()
		_migrate_equipment_requests()
		frappe.db.commit()
	finally:
		for t in STAGING_TABLES:
			if frappe.db.table_exists(t):
				frappe.db.sql_ddl("DROP TABLE IF EXISTS `{}`".format(t))
		frappe.db.commit()


def _migrate_existing_activity_rows_from_staging():
	if not frappe.db.table_exists("tabSpecial Project Activity"):
		return
	if not frappe.db.table_exists("_sp_legacy_special_project_activity"):
		return
	legacy = frappe.db.sql("SELECT * FROM `_sp_legacy_special_project_activity`", as_dict=True)
	for lr in legacy:
		name = lr.get("name")
		if not name or not frappe.db.exists("Special Project Activity", name):
			continue
		old_jt = (lr.get("job_type") or "").strip()
		old_job = (lr.get("job") or "").strip()
		if old_jt in LEGACY_JOB_SELECT_TO_CATEGORY and old_job:
			frappe.db.set_value(
				"Special Project Activity",
				name,
				{
					"job_type": LEGACY_JOB_SELECT_TO_CATEGORY[old_jt],
					"logistics_link_doctype": LEGACY_JOB_SELECT_TO_DOCTYPE[old_jt],
					"logistics_job": old_job,
					"special_project_job": None,
				},
				update_modified=False,
			)
		elif old_job:
			pass
		else:
			parent = lr.get("parent")
			if not parent or not frappe.db.exists("Special Project", parent):
				continue
			title = lr.get("activity_name") or lr.get("description") or name
			sp_job = _ensure_stub_special_project_job(parent, title)
			frappe.db.set_value(
				"Special Project Activity",
				name,
				{
					"job_type": "Project Task Job",
					"logistics_link_doctype": None,
					"logistics_job": None,
					"special_project_job": sp_job,
				},
				update_modified=False,
			)


def _migrate_legacy_job_child_rows():
	if not frappe.db.table_exists("_sp_legacy_special_project_job"):
		return
	rows = frappe.db.sql(
		"SELECT * FROM `_sp_legacy_special_project_job` WHERE parenttype = 'Special Project'",
		as_dict=True,
	)
	by_parent = {}
	for row in rows:
		by_parent.setdefault(row.get("parent"), []).append(row)

	for parent, prow in by_parent.items():
		if not parent or not frappe.db.exists("Special Project", parent):
			continue
		sp = frappe.get_doc("Special Project", parent)
		for row in prow:
			old_jt = (row.get("job_type") or "").strip()
			old_job = (row.get("job") or "").strip()
			if old_jt not in LEGACY_JOB_SELECT_TO_DOCTYPE or not old_job:
				continue
			payload = _ij_from_legacy_operational_job(old_jt, old_job)
			if not payload:
				continue
			note_from_row = row.get("notes") or _("Linked {0}").format(old_job)
			if note_from_row:
				prev = (payload.get("sp_resource_notes") or "").strip()
				payload["sp_resource_notes"] = (note_from_row + (" — " + prev if prev else "")).strip()
			for fin in ("planned_cost", "actual_cost", "planned_revenue", "actual_revenue"):
				if row.get(fin) is not None:
					payload[fin] = row.get(fin)
			sp.append("internal_job_details", payload)
		sp.save(ignore_permissions=True)


def _migrate_resource_rows():
	if not frappe.db.table_exists("_sp_legacy_special_project_resource"):
		return
	rows = frappe.db.sql(
		"SELECT * FROM `_sp_legacy_special_project_resource` WHERE parenttype = 'Special Project'",
		as_dict=True,
	)
	by_parent = {}
	for row in rows:
		by_parent.setdefault(row.get("parent"), []).append(row)

	for parent, prow in by_parent.items():
		if not parent or not frappe.db.exists("Special Project", parent):
			continue
		sp = frappe.get_doc("Special Project", parent)
		for row in prow:
			title = row.get("resource_role") or _("Migrated resource")
			sp_job = _ensure_stub_special_project_job(parent, title)
			res_type = (row.get("resource_type") or "").strip()
			qty = row.get("quantity") or 1
			note_parts = [x for x in (res_type, row.get("resource_role"), row.get("notes")) if x]
			notes = (" — ".join(note_parts)) if note_parts else None
			notes = title + (" — " + notes if notes else "")
			payload = {
				"service_type": "Special Project",
				"job_no": sp_job,
				"sp_resource_notes": notes,
			}
			if res_type == "Personnel":
				payload["sp_manpower"] = qty
			sp.append("internal_job_details", payload)
		sp.save(ignore_permissions=True)


def _migrate_product_rows():
	if not frappe.db.table_exists("_sp_legacy_special_project_product"):
		return
	rows = frappe.db.sql(
		"SELECT * FROM `_sp_legacy_special_project_product` WHERE parenttype = 'Special Project'",
		as_dict=True,
	)
	by_parent = {}
	for row in rows:
		by_parent.setdefault(row.get("parent"), []).append(row)

	for parent, prow in by_parent.items():
		if not parent or not frappe.db.exists("Special Project", parent):
			continue
		sp = frappe.get_doc("Special Project", parent)
		for row in prow:
			item_code = row.get("item")
			title = frappe.db.get_value("Item", item_code, "item_name") if item_code else _("Migrated product")
			sp_job = _ensure_stub_special_project_job(parent, title or item_code or _("Product"))
			parts = []
			if item_code:
				parts.append(_("Item: {0}").format(item_code))
			if row.get("quantity") is not None:
				parts.append(_("Qty: {0} {1}").format(row.get("quantity"), row.get("uom") or ""))
			if row.get("description"):
				parts.append(row.get("description"))
			if row.get("notes"):
				parts.append(row.get("notes"))
			body = " — ".join(parts) if parts else None
			header = (title or item_code or "").strip()
			if header:
				body = header + (" — " + body if body else "")
			sp.append(
				"internal_job_details",
				{
					"service_type": "Special Project",
					"job_no": sp_job,
					"sp_handling": row.get("special_handling"),
					"sp_resource_notes": body,
				},
			)
		sp.save(ignore_permissions=True)


def _migrate_equipment_rows():
	if not frappe.db.table_exists("_sp_legacy_special_project_equipment"):
		return
	rows = frappe.db.sql(
		"SELECT * FROM `_sp_legacy_special_project_equipment` WHERE parenttype = 'Special Project'",
		as_dict=True,
	)
	by_parent = {}
	for row in rows:
		by_parent.setdefault(row.get("parent"), []).append(row)

	for parent, prow in by_parent.items():
		if not parent or not frappe.db.exists("Special Project", parent):
			continue
		sp = frappe.get_doc("Special Project", parent)
		for row in prow:
			title = _("Equipment: {0}").format(row.get("equipment_type") or "?")
			sp_job = _ensure_stub_special_project_job(parent, title)
			notes = row.get("notes")
			if title:
				notes = title + (" — " + notes if notes else "")
			sp.append(
				"internal_job_details",
				{
					"service_type": "Special Project",
					"job_no": sp_job,
					"sp_equipment_type": row.get("equipment_type"),
					"sp_resource_notes": notes,
				},
			)
		sp.save(ignore_permissions=True)


def _migrate_resource_requests():
	"""Legacy: attached resource rows to Special Project Request. DocType removed; no-op."""
	return


def _migrate_product_requests():
	"""Legacy: attached product rows to Special Project Request. DocType removed; no-op."""
	return


def _migrate_equipment_requests():
	"""Legacy: attached equipment rows to Special Project Request. DocType removed; no-op."""
	return
