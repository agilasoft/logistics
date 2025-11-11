# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	"""Execute Manifest Status Report"""
	filters = frappe._dict(filters or {})
	
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "manifest_number",
			"label": _("Manifest Number"),
			"fieldtype": "Link",
			"options": "Global Manifest",
			"width": 150
		},
		{
			"fieldname": "manifest_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "country",
			"label": _("Country"),
			"fieldtype": "Link",
			"options": "Country",
			"width": 120
		},
		{
			"fieldname": "port_of_loading",
			"label": _("Port of Loading"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 150
		},
		{
			"fieldname": "port_of_discharge",
			"label": _("Port of Discharge"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 150
		},
		{
			"fieldname": "vessel_flight_number",
			"label": _("Vessel/Flight"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "submission_date",
			"label": _("Submission Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "acceptance_date",
			"label": _("Acceptance Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		}
	]


def get_data(filters):
	"""Get report data"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			gm.name as manifest_number,
			gm.manifest_type,
			gm.country,
			gm.port_of_loading,
			gm.port_of_discharge,
			gm.vessel_flight_number,
			gm.eta,
			gm.status,
			gm.submission_date,
			gm.acceptance_date,
			gm.company
		FROM `tabGlobal Manifest` gm
		WHERE gm.docstatus != 2
		{conditions}
		ORDER BY gm.submission_date DESC, gm.name DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build SQL conditions from filters"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("gm.submission_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("gm.submission_date <= %(to_date)s")
	
	if filters.get("country"):
		conditions.append("gm.country = %(country)s")
	
	if filters.get("status"):
		conditions.append("gm.status = %(status)s")
	
	if filters.get("manifest_type"):
		conditions.append("gm.manifest_type = %(manifest_type)s")
	
	if filters.get("company"):
		conditions.append("gm.company = %(company)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

