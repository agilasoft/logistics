# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Seed one default Job Task Template for each booking and execution job."""

import frappe

from logistics.job_management.job_task import DEFAULT_TASKS, JOB_TASK_PARENTS
from logistics.job_management.job_task_template_seed import parents_to_seed


def execute():
	if not frappe.db.exists("DocType", "Job Task Template"):
		return

	parent_names = list(JOB_TASK_PARENTS)
	installed = frappe.get_all(
		"DocType",
		filters={"name": ["in", parent_names]},
		pluck="name",
		ignore_permissions=True,
	)
	existing_defaults = frappe.get_all(
		"Job Task Template",
		filters={"is_default": 1, "applies_to_doctype": ["in", parent_names]},
		pluck="applies_to_doctype",
		ignore_permissions=True,
	)
	existing_names = frappe.get_all(
		"Job Task Template",
		filters={"name": ["in", ["{0} Tasks".format(name) for name in parent_names]]},
		pluck="name",
		ignore_permissions=True,
	)
	specs, skipped = parents_to_seed(
		JOB_TASK_PARENTS,
		DEFAULT_TASKS,
		installed,
		existing_defaults,
		existing_names,
	)
	for doctype in skipped:
		print(
			"Job Task Template: {0} is not installed, skipping its default checklist".format(
				doctype
			)
		)
	for spec in specs:
		doc = frappe.get_doc(
			{
				"doctype": "Job Task Template",
				"template_name": spec["template_name"],
				"product_type": spec["product_type"],
				"applies_to": spec["applies_to"],
				"applies_to_doctype": spec["doctype"],
				"is_default": 1,
				"is_active": 1,
				"description": "Default job tasks for {0}.".format(spec["doctype"]),
				"items": [
					{
						"doctype": "Job Task Template Item",
						"task_code": task["task_code"],
						"subject": task["subject"],
						"description": task.get("description"),
						"sequence": task.get("sequence") or 0,
						"is_required": 1 if task.get("is_required") else 0,
					}
					for task in spec["tasks"]
				],
			}
		)
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
