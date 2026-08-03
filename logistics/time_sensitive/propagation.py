# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Propagate time-sensitive identifiers across CargoNext documents."""

from __future__ import annotations

import frappe
from frappe.utils import cint


TIME_SENSITIVE_DOWNSTREAM_DOCTYPES = (
	"Air Booking",
	"Sea Booking",
	"Air Shipment",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration Order",
	"Declaration",
	"VAS Order",
	"Inbound Order",
	"Release Order",
	"Cross-Docking Order",
	"Warehouse Job",
)

TS_FIELDS = (
	"is_time_sensitive",
	"time_sensitive_case",
	"ts_case_type",
	"critical_deadline",
)


def _meta_has(doctype: str, fieldname: str) -> bool:
	try:
		return bool(frappe.get_meta(doctype).get_field(fieldname))
	except Exception:
		return False


def stamp_document_from_case(doctype: str, docname: str, case) -> None:
	"""Stamp operational document with case identifiers and deadline."""
	if not doctype or not docname or not frappe.db.exists(doctype, docname):
		return
	updates = {}
	if _meta_has(doctype, "is_time_sensitive"):
		updates["is_time_sensitive"] = 1
	if _meta_has(doctype, "time_sensitive_case"):
		updates["time_sensitive_case"] = case.name if hasattr(case, "name") else case
	if _meta_has(doctype, "ts_case_type"):
		updates["ts_case_type"] = getattr(case, "case_type", None)
	if _meta_has(doctype, "critical_deadline") and getattr(case, "critical_deadline", None):
		updates["critical_deadline"] = case.critical_deadline
	for field, value in updates.items():
		try:
			frappe.db.set_value(doctype, docname, field, value, update_modified=False)
		except Exception:
			frappe.log_error(
				title="stamp_document_from_case",
				message=f"{doctype} {docname} {field}",
			)


def apply_time_sensitive_from_source(source_doc, target_doc) -> None:
	"""Copy time-sensitive flag/case/deadline from source onto target when empty/force-set."""
	if not hasattr(target_doc, "is_time_sensitive"):
		return
	if cint(getattr(source_doc, "is_time_sensitive", 0)):
		if not cint(getattr(target_doc, "is_time_sensitive", 0)):
			target_doc.is_time_sensitive = 1
	if hasattr(target_doc, "time_sensitive_case"):
		src_case = getattr(source_doc, "time_sensitive_case", None)
		if src_case and not getattr(target_doc, "time_sensitive_case", None):
			target_doc.time_sensitive_case = src_case
	if hasattr(target_doc, "ts_case_type"):
		src_type = getattr(source_doc, "ts_case_type", None)
		if src_type and not getattr(target_doc, "ts_case_type", None):
			target_doc.ts_case_type = src_type
	if hasattr(target_doc, "critical_deadline"):
		src_dl = getattr(source_doc, "critical_deadline", None)
		if src_dl and not getattr(target_doc, "critical_deadline", None):
			target_doc.critical_deadline = src_dl


def apply_time_sensitive_from_linked_sales_quote(doc) -> None:
	"""On save: inherit time-sensitive flag from linked Sales Quote."""
	if not hasattr(doc, "is_time_sensitive"):
		return
	sq = getattr(doc, "sales_quote", None)
	if not sq:
		return
	try:
		vals = frappe.db.get_value(
			"Sales Quote",
			sq,
			["is_time_sensitive", "time_sensitive_case", "critical_deadline", "ts_case_type"],
			as_dict=True,
		)
	except Exception:
		return
	if not vals:
		return
	if cint(vals.get("is_time_sensitive")):
		doc.is_time_sensitive = 1
	if hasattr(doc, "time_sensitive_case") and vals.get("time_sensitive_case") and not doc.time_sensitive_case:
		doc.time_sensitive_case = vals.time_sensitive_case
	if hasattr(doc, "critical_deadline") and vals.get("critical_deadline") and not doc.critical_deadline:
		doc.critical_deadline = vals.critical_deadline
	if hasattr(doc, "ts_case_type") and vals.get("ts_case_type") and not getattr(doc, "ts_case_type", None):
		doc.ts_case_type = vals.ts_case_type


def propagate_time_sensitive_from_sales_quote(sales_quote_name: str | None) -> None:
	"""Force is_time_sensitive=1 (and case/deadline) on downstream docs linked to the quote."""
	if not sales_quote_name:
		return
	try:
		vals = frappe.db.get_value(
			"Sales Quote",
			sales_quote_name,
			["is_time_sensitive", "time_sensitive_case", "critical_deadline", "ts_case_type"],
			as_dict=True,
		)
	except Exception:
		return
	if not vals or not cint(vals.get("is_time_sensitive")):
		return

	for dt in TIME_SENSITIVE_DOWNSTREAM_DOCTYPES:
		if not _meta_has(dt, "is_time_sensitive") or not _meta_has(dt, "sales_quote"):
			continue
		try:
			names = frappe.get_all(
				dt,
				filters={"sales_quote": sales_quote_name},
				pluck="name",
			)
		except Exception:
			continue
		for name in names:
			updates = {"is_time_sensitive": 1}
			if _meta_has(dt, "time_sensitive_case") and vals.get("time_sensitive_case"):
				updates["time_sensitive_case"] = vals.time_sensitive_case
			if _meta_has(dt, "critical_deadline") and vals.get("critical_deadline"):
				updates["critical_deadline"] = vals.critical_deadline
			if _meta_has(dt, "ts_case_type") and vals.get("ts_case_type"):
				updates["ts_case_type"] = vals.ts_case_type
			try:
				frappe.db.set_value(dt, name, updates, update_modified=False)
			except Exception:
				frappe.log_error(
					title="propagate_time_sensitive_from_sales_quote",
					message=f"{dt} {name}",
				)


def copy_time_sensitive_fields_to_target(source_doc, target_doc) -> None:
	"""Used from module_integration.copy_sales_quote_fields_to_target style flows."""
	apply_time_sensitive_from_source(source_doc, target_doc)
	sq = getattr(source_doc, "sales_quote", None) or getattr(target_doc, "sales_quote", None)
	if sq:
		try:
			sqdoc = frappe.get_cached_doc("Sales Quote", sq)
		except Exception:
			sqdoc = None
		if sqdoc:
			apply_time_sensitive_from_source(sqdoc, target_doc)
