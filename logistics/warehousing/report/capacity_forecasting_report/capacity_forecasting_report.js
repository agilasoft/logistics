// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Capacity Forecasting Report"] = {
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
			"fieldname": "building",
			"label": __("Building"),
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
			"fieldname": "zone",
			"label": __("Zone"),
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"get_query": function() {
				return {
					"filters": {
						"level": "Zone"
					}
				};
			}
		},
		{
			"fieldname": "storage_type",
			"label": __("Storage Type"),
			"fieldtype": "Link",
			"options": "Storage Type"
		},
		{
			"fieldname": "forecast_period",
			"label": __("Forecast Period"),
			"fieldtype": "Select",
			"options": "7 Days\n14 Days\n30 Days\n60 Days\n90 Days\n6 Months\n1 Year",
			"default": "30 Days",
			"reqd": 1
		},
		{
			"fieldname": "forecast_method",
			"label": __("Forecast Method"),
			"fieldtype": "Select",
			"options": "Linear Regression\nMoving Average\nExponential Smoothing\nSeasonal Decomposition\nNeural Network",
			"default": "Linear Regression"
		},
		{
			"fieldname": "include_seasonality",
			"label": __("Include Seasonality"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include seasonal patterns in forecasting")
		},
		{
			"fieldname": "confidence_level",
			"label": __("Confidence Level"),
			"fieldtype": "Select",
			"options": "80%\n85%\n90%\n95%\n99%",
			"default": "95%"
		},
		{
			"fieldname": "show_trend_analysis",
			"label": __("Show Trend Analysis"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include trend analysis in the report")
		},
		{
			"fieldname": "alert_threshold",
			"label": __("Alert Threshold %"),
			"fieldtype": "Float",
			"default": 0,
			"description": __("Show only locations with forecasted utilization >= this percentage (0 = show all)")
		},
		{
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Site\nBuilding\nZone\nStorage Type\nNone",
			"default": "Site"
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
		
		// Color code forecasted utilization
		if (column.fieldname === "forecasted_utilization") {
			const util = parseFloat(data.forecasted_utilization) || 0;
			let color = "green";
			if (util >= 95) {
				color = "red";
			} else if (util >= 85) {
				color = "orange";
			} else if (util >= 70) {
				color = "#FFA500"; // Darker orange/yellow
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${formatted_value}</span>`;
		}
		
		// Color code current utilization
		if (column.fieldname === "current_utilization") {
			const util = parseFloat(data.current_utilization) || 0;
			let color = "green";
			if (util >= 95) {
				color = "red";
			} else if (util >= 85) {
				color = "orange";
			} else if (util >= 70) {
				color = "#FFA500";
			}
			formatted_value = `<span style="color: ${color};">${formatted_value}</span>`;
		}
		
		// Color code trend indicators - use simple text to avoid breaking table layout
		if (column.fieldname === "trend") {
			const trend = String(data.trend || "").toLowerCase();
			let color = "blue";
			let icon = "→";
			if (trend.includes("increas")) {
				color = "red";
				icon = "↗";
			} else if (trend.includes("decreas")) {
				color = "green";
				icon = "↘";
			} else if (trend.includes("stable") || trend.includes("good")) {
				color = "blue";
				icon = "→";
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${icon} ${formatted_value}</span>`;
		}
		
		// Color code confidence levels
		if (column.fieldname === "confidence_score") {
			const confidence = parseFloat(data.confidence_score) || 0;
			let color = "red";
			if (confidence >= 90) {
				color = "green";
			} else if (confidence >= 75) {
				color = "orange";
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${formatted_value}</span>`;
		}
		
		// Color code alerts - use simple text
		if (column.fieldname === "alert_status") {
			const status = String(data.alert_status || "").toLowerCase();
			let color = "green";
			let icon = "●";
			if (status.includes("critical")) {
				color = "red";
				icon = "●";
			} else if (status.includes("warn")) {
				color = "orange";
				icon = "●";
			} else if (status.includes("good")) {
				color = "green";
				icon = "●";
			}
			formatted_value = `<span style="color: ${color}; font-weight: bold;">${icon} ${formatted_value}</span>`;
		}
		
		return formatted_value;
	},
	"onload": function(report) {
		// Add Actions dropdown menu
		report.page.add_inner_button(__("Generate Forecast"), function() {
			frappe.call({
				method: "logistics.warehousing.report.capacity_forecasting_report.capacity_forecasting_report.generate_forecast",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Forecast generated successfully"),
							indicator: "green"
						});
						report.refresh();
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Export Forecast"), function() {
			frappe.call({
				method: "logistics.warehousing.report.capacity_forecasting_report.capacity_forecasting_report.export_forecast",
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
		
		report.page.add_inner_button(__("View Forecast Chart"), function() {
			frappe.call({
				method: "logistics.warehousing.report.capacity_forecasting_report.capacity_forecasting_report.get_forecast_chart",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message && r.message.chart_config) {
						// Open chart in new window
						const chartWindow = window.open('', '_blank');
						chartWindow.document.write(`
							<html>
								<head><title>Capacity Forecast Chart</title></head>
								<body>
									<h2>Capacity Forecast Chart</h2>
									<div id="chart-container"></div>
									<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
									<script>
										const ctx = document.getElementById('chart-container').getContext('2d');
										new Chart(ctx, ${JSON.stringify(r.message.chart_config)});
									</script>
								</body>
							</html>
						`);
					} else if (r.message && r.message.error) {
						frappe.show_alert({
							message: __("Error loading chart: {0}").format(r.message.error),
							indicator: "red"
						});
					} else {
						frappe.show_alert({
							message: __("No chart data available"),
							indicator: "orange"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Forecast Insights"), function() {
			frappe.call({
				method: "logistics.warehousing.report.capacity_forecasting_report.capacity_forecasting_report.get_forecast_insights",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Forecast Insights"),
							message: r.message.insights_html,
							indicator: "blue"
						});
					}
				}
			});
		}, __("Actions"));
	}
};
