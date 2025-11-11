// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Manifest Status Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "country",
			"label": __("Country"),
			"fieldtype": "Link",
			"options": "Country"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nSubmitted\nAccepted\nRejected\nAmended"
		},
		{
			"fieldname": "manifest_type",
			"label": __("Manifest Type"),
			"fieldtype": "Select",
			"options": "\nImport\nExport\nTransit"
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		}
	]
};

