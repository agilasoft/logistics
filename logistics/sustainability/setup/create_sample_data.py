# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, add_months, today, date_diff
import random
from datetime import timedelta


def create_sample_sustainability_data():
	"""Create comprehensive sample data for sustainability module - dynamically generated"""
	
	print("🔧 Creating sample sustainability data...")
	
	try:
		# Get companies from system
		companies = frappe.get_all("Company", fields=["name"])
		
		if not companies:
			print("⚠️ No companies found in the system. Please create a company first.")
			return
		
		# Get branches if available (safely handle if Branch doctype doesn't exist or has different structure)
		branch_map = {}
		try:
			# Check if Branch doctype exists
			if frappe.db.exists("DocType", "Branch"):
				# Try to get branches with company field
				try:
					branches = frappe.get_all("Branch", fields=["name", "company"])
					for branch in branches:
						company = getattr(branch, 'company', None)
						if company:
							if company not in branch_map:
								branch_map[company] = []
							branch_map[company].append(branch.name)
				except:
					# Branch exists but doesn't have company field - get all branches
					try:
						branches = frappe.get_all("Branch", fields=["name"])
						# Assign branches to all companies if no company field
						for company in companies:
							branch_map[company.name] = [b.name for b in branches] if branches else []
					except:
						pass
		except:
			# Branch doctype doesn't exist or can't be queried - continue without branches
			pass
		
		# Modules to generate data for
		modules = ["Transport", "Warehousing", "Air Freight", "Sea Freight"]
		
		# Date range - last 6 months
		end_date = today()
		start_date = add_months(end_date, -6)
		
		records_created = {
			"sustainability_metrics": 0,
			"carbon_footprint": 0,
			"energy_consumption": 0,
			"sustainability_goals": 0,
			"sustainability_compliance": 0
		}
		
		for company in companies:
			print(f"\n📊 Processing company: {company.name}")
			
			# Get available branches for this company
			company_branches = branch_map.get(company.name, [None])
			
			# Generate data for each module
			for module in modules:
				print(f"  📦 Generating data for {module}...")
				
				# Generate data for the last 6 months (approximately weekly records)
				current_date = start_date
				day_count = 0
				
				while current_date <= end_date:
					# Skip some days to make it realistic (not every day)
					day_count += 1
					if day_count % 7 == 0 or random.random() < 0.3:  # Weekly-ish or random
						
						# Select a random branch if available
						branch = random.choice(company_branches) if company_branches else None
						
						# Generate energy consumption data
						energy_data = create_sample_energy_consumption(
							company.name, module, current_date, branch
						)
						if energy_data:
							records_created["energy_consumption"] += 1
						
						# Generate carbon footprint data
						carbon_data = create_sample_carbon_footprint(
							company.name, module, current_date, branch, energy_data
						)
						if carbon_data:
							records_created["carbon_footprint"] += 1
						
						# Generate sustainability metrics (weekly)
						if day_count % 7 == 0:
							metrics_data = create_sample_sustainability_metrics(
								company.name, module, current_date, branch
							)
							if metrics_data:
								records_created["sustainability_metrics"] += 1
					
					current_date = add_days(current_date, 1)
			
			# Create sample Sustainability Goals for this company
			goals_created = create_sample_sustainability_goals(company.name, company_branches)
			records_created["sustainability_goals"] += goals_created
			
			# Create sample Sustainability Compliance records for this company
			compliance_created = create_sample_sustainability_compliance(company.name, company_branches)
			records_created["sustainability_compliance"] += compliance_created
			
			frappe.db.commit()
		
		print(f"\n✅ Sample data creation completed!")
		print(f"   📊 Sustainability Metrics: {records_created['sustainability_metrics']}")
		print(f"   🔥 Carbon Footprint: {records_created['carbon_footprint']}")
		print(f"   ⚡ Energy Consumption: {records_created['energy_consumption']}")
		print(f"   🎯 Sustainability Goals: {records_created['sustainability_goals']}")
		print(f"   ✅ Sustainability Compliance: {records_created['sustainability_compliance']}")
		
	except Exception as e:
		print(f"❌ Error creating sample data: {e}")
		frappe.log_error(f"Error creating sample sustainability data: {e}", "Sample Data Error")
		raise


