// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Special Project Billing Status Report"] = {
	filters: [
		{
			fieldname: "sales_invoice_status",
			label: __("SI Status"),
			fieldtype: "Data",
		},
		{
			fieldname: "charge_type",
			label: __("Charge Type"),
			fieldtype: "Select",
			options: "\nRevenue\nCost\nDisbursement",
		},
		{ fieldname: "special_project", label: __("Special Project"), fieldtype: "Link", options: "Special Project" },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
	],
};
