// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Sustainability Compliance Report"] = {
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
			"fieldname": "compliance_type",
			"label": __("Compliance Type"),
			"fieldtype": "Select",
			"options": "\nISO 14001\nISO 50001\nCarbon Neutral\nRE100\nLEED\nBREEAM\nOther"
		},
		{
			"fieldname": "certification_status",
			"label": __("Certification Status"),
			"fieldtype": "Select",
			"options": "\nCertified\nIn Progress\nNot Certified\nExpired"
		}
	]
};