def create_sample_energy_consumption(company, module, date, branch=None):
	"""Create sample energy consumption record"""
	
	try:
		# Base values vary by module
		base_values = {
			"Transport": {"base": 500, "variation": 300, "unit": "Liters"},
			"Warehousing": {"base": 2000, "variation": 800, "unit": "kWh"},
			"Air Freight": {"base": 800, "variation": 400, "unit": "Liters"},
			"Sea Freight": {"base": 600, "variation": 300, "unit": "Liters"}
		}
		
		if module not in base_values:
			return None
		
		config = base_values[module]
		
		# Generate realistic consumption value
		consumption = round(
			config["base"] + random.uniform(-config["variation"], config["variation"]),
			2
		)
		consumption = max(consumption, config["base"] * 0.3)  # Minimum 30% of base
		
		# Cost per unit varies
		cost_per_unit = round(random.uniform(0.5, 2.5), 2)
		total_cost = round(consumption * cost_per_unit, 2)
		
		# Renewable percentage varies
		renewable_percentage = round(random.uniform(10, 50), 2)
		
		# Energy type based on module (must match doctype options: Electricity, Natural Gas, Diesel, Petrol, Solar, Wind, Hydro, Other)
		energy_types = {
			"Transport": ["Diesel", "Petrol", "Electricity", "Natural Gas", "Other"],
			"Warehousing": ["Electricity", "Solar", "Natural Gas", "Other"],
			"Air Freight": ["Diesel", "Petrol", "Electricity", "Other"],
			"Sea Freight": ["Diesel", "Petrol", "Natural Gas", "Other"]
		}
		energy_type = random.choice(energy_types.get(module, ["Electricity"]))
		
		# Calculate carbon footprint (simplified: kg CO2 per unit varies by type)
		carbon_per_unit = {
			"Diesel": 2.68, "Petrol": 2.31, "Electricity": 0.5, "Natural Gas": 1.96,
			"Solar": 0.0, "Wind": 0.0, "Hydro": 0.0,
			"Other": 2.0
		}
		carbon_footprint = round(consumption * carbon_per_unit.get(energy_type, 2.0), 2)
		
		# Check if record already exists
		filters = {
			"company": company,
			"module": module,
			"date": date
		}
		if branch:
			filters["branch"] = branch
		
		if frappe.db.exists("Energy Consumption", filters):
			return None
		
		doc = frappe.new_doc("Energy Consumption")
		doc.company = company
		doc.module = module
		doc.date = getdate(date) if isinstance(date, str) else date  # Ensure date is a date object
		doc.energy_type = energy_type
		doc.consumption_value = consumption
		# Unit of measure must match exactly from the Select options
		doc.unit_of_measure = config["unit"]  # Options: kWh, MWh, GJ, Therms, Liters, Gallons, Other
		doc.cost_per_unit = cost_per_unit
		doc.total_cost = total_cost
		doc.renewable_percentage = renewable_percentage
		doc.carbon_footprint = carbon_footprint
		doc.carbon_intensity = round(carbon_footprint / max(consumption, 1), 3)
		
		if branch:
			doc.branch = branch
		
		doc.notes = f"Sample data for {module} module"
		doc.insert(ignore_permissions=True)
		
		return doc.name
		
	except Exception as e:
		print(f"    ⚠️ Error creating energy consumption: {e}")
		return None


