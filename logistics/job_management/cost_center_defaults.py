# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Defaults for Cost Center customizations (e.g. mandatory Branch link)."""

from __future__ import annotations

import frappe
from frappe import _


def _company_fieldname(doctype: str) -> str | None:
	meta = frappe.get_meta(doctype)
	for fieldname in ("company", "custom_company"):
		if meta.has_field(fieldname):
			return fieldname
	return None


def default_branch_for_company(company: str | None = None) -> str | None:
	"""Return a Branch for ``company``, or the first Branch in the site."""
	if company:
		company_field = _company_fieldname("Branch")
		if company_field:
			branch = frappe.db.get_value(
				"Branch",
				{company_field: company},
				"name",
				order_by="creation asc",
			)
			if branch:
				return branch

	return frappe.db.get_value("Branch", {}, "name", order_by="creation asc")


def default_company() -> str | None:
	"""Site company used when a Cost Center is saved without one."""
	return (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name", order_by="creation asc")
	)


def set_cost_center_company_default(doc, method=None):
	"""Fill Company after it is hidden on the Cost Center form.

	ERPNext still stores Company and checks that a parent belongs to the same
	company. Inherit the parent when there is one, otherwise use the site default.
	"""
	if (doc.get("company") or "").strip():
		return

	if doc.get("parent_cost_center"):
		parent_company = frappe.db.get_value("Cost Center", doc.parent_cost_center, "company")
		if parent_company:
			doc.company = parent_company
			return

	company = default_company()
	if not company:
		frappe.throw(_("Company is required for a Cost Center."))
	doc.company = company


def set_cost_center_branch_default(doc, method=None):
	"""Populate ``custom_branch`` when Cost Centers are created without it (e.g. Company setup)."""
	cc_meta = frappe.get_meta("Cost Center")
	if not cc_meta.has_field("custom_branch") or doc.get("custom_branch"):
		return

	if doc.get("parent_cost_center"):
		parent_branch = frappe.db.get_value(
			"Cost Center", doc.parent_cost_center, "custom_branch"
		)
		if parent_branch:
			doc.custom_branch = parent_branch
			return

	doc.custom_branch = default_branch_for_company(doc.get("company"))


def set_branch_document_name(doc, method=None):
	"""Name a Branch from its label when the document name was left blank.

	Branch naming is "Set by user". Code that only fills the Branch field then
	saves it, and Frappe throws "Please set the document name".
	"""
	if (doc.get("name") or "").strip() or (doc.get("__newname") or "").strip():
		return
	label = (doc.get("branch") or "").strip()
	if not label:
		return
	autoname = (getattr(doc.meta, "autoname", None) or "").strip().lower()
	if autoname != "prompt":
		return
	doc.__newname = label
