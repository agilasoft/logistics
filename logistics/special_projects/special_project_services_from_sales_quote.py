# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy Sales Quote programme data onto Special Project without cloning service records."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from logistics.special_projects.special_project_service_compat import (
	special_project_service_doctype,
	special_project_service_record_exists,
)
from logistics.special_projects.special_project_service_persistence import (
	_create_service_doc_from_row,
	_delete_orphan_service_docs,
	_special_project_service_names_from_db,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.lifecycle_stage import FOR_SPECIAL_PROJECT, resolve_default_lifecycle_stage
from logistics.utils.linked_service_compat import (
	charge_row_linked_service_link,
	linked_service_doctype_exists,
	linked_service_record_exists,
	normalize_charge_scope,
)
from logistics.utils.sales_quote_one_off_internal_jobs import _payload_from_linked_service_doc

_SERVICE_TYPE_DEFAULT_LIFECYCLE_STAGE: dict[str, str] = {
	"Air": "Port operation",
	"Sea": "Port operation",
	"Customs": "Logistics",
	"Transport": "Delivery to site",
	"Special Project": "On-Site",
	"Warehousing": "Logistics",
	"MICE": "Pre-Shipment",
}

_QUOTE_LINKED_SERVICE_VIEW_FLAG = "__quote_linked_service_readonly__"


def _norm(val: Any) -> str:
	if val is None:
		return ""
	return str(val).strip()


def resolve_lifecycle_stage_for_service_type(service_type: str | None) -> str | None:
	"""Pick a lifecycle stage for a new Special Project Service row."""
	st = _norm(service_type)
	preferred = _SERVICE_TYPE_DEFAULT_LIFECYCLE_STAGE.get(st)
	if preferred and frappe.db.exists(
		"Lifecycle Stage", {"name": preferred, FOR_SPECIAL_PROJECT: 1}
	):
		return preferred
	return resolve_default_lifecycle_stage(
		module_filter=FOR_SPECIAL_PROJECT,
		preferred=preferred or "Logistics",
	)


def _row_from_linked_service_doc(ls_doc: Any) -> dict[str, Any]:
	row = _payload_from_linked_service_doc(ls_doc, ls_doc.name)
	row["lifecycle_stage"] = resolve_lifecycle_stage_for_service_type(
		getattr(ls_doc, "service_type", None)
	)
	return row


def _linked_services_for_sales_quote(sales_quote_name: str) -> list[Any]:
	if not sales_quote_name or not linked_service_doctype_exists():
		return []
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_sales_quote,
	)

	return list(get_linked_services_for_sales_quote(sales_quote_name))


def linked_services_view_rows_for_sales_quote(sales_quote_name: str) -> list[dict[str, Any]]:
	"""Read-only Services grid rows backed by quote-owned Linked Service documents."""
	rows: list[dict[str, Any]] = []
	for ls_doc in _linked_services_for_sales_quote(sales_quote_name):
		ls_name = _norm(getattr(ls_doc, "name", None))
		if not ls_name:
			continue
		row = _row_from_linked_service_doc(ls_doc)
		row["name"] = ls_name
		row[_QUOTE_LINKED_SERVICE_VIEW_FLAG] = 1
		rows.append(row)
	return rows


def _sync_charge_lifecycle_from_linked_services(sp_doc: Any) -> None:
	"""Inherit lifecycle stage from the linked quote service when the charge row has one."""
	for charge in sp_doc.get("charges") or []:
		ls_name = charge_row_linked_service_link(charge)
		if not ls_name or not linked_service_record_exists(ls_name):
			continue
		if _norm(getattr(charge, "lifecycle_stage", None)):
			continue
		ls_doc = frappe.get_doc("Linked Service", ls_name)
		row = _row_from_linked_service_doc(ls_doc)
		stage = row.get("lifecycle_stage")
		if _norm(stage):
			charge.lifecycle_stage = stage


