// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Driver Performance Report"] = {
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
			"fieldname": "driver",
			"label": __("Driver"),
			"fieldtype": "Link",
			"options": "Driver"
		},
		{
			"fieldname": "transport_company",
			"label": __("Transport Company"),
			"fieldtype": "Link",
			"options": "Transport Company"
		},
		{
			"fieldname": "performance_rating",
			"label": __("Performance Rating"),
			"fieldtype": "Select",
			"options": "All\nExcellent\nGood\nAverage\nBelow Average\nPoor"
		}
	]
};
