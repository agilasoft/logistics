// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Special Project Billing Status Report"] = {
	filters: [
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nPending\nInvoiced\nPaid" },
		{ fieldname: "bill_type", label: __("Bill Type"), fieldtype: "Select", options: "\nMilestone\nInterim\nFinal\nAd-hoc" },
		{ fieldname: "special_project", label: __("Special Project"), fieldtype: "Link", options: "Special Project" },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
	],
};
