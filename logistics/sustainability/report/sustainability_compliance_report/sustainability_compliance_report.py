# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""Execute Sustainability Compliance Report"""
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
			"fieldname": "compliance_name",
			"label": _("Compliance Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "compliance_type",
			"label": _("Compliance Type"),
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
			"fieldname": "standard_name",
			"label": _("Standard Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "certification_status",
			"label": _("Certification Status"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "compliance_status",
			"label": _("Compliance Status"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "audit_status",
			"label": _("Audit Status"),
			"fieldtype": "Data",
			"width": 130
		},
		{
			"fieldname": "certification_date",
			"label": _("Certification Date"),
			"fieldtype": "Date",
			"width": 130
		},
		{
			"fieldname": "expiry_date",
			"label": _("Expiry Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "next_audit_date",
			"label": _("Next Audit Date"),
			"fieldtype": "Date",
			"width": 120
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
	if filters.compliance_type:
		report_filters["compliance_type"] = filters.compliance_type
	if filters.certification_status:
		report_filters["certification_status"] = filters.certification_status
	
	# Get sustainability compliance data
	compliance = frappe.get_all("Sustainability Compliance",
		filters=report_filters,
		fields=["name", "compliance_name", "compliance_type", "module", "branch", "facility",
				"standard_name", "certification_status", "compliance_status", "audit_status",
				"certification_date", "expiry_date", "next_audit_date"],
		order_by="expiry_date asc, compliance_name"
	)
	
	# Format data for report
	data = []
	for record in compliance:
		row = {
			"compliance_name": record.compliance_name,
			"compliance_type": record.compliance_type,
			"module": record.module,
			"branch": record.branch,
			"standard_name": record.standard_name,
			"certification_status": record.certification_status,
			"compliance_status": record.compliance_status,
			"audit_status": record.audit_status,
			"certification_date": record.certification_date,
			"expiry_date": record.expiry_date,
			"next_audit_date": record.next_audit_date
		}
		data.append(row)
	
	return data


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by certification status for pie chart
	cert_status_data = {}
	for record in data:
		status = record.get("certification_status") or "Not Certified"
		if status not in cert_status_data:
			cert_status_data[status] = 0
		cert_status_data[status] += 1
	
	# Group by compliance type for bar chart
	compliance_type_data = {}
	for record in data:
		compliance_type = record.get("compliance_type") or "Other"
		if compliance_type not in compliance_type_data:
			compliance_type_data[compliance_type] = 0
		compliance_type_data[compliance_type] += 1
	
	compliance_types = list(compliance_type_data.keys())
	counts = [compliance_type_data[ct] for ct in compliance_types]
	
	chart = {
		"data": {
			"labels": compliance_types,
			"datasets": [
				{
					"name": "Compliance Count",
					"values": counts
				}
			]
		},
		"type": "bar",
		"colors": ["#36a2eb"]
	}
	
	return chart

