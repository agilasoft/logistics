// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Sustainability Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -12),
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
			"fieldname": "site",
			"label": __("Site"),
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"get_query": function() {
				return {
					"filters": {
						"level": "Site"
					}
				};
			}
		},
		{
			"fieldname": "facility",
			"label": __("Facility"),
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"get_query": function() {
				return {
					"filters": {
						"level": "Building"
					}
				};
			}
		},
		{
			"fieldname": "energy_type",
			"label": __("Energy Type"),
			"fieldtype": "Select",
			"options": "Electricity\nNatural Gas\nDiesel\nSolar\nWind\nHydro\nOther"
		},
		{
			"fieldname": "scope",
			"label": __("Carbon Scope"),
			"fieldtype": "Select",
			"options": "Scope 1\nScope 2\nScope 3\nTotal"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code sustainability rating
		if (column.fieldname === "sustainability_rating") {
			if (value === "Excellent") {
				value = `<span style="color: #28a745; font-weight: bold;">${value}</span>`;
			} else if (value === "Very Good") {
				value = `<span style="color: #20c997; font-weight: bold;">${value}</span>`;
			} else if (value === "Good") {
				value = `<span style="color: #17a2b8; font-weight: bold;">${value}</span>`;
			} else if (value === "Fair") {
				value = `<span style="color: #ffc107; font-weight: bold;">${value}</span>`;
			} else if (value === "Poor") {
				value = `<span style="color: #fd7e14; font-weight: bold;">${value}</span>`;
			} else if (value === "Very Poor") {
				value = `<span style="color: #dc3545; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code efficiency score
		if (column.fieldname === "efficiency_score") {
			const score = parseFloat(value);
			if (score >= 90) {
				value = `<span style="color: #28a745; font-weight: bold;">${value}</span>`;
			} else if (score >= 80) {
				value = `<span style="color: #20c997; font-weight: bold;">${value}</span>`;
			} else if (score >= 70) {
				value = `<span style="color: #17a2b8; font-weight: bold;">${value}</span>`;
			} else if (score >= 60) {
				value = `<span style="color: #ffc107; font-weight: bold;">${value}</span>`;
			} else if (score >= 50) {
				value = `<span style="color: #fd7e14; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: #dc3545; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code renewable percentage
		if (column.fieldname === "renewable_percentage") {
			const percentage = parseFloat(value);
			if (percentage >= 50) {
				value = `<span style="color: #28a745; font-weight: bold;">${value}%</span>`;
			} else if (percentage >= 25) {
				value = `<span style="color: #20c997; font-weight: bold;">${value}%</span>`;
			} else if (percentage >= 10) {
				value = `<span style="color: #17a2b8; font-weight: bold;">${value}%</span>`;
			} else if (percentage >= 5) {
				value = `<span style="color: #ffc107; font-weight: bold;">${value}%</span>`;
			} else {
				value = `<span style="color: #dc3545; font-weight: bold;">${value}%</span>`;
			}
		}
		
		return value;
	},
	"onload": function(report) {
		// Add custom buttons for sustainability actions
		report.page.add_inner_button(__("Generate Sustainability Dashboard"), function() {
			frappe.call({
				method: "logistics.warehousing.sustainability_dashboard.get_sustainability_dashboard_data",
				args: {
					site: report.get_filter_value("site"),
					facility: report.get_filter_value("facility"),
					from_date: report.get_filter_value("from_date"),
					to_date: report.get_filter_value("to_date")
				},
				callback: function(r) {
					if (r.message) {
						// Open dashboard in new window or modal
						frappe.msgprint(__("Sustainability Dashboard generated successfully"));
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Export to Excel"), function() {
			// Export functionality
			frappe.msgprint(__("Export functionality will be implemented"));
		}, __("Actions"));
	}
};
