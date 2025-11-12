// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Customs Compliance Report"] = {
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
			"fieldname": "issue_type",
			"label": __("Issue Type"),
			"fieldtype": "Select",
			"options": "\nPending Approval\nMissing Documents\nExpired Documents\nOverdue"
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
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
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname === "priority") {
			if (data.priority === "High") {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (data.priority === "Medium") {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			}
		}
		
		if (column.fieldname === "days_overdue" && data.days_overdue > 0) {
			value = `<span style="color: red;">${value}</span>`;
		}
		
		return value;
	}
};


