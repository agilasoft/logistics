# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Helper functions for creating test master data
"""
import frappe
from frappe.utils import today


def create_test_company(company_name="Test Air Freight Company"):
	"""Create a test company if it doesn't exist"""
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc({
			"doctype": "Company",
			"company_name": company_name,
			"abbr": "TAFC",
			"default_currency": "USD"
		})
		company.insert()
	return company_name


def create_test_customer(customer_name="Test Customer"):
	"""Create a test customer if it doesn't exist"""
	if not frappe.db.exists("Customer", customer_name):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_type": "Company"
		})
		customer.insert()
	return customer_name


def create_test_airport(iata_code, airport_name=None, city=None, country=None):
	"""Create a test airport master record"""
	if not airport_name:
		airport_name = f"{iata_code} Airport"
	
	if not frappe.db.exists("Airport Master", iata_code):
		airport = frappe.get_doc({
			"doctype": "Airport Master",
			"iata_code": iata_code,
			"airport_name": airport_name,
			"city": city or f"City {iata_code}",
			"country": country or "United States",
			"is_active": 1
		})
		airport.insert()
	return iata_code


def create_test_unloco(unlocode, location_name=None, iata_code=None, country_code="US", location_type="Airport"):
	"""Create a test UNLOCO record (used for origin/destination ports in Air Shipment)"""
	if not location_name:
		location_name = f"{unlocode} Location"
	
	# Check if UNLOCO already exists
	if frappe.db.exists("UNLOCO", unlocode):
		return unlocode
	
	# Create UNLOCO record
	# Only set required fields and optional fields that don't have select validation
	unloco = frappe.get_doc({
		"doctype": "UNLOCO",
		"unlocode": unlocode,
		"location_name": location_name,
		"country": "United States" if country_code == "US" else "Unknown",
		"country_code": country_code,
		"auto_populate": 0  # Disable auto-populate to avoid external API calls during tests
	})
	
	# Set optional fields only if they don't cause validation issues
	if location_type:
		unloco.location_type = location_type
	if location_type == "Airport":
		unloco.has_airport = 1
	
	# Add IATA code if provided
	if iata_code:
		unloco.iata_code = iata_code
	
	unloco.insert(ignore_permissions=True)
	return unlocode


def create_test_airline(code="TA", airline_name="Test Airline"):
	"""Create a test airline"""
	if not frappe.db.exists("Airline", code):
		airline = frappe.get_doc({
			"doctype": "Airline",
			"code": code,
			"airline_name": airline_name,
			"iata_code": code,
			"icao_code": f"{code}L"
		})
		airline.insert()
	return code


def create_test_shipper(code="TEST-SHIPPER", shipper_name="Test Shipper"):
	"""Create a test shipper"""
	if not frappe.db.exists("Shipper", code):
		shipper = frappe.get_doc({
			"doctype": "Shipper",
			"code": code,
			"shipper_name": shipper_name
		})
		shipper.insert()
	return code


def create_test_consignee(code="TEST-CONSIGNEE", consignee_name="Test Consignee"):
	"""Create a test consignee"""
	if not frappe.db.exists("Consignee", code):
		consignee = frappe.get_doc({
			"doctype": "Consignee",
			"code": code,
			"consignee_name": consignee_name
		})
		consignee.insert()
	return code


def create_test_branch(company, branch_name="Test Branch"):
	"""Create a test branch"""
	# Branch uses autoname: prompt and requires custom_company field
	# Try to find existing branch first
	existing = frappe.db.get_value("Branch", {"custom_company": company, "branch": branch_name}, "name")
	if existing:
		return existing
	
	# Create new branch
	branch = frappe.get_doc({
		"doctype": "Branch",
		"branch": branch_name,
		"custom_company": company  # Required custom field
	})
	# Set name explicitly for prompt autoname
	branch.name = f"{company}-{branch_name}".replace(" ", "-")
	branch.insert(ignore_permissions=True)
	return branch.name


