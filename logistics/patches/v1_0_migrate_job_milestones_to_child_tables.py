# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate Job Milestone records into parent child tables (Air Shipment Milestone, etc.)."""

from __future__ import unicode_literals

import frappe


# job_type -> (parent doctype, child table field name)
JOB_TYPE_TO_PARENT = {
	"Air Shipment": ("Air Shipment", "milestones"),
	"Sea Shipment": ("Sea Shipment", "milestones"),
	"Transport Job": ("Transport Job", "milestones"),
	"Declaration": ("Declaration", "milestones"),
}


def execute():
	"""Copy existing Job Milestone rows into the new child tables. Skip parents that already have child rows."""
	for job_type, (parent_doctype, child_field) in JOB_TYPE_TO_PARENT.items():
		_migrate_milestones_for_type(parent_doctype, job_type, child_field)
	frappe.db.commit()


def _migrate_milestones_for_type(parent_doctype, job_type, child_field):
	# All Job Milestone rows for this job_type, ordered by job_number and planned_start
	rows = frappe.db.sql("""
		SELECT name, job_number, milestone, status, planned_start, planned_end, actual_start, actual_end
		FROM `tabJob Milestone`
		WHERE job_type = %(job_type)s
		ORDER BY job_number, planned_start ASC
	""", {"job_type": job_type}, as_dict=True)
	if not rows:
		return
	# Group by job_number (parent name)
	by_parent = {}
	for r in rows:
		parent_name = r.job_number
		if not parent_name:
			continue
		if parent_name not in by_parent:
			by_parent[parent_name] = []
		by_parent[parent_name].append(r)
	# Resolve child table doctype
	child_table = _get_child_table_doctype(parent_doctype, child_field)
	if not child_table:
		return
	# Insert child rows directly to avoid validating the whole parent (e.g. other child tables like charges)
	for parent_name, jm_list in by_parent.items():
		if not frappe.db.exists(parent_doctype, parent_name):
			continue
		existing = frappe.db.count(
			child_table,
			{"parent": parent_name, "parenttype": parent_doctype, "parentfield": child_field},
		)
		if existing > 0:
			continue
		for i, jm in enumerate(jm_list):
			child = frappe.new_doc(child_table)
			child.parent = parent_name
			child.parenttype = parent_doctype
			child.parentfield = child_field
			child.milestone = jm.milestone
			child.status = jm.status or "Planned"
			child.planned_start = jm.planned_start
			child.planned_end = jm.planned_end
			child.actual_start = jm.actual_start
			child.actual_end = jm.actual_end
			child.source = "Manual"
			child.flags.ignore_validate = True
			child.insert(ignore_permissions=True)
		frappe.clear_cache(doctype=parent_doctype)


def _get_child_table_doctype(parent_doctype, child_field):
	"""Resolve child table doctype from parent's field options."""
	meta = frappe.get_meta(parent_doctype)
	df = meta.get_field(child_field)
	if df and df.fieldtype == "Table" and df.options:
		return df.options
	return None
