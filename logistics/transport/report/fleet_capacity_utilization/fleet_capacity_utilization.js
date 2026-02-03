// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Fleet Capacity Utilization"] = {
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
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Vehicle Type\nVehicle",
			"default": "Vehicle Type"
		},
		{
			"fieldname": "vehicle_type",
			"label": __("Vehicle Type"),
			"fieldtype": "Link",
			"options": "Vehicle Type"
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
		}
	]
};
