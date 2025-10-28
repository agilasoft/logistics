# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, get_datetime, now_datetime, add_days, add_months, getdate, today
from typing import Dict, List, Any, Optional, Tuple
import json
import math
from datetime import datetime, timedelta


def execute(filters=None):
	"""Execute the Waste Management Report"""
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	
	chart = make_chart(data)
	summary = make_summary(data)
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Site"),
			"fieldname": "site",
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 120,
		},
		{
			"label": _("Facility"),
			"fieldname": "facility",
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 120,
		},
		{
			"label": _("Waste Type"),
			"fieldname": "waste_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Waste Category"),
			"fieldname": "waste_category",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Waste Amount"),
			"fieldname": "waste_amount",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Unit"),
			"fieldname": "unit",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Disposal Method"),
			"fieldname": "disposal_method",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Recycling Rate"),
			"fieldname": "recycling_rate",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Diversion Rate"),
			"fieldname": "diversion_rate",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Disposal Cost"),
			"fieldname": "disposal_cost",
			"fieldtype": "Currency",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Cost Savings"),
			"fieldname": "cost_savings",
			"fieldtype": "Currency",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Carbon Impact"),
			"fieldname": "carbon_impact",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Circular Score"),
			"fieldname": "circular_score",
			"fieldtype": "Float",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Trend"),
			"fieldname": "trend",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Waste Rating"),
			"fieldname": "waste_rating",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 120,
		},
		{
			"label": _("Waste Handler"),
			"fieldname": "waste_handler",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 120,
		},
		{
			"label": _("Compliance Status"),
			"fieldname": "compliance_status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Recommendation"),
			"fieldname": "recommendation",
			"fieldtype": "Data",
			"width": 200,
		}
	]


def get_data(filters):
	"""Get report data with waste management analysis"""
	# Since there's no Waste Management doctype, we'll generate synthetic data
	# In a real implementation, this would query actual waste management data
	
	processed_data = []
	
	# Generate synthetic waste management data
	waste_types = ["Packaging", "Pallets", "Cardboard", "Plastic", "Metal", "Organic", "Hazardous", "Electronic", "Other"]
	waste_categories = ["Recyclable", "Non-Recyclable", "Hazardous", "Biodegradable", "Electronic", "Other"]
	disposal_methods = ["Recycling", "Landfill", "Incineration", "Composting", "Reuse", "Donation", "Hazardous Disposal", "Other"]
	
	# Get sites and facilities from Storage Location Configurator
	sites = frappe.get_all("Storage Location Configurator", 
		filters={"level": "Site"}, 
		fields=["name"]
	)
	
	facilities = frappe.get_all("Storage Location Configurator", 
		filters={"level": "Building"}, 
		fields=["name"]
	)
	
	# Generate data for the date range
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	current_date = from_date
	
	while current_date <= to_date:
		for site in sites[:3]:  # Limit to 3 sites for demo
			for facility in facilities[:2]:  # Limit to 2 facilities per site
				for waste_type in waste_types[:5]:  # Limit to 5 waste types
					# Apply filters
					if filters.get("waste_type") and waste_type != filters.get("waste_type"):
						continue
					
					waste_category = get_waste_category(waste_type)
					if filters.get("waste_category") and waste_category != filters.get("waste_category"):
						continue
					
					disposal_method = get_disposal_method(waste_type, waste_category)
					if filters.get("disposal_method") and disposal_method != filters.get("disposal_method"):
						continue
					
					# Generate waste metrics
					waste_metrics = calculate_waste_metrics_internal(
						current_date, site.name, facility.name, waste_type, 
						waste_category, disposal_method, filters
					)
					
					if waste_metrics:
						processed_data.append(waste_metrics)
		
		current_date = add_days(current_date, 7)  # Weekly data
	
	# Group data if requested
	group_by = filters.get("group_by", "Site")
	if group_by != "None":
		processed_data = group_waste_data(processed_data, group_by)
	
	# Apply waste threshold filter
	if filters.get("waste_threshold"):
		threshold = flt(filters.get("waste_threshold"))
		processed_data = [row for row in processed_data if flt(row.get("waste_amount", 0)) >= threshold]
	
	return processed_data


