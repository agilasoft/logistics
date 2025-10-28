// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Handling Unit Capacity"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"get_query": function() {
				return {
					"filters": {
						"company": frappe.query_report.get_filter_value("company")
					}
				};
			}
		},
		{
			"fieldname": "type",
			"label": __("Handling Unit Type"),
			"fieldtype": "Link",
			"options": "Handling Unit Type"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "Available\nIn Use\nUnder Maintenance\nInactive",
			"default": ""
		},
		{
			"fieldname": "brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "utilization_threshold",
			"label": __("Min Utilization %"),
			"fieldtype": "Float",
			"default": 0,
			"description": __("Show only handling units with utilization above this percentage")
		},
		{
			"fieldname": "capacity_alerts_only",
			"label": __("Capacity Alerts Only"),
			"fieldtype": "Check",
			"default": 0,
			"description": __("Show only handling units with capacity alerts enabled")
		},
		{
			"fieldname": "show_inactive",
			"label": __("Show Inactive"),
			"fieldtype": "Check",
			"default": 0,
			"description": __("Include inactive handling units in the report")
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code utilization percentage
		if (column.fieldname === "utilization_percentage") {
			const util = parseFloat(data.utilization_percentage) || 0;
			if (util >= 90) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (util >= 75) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (util >= 50) {
				value = `<span style="color: green;">${value}</span>`;
			}
		}
		
		// Color code status
		if (column.fieldname === "status") {
			const status = data.status;
			if (status === "In Use") {
				value = `<span style="color: blue; font-weight: bold;">${value}</span>`;
			} else if (status === "Under Maintenance") {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (status === "Inactive") {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (status === "Available") {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code capacity alerts
		if (column.fieldname === "capacity_status") {
			const status = data.capacity_status;
			if (status === "Critical") {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (status === "Warning") {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (status === "Good") {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	},
	"onload": function(report) {
		// Add Actions dropdown menu
		report.page.add_inner_button(__("Refresh Capacity Data"), function() {
			frappe.call({
				method: "logistics.warehousing.api_parts.capacity_management.refresh_capacity_data",
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Capacity data refreshed successfully"),
							indicator: "green"
						});
						report.refresh();
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Export to Excel"), function() {
			frappe.call({
				method: "logistics.warehousing.report.handling_unit_capacity.handling_unit_capacity.export_to_excel",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						window.open(r.message.file_url);
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Capacity Insights"), function() {
			frappe.call({
				method: "logistics.warehousing.report.handling_unit_capacity.handling_unit_capacity.get_capacity_insights",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Capacity Management Insights"),
							message: r.message.insights_html,
							indicator: "blue"
						});
					}
				}
			});
		}, __("Actions"));
	}
};
