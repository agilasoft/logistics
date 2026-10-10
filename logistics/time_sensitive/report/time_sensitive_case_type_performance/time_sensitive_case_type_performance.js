// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Time Sensitive Case Type Performance"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "coordinator",
			label: __("Coordinator"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