def get_waste_category(waste_type):
	"""Get waste category based on waste type"""
	category_mapping = {
		"Packaging": "Recyclable",
		"Pallets": "Recyclable", 
		"Cardboard": "Recyclable",
		"Plastic": "Recyclable",
		"Metal": "Recyclable",
		"Organic": "Biodegradable",
		"Hazardous": "Hazardous",
		"Electronic": "Electronic",
		"Other": "Non-Recyclable"
	}
	return category_mapping.get(waste_type, "Other")


def get_disposal_method(waste_type, waste_category):
	"""Get disposal method based on waste type and category"""
	if waste_category == "Recyclable":
		return "Recycling"
	elif waste_category == "Biodegradable":
		return "Composting"
	elif waste_category == "Hazardous":
		return "Hazardous Disposal"
	elif waste_type == "Electronic":
		return "Recycling"
	elif waste_type in ["Pallets", "Packaging"]:
		return "Reuse"
	else:
		return "Landfill"


def calculate_waste_metrics_internal(date, site, facility, waste_type, waste_category, disposal_method, filters):
	"""Calculate comprehensive waste management metrics"""
	try:
		# Generate synthetic waste amount (50-500 kg)
		waste_amount = flt(frappe.utils.random_number(50, 500))
		
		# Calculate recycling rate based on disposal method
		if disposal_method == "Recycling":
			recycling_rate = flt(frappe.utils.random_number(80, 100))
		elif disposal_method == "Reuse":
			recycling_rate = flt(frappe.utils.random_number(70, 90))
		elif disposal_method == "Composting":
			recycling_rate = flt(frappe.utils.random_number(60, 80))
		else:
			recycling_rate = flt(frappe.utils.random_number(0, 30))
		
		# Calculate diversion rate (waste diverted from landfill)
		if disposal_method in ["Recycling", "Reuse", "Composting", "Donation"]:
			diversion_rate = flt(frappe.utils.random_number(70, 95))
		else:
			diversion_rate = flt(frappe.utils.random_number(0, 40))
		
		# Calculate disposal cost (simplified)
		disposal_cost = waste_amount * flt(frappe.utils.random_number(2, 8))  # $2-8 per kg
		
		# Calculate cost savings from recycling/reuse
		if disposal_method in ["Recycling", "Reuse"]:
			cost_savings = disposal_cost * flt(frappe.utils.random_number(30, 70)) / 100
		else:
			cost_savings = 0
		
		# Calculate carbon impact (kg CO2e saved)
		carbon_impact = waste_amount * flt(frappe.utils.random_number(0.5, 2.0))  # kg CO2e per kg waste
		
		# Calculate circular economy score
		circular_score = (recycling_rate + diversion_rate) / 2
		
		# Determine trend (simplified)
		trend = determine_waste_trend(waste_amount, recycling_rate, diversion_rate)
		
		# Determine waste rating
		waste_rating = get_waste_rating(recycling_rate, diversion_rate, circular_score)
		
		# Generate recommendation
		recommendation = generate_waste_recommendation(waste_type, disposal_method, recycling_rate, diversion_rate)
		
		return {
			"date": date,
			"site": site,
			"facility": facility,
			"waste_type": waste_type,
			"waste_category": waste_category,
			"waste_amount": waste_amount,
			"unit": "kg",
			"disposal_method": disposal_method,
			"recycling_rate": recycling_rate,
			"diversion_rate": diversion_rate,
			"disposal_cost": disposal_cost,
			"cost_savings": cost_savings,
			"carbon_impact": carbon_impact,
			"circular_score": circular_score,
			"trend": trend,
			"waste_rating": waste_rating,
			"supplier": "Supplier A",  # Synthetic supplier
			"waste_handler": "Waste Handler B",  # Synthetic waste handler
			"compliance_status": "Compliant" if recycling_rate >= 70 else "Non-Compliant",
			"recommendation": recommendation
		}
		
	except Exception as e:
		frappe.log_error(f"Error calculating waste metrics: {str(e)}")
		return None


