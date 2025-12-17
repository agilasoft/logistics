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
			"options": "Branch"
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
		// Get default formatted value first
		let formatted_value = default_formatter(value, row, column, data);
		
		// Safety check: if data is undefined/null (e.g., footer row), return default formatted value
		if (!data || typeof data !== "object") {
			return formatted_value;
		}
		
		// Skip formatting if value is empty/null (but allow 0)
		if (value === null || value === undefined || value === "") {
			return formatted_value;
		}
		
		// Color code utilization percentage
		if (column.fieldname === "utilization_percentage") {
			const util = parseFloat(data.utilization_percentage) || 0;
			let color = "green";
			if (util >= 90) {
				color = "red";
			} else if (util >= 75) {
				color = "orange";
			} else if (util >= 50) {
				color = "green";
			} else {
				color = "#888"; // Gray for low utilization
			}
			formatted_value = `<span style="color: ${color}; font-weight: ${util >= 75 ? 'bold' : 'normal'};">${formatted_value}</span>`;
		}
		
		// Color code status
		if (column.fieldname === "status") {
			const status = String(data.status || "").toLowerCase();
			let color = "gray";
			if (status === "in use") {
				color = "blue";
			} else if (status === "under maintenance") {
				color = "orange";
			} else if (status === "inactive") {
				color = "red";
			} else if (status === "available") {
				color = "green";
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${formatted_value}</span>`;
		}
		
		// Color code capacity status
		if (column.fieldname === "capacity_status") {
			const status = String(data.capacity_status || "").toLowerCase();
			let color = "green";
			if (status.includes("critical")) {
				color = "red";
			} else if (status.includes("warn")) {
				color = "orange";
			} else if (status.includes("good")) {
				color = "green";
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${formatted_value}</span>`;
		}
		
		// Color code efficiency score
		if (column.fieldname === "efficiency_score") {
			const score = parseFloat(data.efficiency_score) || 0;
			let color = "red";
			if (score >= 90) {
				color = "green";
			} else if (score >= 75) {
				color = "orange";
			} else if (score >= 50) {
				color = "#FFA500";
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${formatted_value}</span>`;
		}
		
		return formatted_value;
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
