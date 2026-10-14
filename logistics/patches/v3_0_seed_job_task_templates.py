# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Seed one default Job Task Template for each booking and execution job."""

import frappe

from logistics.job_management.job_task import DEFAULT_TASKS, JOB_TASK_PARENTS


def execute():
	if not frappe.db.exists("DocType", "Job Task Template"):
		return
	for doctype, (product_type, applies_to) in JOB_TASK_PARENTS.items():
		if frappe.db.exists(
			"Job Task Template",
			{"applies_to_doctype": doctype, "is_default": 1},
		):
			continue
		template_name = f"{doctype} Tasks"
		if frappe.db.exists("Job Task Template", template_name):
			continue
		tasks = DEFAULT_TASKS.get(doctype) or ()
		if not tasks:
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Job Task Template",
				"template_name": template_name,
				"product_type": product_type,
				"applies_to": applies_to,
				"applies_to_doctype": doctype,
				"is_default": 1,
				"is_active": 1,
				"description": f"Default job tasks for {doctype}.",
				"items": [
					{
						"doctype": "Job Task Template Item",
						"task_code": task["task_code"],
						"subject": task["subject"],
						"description": task.get("description"),
						"sequence": task.get("sequence") or 0,
						"is_required": 1 if task.get("is_required") else 0,
					}
					for task in tasks
				],
			}
		)
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