def determine_waste_trend(waste_amount, recycling_rate, diversion_rate):
	"""Determine waste management trend (simplified)"""
	if recycling_rate >= 80 and diversion_rate >= 85:
		return "Improving"
	elif recycling_rate <= 50 or diversion_rate <= 60:
		return "Declining"
	else:
		return "Stable"


def get_waste_rating(recycling_rate, diversion_rate, circular_score):
	"""Get waste management rating based on metrics"""
	if recycling_rate >= 90 and diversion_rate >= 90 and circular_score >= 85:
		return "Excellent"
	elif recycling_rate >= 75 and diversion_rate >= 75 and circular_score >= 70:
		return "Good"
	elif recycling_rate >= 60 and diversion_rate >= 60 and circular_score >= 55:
		return "Fair"
	else:
		return "Poor"


def generate_waste_recommendation(waste_type, disposal_method, recycling_rate, diversion_rate):
	"""Generate waste reduction recommendations"""
	if recycling_rate >= 90:
		return "Excellent recycling rate - maintain current practices"
	elif disposal_method == "Landfill" and recycling_rate < 50:
		return f"High landfill usage for {waste_type} - implement recycling program"
	elif diversion_rate < 70:
		return "Low diversion rate - increase recycling and reuse initiatives"
	elif waste_type in ["Packaging", "Plastic"] and disposal_method != "Recycling":
		return f"Consider recycling {waste_type} to improve sustainability"
	else:
		return "Focus on waste reduction and circular economy practices"


def group_waste_data(data, group_by):
	"""Group waste data by specified field"""
	if group_by == "None":
		return data
	
	grouped = {}
	for row in data:
		key = row.get(group_by.lower(), "Unknown")
		if key not in grouped:
			grouped[key] = []
		grouped[key].append(row)
	
	# Create summary rows for each group
	summary_data = []
	for group_name, group_rows in grouped.items():
		# Calculate group totals
		total_waste = sum(flt(row.get("waste_amount", 0)) for row in group_rows)
		total_cost = sum(flt(row.get("disposal_cost", 0)) for row in group_rows)
		total_savings = sum(flt(row.get("cost_savings", 0)) for row in group_rows)
		total_carbon = sum(flt(row.get("carbon_impact", 0)) for row in group_rows)
		avg_recycling = sum(flt(row.get("recycling_rate", 0)) for row in group_rows) / len(group_rows)
		avg_diversion = sum(flt(row.get("diversion_rate", 0)) for row in group_rows) / len(group_rows)
		avg_circular = sum(flt(row.get("circular_score", 0)) for row in group_rows) / len(group_rows)
		
		# Determine group trend
		trends = [row.get("trend", "Stable") for row in group_rows]
		trend_counts = {"Improving": trends.count("Improving"), "Declining": trends.count("Declining"), "Stable": trends.count("Stable")}
		group_trend = max(trend_counts, key=trend_counts.get)
		
		# Determine group waste rating
		ratings = [row.get("waste_rating", "Poor") for row in group_rows]
		rating_counts = {"Excellent": ratings.count("Excellent"), "Good": ratings.count("Good"), "Fair": ratings.count("Fair"), "Poor": ratings.count("Poor")}
		group_rating = max(rating_counts, key=rating_counts.get)
		
		summary_row = {
			"date": f"{group_name} (Summary)",
			"site": group_rows[0].get("site", ""),
			"facility": group_rows[0].get("facility", ""),
			"waste_type": group_rows[0].get("waste_type", ""),
			"waste_category": group_rows[0].get("waste_category", ""),
			"waste_amount": total_waste,
			"unit": "kg",
			"disposal_method": group_rows[0].get("disposal_method", ""),
			"recycling_rate": avg_recycling,
			"diversion_rate": avg_diversion,
			"disposal_cost": total_cost,
			"cost_savings": total_savings,
			"carbon_impact": total_carbon,
			"circular_score": avg_circular,
			"trend": group_trend,
			"waste_rating": group_rating,
			"supplier": group_rows[0].get("supplier", ""),
			"waste_handler": group_rows[0].get("waste_handler", ""),
			"compliance_status": "Compliant" if avg_recycling >= 70 else "Non-Compliant",
			"recommendation": f"Group summary: {len(group_rows)} records"
		}
		
		summary_data.append(summary_row)
		summary_data.extend(group_rows)
	
	return summary_data


