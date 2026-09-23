// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.query_reports["High Value SLA Aging"] = {
	filters: [
		{
			fieldname: "as_on_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: "Today",
		},
		{
			fieldname: "hv_brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "HV Brands",
		},
		{
			fieldname: "modality",
			label: __("Modality"),
			fieldtype: "Select",
			options: "\nAir\nSea\nTransport",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
