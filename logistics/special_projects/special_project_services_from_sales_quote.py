# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Populate Special Project Services from Sales Quote Linked Service documents."""

from __future__ import annotations

from typing import Any

import frappe

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


def _norm(val: Any) -> str:
	if val is None:
		return ""
	return str(val).strip()


def resolve_lifecycle_stage_for_service_type(service_type: str | None) -> str | None:
	"""Pick a lifecycle stage for a new Special Project Service row."""
	st = _norm(service_type)
	preferred = _SERVICE_TYPE_DEFAULT_LIFECYCLE_STAGE.get(st)
	if preferred and frappe.db.exists("Lifecycle Stage", preferred):
		return preferred
	return resolve_default_lifecycle_stage(
		module_filter=FOR_SPECIAL_PROJECT,
		preferred=preferred or "Pre-Show",
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

	Returns ``{linked_service_name: special_project_service_name}`` for charge remapping.
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


def remap_special_project_charges_after_quote_populate(
	sp_doc: Any,
	ls_to_sps: dict[str, str] | None = None,
) -> None:
	"""Tag programme charges to Service Line rows and drop stale quote Linked Service links."""
	if not sp_doc or sp_doc.doctype != "Special Project":
		return
	ls_to_sps = dict(ls_to_sps or {})
	main_sps = ls_to_sps.get("__main_special_project__")
	meta = frappe.get_meta("Special Project Charges")

	for charge in sp_doc.get("charges") or []:
		ls_name = charge_row_linked_service_link(charge)
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

		if meta.has_field("linked_service"):
			charge.linked_service = None
		if meta.has_field("internal_job"):
			charge.internal_job = None


@frappe.whitelist()
def repair_special_project_from_sales_quote(docname: str) -> dict[str, Any]:
	"""Backfill Services and charge Service Line links from the linked Sales Quote."""
	if not docname or not frappe.db.exists("Special Project", docname):
		frappe.throw(_("Special Project {0} not found.").format(docname))

	from logistics.special_projects.special_project_service_helpers import (
		tag_untagged_charges_to_planning_services,
	)

	sp = frappe.get_doc("Special Project", docname)
	sq_name = (getattr(sp, "sales_quote", None) or "").strip()
	if not sq_name:
		frappe.throw(_("No Sales Quote linked on {0}.").format(docname))

	ls_to_sps = populate_special_project_services_from_sales_quote(
		sp, sq_name, clear_existing=True
	)
	remap_special_project_charges_after_quote_populate(sp, ls_to_sps)
	tag_untagged_charges_to_planning_services(sp)
	sp.flags.ignore_permissions = True
	sp.save(ignore_permissions=True)
	frappe.db.commit()

	service_count = len(
		frappe.get_all(
			special_project_service_doctype(),
			filters={
				"parent_booking_type": "Special Project",
				"parent_booking_name": docname,
			},
		)
	)
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
		"service_count": service_count,
		"charges": charges,
	}