def copy_special_project_programme_data_from_sales_quote(
	sp_doc: Any,
	sales_quote_name: str | None = None,
	*,
	clear_existing: bool = True,
) -> int:
	"""Copy quote charges onto Special Project, preserving Linked Service links as-is."""
	if not sp_doc or sp_doc.doctype != "Special Project":
		return 0
	sq_name = _norm(sales_quote_name) or _norm(getattr(sp_doc, "sales_quote", None))
	if not sq_name:
		return 0

	from logistics.utils.sales_quote_programme_charges import populate_programme_charges_from_sales_quote

	added = populate_programme_charges_from_sales_quote(
		sp_doc, sq_name, clear_existing=clear_existing, service_types="__all__"
	)
	_sync_charge_lifecycle_from_linked_services(sp_doc)
	return added


def _clear_owned_special_project_services(sp_doc: Any) -> None:
	parent_name = _norm(getattr(sp_doc, "name", None))
	if not parent_name:
		return
	existing = _special_project_service_names_from_db(parent_name)
	_delete_orphan_service_docs(existing, set())


def _service_types_on_doc(sp_doc: Any) -> set[str]:
	types: set[str] = set()
	for name in _special_project_service_names_from_db(_norm(getattr(sp_doc, "name", None))):
		st = frappe.db.get_value(special_project_service_doctype(), name, "service_type")
		if _norm(st):
			types.add(_norm(st))
	return types


def _ensure_main_special_project_service(sp_doc: Any, ls_to_sps: dict[str, str]) -> dict[str, str]:
	"""Create an On-Site Special Project leg when programme charges include Main SP scope."""
	has_main_sp_charge = False
	for charge in sp_doc.get("charges") or []:
		if normalize_charge_scope(getattr(charge, "charge_scope", None)) != "Main":
			continue
		if sales_quote_charge_service_types_equal(
			getattr(charge, "service_type", None), "Special Project"
		):
			has_main_sp_charge = True
			break
	if not has_main_sp_charge:
		return ls_to_sps
	if any(
		sales_quote_charge_service_types_equal(st, "Special Project")
		for st in _service_types_on_doc(sp_doc)
	):
		return ls_to_sps

	row = {
		"service_type": "Special Project",
		"lifecycle_stage": resolve_lifecycle_stage_for_service_type("Special Project"),
	}
	sps_name = _create_service_doc_from_row(sp_doc, row)
	ls_to_sps.setdefault("__main_special_project__", sps_name)
	return ls_to_sps


def populate_special_project_services_from_sales_quote(
	sp_doc: Any,
	sales_quote_name: str | None = None,
	*,
	clear_existing: bool = False,
) -> dict[str, str]:
	"""Create Special Project Service documents from quote-owned Linked Services.

	Used by explicit repair / service rebuild flows. Sales Quote → Special Project
	create copies quote Linked Service links on charges instead of cloning services.
	"""
	if not sp_doc or sp_doc.doctype != "Special Project":
		return {}
	if not frappe.db.exists("DocType", special_project_service_doctype()):
		return {}
	sq_name = sales_quote_name or getattr(sp_doc, "sales_quote", None)
	if not sq_name or not sp_doc.name:
		return {}

	if clear_existing:
		_clear_owned_special_project_services(sp_doc)

	ls_to_sps: dict[str, str] = {}
	for ls_doc in _linked_services_for_sales_quote(sq_name):
		ls_name = _norm(getattr(ls_doc, "name", None))
		if not ls_name:
			continue
		row = _row_from_linked_service_doc(ls_doc)
		sps_name = _create_service_doc_from_row(sp_doc, row)
		ls_to_sps[ls_name] = sps_name

	return _ensure_main_special_project_service(sp_doc, ls_to_sps)