def create_sample_carbon_footprint(company, module, date, branch=None, energy_ref=None):
	"""Create sample carbon footprint record"""
	
	try:
		# Base emissions vary by module
		base_emissions = {
			"Transport": 1500,
			"Warehousing": 800,
			"Air Freight": 2500,
			"Sea Freight": 2000
		}
		
		if module not in base_emissions:
			return None
		
		# Generate realistic total emissions
		base = base_emissions[module]
		total_emissions = round(
			base + random.uniform(-base * 0.4, base * 0.4),
			2
		)
		total_emissions = max(total_emissions, base * 0.3)
		
		# Scope distribution
		scope1_pct = random.uniform(40, 70) / 100
		scope2_pct = random.uniform(20, 40) / 100
		scope3_pct = 1 - scope1_pct - scope2_pct
		
		scope1 = round(total_emissions * scope1_pct, 2)
		scope2 = round(total_emissions * scope2_pct, 2)
		scope3 = round(total_emissions * scope3_pct, 2)
		
		# Determine primary scope
		if scope1 >= scope2 and scope1 >= scope3:
			primary_scope = "Scope 1"
		elif scope2 >= scope3:
			primary_scope = "Scope 2"
		else:
			primary_scope = "Scope 3"
		
		# Carbon offset (some companies have offsets)
		carbon_offset = round(random.uniform(0, total_emissions * 0.2), 2) if random.random() < 0.3 else 0
		net_emissions = round(total_emissions - carbon_offset, 2)
		
		# Check if record already exists
		filters = {
			"company": company,
			"module": module,
			"date": date
		}
		if branch:
			filters["branch"] = branch
		
		if frappe.db.exists("Carbon Footprint", filters):
			return None
		
		doc = frappe.new_doc("Carbon Footprint")
		doc.company = company
		doc.module = module
		doc.date = getdate(date) if isinstance(date, str) else date  # Ensure date is a date object
		doc.scope = primary_scope
		doc.total_emissions = total_emissions
		doc.carbon_offset = carbon_offset
		doc.net_emissions = net_emissions
		doc.calculation_method = random.choice(["Emission Factor", "Activity Data", "Hybrid", "External Provider"])
		# Verification status (must match options: Verified, Pending Verification, Not Verified, Failed Verification)
		doc.verification_status = random.choice(["Verified", "Pending Verification", "Not Verified", "Failed Verification"])
		
		if branch:
			doc.branch = branch
		
		# Facility is optional but helps with naming series
		doc.facility = f"{module} Facility"
		
		if energy_ref:
			doc.reference_doctype = "Energy Consumption"
			doc.reference_name = energy_ref
		
		doc.notes = f"Sample carbon footprint data for {module}"
		doc.insert(ignore_permissions=True)
		
		# Add breakdown data
		if doc.total_emissions > 0:
			try:
				breakdown = frappe.new_doc("Carbon Emission Breakdown")
				breakdown.parent = doc.name
				breakdown.parenttype = "Carbon Footprint"
				breakdown.parentfield = "emission_breakdown"
				breakdown.scope = "Scope 1"
				breakdown.emission_value = scope1
				breakdown.unit_of_measure = "kg CO2e"
				breakdown.insert(ignore_permissions=True)
				
				if scope2 > 0:
					breakdown2 = frappe.new_doc("Carbon Emission Breakdown")
					breakdown2.parent = doc.name
					breakdown2.parenttype = "Carbon Footprint"
					breakdown2.parentfield = "emission_breakdown"
					breakdown2.scope = "Scope 2"
					breakdown2.emission_value = scope2
					breakdown2.unit_of_measure = "kg CO2e"
					breakdown2.insert(ignore_permissions=True)
				
				if scope3 > 0:
					breakdown3 = frappe.new_doc("Carbon Emission Breakdown")
					breakdown3.parent = doc.name
					breakdown3.parenttype = "Carbon Footprint"
					breakdown3.parentfield = "emission_breakdown"
					breakdown3.scope = "Scope 3"
					breakdown3.emission_value = scope3
					breakdown3.unit_of_measure = "kg CO2e"
					breakdown3.insert(ignore_permissions=True)
			except Exception as e:
				# Breakdown is optional
				pass
		
		return doc.name
		
	except Exception as e:
		print(f"    ⚠️ Error creating carbon footprint: {e}")
		return None


