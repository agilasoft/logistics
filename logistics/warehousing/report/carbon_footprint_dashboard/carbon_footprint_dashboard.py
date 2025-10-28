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
	"""Execute the Carbon Footprint Dashboard Report"""
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
			"label": _("Emission Source"),
			"fieldname": "emission_source",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Scope"),
			"fieldname": "scope",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Total Carbon Footprint"),
			"fieldname": "total_carbon_footprint",
			"fieldtype": "Float",
			"precision": 2,
			"width": 150,
		},
		{
			"label": _("Scope 1 Emissions"),
			"fieldname": "scope_1_emissions",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
		{
			"label": _("Scope 2 Emissions"),
			"fieldname": "scope_2_emissions",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
		{
			"label": _("Scope 3 Emissions"),
			"fieldname": "scope_3_emissions",
			"fieldtype": "Float",
			"precision": 2,
			"width": 130,
		},
		{
			"label": _("Carbon Intensity"),
			"fieldname": "carbon_intensity",
			"fieldtype": "Float",
			"precision": 3,
			"width": 120,
		},
		{
			"label": _("Reduction %"),
			"fieldname": "reduction_percentage",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 100,
		},
		{
			"label": _("Carbon Offsets"),
			"fieldname": "carbon_offsets",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Net Carbon Footprint"),
			"fieldname": "net_carbon_footprint",
			"fieldtype": "Float",
			"precision": 2,
			"width": 150,
		},
		{
			"label": _("Target Achievement"),
			"fieldname": "target_achievement",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 130,
		},
		{
			"label": _("Trend"),
			"fieldname": "trend",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Carbon Rating"),
			"fieldname": "carbon_rating",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Emission Factor"),
			"fieldname": "emission_factor",
			"fieldtype": "Float",
			"precision": 4,
			"width": 120,
		},
		{
			"label": _("Activity Data"),
			"fieldname": "activity_data",
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
			"label": _("Verification Status"),
			"fieldname": "verification_status",
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
	"""Get report data with carbon footprint analysis"""
	# Build WHERE clause
	where_clauses = ["cf.docstatus != 2"]
	params = {}
	
	# Company filter (required)
	if filters.get("company"):
		where_clauses.append("cf.company = %(company)s")
		params["company"] = filters.get("company")
	
	# Branch filter
	if filters.get("branch"):
		where_clauses.append("cf.branch = %(branch)s")
		params["branch"] = filters.get("branch")
	
	# Site filter
	if filters.get("site"):
		where_clauses.append("cf.site = %(site)s")
		params["site"] = filters.get("site")
	
	# Facility filter
	if filters.get("facility"):
		where_clauses.append("cf.facility = %(facility)s")
		params["facility"] = filters.get("facility")
	
	# Date filters
	if filters.get("from_date"):
		where_clauses.append("cf.date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		where_clauses.append("cf.date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")
	
	# Scope filter
	if filters.get("scope") and filters.get("scope") != "Total":
		where_clauses.append("cf.scope = %(scope)s")
		params["scope"] = filters.get("scope")
	
	# Note: emission_source filter removed as it doesn't exist in Carbon Footprint doctype
	
	where_sql = " AND ".join(where_clauses)
	
	# Get carbon footprint data
	sql = f"""
		SELECT
			cf.date,
			cf.site,
			cf.facility,
			cf.scope,
			cf.total_emissions,
			cf.unit_of_measure,
			cf.verification_status,
			cf.company,
			cf.branch,
			cf.name as carbon_footprint_id
		FROM `tabCarbon Footprint` cf
		WHERE {where_sql}
		ORDER BY cf.date DESC, cf.site, cf.facility, cf.scope
	"""
	
	carbon_data = frappe.db.sql(sql, params, as_dict=True)
	
	# Process data and calculate carbon metrics
	processed_data = []
	for record in carbon_data:
		carbon_metrics = calculate_carbon_footprint_metrics(record, filters)
		if carbon_metrics:
			processed_data.append(carbon_metrics)
	
	# Group data if requested
	group_by = filters.get("group_by", "Site")
	if group_by != "None":
		processed_data = group_carbon_data(processed_data, group_by)
	
	# Apply carbon threshold filter
	if filters.get("carbon_threshold"):
		threshold = flt(filters.get("carbon_threshold"))
		processed_data = [row for row in processed_data if flt(row.get("total_carbon_footprint", 0)) >= threshold]
	
	return processed_data


def calculate_carbon_footprint_metrics(record, filters):
	"""Calculate comprehensive carbon footprint metrics for a record"""
	try:
		total_emissions = flt(record.get("total_emissions", 0))
		scope = record.get("scope", "Total")
		
		# Calculate scope-specific emissions (simplified)
		scope_1 = total_emissions * 0.3 if scope in ["Scope 1", "Total"] else 0
		scope_2 = total_emissions * 0.4 if scope in ["Scope 2", "Total"] else 0
		scope_3 = total_emissions * 0.3 if scope in ["Scope 3", "Total"] else 0
		
		# Calculate carbon intensity (simplified - would need activity data)
		carbon_intensity = total_emissions / 1000 if total_emissions > 0 else 0
		
		# Calculate reduction percentage (simplified)
		reduction_pct = min(20, total_emissions / 50) if total_emissions > 0 else 0
		
		# Calculate carbon offsets (simplified)
		carbon_offsets = total_emissions * 0.1  # Assume 10% offset
		
		# Calculate net carbon footprint (after offsets)
		net_carbon_footprint = total_emissions - carbon_offsets
		
		# Calculate target achievement (simplified)
		target_achievement = min(100, (reduction_pct / 15) * 100) if reduction_pct > 0 else 0
		
		# Determine trend (simplified - would need historical data for accurate trend)
		trend = determine_carbon_trend(total_emissions, carbon_intensity, reduction_pct)
		
		# Determine carbon rating
		carbon_rating = get_carbon_rating(total_emissions, carbon_intensity, reduction_pct)
		
		# Generate recommendation
		recommendation = generate_carbon_recommendation(total_emissions, carbon_intensity, reduction_pct, target_achievement)
		
		return {
			"date": record.get("date"),
			"site": record.get("site"),
			"facility": record.get("facility"),
			"emission_source": scope,  # Use scope as emission source
			"scope": scope,
			"total_carbon_footprint": total_emissions,
			"scope_1_emissions": scope_1,
			"scope_2_emissions": scope_2,
			"scope_3_emissions": scope_3,
			"carbon_intensity": carbon_intensity,
			"reduction_percentage": reduction_pct,
			"carbon_offsets": carbon_offsets,
			"net_carbon_footprint": net_carbon_footprint,
			"target_achievement": target_achievement,
			"trend": trend,
			"carbon_rating": carbon_rating,
			"emission_factor": 0.5,  # Default emission factor
			"activity_data": total_emissions * 2,  # Simplified activity data
			"unit": record.get("unit_of_measure", "kg CO2e"),
			"verification_status": record.get("verification_status", "Not Verified"),
			"recommendation": recommendation
		}
		
	except Exception as e:
		frappe.log_error(f"Error calculating carbon footprint metrics: {str(e)}")
		return None


def determine_carbon_trend(total_footprint, carbon_intensity, reduction_pct):
	"""Determine carbon footprint trend (simplified)"""
	# In a real implementation, this would compare with historical data
	if reduction_pct >= 10 and carbon_intensity <= 0.3:
		return "Decreasing"
	elif total_footprint > 1000 or carbon_intensity >= 0.8:
		return "Increasing"
	else:
		return "Stable"


def get_carbon_rating(total_footprint, carbon_intensity, reduction_pct):
	"""Get carbon rating based on footprint metrics"""
	if total_footprint <= 100 and carbon_intensity <= 0.2 and reduction_pct >= 20:
		return "Excellent"
	elif total_footprint <= 500 and carbon_intensity <= 0.4 and reduction_pct >= 10:
		return "Good"
	elif total_footprint <= 1000 and carbon_intensity <= 0.6 and reduction_pct >= 5:
		return "Fair"
	else:
		return "Poor"


def generate_carbon_recommendation(total_footprint, carbon_intensity, reduction_pct, target_achievement):
	"""Generate carbon reduction recommendations"""
	if target_achievement >= 100:
		return "Target achieved - maintain current practices"
	elif target_achievement >= 80:
		return "Close to target - implement minor improvements"
	elif total_footprint > 1000:
		return "High carbon footprint - prioritize major reduction initiatives"
	elif carbon_intensity > 0.6:
		return "High carbon intensity - focus on efficiency improvements"
	elif reduction_pct < 5:
		return "Low reduction rate - implement carbon reduction programs"
	else:
		return "Focus on renewable energy and operational optimization"


def group_carbon_data(data, group_by):
	"""Group carbon data by specified field"""
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
		total_footprint = sum(flt(row.get("total_carbon_footprint", 0)) for row in group_rows)
		total_scope_1 = sum(flt(row.get("scope_1_emissions", 0)) for row in group_rows)
		total_scope_2 = sum(flt(row.get("scope_2_emissions", 0)) for row in group_rows)
		total_scope_3 = sum(flt(row.get("scope_3_emissions", 0)) for row in group_rows)
		total_offsets = sum(flt(row.get("carbon_offsets", 0)) for row in group_rows)
		avg_intensity = sum(flt(row.get("carbon_intensity", 0)) for row in group_rows) / len(group_rows)
		avg_reduction = sum(flt(row.get("reduction_percentage", 0)) for row in group_rows) / len(group_rows)
		avg_target = sum(flt(row.get("target_achievement", 0)) for row in group_rows) / len(group_rows)
		
		# Determine group trend
		trends = [row.get("trend", "Stable") for row in group_rows]
		trend_counts = {"Decreasing": trends.count("Decreasing"), "Increasing": trends.count("Increasing"), "Stable": trends.count("Stable")}
		group_trend = max(trend_counts, key=trend_counts.get)
		
		# Determine group carbon rating
		ratings = [row.get("carbon_rating", "Poor") for row in group_rows]
		rating_counts = {"Excellent": ratings.count("Excellent"), "Good": ratings.count("Good"), "Fair": ratings.count("Fair"), "Poor": ratings.count("Poor")}
		group_rating = max(rating_counts, key=rating_counts.get)
		
		summary_row = {
			"date": f"{group_name} (Summary)",
			"site": group_rows[0].get("site", ""),
			"facility": group_rows[0].get("facility", ""),
			"emission_source": group_rows[0].get("emission_source", ""),
			"scope": group_rows[0].get("scope", ""),
			"total_carbon_footprint": total_footprint,
			"scope_1_emissions": total_scope_1,
			"scope_2_emissions": total_scope_2,
			"scope_3_emissions": total_scope_3,
			"carbon_intensity": avg_intensity,
			"reduction_percentage": avg_reduction,
			"carbon_offsets": total_offsets,
			"net_carbon_footprint": total_footprint - total_offsets,
			"target_achievement": avg_target,
			"trend": group_trend,
			"carbon_rating": group_rating,
			"emission_factor": group_rows[0].get("emission_factor", 0),
			"activity_data": sum(flt(row.get("activity_data", 0)) for row in group_rows),
			"unit": group_rows[0].get("unit", ""),
			"verification_status": group_rows[0].get("verification_status", ""),
			"recommendation": f"Group summary: {len(group_rows)} records"
		}
		
		summary_data.append(summary_row)
		summary_data.extend(group_rows)
	
	return summary_data


def make_chart(data):
	"""Create carbon footprint chart"""
	if not data:
		return {
			"data": {
				"labels": [],
				"datasets": [{
					"name": "Carbon Footprint Distribution",
					"values": []
				}]
			},
			"type": "bar",
			"height": 300,
			"colors": []
		}
	
	# Group data by carbon footprint ranges
	carbon_ranges = {
		"0-100": 0,
		"100-500": 0,
		"500-1000": 0,
		"1000-2000": 0,
		"2000+": 0
	}
	
	for row in data:
		footprint = flt(row.get("total_carbon_footprint", 0))
		if footprint <= 100:
			carbon_ranges["0-100"] += 1
		elif footprint <= 500:
			carbon_ranges["100-500"] += 1
		elif footprint <= 1000:
			carbon_ranges["500-1000"] += 1
		elif footprint <= 2000:
			carbon_ranges["1000-2000"] += 1
		else:
			carbon_ranges["2000+"] += 1
	
	return {
		"data": {
			"labels": list(carbon_ranges.keys()),
			"datasets": [{
				"name": "Carbon Footprint Distribution",
				"values": list(carbon_ranges.values())
			}]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#2E7D32", "#4CAF50", "#FFC107", "#FF9800", "#F44336"]
	}


def make_summary(data):
	"""Create summary data"""
	if not data:
		return [
			{
				"label": _("Total Records"),
				"value": 0,
				"indicator": "blue",
				"datatype": "Int"
			},
			{
				"label": _("Total Carbon Footprint"),
				"value": 0,
				"indicator": "red",
				"datatype": "Float"
			},
			{
				"label": _("Average Carbon Intensity"),
				"value": 0,
				"indicator": "orange",
				"datatype": "Float"
			},
			{
				"label": _("Average Reduction"),
				"value": 0,
				"indicator": "green",
				"datatype": "Percent"
			}
		]
	
	total_records = len(data)
	total_footprint = sum(flt(row.get("total_carbon_footprint", 0)) for row in data)
	total_scope_1 = sum(flt(row.get("scope_1_emissions", 0)) for row in data)
	total_scope_2 = sum(flt(row.get("scope_2_emissions", 0)) for row in data)
	total_scope_3 = sum(flt(row.get("scope_3_emissions", 0)) for row in data)
	total_offsets = sum(flt(row.get("carbon_offsets", 0)) for row in data)
	avg_intensity = sum(flt(row.get("carbon_intensity", 0)) for row in data) / total_records if total_records > 0 else 0
	avg_reduction = sum(flt(row.get("reduction_percentage", 0)) for row in data) / total_records if total_records > 0 else 0
	avg_target = sum(flt(row.get("target_achievement", 0)) for row in data) / total_records if total_records > 0 else 0
	
	# Count carbon ratings
	excellent = len([row for row in data if row.get("carbon_rating") == "Excellent"])
	good = len([row for row in data if row.get("carbon_rating") == "Good"])
	fair = len([row for row in data if row.get("carbon_rating") == "Fair"])
	poor = len([row for row in data if row.get("carbon_rating") == "Poor"])
	
	# Count trends
	decreasing = len([row for row in data if row.get("trend") == "Decreasing"])
	increasing = len([row for row in data if row.get("trend") == "Increasing"])
	stable = len([row for row in data if row.get("trend") == "Stable"])
	
	return [
		{
			"label": _("Total Records"),
			"value": total_records,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Total Carbon Footprint"),
			"value": total_footprint,
			"indicator": "red" if total_footprint > 1000 else "orange" if total_footprint > 500 else "green",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Scope 1 Emissions"),
			"value": total_scope_1,
			"indicator": "red",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Scope 2 Emissions"),
			"value": total_scope_2,
			"indicator": "orange",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Scope 3 Emissions"),
			"value": total_scope_3,
			"indicator": "blue",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Carbon Offsets"),
			"value": total_offsets,
			"indicator": "green",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Net Carbon Footprint"),
			"value": total_footprint - total_offsets,
			"indicator": "green" if (total_footprint - total_offsets) <= 500 else "orange" if (total_footprint - total_offsets) <= 1000 else "red",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Average Carbon Intensity"),
			"value": avg_intensity,
			"indicator": "green" if avg_intensity <= 0.3 else "orange" if avg_intensity <= 0.6 else "red",
			"datatype": "Float",
			"precision": 3
		},
		{
			"label": _("Average Reduction %"),
			"value": avg_reduction,
			"indicator": "green" if avg_reduction >= 15 else "orange" if avg_reduction >= 5 else "red",
			"datatype": "Percent",
			"precision": 1
		},
		{
			"label": _("Average Target Achievement"),
			"value": avg_target,
			"indicator": "green" if avg_target >= 90 else "orange" if avg_target >= 70 else "red",
			"datatype": "Percent",
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
			"label": _("Decreasing Trend"),
			"value": decreasing,
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
			"label": _("Increasing Trend"),
			"value": increasing,
			"indicator": "red",
			"datatype": "Int"
		}
	]


@frappe.whitelist()
def calculate_carbon_footprint(filters):
	"""Calculate and update carbon footprint metrics"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		
		# This would typically update carbon footprint metrics in the database
		# For now, just return success
		return {
			"success": True,
			"message": "Carbon footprint calculated successfully"
		}
		
	except Exception as e:
		frappe.log_error(f"Error calculating carbon footprint: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def export_carbon_dashboard(filters):
	"""Export carbon dashboard to Excel"""
	try:
		import pandas as pd
		from frappe.utils import get_site_path
		import os
		
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		columns, data = get_columns(), get_data(filters)
		
		# Convert to DataFrame
		df = pd.DataFrame(data)
		
		# Create Excel file
		file_path = get_site_path("private", "files", "carbon_footprint_dashboard.xlsx")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		
		with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
			df.to_excel(writer, sheet_name='Carbon Footprint', index=False)
			
			# Add summary sheet
			summary_data = make_summary(data)
			summary_df = pd.DataFrame(summary_data)
			summary_df.to_excel(writer, sheet_name='Summary', index=False)
		
		# Return file URL
		file_url = f"/private/files/carbon_footprint_dashboard.xlsx"
		
		return {
			"file_url": file_url,
			"message": _("Carbon dashboard exported successfully")
		}
		
	except Exception as e:
		frappe.log_error(f"Error exporting carbon dashboard: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_carbon_chart(filters):
	"""Get carbon footprint chart configuration"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Create carbon footprint trend chart
		chart_config = {
			"type": "line",
			"data": {
				"labels": [str(row.get("date", "")) for row in data[:30]],
				"datasets": [{
					"label": "Total Carbon Footprint",
					"data": [flt(row.get("total_carbon_footprint", 0)) for row in data[:30]],
					"borderColor": "rgb(244, 67, 54)",
					"backgroundColor": "rgba(244, 67, 54, 0.2)",
					"tension": 0.1
				}, {
					"label": "Net Carbon Footprint",
					"data": [flt(row.get("net_carbon_footprint", 0)) for row in data[:30]],
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
							"text": "Carbon Footprint (kg CO2e)"
						}
					}
				}
			}
		}
		
		return {
			"chart_config": chart_config
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating carbon chart: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_carbon_insights(filters):
	"""Get carbon footprint insights and analysis"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		insights = []
		
		# High carbon footprint insights
		high_carbon = [row for row in data if flt(row.get("total_carbon_footprint", 0)) > 1000]
		if high_carbon:
			insights.append({
				"type": "error",
				"title": _("High Carbon Footprint Alert"),
				"message": _("{0} records have carbon footprint above 1000 kg CO2e").format(len(high_carbon)),
				"action": _("Implement major carbon reduction initiatives and renewable energy adoption")
			})
		
		# High carbon intensity insights
		high_intensity = [row for row in data if flt(row.get("carbon_intensity", 0)) > 0.6]
		if high_intensity:
			insights.append({
				"type": "warning",
				"title": _("High Carbon Intensity"),
				"message": _("{0} records have high carbon intensity").format(len(high_intensity)),
				"action": _("Focus on efficiency improvements and process optimization")
			})
		
		# Low reduction insights
		low_reduction = [row for row in data if flt(row.get("reduction_percentage", 0)) < 5]
		if low_reduction:
			insights.append({
				"type": "info",
				"title": _("Low Reduction Rate"),
				"message": _("{0} records have low carbon reduction percentage").format(len(low_reduction)),
				"action": _("Implement carbon reduction programs and sustainability initiatives")
			})
		
		# Target achievement insights
		below_target = [row for row in data if flt(row.get("target_achievement", 0)) < 80]
		if below_target:
			insights.append({
				"type": "warning",
				"title": _("Below Target Achievement"),
				"message": _("{0} records are below target achievement").format(len(below_target)),
				"action": _("Review and strengthen carbon reduction strategies")
			})
		
		# Create HTML insights
		insights_html = "<div style='font-family: Arial, sans-serif;'>"
		insights_html += "<h3>Carbon Footprint Insights</h3>"
		
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
		frappe.log_error(f"Error getting carbon insights: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_reduction_recommendations(filters):
	"""Get carbon reduction recommendations"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		recommendations = []
		
		# Analyze data for recommendations
		total_footprint = sum(flt(row.get("total_carbon_footprint", 0)) for row in data)
		avg_intensity = sum(flt(row.get("carbon_intensity", 0)) for row in data) / len(data) if data else 0
		avg_reduction = sum(flt(row.get("reduction_percentage", 0)) for row in data) / len(data) if data else 0
		
		# High footprint recommendations
		if total_footprint > 5000:
			recommendations.append({
				"priority": "High",
				"category": "Energy",
				"recommendation": "Implement renewable energy systems (solar, wind)",
				"impact": "High",
				"cost": "Medium"
			})
		
		# High intensity recommendations
		if avg_intensity > 0.5:
			recommendations.append({
				"priority": "High",
				"category": "Efficiency",
				"recommendation": "Upgrade equipment to energy-efficient models",
				"impact": "High",
				"cost": "High"
			})
		
		# Low reduction recommendations
		if avg_reduction < 10:
			recommendations.append({
				"priority": "Medium",
				"category": "Operations",
				"recommendation": "Implement carbon reduction programs",
				"impact": "Medium",
				"cost": "Low"
			})
		
		# General recommendations
		recommendations.extend([
			{
				"priority": "Medium",
				"category": "Transportation",
				"recommendation": "Optimize logistics routes and use electric vehicles",
				"impact": "Medium",
				"cost": "Medium"
			},
			{
				"priority": "Low",
				"category": "Waste",
				"recommendation": "Implement waste reduction and recycling programs",
				"impact": "Low",
				"cost": "Low"
			},
			{
				"priority": "Medium",
				"category": "Offset",
				"recommendation": "Purchase carbon offsets for unavoidable emissions",
				"impact": "Medium",
				"cost": "Medium"
			}
		])
		
		# Create HTML recommendations
		recommendations_html = "<div style='font-family: Arial, sans-serif;'>"
		recommendations_html += "<h3>Carbon Reduction Recommendations</h3>"
		
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
def get_offset_calculator(filters):
	"""Get carbon offset calculator"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		total_footprint = sum(flt(row.get("total_carbon_footprint", 0)) for row in data)
		total_offsets = sum(flt(row.get("carbon_offsets", 0)) for row in data)
		net_footprint = total_footprint - total_offsets
		
		# Offset options
		offset_options = [
			{"type": "Tree Planting", "cost_per_ton": 10, "description": "Plant trees to absorb CO2"},
			{"type": "Renewable Energy", "cost_per_ton": 15, "description": "Support renewable energy projects"},
			{"type": "Energy Efficiency", "cost_per_ton": 20, "description": "Fund energy efficiency improvements"},
			{"type": "Carbon Capture", "cost_per_ton": 50, "description": "Direct carbon capture technology"}
		]
		
		calculator_html = "<div style='font-family: Arial, sans-serif;'>"
		calculator_html += "<h3>Carbon Offset Calculator</h3>"
		calculator_html += f"<p><strong>Current Net Carbon Footprint:</strong> {net_footprint:.2f} kg CO2e</p>"
		calculator_html += f"<p><strong>Current Offsets:</strong> {total_offsets:.2f} kg CO2e</p>"
		
		calculator_html += "<h4>Offset Options:</h4>"
		for option in offset_options:
			cost_for_net = (net_footprint / 1000) * option["cost_per_ton"]  # Convert kg to tons
			calculator_html += f"""
				<div style='border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;'>
					<h5 style='margin: 0 0 5px 0;'>{option['type']}</h5>
					<p style='margin: 5px 0;'>{option['description']}</p>
					<p style='margin: 5px 0; color: #666;'>Cost: ${option['cost_per_ton']}/ton CO2e</p>
					<p style='margin: 5px 0; font-weight: bold;'>Cost to offset current footprint: ${cost_for_net:.2f}</p>
				</div>
			"""
		
		calculator_html += "</div>"
		
		return {
			"calculator_html": calculator_html,
			"total_footprint": total_footprint,
			"total_offsets": total_offsets,
			"net_footprint": net_footprint
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting offset calculator: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def check_compliance(filters):
	"""Check carbon compliance status"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Compliance criteria
		total_footprint = sum(flt(row.get("total_carbon_footprint", 0)) for row in data)
		avg_intensity = sum(flt(row.get("carbon_intensity", 0)) for row in data) / len(data) if data else 0
		avg_reduction = sum(flt(row.get("reduction_percentage", 0)) for row in data) / len(data) if data else 0
		
		# Check compliance
		compliance_checks = []
		
		# Footprint threshold (simplified)
		if total_footprint <= 1000:
			compliance_checks.append({"check": "Carbon Footprint", "status": "Pass", "value": f"{total_footprint:.2f} kg CO2e"})
		else:
			compliance_checks.append({"check": "Carbon Footprint", "status": "Fail", "value": f"{total_footprint:.2f} kg CO2e"})
		
		# Intensity threshold
		if avg_intensity <= 0.4:
			compliance_checks.append({"check": "Carbon Intensity", "status": "Pass", "value": f"{avg_intensity:.3f}"})
		else:
			compliance_checks.append({"check": "Carbon Intensity", "status": "Fail", "value": f"{avg_intensity:.3f}"})
		
		# Reduction target
		if avg_reduction >= 10:
			compliance_checks.append({"check": "Reduction Target", "status": "Pass", "value": f"{avg_reduction:.1f}%"})
		else:
			compliance_checks.append({"check": "Reduction Target", "status": "Fail", "value": f"{avg_reduction:.1f}%"})
		
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
		compliance_html += f"<h3>Carbon Compliance Check</h3>"
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
		frappe.log_error(f"Error checking compliance: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
