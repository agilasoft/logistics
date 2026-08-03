// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Time Sensitive Case Health"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nTriage\nActivated\nIn Execution\nDelivered\nClosed\nOn Hold\nCancelled",
		},
		{
			fieldname: "sla_status",
			label: __("SLA Status"),
			fieldtype: "Select",
			options: "\nOn Track\nAt Risk\nBreached\nCompleted",
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
	],
};
