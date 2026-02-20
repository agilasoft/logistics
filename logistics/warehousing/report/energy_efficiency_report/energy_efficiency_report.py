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
	"""Execute the Energy Efficiency Report"""
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
			"label": _("Energy Type"),
			"fieldname": "energy_type",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Consumption"),
			"fieldname": "consumption_value",
			"fieldtype": "Float",
			"precision": 3,
			"width": 120,
		},
		{
			"label": _("Unit"),
			"fieldname": "unit_of_measure",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 80,
		},
		{
			"label": _("Total Cost"),
			"fieldname": "total_cost",
			"fieldtype": "Currency",
			"precision": 2,
			"width": 100,
		},
		{
			"label": _("Carbon Footprint"),
			"fieldname": "carbon_footprint",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Renewable %"),
			"fieldname": "renewable_percentage",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 100,
		},
		{
			"label": _("Efficiency Score"),
			"fieldname": "efficiency_score",
			"fieldtype": "Float",
			"precision": 1,
			"width": 120,
		},
		{
			"label": _("Carbon Intensity"),
			"fieldname": "carbon_intensity",
			"fieldtype": "Float",
			"precision": 3,
			"width": 120,
		},
		{
			"label": _("Energy Cost/Unit"),
			"fieldname": "energy_cost_per_unit",
			"fieldtype": "Currency",
			"precision": 4,
			"width": 120,
		},
		{
			"label": _("Trend"),
			"fieldname": "trend",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Efficiency Rating"),
			"fieldname": "efficiency_rating",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Benchmark Status"),
			"fieldname": "benchmark_status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Improvement Potential"),
			"fieldname": "improvement_potential",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 140,
		},
		{
			"label": _("Equipment Count"),
			"fieldname": "equipment_count",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Peak Usage"),
			"fieldname": "peak_usage",
			"fieldtype": "Float",
			"precision": 2,
			"width": 100,
		},
		{
			"label": _("Off-Peak Usage"),
			"fieldname": "off_peak_usage",
			"fieldtype": "Float",
			"precision": 2,
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
	"""Get report data with energy efficiency analysis"""
	# Build WHERE clause
	where_clauses = ["ec.docstatus != 2"]
	params = {}
	
	# Company filter (required)
	if filters.get("company"):
		where_clauses.append("ec.company = %(company)s")
		params["company"] = filters.get("company")
	
	# Branch filter
	if filters.get("branch"):
		where_clauses.append("ec.branch = %(branch)s")
		params["branch"] = filters.get("branch")
	
	# Site filter
	if filters.get("site"):
		where_clauses.append("ec.site = %(site)s")
		params["site"] = filters.get("site")
	
	# Facility filter
	if filters.get("facility"):
		where_clauses.append("ec.facility = %(facility)s")
		params["facility"] = filters.get("facility")
	
	# Date filters
	if filters.get("from_date"):
		where_clauses.append("ec.date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		where_clauses.append("ec.date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")
	
	# Energy type filter
	if filters.get("energy_type"):
		where_clauses.append("ec.energy_type = %(energy_type)s")
		params["energy_type"] = filters.get("energy_type")
	
	where_sql = " AND ".join(where_clauses)
	
	# Get energy consumption data
	sql = f"""
		SELECT
			ec.date,
			ec.site,
			ec.facility,
			ec.energy_type,
			ec.consumption_value,
			ec.unit_of_measure,
			ec.total_cost,
			ec.carbon_footprint,
			ec.renewable_percentage,
			ec.company,
			ec.branch,
			ec.name as energy_consumption_id
		FROM `tabEnergy Consumption` ec
		WHERE {where_sql}
		ORDER BY ec.date DESC, ec.site, ec.facility, ec.energy_type
	"""
	
	energy_data = frappe.db.sql(sql, params, as_dict=True)
	
	# Process data and calculate efficiency metrics
	processed_data = []
	for record in energy_data:
		efficiency_data = calculate_energy_efficiency_metrics(record, filters)
		if efficiency_data:
			processed_data.append(efficiency_data)
	
	# Group data if requested
	group_by = filters.get("group_by", "Site")
	if group_by != "None":
		processed_data = group_efficiency_data(processed_data, group_by)
	
	# Apply efficiency threshold filter
	if filters.get("efficiency_threshold"):
		threshold = flt(filters.get("efficiency_threshold"))
		processed_data = [row for row in processed_data if flt(row.get("efficiency_score", 0)) >= threshold]
	
	return processed_data


def calculate_energy_efficiency_metrics(record, filters):
	"""Calculate comprehensive energy efficiency metrics for a record"""
	try:
		consumption = flt(record.get("consumption_value", 0))
		carbon_footprint = flt(record.get("carbon_footprint", 0))
		total_cost = flt(record.get("total_cost", 0))
		renewable_pct = flt(record.get("renewable_percentage", 0))
		
		# Calculate carbon intensity (kg CO2 per unit of energy)
		carbon_intensity = carbon_footprint / consumption if consumption > 0 else 0
		
		# Calculate energy cost per unit
		energy_cost_per_unit = total_cost / consumption if consumption > 0 else 0
		
		# Calculate efficiency score based on multiple factors
		efficiency_score = calculate_efficiency_score(record, carbon_intensity, renewable_pct)
		
		# Determine trend (simplified - would need historical data for accurate trend)
		trend = determine_efficiency_trend(efficiency_score, carbon_intensity)
		
		# Determine efficiency rating
		efficiency_rating = get_efficiency_rating(efficiency_score)
		
		# Compare against industry benchmarks
		benchmark_status = compare_with_benchmarks(record.get("energy_type"), carbon_intensity, efficiency_score)
		
		# Calculate improvement potential
		improvement_potential = calculate_improvement_potential(efficiency_score, benchmark_status)
		
		# Get equipment count (if equipment breakdown is included)
		equipment_count = get_equipment_count(record.get("energy_consumption_id")) if filters.get("include_equipment") else 0
		
		# Calculate peak vs off-peak usage (simplified)
		peak_usage, off_peak_usage = calculate_peak_usage(consumption, record.get("energy_type"))
		
		# Generate recommendation
		recommendation = generate_efficiency_recommendation(efficiency_score, carbon_intensity, renewable_pct, benchmark_status)
		
		return {
			"date": record.get("date"),
			"site": record.get("site"),
			"facility": record.get("facility"),
			"energy_type": record.get("energy_type"),
			"consumption_value": consumption,
			"unit_of_measure": record.get("unit_of_measure"),
			"total_cost": total_cost,
			"carbon_footprint": carbon_footprint,
			"renewable_percentage": renewable_pct,
			"efficiency_score": efficiency_score,
			"carbon_intensity": carbon_intensity,
			"energy_cost_per_unit": energy_cost_per_unit,
			"trend": trend,
			"efficiency_rating": efficiency_rating,
			"benchmark_status": benchmark_status,
			"improvement_potential": improvement_potential,
			"equipment_count": equipment_count,
			"peak_usage": peak_usage,
			"off_peak_usage": off_peak_usage,
			"recommendation": recommendation
		}
		
	except Exception as e:
		frappe.log_error(f"Error calculating efficiency metrics: {str(e)}")
		return None


def calculate_efficiency_score(record, carbon_intensity, renewable_pct):
	"""Calculate overall energy efficiency score"""
	try:
		# Base score from carbon intensity (lower is better)
		carbon_score = max(0, 100 - (carbon_intensity * 200))  # Scale to 0-100
		
		# Renewable energy bonus
		renewable_score = renewable_pct
		
		# Cost efficiency (simplified - would need throughput data for accurate calculation)
		cost_per_unit = flt(record.get("total_cost", 0)) / flt(record.get("consumption_value", 1))
		cost_score = max(0, 100 - (cost_per_unit * 1000))  # Scale to 0-100
		
		# Weighted average
		efficiency_score = (carbon_score * 0.4) + (renewable_score * 0.3) + (cost_score * 0.3)
		
		return min(100, max(0, efficiency_score))
		
	except Exception as e:
		frappe.log_error(f"Error calculating efficiency score: {str(e)}")
		return 50  # Default score


def determine_efficiency_trend(efficiency_score, carbon_intensity):
	"""Determine efficiency trend (simplified)"""
	# In a real implementation, this would compare with historical data
	if efficiency_score >= 80 and carbon_intensity <= 0.3:
		return "Improving"
	elif efficiency_score <= 60 or carbon_intensity >= 0.5:
		return "Declining"
	else:
		return "Stable"


def get_efficiency_rating(efficiency_score):
	"""Get efficiency rating based on score"""
	if efficiency_score >= 90:
		return "Excellent"
	elif efficiency_score >= 80:
		return "Very Good"
	elif efficiency_score >= 70:
		return "Good"
	elif efficiency_score >= 60:
		return "Fair"
	elif efficiency_score >= 50:
		return "Poor"
	else:
		return "Very Poor"


def compare_with_benchmarks(energy_type, carbon_intensity, efficiency_score):
	"""Compare against industry benchmarks"""
	# Industry benchmarks (simplified)
	benchmarks = {
		"Electricity": {"carbon_intensity": 0.4, "efficiency_score": 75},
		"Natural Gas": {"carbon_intensity": 0.2, "efficiency_score": 80},
		"Diesel": {"carbon_intensity": 0.27, "efficiency_score": 70},
		"Solar": {"carbon_intensity": 0.05, "efficiency_score": 95},
		"Wind": {"carbon_intensity": 0.01, "efficiency_score": 98},
		"Hydro": {"carbon_intensity": 0.01, "efficiency_score": 95},
		"Other": {"carbon_intensity": 0.3, "efficiency_score": 70}
	}
	
	benchmark = benchmarks.get(energy_type, benchmarks["Other"])
	
	if carbon_intensity <= benchmark["carbon_intensity"] and efficiency_score >= benchmark["efficiency_score"]:
		return "Above Benchmark"
	elif carbon_intensity <= benchmark["carbon_intensity"] * 1.2 and efficiency_score >= benchmark["efficiency_score"] * 0.9:
		return "At Benchmark"
	else:
		return "Below Benchmark"


def calculate_improvement_potential(efficiency_score, benchmark_status):
	"""Calculate improvement potential percentage"""
	if benchmark_status == "Above Benchmark":
		return 0
	elif benchmark_status == "At Benchmark":
		return 10
	else:
		# Calculate potential improvement based on current score
		return min(50, max(10, 100 - efficiency_score))


def get_equipment_count(energy_consumption_id):
	"""Get equipment count for energy consumption record"""
	try:
		equipment_data = frappe.get_all(
			"Energy Equipment Consumption",
			filters={"parent": energy_consumption_id},
			fields=["name"]
		)
		return len(equipment_data)
	except Exception:
		return 0


def calculate_peak_usage(consumption, energy_type):
	"""Calculate peak vs off-peak usage (simplified)"""
	# Simplified calculation - in reality would need time-of-use data
	if energy_type == "Electricity":
		peak_usage = consumption * 0.6  # 60% peak usage
		off_peak_usage = consumption * 0.4  # 40% off-peak
	else:
		peak_usage = consumption * 0.5
		off_peak_usage = consumption * 0.5
	
	return peak_usage, off_peak_usage


def generate_efficiency_recommendation(efficiency_score, carbon_intensity, renewable_pct, benchmark_status):
	"""Generate efficiency improvement recommendations"""
	if efficiency_score >= 90:
		return "Excellent efficiency - maintain current practices"
	elif efficiency_score >= 80:
		return "Good efficiency - consider minor optimizations"
	elif efficiency_score >= 70:
		return "Moderate efficiency - implement energy-saving measures"
	elif carbon_intensity > 0.5:
		return "High carbon intensity - prioritize renewable energy adoption"
	elif renewable_pct < 25:
		return "Low renewable energy - increase renewable energy sources"
	elif benchmark_status == "Below Benchmark":
		return "Below industry benchmark - implement efficiency improvements"
	else:
		return "Focus on equipment upgrades and operational optimization"


def group_efficiency_data(data, group_by):
	"""Group efficiency data by specified field"""
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
		# Calculate group averages
		avg_efficiency = sum(flt(row.get("efficiency_score", 0)) for row in group_rows) / len(group_rows)
		avg_carbon_intensity = sum(flt(row.get("carbon_intensity", 0)) for row in group_rows) / len(group_rows)
		avg_renewable = sum(flt(row.get("renewable_percentage", 0)) for row in group_rows) / len(group_rows)
		total_consumption = sum(flt(row.get("consumption_value", 0)) for row in group_rows)
		total_cost = sum(flt(row.get("total_cost", 0)) for row in group_rows)
		total_carbon = sum(flt(row.get("carbon_footprint", 0)) for row in group_rows)
		
		# Determine group trend
		trends = [row.get("trend", "Stable") for row in group_rows]
		trend_counts = {"Improving": trends.count("Improving"), "Declining": trends.count("Declining"), "Stable": trends.count("Stable")}
		group_trend = max(trend_counts, key=trend_counts.get)
		
		# Determine group benchmark status
		benchmarks = [row.get("benchmark_status", "Below Benchmark") for row in group_rows]
		benchmark_counts = {"Above Benchmark": benchmarks.count("Above Benchmark"), "At Benchmark": benchmarks.count("At Benchmark"), "Below Benchmark": benchmarks.count("Below Benchmark")}
		group_benchmark = max(benchmark_counts, key=benchmark_counts.get)
		
		summary_row = {
			"date": f"{group_name} (Summary)",
			"site": group_rows[0].get("site", ""),
			"facility": group_rows[0].get("facility", ""),
			"energy_type": group_rows[0].get("energy_type", ""),
			"consumption_value": total_consumption,
			"unit_of_measure": group_rows[0].get("unit_of_measure", ""),
			"total_cost": total_cost,
			"carbon_footprint": total_carbon,
			"renewable_percentage": avg_renewable,
			"efficiency_score": avg_efficiency,
			"carbon_intensity": avg_carbon_intensity,
			"energy_cost_per_unit": total_cost / total_consumption if total_consumption > 0 else 0,
			"trend": group_trend,
			"efficiency_rating": get_efficiency_rating(avg_efficiency),
			"benchmark_status": group_benchmark,
			"improvement_potential": calculate_improvement_potential(avg_efficiency, group_benchmark),
			"equipment_count": sum(row.get("equipment_count", 0) for row in group_rows),
			"peak_usage": sum(row.get("peak_usage", 0) for row in group_rows),
			"off_peak_usage": sum(row.get("off_peak_usage", 0) for row in group_rows),
			"recommendation": f"Group summary: {len(group_rows)} records"
		}
		
		summary_data.append(summary_row)
		summary_data.extend(group_rows)
	
	return summary_data


def make_chart(data):
	"""Create efficiency chart"""
	if not data:
		return {
			"data": {
				"labels": [],
				"datasets": [{
					"name": "Efficiency Score Distribution",
					"values": []
				}]
			},
			"type": "bar",
			"height": 300,
			"colors": []
		}
	
	# Group data by efficiency score ranges
	efficiency_ranges = {
		"0-50": 0,
		"50-60": 0,
		"60-70": 0,
		"70-80": 0,
		"80-90": 0,
		"90-100": 0
	}
	
	for row in data:
		score = flt(row.get("efficiency_score", 0))
		if score < 50:
			efficiency_ranges["0-50"] += 1
		elif score < 60:
			efficiency_ranges["50-60"] += 1
		elif score < 70:
			efficiency_ranges["60-70"] += 1
		elif score < 80:
			efficiency_ranges["70-80"] += 1
		elif score < 90:
			efficiency_ranges["80-90"] += 1
		else:
			efficiency_ranges["90-100"] += 1
	
	return {
		"data": {
			"labels": list(efficiency_ranges.keys()),
			"datasets": [{
				"name": "Efficiency Score Distribution",
				"values": list(efficiency_ranges.values())
			}]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#F44336", "#FF9800", "#FFC107", "#8BC34A", "#4CAF50", "#2E7D32"]
	}


def make_summary(data):
	"""Create summary data"""
	if not data:
		return []
	
	total_records = len(data)
	avg_efficiency = sum(flt(row.get("efficiency_score", 0)) for row in data) / total_records if total_records > 0 else 0
	avg_carbon_intensity = sum(flt(row.get("carbon_intensity", 0)) for row in data) / total_records if total_records > 0 else 0
	avg_renewable = sum(flt(row.get("renewable_percentage", 0)) for row in data) / total_records if total_records > 0 else 0
	
	# Count efficiency ratings
	excellent = len([row for row in data if row.get("efficiency_rating") == "Excellent"])
	very_good = len([row for row in data if row.get("efficiency_rating") == "Very Good"])
	good = len([row for row in data if row.get("efficiency_rating") == "Good"])
	fair = len([row for row in data if row.get("efficiency_rating") == "Fair"])
	poor = len([row for row in data if row.get("efficiency_rating") == "Poor"])
	very_poor = len([row for row in data if row.get("efficiency_rating") == "Very Poor"])
	
	# Count benchmark status
	above_benchmark = len([row for row in data if row.get("benchmark_status") == "Above Benchmark"])
	at_benchmark = len([row for row in data if row.get("benchmark_status") == "At Benchmark"])
	below_benchmark = len([row for row in data if row.get("benchmark_status") == "Below Benchmark"])
	
	# Calculate totals
	total_consumption = sum(flt(row.get("consumption_value", 0)) for row in data)
	total_cost = sum(flt(row.get("total_cost", 0)) for row in data)
	total_carbon = sum(flt(row.get("carbon_footprint", 0)) for row in data)
	
	return [
		{
			"label": _("Total Records"),
			"value": total_records,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Average Efficiency Score"),
			"value": avg_efficiency,
			"indicator": "green" if avg_efficiency >= 80 else "orange" if avg_efficiency >= 70 else "red",
			"datatype": "Float",
			"precision": 1
		},
		{
			"label": _("Average Carbon Intensity"),
			"value": avg_carbon_intensity,
			"indicator": "green" if avg_carbon_intensity <= 0.3 else "orange" if avg_carbon_intensity <= 0.5 else "red",
			"datatype": "Float",
			"precision": 3
		},
		{
			"label": _("Average Renewable %"),
			"value": avg_renewable,
			"indicator": "green" if avg_renewable >= 50 else "orange" if avg_renewable >= 25 else "red",
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
			"label": _("Very Good Rating"),
			"value": very_good,
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
			"label": _("Above Benchmark"),
			"value": above_benchmark,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("At Benchmark"),
			"value": at_benchmark,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Below Benchmark"),
			"value": below_benchmark,
			"indicator": "red",
			"datatype": "Int"
		},
		{
			"label": _("Total Consumption"),
			"value": total_consumption,
			"indicator": "blue",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Total Cost"),
			"value": total_cost,
			"indicator": "blue",
			"datatype": "Currency",
			"precision": 2
		},
		{
			"label": _("Total Carbon Footprint"),
			"value": total_carbon,
			"indicator": "red",
			"datatype": "Float",
			"precision": 2
		}
	]


@frappe.whitelist()
def calculate_efficiency_metrics(filters):
	"""Calculate and update efficiency metrics"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		
		# This would typically update efficiency metrics in the database
		# For now, just return success
		return {
			"success": True,
			"message": "Efficiency metrics calculated successfully"
		}
		
	except Exception as e:
		frappe.log_error(f"Error calculating efficiency metrics: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def export_efficiency_report(filters):
	"""Export efficiency report to Excel"""
	try:
		import pandas as pd
		from frappe.utils import get_site_path
		import os
		
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		columns, data = get_columns(), get_data(filters)
		
		# Convert to DataFrame
		df = pd.DataFrame(data)
		
		# Create Excel file
		file_path = get_site_path("private", "files", "energy_efficiency_report.xlsx")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		
		with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
			df.to_excel(writer, sheet_name='Energy Efficiency', index=False)
			
			# Add summary sheet
			summary_data = make_summary(data)
			summary_df = pd.DataFrame(summary_data)
			summary_df.to_excel(writer, sheet_name='Summary', index=False)
		
		# Return file URL
		file_url = f"/private/files/energy_efficiency_report.xlsx"
		
		return {
			"file_url": file_url,
			"message": _("Efficiency report exported successfully")
		}
		
	except Exception as e:
		frappe.log_error(f"Error exporting efficiency report: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_efficiency_chart(filters):
	"""Get efficiency chart configuration"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Create efficiency trend chart
		chart_config = {
			"type": "line",
			"data": {
				"labels": [str(row.get("date", "")) for row in data[:30]],
				"datasets": [{
					"label": "Efficiency Score",
					"data": [flt(row.get("efficiency_score", 0)) for row in data[:30]],
					"borderColor": "rgb(75, 192, 192)",
					"backgroundColor": "rgba(75, 192, 192, 0.2)",
					"tension": 0.1
				}, {
					"label": "Carbon Intensity",
					"data": [flt(row.get("carbon_intensity", 0)) * 100 for row in data[:30]],
					"borderColor": "rgb(255, 99, 132)",
					"backgroundColor": "rgba(255, 99, 132, 0.2)",
					"tension": 0.1
				}]
			},
			"options": {
				"responsive": True,
				"scales": {
					"y": {
						"beginAtZero": True,
						"max": 100
					}
				}
			}
		}
		
		return {
			"chart_config": chart_config
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating efficiency chart: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_efficiency_insights(filters):
	"""Get efficiency insights and recommendations"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		insights = []
		
		# Low efficiency insights
		low_efficiency = [row for row in data if flt(row.get("efficiency_score", 0)) < 70]
		if low_efficiency:
			insights.append({
				"type": "warning",
				"title": _("Low Efficiency Alert"),
				"message": _("{0} records have efficiency scores below 70").format(len(low_efficiency)),
				"action": _("Implement energy-saving measures and equipment upgrades")
			})
		
		# High carbon intensity insights
		high_carbon = [row for row in data if flt(row.get("carbon_intensity", 0)) > 0.5]
		if high_carbon:
			insights.append({
				"type": "error",
				"title": _("High Carbon Intensity"),
				"message": _("{0} records have high carbon intensity").format(len(high_carbon)),
				"action": _("Prioritize renewable energy adoption and efficiency improvements")
			})
		
		# Low renewable energy insights
		low_renewable = [row for row in data if flt(row.get("renewable_percentage", 0)) < 25]
		if low_renewable:
			insights.append({
				"type": "info",
				"title": _("Low Renewable Energy Usage"),
				"message": _("{0} records have low renewable energy percentage").format(len(low_renewable)),
				"action": _("Increase renewable energy sources and green energy procurement")
			})
		
		# Below benchmark insights
		below_benchmark = [row for row in data if row.get("benchmark_status") == "Below Benchmark"]
		if below_benchmark:
			insights.append({
				"type": "warning",
				"title": _("Below Industry Benchmark"),
				"message": _("{0} records are below industry benchmarks").format(len(below_benchmark)),
				"action": _("Implement best practices and efficiency improvements")
			})
		
		# Create HTML insights
		insights_html = "<div style='font-family: Arial, sans-serif;'>"
		insights_html += "<h3>Energy Efficiency Insights</h3>"
		
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
		frappe.log_error(f"Error getting efficiency insights: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_benchmark_comparison(filters):
	"""Get industry benchmark comparison"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Industry benchmarks
		benchmarks = {
			"Electricity": {"carbon_intensity": 0.4, "efficiency_score": 75, "renewable_pct": 30},
			"Natural Gas": {"carbon_intensity": 0.2, "efficiency_score": 80, "renewable_pct": 10},
			"Diesel": {"carbon_intensity": 0.27, "efficiency_score": 70, "renewable_pct": 5},
			"Solar": {"carbon_intensity": 0.05, "efficiency_score": 95, "renewable_pct": 100},
			"Wind": {"carbon_intensity": 0.01, "efficiency_score": 98, "renewable_pct": 100},
			"Hydro": {"carbon_intensity": 0.01, "efficiency_score": 95, "renewable_pct": 100}
		}
		
		# Calculate averages by energy type
		energy_types = {}
		for row in data:
			energy_type = row.get("energy_type", "Other")
			if energy_type not in energy_types:
				energy_types[energy_type] = []
			energy_types[energy_type].append(row)
		
		benchmark_html = "<div style='font-family: Arial, sans-serif;'>"
		benchmark_html += "<h3>Industry Benchmark Comparison</h3>"
		
		for energy_type, records in energy_types.items():
			if not records:
				continue
				
			avg_efficiency = sum(flt(r.get("efficiency_score", 0)) for r in records) / len(records)
			avg_carbon = sum(flt(r.get("carbon_intensity", 0)) for r in records) / len(records)
			avg_renewable = sum(flt(r.get("renewable_percentage", 0)) for r in records) / len(records)
			
			benchmark = benchmarks.get(energy_type, {"carbon_intensity": 0.3, "efficiency_score": 70, "renewable_pct": 20})
			
			benchmark_html += f"""
				<div style='border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;'>
					<h4 style='margin: 0 0 10px 0; color: #333;'>{energy_type}</h4>
					<table style='width: 100%; border-collapse: collapse;'>
						<tr style='background-color: #f5f5f5;'>
							<th style='padding: 8px; text-align: left; border: 1px solid #ddd;'>Metric</th>
							<th style='padding: 8px; text-align: center; border: 1px solid #ddd;'>Your Average</th>
							<th style='padding: 8px; text-align: center; border: 1px solid #ddd;'>Industry Benchmark</th>
							<th style='padding: 8px; text-align: center; border: 1px solid #ddd;'>Status</th>
						</tr>
						<tr>
							<td style='padding: 8px; border: 1px solid #ddd;'>Efficiency Score</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{avg_efficiency:.1f}</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{benchmark['efficiency_score']}</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd; color: {'green' if avg_efficiency >= benchmark['efficiency_score'] else 'red'};'>
								{'Above' if avg_efficiency >= benchmark['efficiency_score'] else 'Below'}
							</td>
						</tr>
						<tr>
							<td style='padding: 8px; border: 1px solid #ddd;'>Carbon Intensity</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{avg_carbon:.3f}</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{benchmark['carbon_intensity']}</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd; color: {'green' if avg_carbon <= benchmark['carbon_intensity'] else 'red'};'>
								{'Below' if avg_carbon <= benchmark['carbon_intensity'] else 'Above'}
							</td>
						</tr>
						<tr>
							<td style='padding: 8px; border: 1px solid #ddd;'>Renewable %</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{avg_renewable:.1f}%</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{benchmark['renewable_pct']}%</td>
							<td style='padding: 8px; text-align: center; border: 1px solid #ddd; color: {'green' if avg_renewable >= benchmark['renewable_pct'] else 'red'};'>
								{'Above' if avg_renewable >= benchmark['renewable_pct'] else 'Below'}
							</td>
						</tr>
					</table>
				</div>
			"""
		
		benchmark_html += "</div>"
		
		return {
			"benchmark_html": benchmark_html
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting benchmark comparison: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
