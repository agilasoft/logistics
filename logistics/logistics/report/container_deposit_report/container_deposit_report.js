// Copyright (c) 2025, Logistics Team and contributors
// For license information, please see license.txt

frappe.query_reports["Container Deposit Report"] = {
	filters: [
		{
			fieldname: "hide_zero_balance",
			label: __("Hide containers with zero net balance"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "report_date",
			label: __("Ageing as on"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "calculate_ageing_with",
			label: __("Calculate ageing with"),
			fieldtype: "Select",
			options: "Report Date\nToday Date",
			default: "Report Date",
		},
		{
			fieldname: "range",
			label: __("Ageing range"),
			fieldtype: "Data",
			default: "30, 60, 90, 120",
		},
		{
			fieldname: "from_date",
			label: __("From Date (posting)"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date (posting)"),
			fieldtype: "Date",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "shipping_line",
			label: __("Shipping Line"),
			fieldtype: "Link",
			options: "Shipping Line",
		},
		{
			fieldname: "master_bill",
			label: __("Master Bill"),
			fieldtype: "Link",
			options: "Master Bill",
		},
		{
			fieldname: "container",
			label: __("Container"),
			fieldtype: "Link",
			options: "Container",
		},
		{
			fieldname: "job_number",
			label: __("Job Number"),
			fieldtype: "Link",
			options: "Job Number",
		},
		{
			fieldname: "include_returned",
			label: __(
				"Include returned containers (off hides rows where Return Status is Returned — even if GL deposit balance remains)"
			),
			fieldtype: "Check",
			default: 1,
		},
	],
};
