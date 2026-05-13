# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, today


def execute(filters=None):
	"""Execute Global Customs Dashboard"""
	filters = frappe._dict(filters or {})
	
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart, []


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "metric",
			"label": _("Metric"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "value",
			"label": _("Value"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "details",
			"label": _("Details"),
			"fieldtype": "Data",
			"width": 300
		}
	]


def get_data(filters):
	"""Get dashboard metrics"""
	data = []
	company = filters.get("company") or frappe.defaults.get_user_default("Company")
	
	# Global Manifest metrics
	global_manifests = frappe.db.count("Global Manifest", {"company": company, "docstatus": ["!=", 2]})
	data.append({
		"metric": "Total Global Manifests",
		"value": global_manifests,
		"details": f"{global_manifests} active manifests"
	})
	
	# Status breakdown
	statuses = ["Draft", "Submitted", "Accepted", "Rejected", "Amended"]
	for status in statuses:
		count = frappe.db.count("Global Manifest", {"company": company, "status": status, "docstatus": ["!=", 2]})
		if count > 0:
			data.append({
				"metric": f"Manifests - {status}",
				"value": count,
				"details": f"{count} manifests in {status} status"
			})
	
	# US AMS metrics
	ams_total = frappe.db.count("US AMS", {"company": company, "docstatus": ["!=", 2]})
	data.append({
		"metric": "US AMS Filings",
		"value": ams_total,
		"details": f"{ams_total} total AMS filings"
	})
	
	ams_accepted = frappe.db.count("US AMS", {"company": company, "status": "Accepted", "docstatus": ["!=", 2]})
	data.append({
		"metric": "US AMS - Accepted",
		"value": ams_accepted,
		"details": f"{ams_accepted} accepted AMS filings"
	})
	
	# CA eManifest metrics
	emanifest_total = frappe.db.count("CA eManifest Forwarder", {"company": company, "docstatus": ["!=", 2]})
	data.append({
		"metric": "CA eManifest Filings",
		"value": emanifest_total,
		"details": f"{emanifest_total} total eManifest filings"
	})
	
	# JP AFR metrics
	afr_total = frappe.db.count("JP AFR", {"company": company, "docstatus": ["!=", 2]})
	data.append({
		"metric": "JP AFR Filings",
		"value": afr_total,
		"details": f"{afr_total} total AFR filings"
	})
	
	# US ISF metrics
	isf_total = frappe.db.count("US ISF", {"company": company, "docstatus": ["!=", 2]})
	data.append({
		"metric": "US ISF Filings",
		"value": isf_total,
		"details": f"{isf_total} total ISF filings"
	})
	
	# Pending submissions
	pending_manifests = frappe.db.count("Global Manifest", {
		"company": company,
		"status": "Draft",
		"docstatus": ["!=", 2],
		"eta": [">=", today()]
	})
	data.append({
		"metric": "Pending Submissions",
		"value": pending_manifests,
		"details": f"{pending_manifests} drafts with upcoming ETA"
	})
	
	return data


def get_chart_data(data, filters):
	"""Generate chart data — Global Manifest status distribution for the selected company."""
	company = filters.get("company") or frappe.defaults.get_user_default("Company")
	if not company:
		return {
			"data": {
				"labels": [_("Set company filter")],
				"datasets": [{"name": _("Manifests"), "values": [0]}],
			},
			"type": "bar",
			"colors": ["#6c757d"],
		}
	status_rows = frappe.db.sql(
		"""
		SELECT status, COUNT(*) AS cnt
		FROM `tabGlobal Manifest`
		WHERE docstatus < 2 AND company = %(company)s
		GROUP BY status
		ORDER BY cnt DESC
		""",
		{"company": company},
		as_dict=1,
	)
	if status_rows:
		return {
			"data": {
				"labels": [r.status or _("Unknown") for r in status_rows],
				"datasets": [
					{
						"name": _("Manifests by Status"),
						"values": [cint(r.cnt) for r in status_rows],
					}
				],
			},
			"type": "pie",
			"colors": ["#36a2eb", "#4bc0c0", "#9966ff", "#ff6384", "#ff9f40"],
		}
	return {
		"data": {
			"labels": [_("No manifests on file")],
			"datasets": [{"name": _("Manifests by Status"), "values": [0]}],
		},
		"type": "bar",
		"colors": ["#6c757d"],
	}

