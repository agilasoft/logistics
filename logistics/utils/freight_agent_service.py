# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Validate Freight Agent links against applicable service types on operational documents."""

from __future__ import annotations

import frappe
from frappe import _

from logistics.utils.charge_service_type import (
	IMPLIED_SERVICE_TYPE_BY_DOCTYPE,
	implied_service_type_for_doctype,
	operational_booking_charge_service_type_label,
)
from logistics.utils.service_mode_flags import validate_service_mode_link

FREIGHT_AGENT_LINK_FIELDS = frozenset({"freight_agent", "freight_agent_sea"})

# Explicit field → service label when it cannot be inferred from doctype alone.
_FIELD_SERVICE_TYPE_LABELS: dict[str, str] = {
	"freight_agent_sea": "Sea",
	"air_default_sending_agent": "Air",
	"air_default_receiving_agent": "Air",
	"air_default_broker": "Air",
	"sea_default_sending_agent": "Sea",
	"sea_default_receiving_agent": "Sea",
	"customs_default_freight_agent": "Customs",
}

_SETTINGS_DOCTYPE_SERVICE: dict[str, str] = {
	"Air Freight Settings": "Air",
	"Sea Freight Settings": "Sea",
}

_DOCTYPE_HAS_FREIGHT_AGENT_CACHE: dict[str, bool] = {}


def _meta_has_freight_agent_reference(meta) -> bool:
	for df in meta.fields:
		if df.fieldtype == "Link" and df.options == "Freight Agent":
			return True
		if df.fieldtype == "Table":
			try:
				child_meta = frappe.get_meta(df.options)
			except Exception:
				continue
			for cdf in child_meta.fields:
				if cdf.fieldtype == "Link" and cdf.options == "Freight Agent":
					return True
	return False


def doctype_references_freight_agent(doctype: str) -> bool:
	if doctype in _DOCTYPE_HAS_FREIGHT_AGENT_CACHE:
		return _DOCTYPE_HAS_FREIGHT_AGENT_CACHE[doctype]
	try:
		meta = frappe.get_meta(doctype)
	except Exception:
		_DOCTYPE_HAS_FREIGHT_AGENT_CACHE[doctype] = False
		return False
	out = _meta_has_freight_agent_reference(meta)
	_DOCTYPE_HAS_FREIGHT_AGENT_CACHE[doctype] = out
	return out


def resolve_service_type_label_for_freight_agent(doc, fieldname: str, row=None) -> str | None:
	"""Return UI service label (Air, Sea, …) for validating a Freight Agent link."""
	ctx = row if row is not None else doc

	service_type = _read_value(ctx, "service_type")
	if service_type:
		return operational_booking_charge_service_type_label(service_type, default=service_type)

	if fieldname in _FIELD_SERVICE_TYPE_LABELS:
		return _FIELD_SERVICE_TYPE_LABELS[fieldname]

	main_service = _read_value(doc, "main_service")
	if main_service:
		return operational_booking_charge_service_type_label(main_service, default=main_service)

	doctype = getattr(doc, "doctype", None) or ""
	if doctype in _SETTINGS_DOCTYPE_SERVICE:
		return _SETTINGS_DOCTYPE_SERVICE[doctype]

	implied = implied_service_type_for_doctype(doctype)
	if implied:
		return implied

	if fieldname in FREIGHT_AGENT_LINK_FIELDS:
		return IMPLIED_SERVICE_TYPE_BY_DOCTYPE.get(doctype)

	return None


def validate_freight_agent_link(
	agent_name: str | None,
	service_type_label: str | None,
	*,
	context: str,
) -> None:
	validate_service_mode_link(
		"Freight Agent",
		agent_name,
		service_type_label,
		context=context,
	)


def validate_freight_agent_links_on_doc(doc, method=None) -> None:
	if getattr(frappe.flags, "in_install", None) or getattr(frappe.flags, "in_migrate", None):
		return
	if getattr(frappe.flags, "in_import", None):
		return
	if not doctype_references_freight_agent(doc.doctype):
		return

	prev = doc.get_doc_before_save() if not doc.is_new() else None
	_validate_parent_freight_agent_links(doc, prev)
	_validate_child_table_freight_agent_links(doc, prev)


def _validate_parent_freight_agent_links(doc, prev) -> None:
	meta = frappe.get_meta(doc.doctype)
	for df in meta.fields:
		if df.fieldtype != "Link" or df.options != "Freight Agent":
			continue
		val = doc.get(df.fieldname)
		if not val:
			continue
		old_val = prev.get(df.fieldname) if prev else None
		if prev and old_val == val:
			continue
		service_label = resolve_service_type_label_for_freight_agent(doc, df.fieldname)
		if not service_label:
			continue
		validate_freight_agent_link(
			val,
			service_label,
			context=_("{0} ({1})").format(df.label or df.fieldname, doc.doctype),
		)


def _validate_child_table_freight_agent_links(doc, prev) -> None:
	meta = frappe.get_meta(doc.doctype)
	prev_by_name: dict[tuple[str, str], object] = {}
	if prev:
		for df in meta.fields:
			if df.fieldtype != "Table":
				continue
			for row in prev.get(df.fieldname) or []:
				if row.name:
					prev_by_name[(df.fieldname, row.name)] = row

	for df in meta.fields:
		if df.fieldtype != "Table":
			continue
		child_meta = frappe.get_meta(df.options)
		link_fields = [
			cdf for cdf in child_meta.fields if cdf.fieldtype == "Link" and cdf.options == "Freight Agent"
		]
		if not link_fields:
			continue
		table_label = df.label or df.fieldname
		for row in doc.get(df.fieldname) or []:
			pr = prev_by_name.get((df.fieldname, row.name)) if row.name else None
			for lf in link_fields:
				val = row.get(lf.fieldname)
				if not val:
					continue
				old_val = pr.get(lf.fieldname) if pr else None
				if pr and old_val == val:
					continue
				service_label = resolve_service_type_label_for_freight_agent(doc, lf.fieldname, row=row)
				if not service_label:
					continue
				validate_freight_agent_link(
					val,
					service_label,
					context=_("{0} row {1} ({2})").format(table_label, row.idx, lf.label or lf.fieldname),
				)


def _read_value(doc, fieldname: str):
	if doc is None:
		return None
	if isinstance(doc, dict):
		return doc.get(fieldname)
	return getattr(doc, fieldname, None)
