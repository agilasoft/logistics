// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Route Cost Analysis"] = {
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
			"fieldname": "route_name",
			"label": __("Route Name"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "vehicle_type",
			"label": __("Vehicle Type"),
			"fieldtype": "Link",
			"options": "Vehicle Type"
		},
		{
			"fieldname": "transport_company",
			"label": __("Transport Company"),
			"fieldtype": "Link",
			"options": "Transport Company"
		},
		{
			"fieldname": "cost_range",
			"label": __("Cost Range"),
			"fieldtype": "Select",
			"options": "All\nLow Cost (<$1.00/km)\nMedium Cost ($1.00-$2.00/km)\nHigh Cost (>$2.00/km)"
		}
	]
};
