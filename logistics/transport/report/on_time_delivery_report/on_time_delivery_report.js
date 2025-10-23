// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["On-Time Delivery Report"] = {
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
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "vehicle",
			"label": __("Vehicle"),
			"fieldtype": "Link",
			"options": "Transport Vehicle"
		},
		{
			"fieldname": "transport_company",
			"label": __("Transport Company"),
			"fieldtype": "Link",
			"options": "Transport Company"
		},
		{
			"fieldname": "delivery_status",
			"label": __("Delivery Status"),
			"fieldtype": "Select",
			"options": "Draft\nDispatched\nIn-Progress\nHold\nCompleted\nCancelled"
		},
		{
			"fieldname": "on_time_status",
			"label": __("On-Time Status"),
			"fieldtype": "Select",
			"options": "On Time\nLate\nEarly"
		}
	]
};
