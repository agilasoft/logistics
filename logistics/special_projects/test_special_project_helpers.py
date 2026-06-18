# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime


def ensure_cost_center_for_company(company: str) -> str | None:
	"""Return a leaf Cost Center for company, creating one under the company root if needed."""
	cc = frappe.db.get_value(
		"Cost Center",
		{"is_group": 0, "disabled": 0, "company": company},
		"name",
		order_by="creation asc",
	)
	if cc:
		return cc
	cc = frappe.db.get_value("Company", company, "cost_center")
	if cc:
		return cc
	abbr = frappe.db.get_value("Company", company, "abbr")
	root = f"{company} - {abbr}" if abbr else company
	if not frappe.db.exists("Cost Center", root):
		return None
	cc_doc = frappe.new_doc("Cost Center")
	cc_doc.cost_center_name = f"Test SP CC {frappe.generate_hash(length=6)}"
	cc_doc.company = company
	cc_doc.is_group = 0
	cc_doc.parent_cost_center = root
	branch = frappe.db.get_value("Branch", {}, "name", order_by="creation asc")
	if branch and frappe.get_meta("Cost Center").has_field("custom_branch"):
		cc_doc.custom_branch = branch
	cc_doc.insert(ignore_permissions=True)
	return cc_doc.name


def _company_with_cost_center() -> tuple[str | None, str | None]:
	"""Prefer a company that already has a leaf cost center (avoids creating CCs in tests)."""
	row = frappe.db.sql(
		"""
		SELECT cc.company, cc.name
		FROM `tabCost Center` cc
		WHERE cc.is_group = 0 AND IFNULL(cc.disabled, 0) = 0
		ORDER BY cc.creation ASC
		LIMIT 1
		""",
		as_dict=True,
	)
	if row:
		return row[0].company, row[0].name
	company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
	if not company:
		return None, None
	return company, ensure_cost_center_for_company(company)


def new_special_project_for_test(name_prefix: str = "Test SP"):
	customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
	if not customer:
		return None
	company, cost_center = _company_with_cost_center()
	if not company or not cost_center:
		return None
	sp = frappe.new_doc("Special Project")
	sp.project_name = f"{name_prefix} {now_datetime()}"
	sp.customer = customer
	sp.company = company
	sp.cost_center = cost_center
	return sp
