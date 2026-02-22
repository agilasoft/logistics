// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Special Project Pipeline Report"] = {
	filters: [
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "priority", label: __("Priority"), fieldtype: "Select", options: "\nLow\nNormal\nHigh\nUrgent" },
		{ fieldname: "include_cancelled", label: __("Include Cancelled"), fieldtype: "Check", default: 0 },
	],
};