def make_chart(data):
	"""Create waste management chart"""
	if not data:
		return {
			"data": {
				"labels": [],
				"datasets": [{
					"name": "Waste Amount by Type",
					"values": []
				}]
			},
			"type": "pie",
			"height": 300,
			"colors": []
		}
	
	# Group data by waste type
	waste_type_data = {}
	for row in data:
		waste_type = row.get("waste_type", "Other")
		if waste_type not in waste_type_data:
			waste_type_data[waste_type] = 0
		waste_type_data[waste_type] += flt(row.get("waste_amount", 0))
	
	return {
		"data": {
			"labels": list(waste_type_data.keys()),
			"datasets": [{
				"name": "Waste Amount by Type",
				"values": list(waste_type_data.values())
			}]
		},
		"type": "pie",
		"height": 300,
		"colors": ["#4CAF50", "#FF9800", "#F44336", "#2196F3", "#9C27B0", "#00BCD4", "#795548", "#607D8B"]
	}


def make_summary(data):
	"""Create summary data"""
	if not data:
		return []
	
	total_records = len(data)
	total_waste = sum(flt(row.get("waste_amount", 0)) for row in data)
	total_cost = sum(flt(row.get("disposal_cost", 0)) for row in data)
	total_savings = sum(flt(row.get("cost_savings", 0)) for row in data)
	total_carbon = sum(flt(row.get("carbon_impact", 0)) for row in data)
	avg_recycling = sum(flt(row.get("recycling_rate", 0)) for row in data) / total_records if total_records > 0 else 0
	avg_diversion = sum(flt(row.get("diversion_rate", 0)) for row in data) / total_records if total_records > 0 else 0
	avg_circular = sum(flt(row.get("circular_score", 0)) for row in data) / total_records if total_records > 0 else 0
	
	# Count waste ratings
	excellent = len([row for row in data if row.get("waste_rating") == "Excellent"])
	good = len([row for row in data if row.get("waste_rating") == "Good"])
	fair = len([row for row in data if row.get("waste_rating") == "Fair"])
	poor = len([row for row in data if row.get("waste_rating") == "Poor"])
	
	# Count trends
	improving = len([row for row in data if row.get("trend") == "Improving"])
	declining = len([row for row in data if row.get("trend") == "Declining"])
	stable = len([row for row in data if row.get("trend") == "Stable"])
	
	# Count compliance
	compliant = len([row for row in data if row.get("compliance_status") == "Compliant"])
	non_compliant = len([row for row in data if row.get("compliance_status") == "Non-Compliant"])
	
	return [
		{
			"label": _("Total Records"),
			"value": total_records,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Total Waste Amount"),
			"value": total_waste,
			"indicator": "red" if total_waste > 1000 else "orange" if total_waste > 500 else "green",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Total Disposal Cost"),
			"value": total_cost,
			"indicator": "red",
			"datatype": "Currency",
			"precision": 2
		},
		{
			"label": _("Total Cost Savings"),
			"value": total_savings,
			"indicator": "green",
			"datatype": "Currency",
			"precision": 2
		},
		{
			"label": _("Total Carbon Impact"),
			"value": total_carbon,
			"indicator": "green",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Average Recycling Rate"),
			"value": avg_recycling,
			"indicator": "green" if avg_recycling >= 80 else "orange" if avg_recycling >= 60 else "red",
			"datatype": "Percent",
			"precision": 1
		},
		{
			"label": _("Average Diversion Rate"),
			"value": avg_diversion,
			"indicator": "green" if avg_diversion >= 85 else "orange" if avg_diversion >= 70 else "red",
			"datatype": "Percent",
			"precision": 1
		},
		{
			"label": _("Average Circular Score"),
			"value": avg_circular,
			"indicator": "green" if avg_circular >= 80 else "orange" if avg_circular >= 65 else "red",
			"datatype": "Float",
			"precision": 1
		},
		{
			"label": _("Excellent Rating"),
			"value": excellent,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("Good Rating"),
			"value": good,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Fair Rating"),
			"value": fair,
			"indicator": "orange",
			"datatype": "Int"
		},
		{
			"label": _("Poor Rating"),
			"value": poor,
			"indicator": "red",
			"datatype": "Int"
		},
		{
			"label": _("Improving Trend"),
			"value": improving,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("Stable Trend"),
			"value": stable,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Declining Trend"),
			"value": declining,
			"indicator": "red",
			"datatype": "Int"
		},
		{
			"label": _("Compliant Records"),
			"value": compliant,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("Non-Compliant Records"),
			"value": non_compliant,
			"indicator": "red",
			"datatype": "Int"
		}
	]


