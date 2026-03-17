// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Special Project Delivery Status Report"] = {
	filters: [
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nPending\nScheduled\nCompleted\nDelayed" },
		{ fieldname: "delivery_type", label: __("Delivery Type"), fieldtype: "Select", options: "\nFull\nPartial\nMilestone\nProof of Delivery" },
		{ fieldname: "special_project", label: __("Special Project"), fieldtype: "Link", options: "Special Project" },
		{ fieldname: "from_date", label: __("Delivery Date From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Delivery Date To"), fieldtype: "Date" },
	],
};
