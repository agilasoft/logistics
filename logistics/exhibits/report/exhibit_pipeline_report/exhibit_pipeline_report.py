# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from logistics.analytics_reports.bootstrap import series_chart
from logistics.utils.lifecycle_stage import FOR_EXHIBITS, get_lifecycle_stages


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = series_chart(data, "lifecycle_stage", "program_count")
	return columns, data, None, chart, []


def get_columns():
	return [
		{"fieldname": "lifecycle_stage", "label": _("Lifecycle Stage"), "fieldtype": "Data", "width": 120},
		{"fieldname": "program_count", "label": _("Count"), "fieldtype": "Int", "width": 90},
		{"fieldname": "programs", "label": _("Programs"), "fieldtype": "Data", "width": 400},
	]


def get_data(filters):
	conditions = ["1=1"]
	values = {}

	if filters.get("customer"):
		conditions.append("ep.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("priority"):
		conditions.append("ep.priority = %(priority)s")
		values["priority"] = filters["priority"]
	if filters.get("lifecycle_stage"):
		conditions.append("ep.lifecycle_stage = %(lifecycle_stage)s")
		values["lifecycle_stage"] = filters["lifecycle_stage"]

	where = " AND ".join(conditions)
	lifecycle_order = get_lifecycle_stages(FOR_EXHIBITS)
	order_field = ", ".join(f"'{s}'" for s in lifecycle_order)

	rows = frappe.db.sql(
		f"""
		SELECT ep.lifecycle_stage, ep.name
		FROM `tabExhibit` ep
		WHERE {where}
		ORDER BY FIELD(ep.lifecycle_stage, {order_field}), ep.modified DESC
		""",
		values,
		as_dict=1,
	)

	by_stage = {}
	for row in rows:
		stage = row.lifecycle_stage or "Pre-Show"
		by_stage.setdefault(stage, []).append(row.name)

	result = []
	for stage in lifecycle_order:
		if stage in by_stage:
			names = by_stage[stage]
			result.append(
				{
					"lifecycle_stage": stage,
					"program_count": len(names),
					"programs": ", ".join(names[:10]) + ("..." if len(names) > 10 else ""),
				}
			)
	return result
