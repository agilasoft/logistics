# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""Execute Sustainability Goals Report"""
	filters = frappe._dict(filters or {})
	
	# Get data based on filters
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	
	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "goal_name",
			"label": _("Goal Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "goal_type",
			"label": _("Goal Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "module",
			"label": _("Module"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "branch",
			"label": _("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"width": 120
		},
		{
			"fieldname": "baseline_value",
			"label": _("Baseline Value"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "target_value",
			"label": _("Target Value"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "current_value",
			"label": _("Current Value"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "progress_percentage",
			"label": _("Progress %"),
			"fieldtype": "Percent",
			"precision": 1,
			"width": 100
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "target_date",
			"label": _("Target Date"),
			"fieldtype": "Date",
			"width": 100
		}
	]


def get_data(filters):
	"""Get report data"""
	
	# Build filters
	report_filters = {}
	if filters.company:
		report_filters["company"] = filters.company
	if filters.module:
		report_filters["module"] = filters.module
	if filters.branch:
		report_filters["branch"] = filters.branch
	if filters.facility:
		report_filters["facility"] = filters.facility
	if filters.goal_type:
		report_filters["goal_type"] = filters.goal_type
	if filters.status:
		report_filters["status"] = filters.status
	
	# Get sustainability goals data
	goals = frappe.get_all("Sustainability Goals",
		filters=report_filters,
		fields=["name", "goal_name", "goal_type", "module", "branch", "facility",
				"baseline_value", "target_value", "current_value",
				"progress_percentage", "status", "target_date"],
		order_by="target_date asc, goal_name"
	)
	
	# Format data for report
	data = []
	for goal in goals:
		row = {
			"goal_name": goal.goal_name,
			"goal_type": goal.goal_type,
			"module": goal.module,
			"branch": goal.branch,
			"baseline_value": flt(goal.baseline_value),
			"target_value": flt(goal.target_value),
			"current_value": flt(goal.current_value),
			"progress_percentage": flt(goal.progress_percentage),
			"status": goal.status,
			"target_date": goal.target_date
		}
		data.append(row)
	
	return data


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by status for pie chart
	status_data = {}
	for record in data:
		status = record.get("status") or "Not Started"
		if status not in status_data:
			status_data[status] = 0
		status_data[status] += 1
	
	# Group by goal type for bar chart
	goal_type_data = {}
	for record in data:
		goal_type = record.get("goal_type") or "Other"
		if goal_type not in goal_type_data:
			goal_type_data[goal_type] = {
				"completed": 0,
				"in_progress": 0,
				"not_started": 0
			}
		status = record.get("status", "Not Started")
		if status == "Completed":
			goal_type_data[goal_type]["completed"] += 1
		elif status == "In Progress":
			goal_type_data[goal_type]["in_progress"] += 1
		else:
			goal_type_data[goal_type]["not_started"] += 1
	
	goal_types = list(goal_type_data.keys())
	completed = [goal_type_data[gt]["completed"] for gt in goal_types]
	in_progress = [goal_type_data[gt]["in_progress"] for gt in goal_types]
	
	chart = {
		"data": {
			"labels": goal_types,
			"datasets": [
				{
					"name": "Completed",
					"values": completed
				},
				{
					"name": "In Progress",
					"values": in_progress
				}
			]
		},
		"type": "bar",
		"colors": ["#4bc0c0", "#36a2eb"]
	}
	
	return chart

