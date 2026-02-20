# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days


def setup_sustainability():
	"""Setup sustainability module with default data"""
	create_default_emission_factors()
	create_default_sustainability_settings()
	create_sample_sustainability_goals()
	frappe.db.commit()


def create_default_emission_factors():
	"""Create default emission factors for various activities"""
	
	# Transport emission factors
	transport_factors = [
		{
			"factor_name": "Diesel Truck (per km)",
			"factor_value": 0.8,
			"unit_of_measure": "kg CO2e/km",
			"scope": "Scope 1",
			"category": "Transport",
			"module": "Transport",
			"source": "EPA",
			"description": "Diesel truck emissions per kilometer"
		},
		{
			"factor_name": "Diesel Truck (per ton-km)",
			"factor_value": 0.05,
			"unit_of_measure": "kg CO2e/ton-km",
			"scope": "Scope 1",
			"category": "Transport",
			"module": "Transport",
			"source": "EPA",
			"description": "Diesel truck emissions per ton-kilometer"
		},
		{
			"factor_name": "Van (per km)",
			"factor_value": 0.3,
			"unit_of_measure": "kg CO2e/km",
			"scope": "Scope 1",
			"category": "Transport",
			"module": "Transport",
			"source": "EPA",
			"description": "Van emissions per kilometer"
		},
		{
			"factor_name": "Car (per km)",
			"factor_value": 0.2,
			"unit_of_measure": "kg CO2e/km",
			"scope": "Scope 1",
			"category": "Transport",
			"module": "Transport",
			"source": "EPA",
			"description": "Car emissions per kilometer"
		}
	]
	
	# Energy emission factors
	energy_factors = [
		{
			"factor_name": "Electricity (grid average)",
			"factor_value": 0.4,
			"unit_of_measure": "kg CO2e/kWh",
			"scope": "Scope 2",
			"category": "Energy",
			"module": "All",
			"source": "EPA",
			"description": "Grid electricity emissions per kWh"
		},
		{
			"factor_name": "Natural Gas",
			"factor_value": 0.2,
			"unit_of_measure": "kg CO2e/kWh",
			"scope": "Scope 1",
			"category": "Energy",
			"module": "All",
			"source": "EPA",
			"description": "Natural gas emissions per kWh"
		},
		{
			"factor_name": "Diesel",
			"factor_value": 0.27,
			"unit_of_measure": "kg CO2e/kWh",
			"scope": "Scope 1",
			"category": "Energy",
			"module": "All",
			"source": "EPA",
			"description": "Diesel fuel emissions per kWh"
		},
		{
			"factor_name": "Solar",
			"factor_value": 0.05,
			"unit_of_measure": "kg CO2e/kWh",
			"scope": "Scope 2",
			"category": "Energy",
			"module": "All",
			"source": "EPA",
			"description": "Solar energy emissions per kWh (including manufacturing)"
		}
	]
	
	# Air freight emission factors
	air_freight_factors = [
		{
			"factor_name": "Air Freight (per ton-km)",
			"factor_value": 0.5,
			"unit_of_measure": "kg CO2e/ton-km",
			"scope": "Scope 3",
			"category": "Transport",
			"module": "Air Freight",
			"source": "IATA",
			"description": "Air freight emissions per ton-kilometer"
		}
	]
	
	# Sea freight emission factors
	sea_freight_factors = [
		{
			"factor_name": "Sea Freight (per ton-km)",
			"factor_value": 0.01,
			"unit_of_measure": "kg CO2e/ton-km",
			"scope": "Scope 3",
			"category": "Transport",
			"module": "Sea Freight",
			"source": "IMO",
			"description": "Sea freight emissions per ton-kilometer"
		}
	]
	
	# Waste emission factors
	waste_factors = [
		{
			"factor_name": "Landfill Waste",
			"factor_value": 0.5,
			"unit_of_measure": "kg CO2e/kg",
			"scope": "Scope 3",
			"category": "Waste",
			"module": "All",
			"source": "EPA",
			"description": "Landfill waste emissions per kg"
		},
		{
			"factor_name": "Recycled Waste",
			"factor_value": 0.1,
			"unit_of_measure": "kg CO2e/kg",
			"scope": "Scope 3",
			"category": "Waste",
			"module": "All",
			"source": "EPA",
			"description": "Recycled waste emissions per kg"
		}
	]
	
	# Combine all factors
	all_factors = transport_factors + energy_factors + air_freight_factors + sea_freight_factors + waste_factors
	
	# Create emission factors
	for factor_data in all_factors:
		if not frappe.db.exists("Emission Factors", factor_data["factor_name"]):
			doc = frappe.new_doc("Emission Factors")
			doc.update(factor_data)
			doc.is_active = 1
			doc.valid_from = getdate()
			doc.insert(ignore_permissions=True)
			frappe.db.commit()