def create_sample_sustainability_metrics(company, module, date, branch=None):
	"""Create sample sustainability metrics record"""
	
	try:
		# Aggregate data from energy and carbon for this module/date
		energy_filters = {
			"company": company,
			"module": module,
			"date": date
		}
		carbon_filters = energy_filters.copy()
		
		if branch:
			energy_filters["branch"] = branch
			carbon_filters["branch"] = branch
		
		# Get aggregated energy consumption using SQL
		energy_query = """
			SELECT 
				SUM(consumption_value) as total_energy,
				SUM(carbon_footprint) as total_carbon
			FROM `tabEnergy Consumption`
			WHERE company = %(company)s AND module = %(module)s AND date = %(date)s
		"""
		if branch:
			energy_query += " AND branch = %(branch)s"
		
		energy_params = {"company": company, "module": module, "date": date}
		if branch:
			energy_params["branch"] = branch
		
		energy_result = frappe.db.sql(energy_query, energy_params, as_dict=True)
		energy_records = energy_result if energy_result else [{"total_energy": None, "total_carbon": None}]
		
		# Get aggregated carbon footprint using SQL
		carbon_query = """
			SELECT SUM(total_emissions) as total_emissions
			FROM `tabCarbon Footprint`
			WHERE company = %(company)s AND module = %(module)s AND date = %(date)s
		"""
		if branch:
			carbon_query += " AND branch = %(branch)s"
		
		carbon_params = {"company": company, "module": module, "date": date}
		if branch:
			carbon_params["branch"] = branch
		
		carbon_result = frappe.db.sql(carbon_query, carbon_params, as_dict=True)
		carbon_records = carbon_result if carbon_result else [{"total_emissions": None}]
		
		# Use aggregated values or generate defaults
		if energy_records and energy_records[0].total_energy:
			energy_consumption = round(float(energy_records[0].total_energy), 2)
			carbon_footprint = round(float(energy_records[0].total_carbon or 0), 2)
		else:
			energy_consumption = round(random.uniform(100, 5000), 2)
			carbon_footprint = round(energy_consumption * random.uniform(1.5, 3.0), 2)
		
		if carbon_records and carbon_records[0].total_emissions:
			carbon_footprint = round(float(carbon_records[0].total_emissions), 2)
		
		# Generate other metrics
		waste_generated = round(random.uniform(10, 500), 2)
		water_consumption = round(random.uniform(50, 2000), 2)
		renewable_energy_percentage = round(random.uniform(15, 60), 2)
		
		# Calculate scores (0-100 scale)
		energy_efficiency_score = round(random.uniform(60, 95), 1)
		carbon_efficiency_score = round(random.uniform(55, 90), 1)
		waste_efficiency_score = round(random.uniform(50, 85), 1)
		sustainability_score = round(
			(energy_efficiency_score + carbon_efficiency_score + waste_efficiency_score) / 3,
			1
		)
		
		# Compliance status (must match options: Compliant, Non-Compliant, Under Review, Not Applicable)
		compliance_statuses = ["Compliant", "Non-Compliant", "Under Review", "Not Applicable"]
		compliance_status = random.choice(compliance_statuses)
		
		# Check if record already exists
		filters = {
			"company": company,
			"module": module,
			"date": date
		}
		if branch:
			filters["branch"] = branch
		
		if frappe.db.exists("Sustainability Metrics", filters):
			return None
		
		doc = frappe.new_doc("Sustainability Metrics")
		doc.company = company
		doc.module = module
		doc.date = getdate(date) if isinstance(date, str) else date  # Ensure date is a date object
		doc.energy_consumption = energy_consumption
		doc.carbon_footprint = carbon_footprint
		doc.waste_generated = waste_generated
		doc.water_consumption = water_consumption
		doc.renewable_energy_percentage = renewable_energy_percentage
		doc.sustainability_score = sustainability_score
		doc.energy_efficiency_score = energy_efficiency_score
		doc.carbon_efficiency_score = carbon_efficiency_score
		doc.waste_efficiency_score = waste_efficiency_score
		doc.compliance_status = compliance_status
		doc.certification_status = random.choice(["Certified", "Pending", "Not Certified"])
		# Verification status (must match options: Verified, Pending Verification, Not Verified, Failed Verification)
		doc.verification_status = random.choice(["Verified", "Pending Verification", "Not Verified", "Failed Verification"])
		
		if branch:
			doc.branch = branch
		
		doc.notes = f"Sample aggregated sustainability metrics for {module}"
		doc.insert(ignore_permissions=True)
		
		return doc.name
		
	except Exception as e:
		print(f"    ⚠️ Error creating sustainability metrics: {e}")
		return None