def _iter_special_project_charge_sq_pairs(
	sp_doc: Any,
	sales_quote_name: str,
	*,
	service_types=None,
) -> list[tuple[Any | None, Any]]:
	"""Pair programme charge rows with source Sales Quote charge rows (populate order)."""
	from logistics.utils.sales_quote_programme_charges import _iter_programme_charge_sq_pairs

	if not sales_quote_name or not frappe.db.exists("Sales Quote", sales_quote_name):
		return [(None, charge) for charge in (sp_doc.get("charges") or [])]

	pairs = list(
		_iter_programme_charge_sq_pairs(sp_doc, sales_quote_name, service_types=service_types)
	)
	if pairs:
		return pairs
	return [(None, charge) for charge in (sp_doc.get("charges") or [])]


def remap_special_project_charges_after_quote_populate(
	sp_doc: Any,
	ls_to_sps: dict[str, str] | None = None,
	*,
	sales_quote_name: str | None = None,
	service_types: Any = "__all__",
) -> dict[str, str]:
	"""Tag programme charges to Service Line rows when services were cloned from the quote.

	Returns the updated ``{linked_service_name: special_project_service_name}`` map.
	"""
	if not sp_doc or sp_doc.doctype != "Special Project":
		return dict(ls_to_sps or {})
	ls_to_sps = dict(ls_to_sps or {})
	if not ls_to_sps:
		return ls_to_sps
	sq_name = _norm(sales_quote_name) or _norm(getattr(sp_doc, "sales_quote", None))

	ls_to_sps = _ensure_main_special_project_service(sp_doc, ls_to_sps)
	main_sps = ls_to_sps.get("__main_special_project__")

	charge_pairs = (
		_iter_special_project_charge_sq_pairs(sp_doc, sq_name, service_types=service_types)
		if sq_name
		else [(None, charge) for charge in (sp_doc.get("charges") or [])]
	)

	for sq_row, charge in charge_pairs:
		ls_name = charge_row_linked_service_link(charge)
		if not ls_name and sq_row is not None:
			ls_name = charge_row_linked_service_link(sq_row)
		line_name = None
		if ls_name and ls_name in ls_to_sps:
			line_name = ls_to_sps[ls_name]
		elif (
			normalize_charge_scope(getattr(charge, "charge_scope", None)) == "Main"
			and main_sps
			and sales_quote_charge_service_types_equal(
				getattr(charge, "service_type", None), "Special Project"
			)
		):
			line_name = main_sps

		if line_name and special_project_service_record_exists(line_name):
			charge.special_project_service_line = line_name
			sps_stage = frappe.db.get_value(
				special_project_service_doctype(),
				line_name,
				"lifecycle_stage",
			)
			if _norm(sps_stage):
				charge.lifecycle_stage = sps_stage

	return ls_to_sps


@frappe.whitelist()
def repair_special_project_from_sales_quote(docname: str) -> dict[str, Any]:
	"""Re-copy quote charges (with Linked Service links) onto the Special Project."""
	if not docname or not frappe.db.exists("Special Project", docname):
		frappe.throw(_("Special Project {0} not found.").format(docname))

	sp = frappe.get_doc("Special Project", docname)
	sq_name = (getattr(sp, "sales_quote", None) or "").strip()

	if not sq_name:
		frappe.throw(_("No Sales Quote linked on {0}.").format(docname))

	copy_special_project_programme_data_from_sales_quote(sp, sq_name, clear_existing=True)
	sp.flags.ignore_links = True
	sp.flags.ignore_permissions = True
	sp.save(ignore_permissions=True)
	frappe.db.commit()

	charges = frappe.get_all(
		"Special Project Charges",
		filters={"parent": docname, "parenttype": "Special Project"},
		fields=["idx", "charge_scope", "linked_service", "special_project_service_line"],
		order_by="idx asc",
	)

	return {
		"success": True,
		"special_project": docname,
		"sales_quote": sq_name,
		"service_count": len(linked_services_view_rows_for_sales_quote(sq_name)),
		"charges": charges,
	}
