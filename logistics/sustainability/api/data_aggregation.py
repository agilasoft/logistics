# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, add_months
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class SustainabilityDataAggregation:
	"""Centralized data aggregation service for sustainability metrics"""
	
	def __init__(self, company=None):
		self.company = company or frappe.defaults.get_user_default("Company")
	
	def aggregate_metrics_by_period(self, module=None, site=None, facility=None, 
								   from_date=None, to_date=None, period="monthly"):
		"""Aggregate sustainability metrics by time period"""
		if not from_date:
			from_date = add_months(getdate(), -12)
		if not to_date:
			to_date = getdate()
		
		filters = {
			"company": self.company,
			"date": [">=", from_date, "<=", to_date]
		}
		
		if module:
			filters["module"] = module
		if site:
			filters["site"] = site
		if facility:
			filters["facility"] = facility
		
		# Get all metrics
		metrics = frappe.get_all("Sustainability Metrics",
			filters=filters,
			fields=["*"],
			order_by="date asc"
		)
		
		# Group by period
		grouped_data = self._group_by_period(metrics, period)
		
		# Calculate aggregated values
		aggregated_data = []
		for period_key, period_metrics in grouped_data.items():
			aggregated = self._calculate_period_aggregates(period_metrics, period_key)
			aggregated_data.append(aggregated)
		
		return sorted(aggregated_data, key=lambda x: x["period_start"])
	
	def aggregate_metrics_by_module(self, from_date=None, to_date=None):
		"""Aggregate sustainability metrics by module"""
		if not from_date:
			from_date = add_months(getdate(), -12)
		if not to_date:
			to_date = getdate()
		
		filters = {
			"company": self.company,
			"date": [">=", from_date, "<=", to_date]
		}
		
		# Get all metrics
		metrics = frappe.get_all("Sustainability Metrics",
			filters=filters,
			fields=["*"],
			order_by="module, date asc"
		)
		
		# Group by module
		module_data = {}
		for metric in metrics:
			module = metric.module or "Unknown"
			if module not in module_data:
				module_data[module] = []
			module_data[module].append(metric)
		
		# Calculate aggregated values for each module
		aggregated_data = []
		for module, module_metrics in module_data.items():
			aggregated = self._calculate_module_aggregates(module_metrics, module)
			aggregated_data.append(aggregated)
		
		return aggregated_data
	
	def aggregate_metrics_by_facility(self, module=None, from_date=None, to_date=None):
		"""Aggregate sustainability metrics by facility"""
		if not from_date:
			from_date = add_months(getdate(), -12)
		if not to_date:
			to_date = getdate()
		
		filters = {
			"company": self.company,
			"date": [">=", from_date, "<=", to_date]
		}
		
		if module:
			filters["module"] = module
		
		# Get all metrics
		metrics = frappe.get_all("Sustainability Metrics",
			filters=filters,
			fields=["*"],
			order_by="facility, date asc"
		)
		
		# Group by facility
		facility_data = {}
		for metric in metrics:
			facility = metric.facility or "Unknown"
			if facility not in facility_data:
				facility_data[facility] = []
			facility_data[facility].append(metric)
		
		# Calculate aggregated values for each facility
		aggregated_data = []
		for facility, facility_metrics in facility_data.items():
			aggregated = self._calculate_facility_aggregates(facility_metrics, facility)
			aggregated_data.append(aggregated)
		
		return aggregated_data
	
	def get_cross_module_summary(self, from_date=None, to_date=None):
		"""Get cross-module sustainability summary"""
		if not from_date:
			from_date = add_months(getdate(), -12)
		if not to_date:
			to_date = getdate()
		
		# Get aggregated data by module
		module_data = self.aggregate_metrics_by_module(from_date, to_date)
		
		# Calculate cross-module summary
		summary = {
			"total_modules": len(module_data),
			"total_energy_consumption": 0,
			"total_carbon_footprint": 0,
			"total_waste_generated": 0,
			"total_water_consumption": 0,
			"average_sustainability_score": 0,
			"average_renewable_percentage": 0,
			"module_breakdown": {},
			"top_performing_module": None,
			"bottom_performing_module": None
		}
		
		if module_data:
			# Calculate totals
			for module in module_data:
				summary["total_energy_consumption"] += module.get("total_energy_consumption", 0)
				summary["total_carbon_footprint"] += module.get("total_carbon_footprint", 0)
				summary["total_waste_generated"] += module.get("total_waste_generated", 0)
				summary["total_water_consumption"] += module.get("total_water_consumption", 0)
				
				# Store module breakdown
				summary["module_breakdown"][module["module"]] = {
					"energy_consumption": module.get("total_energy_consumption", 0),
					"carbon_footprint": module.get("total_carbon_footprint", 0),
					"waste_generated": module.get("total_waste_generated", 0),
					"water_consumption": module.get("total_water_consumption", 0),
					"average_sustainability_score": module.get("average_sustainability_score", 0),
					"average_renewable_percentage": module.get("average_renewable_percentage", 0)
				}
			
			# Calculate averages
			summary["average_sustainability_score"] = sum(
				m.get("average_sustainability_score", 0) for m in module_data
			) / len(module_data)
			
			summary["average_renewable_percentage"] = sum(
				m.get("average_renewable_percentage", 0) for m in module_data
			) / len(module_data)
			
			# Find top and bottom performing modules
			sorted_modules = sorted(module_data, key=lambda x: x.get("average_sustainability_score", 0), reverse=True)
			summary["top_performing_module"] = sorted_modules[0]["module"] if sorted_modules else None
			summary["bottom_performing_module"] = sorted_modules[-1]["module"] if sorted_modules else None
		
		return summary
	
	def get_trend_analysis(self, module=None, site=None, facility=None, 
						  from_date=None, to_date=None, period="monthly"):
		"""Get trend analysis for sustainability metrics"""
		if not from_date:
			from_date = add_months(getdate(), -12)
		if not to_date:
			to_date = getdate()
		
		# Get aggregated data
		aggregated_data = self.aggregate_metrics_by_period(
			module, site, facility, from_date, to_date, period
		)
		
		if len(aggregated_data) < 2:
			return {"trends": [], "analysis": "Insufficient data for trend analysis"}
		
		# Calculate trends
		trends = []
		metrics_to_analyze = [
			"total_energy_consumption",
			"total_carbon_footprint",
			"total_waste_generated",
			"total_water_consumption",
			"average_sustainability_score",
			"average_renewable_percentage"
		]
		
		for metric in metrics_to_analyze:
			trend = self._calculate_trend(aggregated_data, metric)
			trends.append(trend)
		
		# Overall trend analysis
		analysis = self._analyze_overall_trends(trends)
		
		return {
			"trends": trends,
			"analysis": analysis,
			"period": period,
			"from_date": from_date,
			"to_date": to_date
		}
	
	def _group_by_period(self, metrics, period):
		"""Group metrics by time period"""
		grouped = {}
		
		for metric in metrics:
			date = metric.date
			
			if period == "daily":
				key = date.strftime("%Y-%m-%d")
			elif period == "weekly":
				# Get start of week (Monday)
				start_of_week = date - timedelta(days=date.weekday())
				key = start_of_week.strftime("%Y-%m-%d")
			elif period == "monthly":
				key = date.strftime("%Y-%m")
			elif period == "quarterly":
				quarter = (date.month - 1) // 3 + 1
				key = f"{date.year}-Q{quarter}"
			elif period == "yearly":
				key = str(date.year)
			else:
				key = date.strftime("%Y-%m-%d")
			
			if key not in grouped:
				grouped[key] = []
			grouped[key].append(metric)
		
		return grouped
	
	def _calculate_period_aggregates(self, metrics, period_key):
		"""Calculate aggregated values for a time period"""
		if not metrics:
			return {}
		
		# Calculate totals
		total_energy = sum(flt(m.energy_consumption) for m in metrics)
		total_carbon = sum(flt(m.carbon_footprint) for m in metrics)
		total_waste = sum(flt(m.waste_generated) for m in metrics)
		total_water = sum(flt(m.water_consumption) for m in metrics)
		
		# Calculate averages
		avg_sustainability = sum(flt(m.sustainability_score) for m in metrics) / len(metrics)
		avg_renewable = sum(flt(m.renewable_energy_percentage) for m in metrics) / len(metrics)
		
		# Get period start and end dates
		dates = [m.date for m in metrics]
		period_start = min(dates)
		period_end = max(dates)
		
		return {
			"period": period_key,
			"period_start": period_start,
			"period_end": period_end,
			"record_count": len(metrics),
			"total_energy_consumption": total_energy,
			"total_carbon_footprint": total_carbon,
			"total_waste_generated": total_waste,
			"total_water_consumption": total_water,
			"average_sustainability_score": avg_sustainability,
			"average_renewable_percentage": avg_renewable
		}
	
	def _calculate_module_aggregates(self, metrics, module):
		"""Calculate aggregated values for a module"""
		if not metrics:
			return {"module": module}
		
		# Calculate totals
		total_energy = sum(flt(m.energy_consumption) for m in metrics)
		total_carbon = sum(flt(m.carbon_footprint) for m in metrics)
		total_waste = sum(flt(m.waste_generated) for m in metrics)
		total_water = sum(flt(m.water_consumption) for m in metrics)
		
		# Calculate averages
		avg_sustainability = sum(flt(m.sustainability_score) for m in metrics) / len(metrics)
		avg_renewable = sum(flt(m.renewable_energy_percentage) for m in metrics) / len(metrics)
		
		return {
			"module": module,
			"record_count": len(metrics),
			"total_energy_consumption": total_energy,
			"total_carbon_footprint": total_carbon,
			"total_waste_generated": total_waste,
			"total_water_consumption": total_water,
			"average_sustainability_score": avg_sustainability,
			"average_renewable_percentage": avg_renewable
		}
	
	def _calculate_facility_aggregates(self, metrics, facility):
		"""Calculate aggregated values for a facility"""
		if not metrics:
			return {"facility": facility}
		
		# Calculate totals
		total_energy = sum(flt(m.energy_consumption) for m in metrics)
		total_carbon = sum(flt(m.carbon_footprint) for m in metrics)
		total_waste = sum(flt(m.waste_generated) for m in metrics)
		total_water = sum(flt(m.water_consumption) for m in metrics)
		
		# Calculate averages
		avg_sustainability = sum(flt(m.sustainability_score) for m in metrics) / len(metrics)
		avg_renewable = sum(flt(m.renewable_energy_percentage) for m in metrics) / len(metrics)
		
		return {
			"facility": facility,
			"record_count": len(metrics),
			"total_energy_consumption": total_energy,
			"total_carbon_footprint": total_carbon,
			"total_waste_generated": total_waste,
			"total_water_consumption": total_water,
			"average_sustainability_score": avg_sustainability,
			"average_renewable_percentage": avg_renewable
		}
	
	def _calculate_trend(self, data, metric):
		"""Calculate trend for a specific metric"""
		if len(data) < 2:
			return {
				"metric": metric,
				"trend": "insufficient_data",
				"change_percentage": 0,
				"direction": "stable"
			}
		
		# Get first and last values
		first_value = data[0].get(metric, 0)
		last_value = data[-1].get(metric, 0)
		
		if first_value == 0:
			change_percentage = 100 if last_value > 0 else 0
		else:
			change_percentage = ((last_value - first_value) / first_value) * 100
		
		# Determine direction
		if abs(change_percentage) < 5:
			direction = "stable"
		elif change_percentage > 0:
			direction = "increasing"
		else:
			direction = "decreasing"
		
		return {
			"metric": metric,
			"trend": direction,
			"change_percentage": change_percentage,
			"direction": direction,
			"first_value": first_value,
			"last_value": last_value
		}
	
	def _analyze_overall_trends(self, trends):
		"""Analyze overall trend patterns"""
		positive_trends = [t for t in trends if t["direction"] == "increasing" and t["metric"] in ["average_sustainability_score", "average_renewable_percentage"]]
		negative_trends = [t for t in trends if t["direction"] == "increasing" and t["metric"] in ["total_energy_consumption", "total_carbon_footprint", "total_waste_generated"]]
		
		if len(positive_trends) > len(negative_trends):
			return "Overall positive trend - sustainability metrics improving"
		elif len(negative_trends) > len(positive_trends):
			return "Overall negative trend - sustainability metrics declining"
		else:
			return "Mixed trends - some metrics improving, others declining"


# Convenience functions
@frappe.whitelist()
def get_data_aggregation(company=None):
	"""Get Sustainability Data Aggregation instance"""
	return SustainabilityDataAggregation(company)


@frappe.whitelist()
def aggregate_metrics_by_period(module=None, site=None, facility=None, from_date=None, to_date=None, period="monthly"):
	"""Aggregate sustainability metrics by time period"""
	aggregator = SustainabilityDataAggregation()
	return aggregator.aggregate_metrics_by_period(module, site, facility, from_date, to_date, period)


@frappe.whitelist()
def get_cross_module_summary(from_date=None, to_date=None):
	"""Get cross-module sustainability summary"""
	aggregator = SustainabilityDataAggregation()
	return aggregator.get_cross_module_summary(from_date, to_date)


@frappe.whitelist()
def get_trend_analysis(module=None, site=None, facility=None, from_date=None, to_date=None, period="monthly"):
	"""Get trend analysis for sustainability metrics"""
	aggregator = SustainabilityDataAggregation()
	return aggregator.get_trend_analysis(module, site, facility, from_date, to_date, period)
