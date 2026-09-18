// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.query_reports["High Value Job Health"] = {
	filters: [
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
			fieldname: "sla_status",
			label: __("SLA Status"),
			fieldtype: "Select",
			options: "\nOn Track\nAt Risk\nBreached\nNot Applicable",
		},
		{
			fieldname: "job_status",
			label: __("Job Status"),
			fieldtype: "Select",
			options:
				"\nDraft\nSubmitted\nIn Progress\nCompleted\nClosed\nReopened\nCancelled",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "live_only",
			label: __("Live Jobs Only"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
