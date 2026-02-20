// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Fuel Consumption Analysis"] = {
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
			"fieldname": "vehicle",
			"label": __("Vehicle"),
			"fieldtype": "Link",
			"options": "Transport Vehicle"
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
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "fuel_efficiency_range",
			"label": __("Fuel Efficiency Range"),
			"fieldtype": "Select",
			"options": "All\nHigh Efficiency (>15 km/L)\nMedium Efficiency (10-15 km/L)\nLow Efficiency (<10 km/L)"
		}
	]
};
