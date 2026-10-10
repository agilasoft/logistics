// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Time Sensitive Escalation Watch"] = {
	filters: [
		{
			fieldname: "watch_reason",
			label: __("Watch"),
			fieldtype: "Select",
			options: "\nDeadline breach\nCheckpoint missed\nUnacknowledged\nAt risk",
		},
		{
			fieldname: "case_type",
			label: __("Case Type"),
			fieldtype: "Link",
			options: "Time Sensitive Case Type",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "coordinator",
			label: __("Coordinator"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
