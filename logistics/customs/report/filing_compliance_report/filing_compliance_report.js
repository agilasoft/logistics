// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Filing Compliance Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nSubmitted\nAccepted\nRejected\nHold\nAmended"
		}
	]
};

