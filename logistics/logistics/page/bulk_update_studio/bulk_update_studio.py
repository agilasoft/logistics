# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Desk API for Bulk Update Studio.

Updates are performed only by Bulk Update.bulk_update(). This module checks
the same System Manager permission, prepares the condition JSON, and returns
the list of failed names (or the background-job signal) that Frappe returns.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint

from logistics.logistics.page.bulk_update_studio.condition import (
	BACKGROUND_MIN_RECORDS,
	DEFAULT_LIMIT,
	MAX_LIMIT,
	NO_VALUE_TYPES,
	OPERATOR_LABELS,
	build_condition_from_rows,
	coerce_limit,
	normalize_update_value,
	split_condition_args,
	validate_condition_json,
)

STANDARD_CONDITION_FIELDS = (
	{"fieldname": "name", "label": "Name", "fieldtype": "Data", "options": None},
	{"fieldname": "docstatus", "label": "Document Status", "fieldtype": "Select", "options": "0\n1\n2"},
	{"fieldname": "owner", "label": "Owner", "fieldtype": "Link", "options": "User"},
	{"fieldname": "creation", "label": "Created On", "fieldtype": "Datetime", "options": None},
	{"fieldname": "modified", "label": "Modified On", "fieldtype": "Datetime", "options": None},
)


def _system_manager():
	frappe.only_for("System Manager")


@frappe.whitelist()
def get_studio_meta():
	"""Limits, operators, and DocType exclusions taken from Frappe Bulk Update."""
	_system_manager()
	return {
		"default_limit": DEFAULT_LIMIT,
		"max_limit": MAX_LIMIT,
		"background_min_records": BACKGROUND_MIN_RECORDS,
		"operators": OPERATOR_LABELS,
		"core_doctypes": list(frappe.model.core_doctypes_list),
		"standard_route": "Form/Bulk Update",
	}


@frappe.whitelist()
def get_eligible_fields(document_type: str):
	"""Fields the standard Bulk Update form can offer for this DocType."""
	_system_manager()
	meta = _meta(document_type)
	update_fields = []
	for df in meta.fields:
		if not df.fieldname or df.fieldtype in NO_VALUE_TYPES:
			continue
		update_fields.append(_field_payload(df))
	update_fields.sort(key=lambda field: (field["label"] or "").lower())

	seen = {field["fieldname"] for field in update_fields}
	condition_fields = []
	for field in STANDARD_CONDITION_FIELDS:
		if field["fieldname"] not in seen:
			condition_fields.append(dict(field))
	condition_fields.extend(update_fields)
	return {"update_fields": update_fields, "condition_fields": condition_fields}


@frappe.whitelist()
def compile_conditions(conditions=None):
	"""Compile visual rows to the JSON string Bulk Update stores in `condition`."""
	_system_manager()
	return {"condition": _rows_or_throw(conditions)}


@frappe.whitelist(methods=["POST"])
def preview_matching_records(
	document_type: str,
	field: str,
	update_value=None,
	condition: str | None = None,
	conditions=None,
	limit=None,
):
	"""Read matching names with the same filter arguments Bulk Update passes to get_all.

	The preview does not save documents. It is not the set Bulk Update will
	lock in, because records can change before the update runs.
	"""
	_system_manager()
	meta = _meta(document_type)
	df = _update_field(meta, field)
	value = _required_update_value(update_value, df.fieldtype)
	condition_text = _resolve_condition(condition, conditions, meta)
	effective_limit = coerce_limit(limit)
	rows = _preview_rows(meta.name, df.fieldname, condition_text, effective_limit)
	records = []
	for row in rows:
		records.append(
			{
				"name": row.get("name"),
				"current_value": row.get(df.fieldname),
				"docstatus": row.get("docstatus"),
			}
		)
	return {
		"records": records,
		"shown": len(records),
		"limit": effective_limit,
		"update_value": value,
		"field": df.fieldname,
		"fieldtype": df.fieldtype,
	}


