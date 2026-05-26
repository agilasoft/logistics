# Copyright (c) 2026, Agilasoft and contributors
"""Drop Project Task Order Job child table; jobs link to Project Task Order via Project Task Job.special_project_order."""

import frappe


def execute():
	# Job DocType was renamed Project Task Job → Project Job; resolve to whichever exists.
	job_doctype = None
	for candidate in ("Project Job", "Project Task Job"):
		if frappe.db.exists("DocType", candidate):
			job_doctype = candidate
			break

	table = "tabProject Task Order Job"
	if frappe.db.table_exists(table) and job_doctype:
		rows = frappe.db.sql(
			f"""
			SELECT parent, special_project_job
			FROM `{table}`
			WHERE IFNULL(special_project_job, '') != ''
			""",
			as_dict=True,
		)
		for row in rows:
			job_name = row.get("special_project_job")
			order_name = row.get("parent")
			if not job_name or not order_name:
				continue
			if not frappe.db.exists(job_doctype, job_name):
				continue
			current = frappe.db.get_value(job_doctype, job_name, "special_project_order")
			if not current:
				frappe.db.set_value(
					job_doctype,
					job_name,
					"special_project_order",
					order_name,
					update_modified=False,
				)

	if frappe.db.exists("DocType", "Project Task Order Job"):
		frappe.delete_doc("DocType", "Project Task Order Job", force=True)
	frappe.db.commit()