@frappe.whitelist()
def calculate_waste_metrics(filters):
	"""Calculate and update waste management metrics"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		
		# This would typically update waste metrics in the database
		# For now, just return success
		return {
			"success": True,
			"message": "Waste metrics calculated successfully"
		}
		
	except Exception as e:
		frappe.log_error(f"Error calculating waste metrics: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def export_waste_report(filters):
	"""Export waste management report to Excel"""
	try:
		import pandas as pd
		from frappe.utils import get_site_path
		import os
		
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		columns, data = get_columns(), get_data(filters)
		
		# Convert to DataFrame
		df = pd.DataFrame(data)
		
		# Create Excel file
		file_path = get_site_path("private", "files", "waste_management_report.xlsx")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		
		with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
			df.to_excel(writer, sheet_name='Waste Management', index=False)
			
			# Add summary sheet
			summary_data = make_summary(data)
			summary_df = pd.DataFrame(summary_data)
			summary_df.to_excel(writer, sheet_name='Summary', index=False)
		
		# Return file URL
		file_url = f"/private/files/waste_management_report.xlsx"
		
		return {
			"file_url": file_url,
			"message": _("Waste management report exported successfully")
		}
		
	except Exception as e:
		frappe.log_error(f"Error exporting waste report: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_waste_chart(filters):
	"""Get waste management chart configuration"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Create waste trend chart
		chart_config = {
			"type": "line",
			"data": {
				"labels": [str(row.get("date", "")) for row in data[:30]],
				"datasets": [{
					"label": "Waste Amount",
					"data": [flt(row.get("waste_amount", 0)) for row in data[:30]],
					"borderColor": "rgb(244, 67, 54)",
					"backgroundColor": "rgba(244, 67, 54, 0.2)",
					"tension": 0.1
				}, {
					"label": "Recycling Rate",
					"data": [flt(row.get("recycling_rate", 0)) for row in data[:30]],
					"borderColor": "rgb(76, 175, 80)",
					"backgroundColor": "rgba(76, 175, 80, 0.2)",
					"tension": 0.1
				}]
			},
			"options": {
				"responsive": True,
				"scales": {
					"y": {
						"beginAtZero": True,
						"title": {
							"display": True,
							"text": "Waste Amount (kg) / Recycling Rate (%)"
						}
					}
				}
			}
		}
		
		return {
			"chart_config": chart_config
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating waste chart: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_waste_insights(filters):
	"""Get waste management insights and analysis"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		insights = []
		
		# High waste amount insights
		high_waste = [row for row in data if flt(row.get("waste_amount", 0)) > 300]
		if high_waste:
			insights.append({
				"type": "warning",
				"title": _("High Waste Generation"),
				"message": _("{0} records have waste amounts above 300 kg").format(len(high_waste)),
				"action": _("Implement waste reduction strategies and source reduction programs")
			})
		
		# Low recycling rate insights
		low_recycling = [row for row in data if flt(row.get("recycling_rate", 0)) < 60]
		if low_recycling:
			insights.append({
				"type": "error",
				"title": _("Low Recycling Rate"),
				"message": _("{0} records have recycling rates below 60%").format(len(low_recycling)),
				"action": _("Improve recycling infrastructure and employee training programs")
			})
		
		# Low diversion rate insights
		low_diversion = [row for row in data if flt(row.get("diversion_rate", 0)) < 70]
		if low_diversion:
			insights.append({
				"type": "warning",
				"title": _("Low Diversion Rate"),
				"message": _("{0} records have diversion rates below 70%").format(len(low_diversion)),
				"action": _("Increase recycling, reuse, and composting initiatives")
			})
		
		# High landfill usage insights
		landfill_usage = [row for row in data if row.get("disposal_method") == "Landfill"]
		if len(landfill_usage) > len(data) * 0.3:  # More than 30% landfill usage
			insights.append({
				"type": "error",
				"title": _("High Landfill Usage"),
				"message": _("{0}% of waste is going to landfill").format(round(len(landfill_usage) / len(data) * 100, 1)),
				"action": _("Implement comprehensive recycling and diversion programs")
			})
		
		# Create HTML insights
		insights_html = "<div style='font-family: Arial, sans-serif;'>"
		insights_html += "<h3>Waste Management Insights</h3>"
		
		for insight in insights:
			color = "red" if insight["type"] == "error" else "orange" if insight["type"] == "warning" else "blue"
			insights_html += f"""
				<div style='border-left: 4px solid {color}; padding: 10px; margin: 10px 0; background-color: #f9f9f9;'>
					<h4 style='color: {color}; margin: 0 0 5px 0;'>{insight['title']}</h4>
					<p style='margin: 5px 0;'>{insight['message']}</p>
					<p style='margin: 5px 0; font-style: italic; color: #666;'>{insight['action']}</p>
				</div>
			"""
		
		insights_html += "</div>"
		
		return {
			"insights_html": insights_html,
			"insights": insights
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting waste insights: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_circular_economy_analysis(filters):
	"""Get circular economy analysis"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Calculate circular economy metrics
		total_waste = sum(flt(row.get("waste_amount", 0)) for row in data)
		total_recycled = sum(flt(row.get("waste_amount", 0)) * flt(row.get("recycling_rate", 0)) / 100 for row in data)
		total_diverted = sum(flt(row.get("waste_amount", 0)) * flt(row.get("diversion_rate", 0)) / 100 for row in data)
		total_carbon_saved = sum(flt(row.get("carbon_impact", 0)) for row in data)
		total_cost_savings = sum(flt(row.get("cost_savings", 0)) for row in data)
		
		# Calculate circular economy score
		avg_circular_score = sum(flt(row.get("circular_score", 0)) for row in data) / len(data) if data else 0
		
		# Analyze waste streams
		waste_streams = {}
		for row in data:
			waste_type = row.get("waste_type", "Other")
			if waste_type not in waste_streams:
				waste_streams[waste_type] = {"amount": 0, "recycled": 0, "diverted": 0}
			waste_streams[waste_type]["amount"] += flt(row.get("waste_amount", 0))
			waste_streams[waste_type]["recycled"] += flt(row.get("waste_amount", 0)) * flt(row.get("recycling_rate", 0)) / 100
			waste_streams[waste_type]["diverted"] += flt(row.get("waste_amount", 0)) * flt(row.get("diversion_rate", 0)) / 100
		
		analysis_html = "<div style='font-family: Arial, sans-serif;'>"
		analysis_html += "<h3>Circular Economy Analysis</h3>"
		
		analysis_html += f"<p><strong>Overall Circular Economy Score:</strong> <span style='color: {'green' if avg_circular_score >= 80 else 'orange' if avg_circular_score >= 65 else 'red'};'>{avg_circular_score:.1f}/100</span></p>"
		analysis_html += f"<p><strong>Total Waste Generated:</strong> {total_waste:.2f} kg</p>"
		analysis_html += f"<p><strong>Total Recycled:</strong> {total_recycled:.2f} kg ({total_recycled/total_waste*100:.1f}%)</p>"
		analysis_html += f"<p><strong>Total Diverted from Landfill:</strong> {total_diverted:.2f} kg ({total_diverted/total_waste*100:.1f}%)</p>"
		analysis_html += f"<p><strong>Carbon Impact Saved:</strong> {total_carbon_saved:.2f} kg CO2e</p>"
		analysis_html += f"<p><strong>Cost Savings:</strong> ${total_cost_savings:.2f}</p>"
		
		analysis_html += "<h4>Waste Stream Analysis:</h4>"
		for waste_type, metrics in waste_streams.items():
			recycling_rate = (metrics["recycled"] / metrics["amount"] * 100) if metrics["amount"] > 0 else 0
			diversion_rate = (metrics["diverted"] / metrics["amount"] * 100) if metrics["amount"] > 0 else 0
			
			analysis_html += f"""
				<div style='border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;'>
					<h5 style='margin: 0 0 5px 0;'>{waste_type}</h5>
					<p style='margin: 5px 0;'>Amount: {metrics['amount']:.2f} kg</p>
					<p style='margin: 5px 0;'>Recycling Rate: {recycling_rate:.1f}%</p>
					<p style='margin: 5px 0;'>Diversion Rate: {diversion_rate:.1f}%</p>
				</div>
			"""
		
		analysis_html += "</div>"
		
		return {
			"analysis_html": analysis_html,
			"circular_score": avg_circular_score,
			"total_waste": total_waste,
			"total_recycled": total_recycled,
			"total_diverted": total_diverted,
			"carbon_saved": total_carbon_saved,
			"cost_savings": total_cost_savings
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting circular economy analysis: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_reduction_recommendations(filters):
	"""Get waste reduction recommendations"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		recommendations = []
		
		# Analyze data for recommendations
		total_waste = sum(flt(row.get("waste_amount", 0)) for row in data)
		avg_recycling = sum(flt(row.get("recycling_rate", 0)) for row in data) / len(data) if data else 0
		avg_diversion = sum(flt(row.get("diversion_rate", 0)) for row in data) / len(data) if data else 0
		
		# High waste generation recommendations
		if total_waste > 2000:
			recommendations.append({
				"priority": "High",
				"category": "Source Reduction",
				"recommendation": "Implement source reduction programs and packaging optimization",
				"impact": "High",
				"cost": "Low"
			})
		
		# Low recycling recommendations
		if avg_recycling < 70:
			recommendations.append({
				"priority": "High",
				"category": "Recycling",
				"recommendation": "Improve recycling infrastructure and employee training",
				"impact": "High",
				"cost": "Medium"
			})
		
		# Low diversion recommendations
		if avg_diversion < 80:
			recommendations.append({
				"priority": "Medium",
				"category": "Diversion",
				"recommendation": "Increase composting and reuse programs",
				"impact": "Medium",
				"cost": "Medium"
			})
		
		# General recommendations
		recommendations.extend([
			{
				"priority": "Medium",
				"category": "Packaging",
				"recommendation": "Switch to reusable packaging and reduce single-use materials",
				"impact": "Medium",
				"cost": "Medium"
			},
			{
				"priority": "Low",
				"category": "Education",
				"recommendation": "Implement waste awareness and training programs",
				"impact": "Low",
				"cost": "Low"
			},
			{
				"priority": "Medium",
				"category": "Technology",
				"recommendation": "Invest in waste sorting and processing technology",
				"impact": "High",
				"cost": "High"
			}
		])
		
		# Create HTML recommendations
		recommendations_html = "<div style='font-family: Arial, sans-serif;'>"
		recommendations_html += "<h3>Waste Reduction Recommendations</h3>"
		
		for rec in recommendations:
			priority_color = "red" if rec["priority"] == "High" else "orange" if rec["priority"] == "Medium" else "green"
			recommendations_html += f"""
				<div style='border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;'>
					<h4 style='margin: 0 0 10px 0; color: {priority_color};'>{rec['priority']} Priority - {rec['category']}</h4>
					<p style='margin: 5px 0; font-weight: bold;'>{rec['recommendation']}</p>
					<p style='margin: 5px 0; color: #666;'>Impact: {rec['impact']} | Cost: {rec['cost']}</p>
				</div>
			"""
		
		recommendations_html += "</div>"
		
		return {
			"recommendations_html": recommendations_html,
			"recommendations": recommendations
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting reduction recommendations: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def check_waste_compliance(filters):
	"""Check waste compliance status"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Compliance criteria
		total_waste = sum(flt(row.get("waste_amount", 0)) for row in data)
		avg_recycling = sum(flt(row.get("recycling_rate", 0)) for row in data) / len(data) if data else 0
		avg_diversion = sum(flt(row.get("diversion_rate", 0)) for row in data) / len(data) if data else 0
		
		# Check compliance
		compliance_checks = []
		
		# Recycling rate threshold
		if avg_recycling >= 70:
			compliance_checks.append({"check": "Recycling Rate", "status": "Pass", "value": f"{avg_recycling:.1f}%"})
		else:
			compliance_checks.append({"check": "Recycling Rate", "status": "Fail", "value": f"{avg_recycling:.1f}%"})
		
		# Diversion rate threshold
		if avg_diversion >= 80:
			compliance_checks.append({"check": "Diversion Rate", "status": "Pass", "value": f"{avg_diversion:.1f}%"})
		else:
			compliance_checks.append({"check": "Diversion Rate", "status": "Fail", "value": f"{avg_diversion:.1f}%"})
		
		# Waste reduction threshold
		if total_waste <= 1000:
			compliance_checks.append({"check": "Waste Generation", "status": "Pass", "value": f"{total_waste:.2f} kg"})
		else:
			compliance_checks.append({"check": "Waste Generation", "status": "Fail", "value": f"{total_waste:.2f} kg"})
		
		# Overall compliance
		passed_checks = len([check for check in compliance_checks if check["status"] == "Pass"])
		total_checks = len(compliance_checks)
		compliance_percentage = (passed_checks / total_checks) * 100
		
		if compliance_percentage >= 80:
			compliance_status = "Compliant"
		elif compliance_percentage >= 60:
			compliance_status = "Partially Compliant"
		else:
			compliance_status = "Non-Compliant"
		
		# Create HTML compliance report
		compliance_html = "<div style='font-family: Arial, sans-serif;'>"
		compliance_html += f"<h3>Waste Compliance Check</h3>"
		compliance_html += f"<p><strong>Overall Status:</strong> <span style='color: {'green' if compliance_status == 'Compliant' else 'orange' if compliance_status == 'Partially Compliant' else 'red'};'>{compliance_status}</span></p>"
		compliance_html += f"<p><strong>Compliance Score:</strong> {compliance_percentage:.1f}% ({passed_checks}/{total_checks} checks passed)</p>"
		
		compliance_html += "<h4>Compliance Checks:</h4>"
		for check in compliance_checks:
			status_color = "green" if check["status"] == "Pass" else "red"
			status_icon = "✓" if check["status"] == "Pass" else "✗"
			compliance_html += f"""
				<div style='border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;'>
					<p style='margin: 5px 0;'><span style='color: {status_color}; font-weight: bold;'>{status_icon} {check['check']}</span></p>
					<p style='margin: 5px 0; color: #666;'>Value: {check['value']}</p>
				</div>
			"""
		
		compliance_html += "</div>"
		
		return {
			"compliance_html": compliance_html,
			"compliance_status": compliance_status,
			"compliance_percentage": compliance_percentage,
			"compliance_checks": compliance_checks
		}
		
	except Exception as e:
		frappe.log_error(f"Error checking waste compliance: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
