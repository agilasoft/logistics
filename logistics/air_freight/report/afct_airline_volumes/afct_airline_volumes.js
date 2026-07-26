// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.query_reports["AFCT Airline Volumes"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
		},
		{
			fieldname: "profit_center",
			label: __("Profit Center"),
			fieldtype: "Link",
			options: "Profit Center",
		},
		{
			fieldname: "unloco",
			label: __("UNLOCO"),
			fieldtype: "Link",
			options: "UNLOCO",
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Int",
			default: frappe.datetime.get_today().slice(0, 4),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.year_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "limit",
			label: __("Top N"),
			fieldtype: "Int",
			default: 10,
		},
		{
			fieldname: "airline",
			label: __("Airline"),
			fieldtype: "Link",
			options: "Airline",
		},
	],
};
