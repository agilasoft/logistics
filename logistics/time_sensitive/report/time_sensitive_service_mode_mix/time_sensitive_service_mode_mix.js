// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Time Sensitive Service Mode Mix"] = {
	filters: [
		{
			fieldname: "service_mode",
			label: __("Service Mode"),
			fieldtype: "Select",
			options: "\nAir Booking\nSea Booking\nTransport Order\nDeclaration Order\nInbound Order",
		},
		{
			fieldname: "status",
			label: __("Case Status"),
			fieldtype: "Select",
			options: "\nDraft\nTriage\nActivated\nIn Execution\nDelivered\nClosed\nOn Hold\nCancelled",
		},
		{
			fieldname: "sla_status",
			label: __("Case SLA"),
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
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
