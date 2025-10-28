// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Carbon Footprint Dashboard"] = {
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
			"fieldname": "scope",
			"label": __("Carbon Scope"),
			"fieldtype": "Select",
			"options": "Scope 1\nScope 2\nScope 3\nTotal",
			"default": "Total"
		},
		{
			"fieldname": "emission_source",
			"label": __("Emission Source"),
			"fieldtype": "Select",
			"options": "Energy Consumption\nTransportation\nWaste Management\nWater Usage\nEquipment\nOther"
		},
		{
			"fieldname": "carbon_threshold",
			"label": __("Min Carbon Footprint (kg CO2e)"),
			"fieldtype": "Float",
			"default": 0,
			"description": __("Show only records with carbon footprint above this value")
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
			"options": "Site\nFacility\nEmission Source\nScope\nMonth\nNone",
			"default": "Site"
		},
		{
			"fieldname": "include_offset",
			"label": __("Include Carbon Offsets"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include carbon offset and reduction data")
		},
		{
			"fieldname": "show_intensity",
			"label": __("Show Carbon Intensity"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Include carbon intensity metrics")
		},
		{
			"fieldname": "show_targets",
			"label": __("Show Reduction Targets"),
			"fieldtype": "Check",
			"default": 1,
			"description": __("Compare against reduction targets")
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code carbon footprint values
		if (column.fieldname === "total_carbon_footprint" || column.fieldname === "scope_1_emissions" || 
			column.fieldname === "scope_2_emissions" || column.fieldname === "scope_3_emissions") {
			const footprint = parseFloat(data[column.fieldname]) || 0;
			if (footprint <= 100) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (footprint <= 500) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code carbon intensity
		if (column.fieldname === "carbon_intensity") {
			const intensity = parseFloat(data.carbon_intensity) || 0;
			if (intensity <= 0.2) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (intensity <= 0.5) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code reduction percentage
		if (column.fieldname === "reduction_percentage") {
			const reduction = parseFloat(data.reduction_percentage) || 0;
			if (reduction >= 20) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (reduction >= 10) {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (reduction >= 0) {
				value = `<span style="color: yellow; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color code target achievement
		if (column.fieldname === "target_achievement") {
			const achievement = parseFloat(data.target_achievement) || 0;
			if (achievement >= 100) {
				value = `<span style="color: green; font-weight: bold;">✓ ${value}</span>`;
			} else if (achievement >= 80) {
				value = `<span style="color: orange; font-weight: bold;">⚠ ${value}</span>`;
			} else {
				value = `<span style="color: red; font-weight: bold;">✗ ${value}</span>`;
			}
		}
		
		// Color code trend indicators
		if (column.fieldname === "trend") {
			const trend = data.trend;
			if (trend === "Decreasing") {
				value = `<span style="color: green; font-weight: bold;">↘ ${value}</span>`;
			} else if (trend === "Increasing") {
				value = `<span style="color: red; font-weight: bold;">↗ ${value}</span>`;
			} else if (trend === "Stable") {
				value = `<span style="color: blue; font-weight: bold;">→ ${value}</span>`;
			}
		}
		
		// Color code carbon rating
		if (column.fieldname === "carbon_rating") {
			const rating = data.carbon_rating;
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
		
		return value;
	},
	"onload": function(report) {
		// Add actions to the existing Actions dropdown using proper Frappe method
		report.page.add_inner_button(__("Calculate Carbon Footprint"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.calculate_carbon_footprint",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Carbon footprint calculated successfully"),
							indicator: "green"
						});
						report.refresh();
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Export Dashboard"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.export_carbon_dashboard",
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
		
		report.page.add_inner_button(__("View Carbon Chart"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.get_carbon_chart",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message && r.message.chart_config) {
						// Open chart in new window
						const chartWindow = window.open('', '_blank');
						chartWindow.document.write(`
							<html>
								<head><title>Carbon Footprint Chart</title></head>
								<body>
									<h2>Carbon Footprint Analysis</h2>
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
		
		report.page.add_inner_button(__("Carbon Insights"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.get_carbon_insights",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Carbon Footprint Insights"),
							message: r.message.insights_html,
							indicator: "blue"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Reduction Recommendations"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.get_reduction_recommendations",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Carbon Reduction Recommendations"),
							message: r.message.recommendations_html,
							indicator: "green"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Offset Calculator"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.get_offset_calculator",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Carbon Offset Calculator"),
							message: r.message.calculator_html,
							indicator: "blue"
						});
					}
				}
			});
		}, __("Actions"));
		
		report.page.add_inner_button(__("Compliance Check"), function() {
			frappe.call({
				method: "logistics.warehousing.report.carbon_footprint_dashboard.carbon_footprint_dashboard.check_compliance",
				args: {
					filters: report.get_filter_values()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Carbon Compliance Check"),
							message: r.message.compliance_html,
							indicator: r.message.compliance_status === "Compliant" ? "green" : "red"
						});
					}
				}
			});
		}, __("Actions"));
		
		// Add Dashboard Integration button
		report.page.add_inner_button(__("Show Dashboard"), function() {
			toggleDashboard(report);
		});
		
		// Dashboard toggle function
		window.toggleDashboard = function(report) {
			const dashboardContainer = $('#carbon-dashboard-container');
			
			if (dashboardContainer.length === 0) {
				// Create dashboard container
				const dashboardHtml = `
					<div id="carbon-dashboard-container" style="margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
						<h4><i class="fa fa-leaf text-success"></i> Carbon Footprint Dashboard</h4>
						<div class="row">
							<div class="col-md-3">
								<div class="card text-center">
									<div class="card-body">
										<h3 class="text-primary" id="overall-score">--</h3>
										<p class="card-text">Overall Score</p>
										<div class="progress">
											<div class="progress-bar bg-primary" id="overall-progress" style="width: 0%"></div>
										</div>
									</div>
								</div>
							</div>
							<div class="col-md-3">
								<div class="card text-center">
									<div class="card-body">
										<h3 class="text-success" id="energy-score">--</h3>
										<p class="card-text">Energy Score</p>
										<div class="progress">
											<div class="progress-bar bg-success" id="energy-progress" style="width: 0%"></div>
										</div>
									</div>
								</div>
							</div>
							<div class="col-md-3">
								<div class="card text-center">
									<div class="card-body">
										<h3 class="text-info" id="carbon-score">--</h3>
										<p class="card-text">Carbon Score</p>
										<div class="progress">
											<div class="progress-bar bg-info" id="carbon-progress" style="width: 0%"></div>
										</div>
									</div>
								</div>
							</div>
							<div class="col-md-3">
								<div class="card text-center">
									<div class="card-body">
										<h3 class="text-warning" id="green-score">--</h3>
										<p class="card-text">Green Score</p>
										<div class="progress">
											<div class="progress-bar bg-warning" id="green-progress" style="width: 0%"></div>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div class="row mt-3">
							<div class="col-md-6">
								<div class="card">
									<div class="card-header">
										<h5 class="card-title">Energy Consumption</h5>
									</div>
									<div class="card-body">
										<div class="row">
											<div class="col-md-6">
												<h6>Total Consumption</h6>
												<p class="h4 text-primary" id="total-consumption">--</p>
											</div>
											<div class="col-md-6">
												<h6>Total Cost</h6>
												<p class="h4 text-success" id="total-cost">--</p>
											</div>
										</div>
									</div>
								</div>
							</div>
							<div class="col-md-6">
								<div class="card">
									<div class="card-header">
										<h5 class="card-title">Carbon Footprint</h5>
									</div>
									<div class="card-body">
										<div class="row">
											<div class="col-md-6">
												<h6>Total Emissions</h6>
												<p class="h4 text-danger" id="total-emissions">--</p>
											</div>
											<div class="col-md-6">
												<h6>Daily Average</h6>
												<p class="h4 text-info" id="daily-average">--</p>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
						<div class="row mt-3">
							<div class="col-md-12">
								<div class="card">
									<div class="card-header">
										<h5 class="card-title">Sustainability Recommendations</h5>
									</div>
									<div class="card-body">
										<div id="dashboard-recommendations">
											<p class="text-muted">Loading recommendations...</p>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				`;
				
				// Insert dashboard after the report table
				$('.report-container').after(dashboardHtml);
				
				// Load dashboard data
				loadDashboardData(report);
				
				// Update button text
				$(this).text(__("Hide Dashboard"));
			} else {
				// Toggle visibility
				if (dashboardContainer.is(':visible')) {
					dashboardContainer.hide();
					$(this).text(__("Show Dashboard"));
				} else {
					dashboardContainer.show();
					$(this).text(__("Hide Dashboard"));
					// Reload data when showing
					loadDashboardData(report);
				}
			}
		};
		
		// Load dashboard data
		function loadDashboardData(report) {
			const filters = report.get_filter_values();
			
			// Get sustainability dashboard data
			frappe.call({
				method: "logistics.warehousing.sustainability_dashboard.get_sustainability_dashboard_data",
				args: {
					site: filters.site,
					facility: filters.facility,
					from_date: filters.from_date,
					to_date: filters.to_date
				},
				callback: function(r) {
					if (r.message) {
						updateDashboardData(r.message);
					}
				}
			});
		}
		
		// Update dashboard data
		function updateDashboardData(data) {
			// Update scores
			const scores = data.sustainability_scores || {};
			$("#overall-score").text(Math.round(scores.overall_score || 0));
			$("#overall-progress").css("width", (scores.overall_score || 0) + "%");
			
			$("#energy-score").text(Math.round(scores.energy_score || 0));
			$("#energy-progress").css("width", (scores.energy_score || 0) + "%");
			
			$("#carbon-score").text(Math.round(scores.carbon_score || 0));
			$("#carbon-progress").css("width", (scores.carbon_score || 0) + "%");
			
			$("#green-score").text(Math.round(scores.green_score || 0));
			$("#green-progress").css("width", (scores.green_score || 0) + "%");
			
			// Update energy data
			const energy = data.energy_data || {};
			const energySummary = energy.summary || {};
			$("#total-consumption").text(formatNumber(energySummary.total_consumption || 0));
			$("#total-cost").text(formatCurrency(energySummary.total_cost || 0));
			
			// Update carbon data
			const carbon = data.carbon_data || {};
			const carbonSummary = carbon.summary || {};
			$("#total-emissions").text(formatNumber(carbonSummary.total_emissions || 0));
			$("#daily-average").text(formatNumber(carbonSummary.average_daily_emissions || 0));
			
			// Update recommendations
			const recommendations = data.recommendations || [];
			let html = "";
			if (recommendations.length === 0) {
				html = "<p class='text-muted'>No specific recommendations at this time.</p>";
			} else {
				recommendations.forEach(rec => {
					html += `<div class="alert alert-info">
						<h6>${rec.category}</h6>
						<p>${rec.recommendation}</p>
						<small class="text-muted">Potential savings: ${rec.potential_savings}</small>
					</div>`;
				});
			}
			$("#dashboard-recommendations").html(html);
		}
		
		// Utility functions
		function formatNumber(num) {
			return new Intl.NumberFormat().format(num);
		}
		
		function formatCurrency(num) {
			return new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency: 'USD'
			}).format(num);
		}
	}
};