def create_default_sustainability_settings():
	"""Create default sustainability settings for all companies"""
	
	companies = frappe.get_all("Company", fields=["name"])
	
	for company in companies:
		if not frappe.db.exists("Sustainability Settings", company.name):
			settings = frappe.new_doc("Sustainability Settings")
			settings.company = company.name
			settings.enable_sustainability_tracking = 1
			settings.enable_module_integration = 1
			settings.enable_automatic_calculations = 1
			settings.enable_compliance_tracking = 1
			settings.enable_expiry_notifications = 1
			settings.expiry_notification_days = 30
			settings.enable_audit_notifications = 1
			settings.audit_notification_days = 30
			settings.default_reporting_period = "Monthly"
			settings.carbon_calculation_method = "Emission Factor"
			settings.energy_calculation_method = "Direct Measurement"
			
			# Add integrated modules (includes Customs and Job Management for Declaration, General Job)
			modules = [
				{"module_name": "Transport", "enable_tracking": 1, "enable_carbon_tracking": 1, "enable_energy_tracking": 1, "enable_waste_tracking": 0, "auto_calculate": 1, "calculation_frequency": "Daily"},
				{"module_name": "Warehousing", "enable_tracking": 1, "enable_carbon_tracking": 1, "enable_energy_tracking": 1, "enable_waste_tracking": 1, "auto_calculate": 1, "calculation_frequency": "Daily"},
				{"module_name": "Air Freight", "enable_tracking": 1, "enable_carbon_tracking": 1, "enable_energy_tracking": 0, "enable_waste_tracking": 0, "auto_calculate": 1, "calculation_frequency": "Daily"},
				{"module_name": "Sea Freight", "enable_tracking": 1, "enable_carbon_tracking": 1, "enable_energy_tracking": 0, "enable_waste_tracking": 0, "auto_calculate": 1, "calculation_frequency": "Daily"},
				{"module_name": "Customs", "enable_tracking": 1, "enable_carbon_tracking": 1, "enable_energy_tracking": 1, "enable_waste_tracking": 0, "auto_calculate": 1, "calculation_frequency": "Daily"},
				{"module_name": "Job Management", "enable_tracking": 1, "enable_carbon_tracking": 1, "enable_energy_tracking": 1, "enable_waste_tracking": 0, "auto_calculate": 1, "calculation_frequency": "Daily"},
			]
			
			for module_data in modules:
				settings.append("integrated_modules", module_data)
			
			settings.insert(ignore_permissions=True)
			frappe.db.commit()


def create_sample_sustainability_goals():
	"""Create sample sustainability goals"""
	
	companies = frappe.get_all("Company", fields=["name"])
	
	for company in companies:
		# Energy efficiency goal
		if not frappe.db.exists("Sustainability Goals", {"company": company.name, "goal_name": "Reduce Energy Consumption by 20%"}):
			goal = frappe.new_doc("Sustainability Goals")
			goal.company = company.name
			goal.goal_name = "Reduce Energy Consumption by 20%"
			goal.goal_type = "Energy Efficiency"
			goal.module = "All"
			goal.target_value = 20
			goal.unit_of_measure = "%"
			goal.baseline_value = 100
			goal.baseline_date = getdate()
			goal.target_date = add_days(getdate(), 365)
			goal.description = "Reduce overall energy consumption by 20% compared to baseline"
			goal.action_plan = "Implement energy efficiency measures, upgrade equipment, and train staff"
			goal.status = "Not Started"
			goal.insert(ignore_permissions=True)
		
		# Carbon reduction goal
		if not frappe.db.exists("Sustainability Goals", {"company": company.name, "goal_name": "Reduce Carbon Footprint by 30%"}):
			goal = frappe.new_doc("Sustainability Goals")
			goal.company = company.name
			goal.goal_name = "Reduce Carbon Footprint by 30%"
			goal.goal_type = "Carbon Reduction"
			goal.module = "All"
			goal.target_value = 30
			goal.unit_of_measure = "%"
			goal.baseline_value = 100
			goal.baseline_date = getdate()
			goal.target_date = add_days(getdate(), 730)
			goal.description = "Reduce carbon footprint by 30% compared to baseline"
			goal.action_plan = "Switch to renewable energy, optimize transport routes, and implement carbon offset programs"
			goal.status = "Not Started"
			goal.insert(ignore_permissions=True)
		
		# Waste reduction goal
		if not frappe.db.exists("Sustainability Goals", {"company": company.name, "goal_name": "Reduce Waste by 50%"}):
			goal = frappe.new_doc("Sustainability Goals")
			goal.company = company.name
			goal.goal_name = "Reduce Waste by 50%"
			goal.goal_type = "Waste Reduction"
			goal.module = "All"
			goal.target_value = 50
			goal.unit_of_measure = "%"
			goal.baseline_value = 100
			goal.baseline_date = getdate()
			goal.target_date = add_days(getdate(), 365)
			goal.description = "Reduce waste generation by 50% compared to baseline"
			goal.action_plan = "Implement waste reduction programs, improve recycling, and optimize packaging"
			goal.status = "Not Started"
			goal.insert(ignore_permissions=True)
		
		frappe.db.commit()


def setup_sustainability_with_sample_data():
	"""Setup sustainability module with sample data for testing"""
	setup_sustainability()
	
	# Import and run sample data creation
	try:
		from logistics.sustainability.setup.create_sample_data import create_sample_sustainability_data
		print("\n📊 Creating sample data...")
		create_sample_sustainability_data()
		print("✅ Sample data created successfully!")
	except Exception as e:
		print(f"⚠️ Error creating sample data: {e}")
		frappe.log_error(f"Error creating sample data: {e}", "Sample Data Error")


@frappe.whitelist()
def setup_sustainability_module():
	"""Setup sustainability module - called from UI"""
	try:
		setup_sustainability()
		frappe.msgprint(_("Sustainability module setup completed successfully!"))
	except Exception as e:
		frappe.log_error(f"Error setting up sustainability module: {str(e)}")
		frappe.throw(_("Error setting up sustainability module. Please check the error log."))
