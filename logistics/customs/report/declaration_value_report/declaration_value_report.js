// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Declaration Value Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -3),
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
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "None\nDay\nWeek\nMonth\nCustomer\nDeclaration Type",
			"default": "Month"
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "declaration_type",
			"label": __("Declaration Type"),
			"fieldtype": "Select",
			"options": "Import\nExport\nTransit\nBonded"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "Draft\nSubmitted\nIn Progress\nApproved\nRejected\nCancelled"
		},
		{
			"fieldname": "customs_authority",
			"label": __("Customs Authority"),
			"fieldtype": "Link",
			"options": "Customs Authority"
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


