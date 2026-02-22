// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Special Project Request Fulfillment Report"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nApproved\nPartially Fulfilled\nFulfilled\nCancelled",
		},
		{
			fieldname: "special_project",
			label: __("Special Project"),
			fieldtype: "Link",
			options: "Special Project",
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: "\nLow\nNormal\nHigh\nUrgent",
		},
		{
			fieldname: "required_by_from",
			label: __("Required By From"),
			fieldtype: "Date",
		},
		{
			fieldname: "required_by_to",
			label: __("Required By To"),
			fieldtype: "Date",
		},
	],
};
