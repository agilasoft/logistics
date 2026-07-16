# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Defaults for Cost Center customizations (e.g. mandatory Branch link)."""

from __future__ import annotations

import frappe


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
