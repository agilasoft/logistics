// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Air Consolidation Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nPending\nIn Transit\nDelivered\nCancelled"
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "origin_airport",
			"label": __("Origin Airport"),
			"fieldtype": "Link",
			"options": "UNLOCO"
		},
		{
			"fieldname": "destination_airport",
			"label": __("Destination Airport"),
			"fieldtype": "Link",
			"options": "UNLOCO"
		}
	]
};


