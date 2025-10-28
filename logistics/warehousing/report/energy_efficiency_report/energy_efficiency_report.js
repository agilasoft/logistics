// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Energy Efficiency Report"] = {
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
			"fieldname": "energy_type",
			"label": __("Energy Type"),
			"fieldtype": "Select",
			"options": "Electricity\nNatural Gas\nDiesel\nSolar\nWind\nHydro\nOther"
		},
		{
			"fieldname": "efficiency_threshold",
			"label": __("Min Efficiency Score"),
			"fieldtype": "Float",
			"default": 0,
			"description": __("Show only records with efficiency score above this value")
		},
		{
			"fieldname": "show_trends",
			"label": __("Show Trends"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include trend analysis in the report")
		},
		{
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Site\nFacility\nEnergy Type\nMonth\nNone",
			"default": "Site"
		},
		{
			"fieldname": "include_equipment",
			"label": __("Include Equipment Breakdown"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include equipment-level energy consumption")
		},
		{
			"fieldname": "show_benchmarks",
			"label": __("Show Industry Benchmarks"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Compare against industry benchmarks")
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code efficiency scores
		if (column.fieldname === "efficiency_score") {
			const score = parseFloat(data.efficiency_score) || 0;
			if (score >= 90) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (score >= 75) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (score >= 60) {
				value = `<span style="color: yellow; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code carbon intensity
		if (column.fieldname === "carbon_intensity") {
			const intensity = parseFloat(data.carbon_intensity) || 0;
			if (intensity <= 0.2) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (intensity <= 0.4) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code renewable percentage
		if (column.fieldname === "renewable_percentage") {
			const renewable = parseFloat(data.renewable_percentage) || 0;
			if (renewable >= 50) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (renewable >= 25) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code energy cost per unit
		if (column.fieldname === "energy_cost_per_unit") {
			const cost = parseFloat(data.energy_cost_per_unit) || 0;
			if (cost <= 0.05) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (cost <= 0.1) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code trend indicators
		if (column.fieldname === "trend") {
			const trend = data.trend;
			if (trend === "Improving") {
				value = `<span style="color: green; font-weight: bold;">↗ ${value}</span>`;
			} else if (trend === "Declining") {
				value = `<span style="color: red; font-weight: bold;">↘ ${value}</span>`;
			} else if (trend === "Stable") {
				value = `<span style="color: blue; font-weight: bold;">→ ${value}</span>`;
			}
		}
		
		return value;
	},
	"onload": function(report) {
		// Add Actions dropdown menu
		report.page.add_inner_button(__("Calculate Efficiency"), function() {
			frappe.call({
				method: "logistics.warehousing.report.energy_efficiency_report.energy_efficiency_report.calculate_efficiency_metrics",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Efficiency metrics calculated successfully"),
							indicator: "green"
						});
						report.refresh();
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Export Report"), function() {
			frappe.call({
				method: "logistics.warehousing.report.energy_efficiency_report.energy_efficiency_report.export_efficiency_report",
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
		
		report.page.add_inner_button(__("View Efficiency Chart"), function() {
			frappe.call({
				method: "logistics.warehousing.report.energy_efficiency_report.energy_efficiency_report.get_efficiency_chart",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message && r.message.chart_config) {
						// Open chart in new window
						const chartWindow = window.open('', '_blank');
						chartWindow.document.write(`
							<html>
								<head><title>Energy Efficiency Chart</title></head>
								<body>
									<h2>Energy Efficiency Analysis</h2>
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
		
		report.page.add_inner_button(__("Efficiency Insights"), function() {
			frappe.call({
				method: "logistics.warehousing.report.energy_efficiency_report.energy_efficiency_report.get_efficiency_insights",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Energy Efficiency Insights"),
							message: r.message.insights_html,
							indicator: "blue"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Benchmark Comparison"), function() {
			frappe.call({
				method: "logistics.warehousing.report.energy_efficiency_report.energy_efficiency_report.get_benchmark_comparison",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Industry Benchmark Comparison"),
							message: r.message.benchmark_html,
							indicator: "green"
						});
					}
				}
			});
		}, __("Actions"));
	}
};
