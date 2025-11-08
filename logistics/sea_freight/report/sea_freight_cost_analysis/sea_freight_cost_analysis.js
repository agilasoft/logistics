// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Sea Freight Cost Analysis"] = {
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
			"fieldname": "shipping_line",
			"label": __("Shipping Line"),
			"fieldtype": "Link",
			"options": "Shipping Line"
		},
		{
			"fieldname": "origin_port",
			"label": __("Origin Port"),
			"fieldtype": "Link",
			"options": "UNLOCO"
		},
		{
			"fieldname": "destination_port",
			"label": __("Destination Port"),
			"fieldtype": "Link",
			"options": "UNLOCO"
		}
	]
};

