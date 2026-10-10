// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Time Sensitive Escalation Coverage"] = {
	filters: [
		{
			fieldname: "case_type",
			label: __("Case Type"),
			fieldtype: "Link",
			options: "Time Sensitive Case Type",
		},
		{
			fieldname: "covered",
			label: __("Covered"),
			fieldtype: "Select",
			options: "\nYes\nNo",
		},
		{
			fieldname: "enabled_only",
			label: __("Enabled Case Types Only"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
