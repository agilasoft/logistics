// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Consolidation Savings Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "consolidation_type",
			"label": __("Consolidation Type"),
			"fieldtype": "Select",
			"options": "All\nLTL\nFTL\nPartial"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "All\nDraft\nPlanned\nIn Progress\nCompleted\nCancelled"
		},
		{
			"fieldname": "run_sheet",
			"label": __("Run Sheet"),
			"fieldtype": "Link",
			"options": "Run Sheet"
		}
	]
};