def create_sample_sustainability_goals(company, branches=None):
	"""Create sample Sustainability Goals records"""
	try:
		goals_created = 0
		goal_types = ["Energy Efficiency", "Carbon Reduction", "Waste Reduction", "Water Conservation", "Renewable Energy"]
		modules = ["Transport", "Warehousing", "Air Freight", "Sea Freight"]
		statuses = ["Not Started", "In Progress", "On Track", "At Risk"]
		
		# Create 2-3 goals per module
		for module in modules:
			num_goals = random.randint(2, 3)
			for i in range(num_goals):
				goal_type = random.choice(goal_types)
				status = random.choice(statuses)
				
				# Generate goal values based on type
				if goal_type == "Energy Efficiency":
					baseline = round(random.uniform(1000, 5000), 2)
					target = round(baseline * random.uniform(0.7, 0.9), 2)  # 10-30% reduction
					current = round(baseline * random.uniform(0.75, 0.95), 2)
					unit = "kWh"
					goal_name = f"Reduce Energy Consumption by {round((1 - target/baseline) * 100, 1)}% for {module}"
				elif goal_type == "Carbon Reduction":
					baseline = round(random.uniform(500, 3000), 2)
					target = round(baseline * random.uniform(0.6, 0.85), 2)  # 15-40% reduction
					current = round(baseline * random.uniform(0.65, 0.9), 2)
					unit = "kg CO2e"
					goal_name = f"Reduce Carbon Emissions by {round((1 - target/baseline) * 100, 1)}% for {module}"
				elif goal_type == "Waste Reduction":
					baseline = round(random.uniform(100, 1000), 2)
					target = round(baseline * random.uniform(0.5, 0.8), 2)  # 20-50% reduction
					current = round(baseline * random.uniform(0.55, 0.85), 2)
					unit = "kg"
					goal_name = f"Reduce Waste Generation by {round((1 - target/baseline) * 100, 1)}% for {module}"
				elif goal_type == "Water Conservation":
					baseline = round(random.uniform(1000, 10000), 2)
					target = round(baseline * random.uniform(0.6, 0.85), 2)  # 15-40% reduction
					current = round(baseline * random.uniform(0.65, 0.9), 2)
					unit = "Liters"
					goal_name = f"Reduce Water Consumption by {round((1 - target/baseline) * 100, 1)}% for {module}"
				else:  # Renewable Energy
					baseline = round(random.uniform(10, 50), 2)
					target = round(baseline + random.uniform(20, 60), 2)  # 20-60% increase
					current = round(baseline + random.uniform(5, 40), 2)
					unit = "%"
					goal_name = f"Increase Renewable Energy to {target}% for {module}"
				
				# Calculate progress percentage
				if goal_type == "Renewable Energy":
					# For renewable energy, progress is based on increase
					progress = ((current - baseline) / (target - baseline)) * 100 if target > baseline else 0
				else:
					# For reduction goals, progress is based on reduction achieved
					reduction_achieved = baseline - current
					reduction_target = baseline - target
					progress = (reduction_achieved / reduction_target) * 100 if reduction_target > 0 else 0
				
				progress_percentage = max(0, min(100, round(progress, 1)))
				
				# Target date - within next 6-12 months
				today_date = getdate(today())
				target_date = add_months(today_date, random.randint(6, 12))
				baseline_date = add_months(today_date, -random.randint(1, 3))
				
				# Select a branch if available
				branch = None
				if branches and len(branches) > 0 and None in branches:
					# Remove None from list
					valid_branches = [b for b in branches if b is not None]
					if valid_branches:
						branch = random.choice(valid_branches)
				
				# Check if goal already exists
				filters = {
					"company": company,
					"module": module,
					"goal_name": goal_name
				}
				if branch:
					filters["branch"] = branch
				
				if frappe.db.exists("Sustainability Goals", filters):
					continue
				
				# Create goal document
				doc = frappe.new_doc("Sustainability Goals")
				doc.company = company
				doc.module = module
				doc.goal_name = goal_name
				doc.goal_type = goal_type
				doc.target_value = target
				doc.unit_of_measure = unit
				doc.baseline_value = baseline
				doc.baseline_date = baseline_date
				doc.target_date = target_date
				doc.current_value = current
				doc.progress_percentage = progress_percentage
				doc.status = status
				
				if branch:
					doc.branch = branch
				
				doc.description = f"Sample {goal_type.lower()} goal for {module} module"
				doc.action_plan = f"1. Implement efficiency measures\n2. Monitor progress monthly\n3. Report on achievements"
				
				doc.insert(ignore_permissions=True)
				goals_created += 1
		
		return goals_created
		
	except Exception as e:
		print(f"    ⚠️ Error creating sustainability goals: {e}")
		frappe.log_error(f"Error creating sustainability goals: {e}", "Sample Data Error")
		return 0


