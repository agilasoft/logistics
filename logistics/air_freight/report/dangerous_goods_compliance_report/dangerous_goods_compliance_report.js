// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Dangerous Goods Compliance Report"] = {
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
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "contains_dg",
			"label": __("Contains Dangerous Goods Only"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "compliance_status",
			"label": __("Compliance Status"),
			"fieldtype": "Select",
			"options": "\nCompliant\nNon-Compliant\nPending\nUnknown"
		},
		{
			"fieldname": "has_compliance_issues",
			"label": __("Has Compliance Issues"),
			"fieldtype": "Check",
			"default": 0
		}
	]
};


