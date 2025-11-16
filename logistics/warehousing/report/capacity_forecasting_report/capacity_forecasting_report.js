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
		value = default_formatter(value, row, column, data);
		
		// Color code forecasted utilization
		if (column.fieldname === "forecasted_utilization") {
			const util = parseFloat(data.forecasted_utilization) || 0;
			if (util >= 95) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (util >= 85) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (util >= 70) {
				value = `<span style="color: yellow; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: green;">${value}</span>`;
			}
		}
		
		// Color code trend indicators
		if (column.fieldname === "trend") {
			const trend = data.trend;
			if (trend === "Increasing") {
				value = `<span style="color: red; font-weight: bold;">↗ ${value}</span>`;
			} else if (trend === "Decreasing") {
				value = `<span style="color: green; font-weight: bold;">↘ ${value}</span>`;
			} else if (trend === "Stable") {
				value = `<span style="color: blue; font-weight: bold;">→ ${value}</span>`;
			}
		}
		
		// Color code confidence levels
		if (column.fieldname === "confidence_score") {
			const confidence = parseFloat(data.confidence_score) || 0;
			if (confidence >= 90) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (confidence >= 75) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code alerts
		if (column.fieldname === "alert_status") {
			const status = data.alert_status;
			if (status === "Critical") {
				value = `<span style="color: red; font-weight: bold;">🔴 ${value}</span>`;
			} else if (status === "Warning") {
				value = `<span style="color: orange; font-weight: bold;">🟡 ${value}</span>`;
			} else if (status === "Good") {
				value = `<span style="color: green; font-weight: bold;">🟢 ${value}</span>`;
			}
		}
		
		return value;
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
