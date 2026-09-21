// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.query_reports["High Value Modality Mix"] = {
	filters: [
		{
			fieldname: "hv_brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "HV Brands",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