@frappe.whitelist(methods=["POST"])
def execute_bulk_update(
	document_type: str,
	field: str,
	update_value,
	condition: str | None = None,
	conditions=None,
	limit=None,
):
	"""Run Frappe's Bulk Update. Return its failed-name list without adding counts."""
	_system_manager()
	meta = _meta(document_type)
	df = _update_field(meta, field)
	value = _required_update_value(update_value, df.fieldtype)
	condition_text = _resolve_condition(condition, conditions, meta)
	effective_limit = coerce_limit(limit)

	# Use the Bulk Update single only in this request. Restore it so the saved
	# form values are left as they were. bulk_update() itself does not save.
	doc = frappe.get_doc("Bulk Update")
	previous = {
		"document_type": doc.document_type,
		"field": doc.field,
		"update_value": doc.update_value,
		"condition": doc.condition,
		"limit": doc.limit,
	}
	doc.document_type = meta.name
	doc.field = df.fieldname
	doc.update_value = value
	doc.condition = condition_text
	doc.limit = effective_limit

	try:
		try:
			failed = doc.bulk_update()
		except frappe.PermissionError:
			raise
		except frappe.ValidationError:
			raise
		except Exception:
			frappe.log_error("Bulk Update Studio could not start the update")
			frappe.throw(_("The update could not be started. Check the Error Log for details."))
	finally:
		doc.update(previous)

	# Synchronous path returns a list (empty when nothing failed).
	# 20 or more names return None after Frappe queues the job.
	if isinstance(failed, list):
		failed_names = [name for name in failed if name]
		enqueued = False
	else:
		failed_names = None
		enqueued = True

	return {
		"failed": failed_names,
		"enqueued": enqueued,
		"limit": effective_limit,
		"document_type": meta.name,
		"field": df.fieldname,
		"update_value": value,
	}


def _meta(document_type: str):
	if not document_type or not frappe.db.exists("DocType", document_type):
		frappe.throw(_("Select a document type."))
	if document_type in frappe.model.core_doctypes_list:
		frappe.throw(_("Bulk Update does not include this document type."))
	if cint(frappe.db.get_value("DocType", document_type, "issingle")):
		frappe.throw(_("Bulk Update does not include single document types."))
	return frappe.get_meta(document_type)


def _update_field(meta, fieldname: str):
	if not fieldname:
		frappe.throw(_("Select a field to update."))
	df = meta.get_field(fieldname)
	if not df or not df.fieldname or df.fieldtype in NO_VALUE_TYPES:
		frappe.throw(_("This field cannot be updated with Bulk Update."))
	return df


def _required_update_value(update_value, fieldtype: str) -> str:
	value = normalize_update_value(update_value, fieldtype)
	if fieldtype == "Check":
		return value
	if value == "":
		frappe.throw(_("Enter the new value. Bulk Update requires a value."))
	return value


def _resolve_condition(condition, conditions, meta) -> str:
	text = str(condition).strip() if condition else ""
	if text:
		try:
			return validate_condition_json(text)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
	if conditions not in (None, "", []):
		_validate_row_fields(meta, conditions)
		return _rows_or_throw(conditions)
	return ""


def _rows_or_throw(conditions) -> str:
	try:
		return build_condition_from_rows(conditions)
	except ValueError as exc:
		frappe.throw(_(str(exc)))


def _validate_row_fields(meta, conditions):
	rows = conditions
	if isinstance(rows, str):
		try:
			rows = json.loads(rows)
		except json.JSONDecodeError:
			frappe.throw(_("Condition rows are not valid JSON."))
	if not isinstance(rows, (list, tuple)):
		return
	for row in rows:
		if not isinstance(row, dict):
			continue
		fieldname = str(row.get("field") or "").strip()
		if not fieldname:
			continue
		if not _condition_field_allowed(meta, fieldname):
			frappe.throw(
				_("The condition field {0} is not available on {1}.").format(fieldname, meta.name)
			)


def _condition_field_allowed(meta, fieldname: str) -> bool:
	if any(field["fieldname"] == fieldname for field in STANDARD_CONDITION_FIELDS):
		return True
	df = meta.get_field(fieldname)
	return bool(df and df.fieldname and df.fieldtype not in NO_VALUE_TYPES)


def _preview_rows(document_type: str, fieldname: str, condition_text: str, limit: int):
	fields = []
	for candidate in ("name", fieldname, "docstatus"):
		if candidate not in fields:
			fields.append(candidate)
	query_args = {"doctype": document_type, "limit": limit, "fields": fields}
	try:
		query_args.update(split_condition_args(condition_text))
		return frappe.get_all(**query_args)
	except Exception:
		frappe.log_error("Bulk Update Studio preview failed")
		frappe.throw(_("The matching records could not be read. Check the condition and try again."))


def _field_payload(df) -> dict:
	return {
		"fieldname": df.fieldname,
		"label": _(df.label) if df.label else df.fieldname,
		"fieldtype": df.fieldtype,
		"options": df.options,
		"read_only": cint(df.read_only),
	}