def create_sample_sustainability_compliance(company, branches=None):
	"""Create sample Sustainability Compliance records"""
	try:
		compliance_created = 0
		compliance_types = ["ISO 14001", "ISO 50001", "Carbon Trust", "LEED", "BREEAM", "Other"]
		modules = ["Transport", "Warehousing", "Air Freight", "Sea Freight"]
		certification_statuses = ["Certified", "Pending", "Not Certified", "Expired"]
		compliance_statuses = ["Compliant", "Non-Compliant", "Under Review", "Not Applicable"]
		audit_statuses = ["Passed", "Failed", "Pending", "Not Required"]
		
		# Create 1-2 compliance records per module
		for module in modules:
			num_records = random.randint(1, 2)
			for i in range(num_records):
				compliance_type = random.choice(compliance_types)
				cert_status = random.choice(certification_statuses)
				comp_status = random.choice(compliance_statuses)
				audit_status = random.choice(audit_statuses)
				
				# Generate compliance name based on type
				compliance_name = f"{compliance_type} Compliance - {module}"
				
				# Generate dates
				today_date = getdate(today())
				certification_date = add_months(today_date, -random.randint(6, 24))  # 6-24 months ago
				expiry_date = add_months(certification_date, random.randint(12, 36))  # 12-36 months from cert date
				last_audit_date = add_months(today_date, -random.randint(0, 6))  # 0-6 months ago
				next_audit_date = add_months(today_date, random.randint(3, 12))  # 3-12 months from now
				
				# Generate standard information
				standard_names = {
					"ISO 14001": "Environmental Management Systems",
					"ISO 50001": "Energy Management Systems",
					"Carbon Trust": "Carbon Management Standard",
					"LEED": "Leadership in Energy and Environmental Design",
					"BREEAM": "Building Research Establishment Environmental Assessment Method",
					"Other": "Sustainability Compliance Standard"
				}
				standard_name = standard_names.get(compliance_type, "Sustainability Standard")
				standard_version = f"{random.randint(1, 3)}.{random.randint(0, 9)}"
				certification_number = f"{compliance_type[:3].upper()}-{random.randint(10000, 99999)}"
				certification_body = random.choice(["DNV GL", "BSI Group", "SGS", "Bureau Veritas", "TUV SUD", "Intertek"])
				
				# Select a branch if available
				branch = None
				if branches and len(branches) > 0 and None in branches:
					# Remove None from list
					valid_branches = [b for b in branches if b is not None]
					if valid_branches:
						branch = random.choice(valid_branches)
				
				# Check if compliance record already exists
				filters = {
					"company": company,
					"module": module,
					"compliance_name": compliance_name
				}
				if branch:
					filters["branch"] = branch
				
				if frappe.db.exists("Sustainability Compliance", filters):
					continue
				
				# Create compliance document
				doc = frappe.new_doc("Sustainability Compliance")
				doc.company = company
				doc.module = module
				doc.compliance_name = compliance_name
				doc.compliance_type = compliance_type
				doc.standard_name = standard_name
				doc.standard_version = standard_version
				doc.certification_body = certification_body
				doc.certification_number = certification_number
				doc.certification_date = certification_date
				doc.expiry_date = expiry_date
				doc.last_audit_date = last_audit_date
				doc.next_audit_date = next_audit_date
				doc.certification_status = cert_status
				doc.compliance_status = comp_status
				doc.audit_status = audit_status
				
				if branch:
					doc.branch = branch
				
				doc.description = f"Sample {compliance_type} compliance record for {module} module"
				doc.requirements = f"1. Maintain compliance with {standard_name} {standard_version}\n2. Conduct regular audits\n3. Report compliance status quarterly"
				
				doc.insert(ignore_permissions=True)
				compliance_created += 1
		
		return compliance_created
		
	except Exception as e:
		print(f"    ⚠️ Error creating sustainability compliance: {e}")
		frappe.log_error(f"Error creating sustainability compliance: {e}", "Sample Data Error")
		return 0


@frappe.whitelist()
def generate_sample_data():
	"""Public method to generate sample data from UI"""
	try:
		create_sample_sustainability_data()
		return {"status": "success", "message": "Sample data generated successfully!"}
	except Exception as e:
		return {"status": "error", "message": str(e)}


if __name__ == "__main__":
	create_sample_sustainability_data()

