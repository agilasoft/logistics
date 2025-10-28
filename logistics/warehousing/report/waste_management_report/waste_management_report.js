// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Waste Management Report"] = {
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
			"fieldname": "waste_type",
			"label": __("Waste Type"),
			"fieldtype": "Select",
			"options": "Packaging\nPallets\nCardboard\nPlastic\nMetal\nOrganic\nHazardous\nElectronic\nOther"
		},
		{
			"fieldname": "waste_category",
			"label": __("Waste Category"),
			"fieldtype": "Select",
			"options": "Recyclable\nNon-Recyclable\nHazardous\nBiodegradable\nElectronic\nOther"
		},
		{
			"fieldname": "disposal_method",
			"label": __("Disposal Method"),
			"fieldtype": "Select",
			"options": "Recycling\nLandfill\nIncineration\nComposting\nReuse\nDonation\nHazardous Disposal\nOther"
		},
		{
			"fieldname": "waste_threshold",
			"label": __("Min Waste Amount (kg)"),
			"fieldtype": "Float",
			"default": 0,
			"description": __("Show only records with waste amount above this value")
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
			"options": "Site\nFacility\nWaste Type\nWaste Category\nDisposal Method\nMonth\nNone",
			"default": "Site"
		},
		{
			"fieldname": "include_costs",
			"label": __("Include Cost Analysis"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include waste disposal costs and savings")
		},
		{
			"fieldname": "show_recycling_rate",
			"label": __("Show Recycling Rate"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include recycling rate calculations")
		},
		{
			"fieldname": "show_circular_economy",
			"label": __("Show Circular Economy Metrics"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include circular economy and sustainability metrics")
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code waste amount
		if (column.fieldname === "waste_amount") {
			const amount = parseFloat(data.waste_amount) || 0;
			if (amount <= 50) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (amount <= 200) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code recycling rate
		if (column.fieldname === "recycling_rate") {
			const rate = parseFloat(data.recycling_rate) || 0;
			if (rate >= 80) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (rate >= 60) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code diversion rate
		if (column.fieldname === "diversion_rate") {
			const rate = parseFloat(data.diversion_rate) || 0;
			if (rate >= 90) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (rate >= 70) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code cost savings
		if (column.fieldname === "cost_savings") {
			const savings = parseFloat(data.cost_savings) || 0;
			if (savings >= 1000) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (savings >= 500) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code waste rating
		if (column.fieldname === "waste_rating") {
			const rating = data.waste_rating;
			if (rating === "Excellent") {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (rating === "Good") {
				value = `<span style="color: blue; font-weight: bold;">${value}</span>`;
			} else if (rating === "Fair") {
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
		
		// Color code disposal method
		if (column.fieldname === "disposal_method") {
			const method = data.disposal_method;
			if (method === "Recycling" || method === "Reuse" || method === "Composting") {
				value = `<span style="color: green; font-weight: bold;">♻ ${value}</span>`;
			} else if (method === "Donation") {
				value = `<span style="color: blue; font-weight: bold;">❤ ${value}</span>`;
			} else if (method === "Hazardous Disposal") {
				value = `<span style="color: red; font-weight: bold;">⚠ ${value}</span>`;
			} else {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	},
	"onload": function(report) {
		// Add Actions dropdown menu
		report.page.add_inner_button(__("Calculate Waste Metrics"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.calculate_waste_metrics",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Waste metrics calculated successfully"),
							indicator: "green"
						});
						report.refresh();
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Export Report"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.export_waste_report",
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
		
		report.page.add_inner_button(__("View Waste Chart"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.get_waste_chart",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message && r.message.chart_config) {
						// Open chart in new window
						const chartWindow = window.open('', '_blank');
						chartWindow.document.write(`
							<html>
								<head><title>Waste Management Chart</title></head>
								<body>
									<h2>Waste Management Analysis</h2>
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
		
		report.page.add_inner_button(__("Waste Insights"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.get_waste_insights",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Waste Management Insights"),
							message: r.message.insights_html,
							indicator: "blue"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Circular Economy Analysis"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.get_circular_economy_analysis",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Circular Economy Analysis"),
							message: r.message.analysis_html,
							indicator: "green"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Reduction Recommendations"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.get_reduction_recommendations",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Waste Reduction Recommendations"),
							message: r.message.recommendations_html,
							indicator: "green"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Compliance Check"), function() {
			frappe.call({
				method: "logistics.warehousing.report.waste_management_report.waste_management_report.check_waste_compliance",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Waste Compliance Check"),
							message: r.message.compliance_html,
							indicator: r.message.compliance_status === "Compliant" ? "green" : "red"
						});
					}
				}
			});
		}, __("Actions"));
	}
};
