// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Road Compliance Report"] = {
	"filters": [
		{
			"fieldname": "compliance_type",
			"label": __("Compliance Type"),
			"fieldtype": "Select",
			"options": "Driver License\nVehicle Registration\nInsurance\nPermit\nWeight Limit\nDimension Limit\nHours of Service\nHazardous Material\nRefrigeration\nEnvironmental"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "Active\nInactive\nExpired\nSuspended"
		},
		{
			"fieldname": "priority",
			"label": __("Priority"),
			"fieldtype": "Select",
			"options": "Low\nMedium\nHigh\nCritical"
		},
		{
			"fieldname": "expiry_filter",
			"label": __("Expiry"),
			"fieldtype": "Select",
			"options": "All\nExpired\nExpiring in 30 days\nExpiring in 90 days\nNo expiry date",
			"default": "All"
		},
		{
			"fieldname": "effective_from",
			"label": __("Effective From"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "effective_to",
			"label": __("Effective To"),
			"fieldtype": "Date"
		}
	]
};
