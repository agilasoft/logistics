# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months
from frappe.model.document import Document


def execute(filters=None):
	"""Execute sustainability report"""
	filters = frappe._dict(filters or {})
	
	# Set default filters
	if not filters.from_date:
		filters.from_date = add_months(getdate(), -12)
	if not filters.to_date:
		filters.to_date = getdate()
	
	# Get data based on filters
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "site",
			"label": _("Site"),
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 120
		},
		{
			"fieldname": "facility",
			"label": _("Facility"),
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 120
		},
		{
			"fieldname": "energy_consumption",
			"label": _("Energy Consumption"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "energy_unit",
			"label": _("Energy Unit"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "carbon_footprint",
			"label": _("Carbon Footprint (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "renewable_percentage",
			"label": _("Renewable %"),
			"fieldtype": "Percent",
			"precision": 1,
			"width": 100
		},
		{
			"fieldname": "energy_cost",
			"label": _("Energy Cost"),
			"fieldtype": "Currency",
			"precision": 2,
			"width": 100
		},
		{
			"fieldname": "efficiency_score",
			"label": _("Efficiency Score"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 120
		},
		{
			"fieldname": "sustainability_rating",
			"label": _("Sustainability Rating"),
			"fieldtype": "Data",
			"width": 150
		}
	]


def get_data(filters):
	"""Get report data"""
	
	# Build filters for energy consumption
	energy_filters = {}
	if filters.site:
		energy_filters["site"] = filters.site
	if filters.facility:
		energy_filters["facility"] = filters.facility
	if filters.energy_type:
		energy_filters["energy_type"] = filters.energy_type
	
	# Handle date range filtering
	if filters.from_date and filters.to_date:
		energy_filters["date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.from_date:
		energy_filters["date"] = [">=", filters.from_date]
	elif filters.to_date:
		energy_filters["date"] = ["<=", filters.to_date]
	
	# Get energy consumption data
	energy_data = frappe.get_all("Energy Consumption", 
		filters=energy_filters,
		fields=["date", "site", "facility", "energy_type", "consumption_value", 
				"unit_of_measure", "carbon_footprint", "renewable_percentage", 
				"total_cost"],
		order_by="date desc, site, facility"
	)
	
	# Get carbon footprint data
	carbon_filters = {}
	if filters.site:
		carbon_filters["site"] = filters.site
	if filters.facility:
		carbon_filters["facility"] = filters.facility
	if filters.scope:
		carbon_filters["scope"] = filters.scope
	
	# Handle date range filtering for carbon data
	if filters.from_date and filters.to_date:
		carbon_filters["date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.from_date:
		carbon_filters["date"] = [">=", filters.from_date]
	elif filters.to_date:
		carbon_filters["date"] = ["<=", filters.to_date]
	
	carbon_data = frappe.get_all("Carbon Footprint", 
		filters=carbon_filters,
		fields=["date", "site", "facility", "total_emissions", "scope"],
		order_by="date desc, site, facility"
	)
	
	# Combine data
	data = []
	
	for energy in energy_data:
		# Find corresponding carbon data
		carbon_record = None
		for carbon in carbon_data:
			if (carbon.date == energy.date and 
				carbon.site == energy.site and 
				carbon.facility == energy.facility):
				carbon_record = carbon
				break
		
		# Calculate efficiency score
		efficiency_score = calculate_efficiency_score(energy)
		
		# Calculate sustainability rating
		sustainability_rating = get_sustainability_rating(efficiency_score, energy.renewable_percentage)
		
		row = {
			"date": energy.date,
			"site": energy.site,
			"facility": energy.facility,
			"energy_consumption": energy.consumption_value,
			"energy_unit": energy.unit_of_measure,
			"carbon_footprint": energy.carbon_footprint,
			"renewable_percentage": energy.renewable_percentage,
			"energy_cost": energy.total_cost,
			"efficiency_score": efficiency_score,
			"sustainability_rating": sustainability_rating
		}
		
		data.append(row)
	
	# Add summary row
	if data:
		summary_row = calculate_summary_row(data)
		data.append(summary_row)
	
	return data


def calculate_efficiency_score(energy_record):
	"""Calculate efficiency score for energy record"""
	# Simplified efficiency calculation
	# In practice, this would be more complex
	
	base_score = 50
	
	# Adjust based on renewable percentage
	if energy_record.renewable_percentage:
		renewable_bonus = flt(energy_record.renewable_percentage) * 0.5
		base_score += renewable_bonus
	
	# Adjust based on carbon intensity
	if energy_record.consumption_value and energy_record.carbon_footprint:
		carbon_intensity = flt(energy_record.carbon_footprint) / flt(energy_record.consumption_value)
		if carbon_intensity < 0.3:  # Good carbon intensity
			base_score += 20
		elif carbon_intensity < 0.5:  # Average carbon intensity
			base_score += 10
	
	return min(base_score, 100)  # Cap at 100


def get_sustainability_rating(efficiency_score, renewable_percentage):
	"""Get sustainability rating based on efficiency score and renewable percentage"""
	
	# Weighted rating calculation
	renewable_weight = flt(renewable_percentage or 0) * 0.3
	efficiency_weight = efficiency_score * 0.7
	
	overall_score = renewable_weight + efficiency_weight
	
	if overall_score >= 90:
		return "Excellent"
	elif overall_score >= 80:
		return "Very Good"
	elif overall_score >= 70:
		return "Good"
	elif overall_score >= 60:
		return "Fair"
	elif overall_score >= 50:
		return "Poor"
	else:
		return "Very Poor"


def calculate_summary_row(data):
	"""Calculate summary row for the report"""
	if not data:
		return {}
	
	# Calculate totals and averages
	total_consumption = sum(flt(row.get("energy_consumption", 0)) for row in data)
	total_carbon = sum(flt(row.get("carbon_footprint", 0)) for row in data)
	total_cost = sum(flt(row.get("energy_cost", 0)) for row in data)
	avg_renewable = sum(flt(row.get("renewable_percentage", 0)) for row in data) / len(data)
	avg_efficiency = sum(flt(row.get("efficiency_score", 0)) for row in data) / len(data)
	
	# Calculate overall sustainability rating
	overall_rating = get_sustainability_rating(avg_efficiency, avg_renewable)
	
	return {
		"date": "TOTAL",
		"site": "",
		"facility": "",
		"energy_consumption": total_consumption,
		"energy_unit": "",
		"carbon_footprint": total_carbon,
		"renewable_percentage": avg_renewable,
		"energy_cost": total_cost,
		"efficiency_score": avg_efficiency,
		"sustainability_rating": overall_rating
	}
