# Copyright (c) 2026, Agilasoft and contributors
"""Convert legacy free-text Project Task Job Resource.resource_name values to Project Resource links."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Project Resource"):
		return
	if not frappe.db.table_exists("tabProject Task Job Resource"):
		return

	rows = frappe.db.sql(
		"""
		SELECT name, resource_name, resource_category
		FROM `tabProject Task Job Resource`
		WHERE IFNULL(resource_name, '') != ''
		""",
		as_dict=True,
	)

	for row in rows:
		val = (row.resource_name or "").strip()
		if not val:
			continue
		if frappe.db.exists("Project Resource", val):
			continue
		category = row.resource_category or "Other"
		pr_name = _find_or_create_project_resource(val, category)
		frappe.db.set_value(
			"Project Task Job Resource",
			row.name,
			"resource_name",
			pr_name,
			update_modified=False,
		)

	frappe.db.commit()


def _find_or_create_project_resource(title: str, category: str) -> str:
	title = (title or "").strip()[:140]
	if not title:
		title = "Unnamed resource"
	existing = frappe.db.get_value(
		"Project Resource",
		{"title": title, "resource_category": category},
		"name",
	)
	if existing:
		return existing

	doc = frappe.get_doc(
		{
			"doctype": "Project Resource",
			"naming_series": "PRRES-.#####",
			"title": title,
			"resource_category": category,
			"is_active": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name