def create_test_cost_center(company, cost_center_name="Test Cost Center", parent_cost_center=None):
	"""Create a test cost center"""
	# Cost Center uses format:{cost_center_number}-{company}
	# Need parent_cost_center (required) and cost_center_number
	
	# Get or create parent cost center (group)
	if not parent_cost_center:
		# Try to find existing group cost center for company
		parent = frappe.db.get_value("Cost Center", 
			{"company": company, "is_group": 1}, "name", order_by="creation asc")
		
		if not parent:
			# Try to find by cost_center_name matching company
			parent = frappe.db.get_value("Cost Center", 
				{"company": company, "cost_center_name": company, "is_group": 1}, "name")
		
		if not parent:
			# Create a parent group cost center
			parent_doc = frappe.get_doc({
				"doctype": "Cost Center",
				"cost_center_name": company,
				"cost_center_number": "1",
				"company": company,
				"is_group": 1,
				"parent_cost_center": company  # Self-reference for root
			})
			parent_doc.insert(ignore_permissions=True)
			parent = parent_doc.name
		
		parent_cost_center = parent
	
	# Generate cost center number - use a high number to avoid conflicts
	# Get max number for this company
	max_cc = frappe.db.sql("""
		SELECT MAX(CAST(cost_center_number AS UNSIGNED)) as max_num
		FROM `tabCost Center`
		WHERE company = %s AND cost_center_number REGEXP '^[0-9]+$'
	""", company, as_dict=True)
	
	if max_cc and max_cc[0].max_num:
		cost_center_number = str(max_cc[0].max_num + 1)
	else:
		cost_center_number = "999"  # Use high number for test
	
	# Check if cost center already exists with this number
	cc_name = f"{cost_center_number}-{company}"
	if frappe.db.exists("Cost Center", cc_name):
		return cc_name
	
	# Create cost center
	cost_center = frappe.get_doc({
		"doctype": "Cost Center",
		"cost_center_name": cost_center_name,
		"cost_center_number": cost_center_number,
		"company": company,
		"parent_cost_center": parent_cost_center,
		"is_group": 0
	})
	cost_center.insert(ignore_permissions=True)
	return cost_center.name


def create_test_profit_center(company, profit_center_name="Test Profit Center", code=None):
	"""Create a test profit center"""
	# Profit Center uses autoname: field:code, so code is required
	if not code:
		code = f"TEST-PC-{company}".replace(" ", "-")[:20]  # Limit length
	
	# Check if exists
	if frappe.db.exists("Profit Center", code):
		return code
	
	# Get required fields
	profit_center = frappe.get_doc({
		"doctype": "Profit Center",
		"code": code,
		"profit_center_name": profit_center_name,
		"company": company
	})
	
	# Check if parent_profit_center is required
	meta = frappe.get_meta("Profit Center")
	parent_field = meta.get_field("parent_profit_center")
	if parent_field and parent_field.reqd:
		# Try to get existing parent or create one
		parent = frappe.db.get_value("Profit Center", 
			{"company": company}, "name", order_by="creation asc")
		if not parent:
			# Create root profit center
			root_code = f"ROOT-{company}".replace(" ", "-")[:20]
			root = frappe.get_doc({
				"doctype": "Profit Center",
				"code": root_code,
				"profit_center_name": company,
				"company": company
			})
			root.insert(ignore_permissions=True)
			parent = root.name
		profit_center.parent_profit_center = parent
	
	profit_center.insert(ignore_permissions=True)
	return profit_center.name


def create_test_item(item_code="Test Air Freight Item", item_name=None):
	"""Create a test item"""
	if not item_name:
		item_name = item_code
	
	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": "Services"
		})
		item.insert()
	return item_code


def create_test_currency(currency="USD"):
	"""Create a test currency if it doesn't exist"""
	if not frappe.db.exists("Currency", currency):
		currency_doc = frappe.get_doc({
			"doctype": "Currency",
			"currency_name": currency,
			"symbol": "$" if currency == "USD" else currency
		})
		currency_doc.insert()
	return currency


def setup_basic_master_data():
	"""Setup all basic master data needed for tests"""
	company = create_test_company()
	customer = create_test_customer()
	create_test_currency("USD")
	
	# Create airports (Airport Master - for reference)
	create_test_airport("LAX", "Los Angeles International Airport", "Los Angeles", "United States")
	create_test_airport("JFK", "John F. Kennedy International Airport", "New York", "United States")
	
	# Create UNLOCO records (required for Air Shipment origin_port and destination_port)
	# UNLOCO codes: USLAX for Los Angeles, USJFK for JFK (standard format: CountryCode + LocationCode)
	create_test_unloco("USLAX", "Los Angeles International Airport", "LAX", "US", "Airport")
	create_test_unloco("USJFK", "John F. Kennedy International Airport", "JFK", "US", "Airport")
	
	# Create airline
	create_test_airline("TA", "Test Airline")
	
	# Create shipper and consignee
	create_test_shipper("TEST-SHIPPER", "Test Shipper")
	create_test_consignee("TEST-CONSIGNEE", "Test Consignee")
	
	# Create accounts (skip if they cause issues - not all tests need them)
	# These are optional and may not be needed for all tests
	try:
		create_test_branch(company)
		create_test_cost_center(company)
		create_test_profit_center(company)
	except Exception:
		pass  # Skip if creation fails - tests can create them individually if needed
	
	# Create item
	create_test_item()
	
	return {
		"company": company,
		"customer": customer
	}

