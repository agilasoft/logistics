# Copyright (c) 2026, Agilasoft and contributors
"""Drop Project Task Order Job child table; jobs link to Project Task Order via Project Task Job.special_project_order."""

import frappe


def execute():
	table = "tabProject Task Order Job"
	if frappe.db.table_exists(table):
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
			if not frappe.db.exists("Project Task Job", job_name):
				continue
			current = frappe.db.get_value("Project Task Job", job_name, "special_project_order")
			if not current:
				frappe.db.set_value(
					"Project Task Job",
					job_name,
					"special_project_order",
					order_name,
					update_modified=False,
				)

	if frappe.db.exists("DocType", "Project Task Order Job"):
		frappe.delete_doc("DocType", "Project Task Order Job", force=True)
	frappe.db.commit()
