# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Build Project Order documents from a Special Project programme."""

from __future__ import annotations

from typing import Any, Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

from logistics.special_projects.doctype.project_order.project_order import (
	_copy_child_rows_by_common_fields,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal


def suggested_order_title_from_lifecycle_row(
	sp_doc: Document, lifecycle_row: Any | None = None, fallback: str | None = None
) -> str:
	"""Default Order Title for the create dialog."""
	if lifecycle_row:
		for fn in ("activity_name", "job_description"):
			val = (getattr(lifecycle_row, fn, None) or "").strip()
			if val:
				return val
	if fallback and str(fallback).strip():
		return str(fallback).strip()
	pn = (getattr(sp_doc, "project_name", None) or sp_doc.name or "").strip()
	return f"{pn} — {_('Task')}" if pn else _("Task")


def _ensure_order_company(order: Document, sp_doc: Document) -> None:
	"""Require company on the order (from programme or global default)."""
	meta = frappe.get_meta("Project Order")
	d = frappe.defaults.get_defaults()
	company = getattr(sp_doc, "company", None) or d.get("company")
	if company and meta.has_field("company"):
		order.company = company
	if not getattr(order, "company", None):
		frappe.throw(
			_(
				"Set Company on the Special Project (Charges tab) or set a default Company in Global Defaults before creating a Project Order."
			)
		)
	for field, sp_attr in (
		("branch", "branch"),
		("cost_center", "cost_center"),
		("profit_center", "profit_center"),
	):
		if not meta.has_field(field):
			continue
		val = getattr(sp_doc, sp_attr, None)
		if val:
			order.set(field, val)


def _append_special_project_charges(sp_doc: Document, order: Document) -> None:
	"""Copy programme charge rows where service_type is Special Project."""
	filtered = [
		ch
		for ch in (getattr(sp_doc, "charges", None) or [])
		if sales_quote_charge_service_types_equal(
			getattr(ch, "service_type", None), "Special Project"
		)
	]
	if not filtered:
		return
	wrapper = frappe._dict({"charges": filtered})
	_copy_child_rows_by_common_fields(wrapper, "charges", order, "charges")


def build_project_order_from_special_project(
	sp_doc: Document,
	order_title: str,
	lifecycle_row: Any | None = None,
) -> Document:
	"""Construct an unsaved Project Order from a Special Project."""
	title = (order_title or "").strip()
	if not title:
		title = suggested_order_title_from_lifecycle_row(sp_doc, lifecycle_row)

	order = frappe.new_doc("Project Order")
	order.special_project = sp_doc.name
	order.order_title = title
	if order.meta.has_field("order_date"):
		order.order_date = today()
	if order.meta.has_field("status"):
		order.status = "Draft"

	_ensure_order_company(order, sp_doc)

	for fn in ("billing_status", "milestone_template", "document_list_template"):
		val = getattr(sp_doc, fn, None)
		if val and order.meta.has_field(fn):
			order.set(fn, val)

	if lifecycle_row and order.meta.has_field("site"):
		site = (getattr(lifecycle_row, "sp_site", None) or "").strip()
		if site:
			order.site = site

	_append_special_project_charges(sp_doc, order)
	return order
