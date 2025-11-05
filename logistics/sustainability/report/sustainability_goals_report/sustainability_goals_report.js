// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Sustainability Goals Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "module",
			"label": __("Module"),
			"fieldtype": "Select",
			"options": "\nTransport\nWarehousing\nAir Freight\nSea Freight\nCustoms\nJob Management\nPricing Center\nAll"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch"
		},
		{
			"fieldname": "facility",
			"label": __("Facility"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "goal_type",
			"label": __("Goal Type"),
			"fieldtype": "Select",
			"options": "\nEnergy Efficiency\nCarbon Reduction\nWaste Reduction\nWater Conservation\nRenewable Energy\nOther"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nNot Started\nIn Progress\nCompleted\nAt Risk"
		}
	]
};

