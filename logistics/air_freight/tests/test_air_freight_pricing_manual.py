# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

"""
Manual test script for Air Freight pricing from Sales Quote
Run this script to verify the implementation works correctly
"""

import frappe
from frappe.utils import today, add_days, flt


def test_air_freight_pricing():
	"""Test Air Freight pricing from Sales Quote"""
	
	print("=" * 80)
	print("Testing Air Freight Pricing from Sales Quote")
	print("=" * 80)
	
	# Test 1: Create Sales Quote with Air Freight lines
	print("\n1. Testing Sales Quote Air Freight creation...")
	try:
		sales_quote = frappe.get_doc({
			"doctype": "Sales Quote",
			"customer": frappe.db.get_value("Customer", {"customer_name": ["like", "%Test%"]}, "name") or "Test Customer",
			"date": today(),
			"valid_until": add_days(today(), 30),
			"one_off": 1,
			"company": frappe.db.get_value("Company", {"company_name": ["like", "%Test%"]}, "name") or frappe.defaults.get_global_default("company"),
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"air_freight": [
				{
					"item_code": frappe.db.get_value("Item", {"item_name": ["like", "%Air%"]}, "name") or "TEST-AIR-FREIGHT",
					"calculation_method": "Per Unit",
					"unit_type": "Weight",
					"unit_rate": 10.0,
					"currency": "USD",
					"quantity": 100
				}
			]
		})
		sales_quote.insert()
		print(f"   ✓ Sales Quote created: {sales_quote.name}")
		print(f"   ✓ Air Freight lines: {len(sales_quote.air_freight)}")
		
		# Test 2: Create Air Shipment from Sales Quote
		print("\n2. Testing Air Shipment creation from Sales Quote...")
		from logistics.pricing_center.doctype.sales_quote.sales_quote import create_air_shipment_from_sales_quote
		
		result = create_air_shipment_from_sales_quote(sales_quote.name)
		
		if result.get("success"):
			print(f"   ✓ Air Shipment created: {result.get('air_shipment')}")
			air_shipment = frappe.get_doc("Air Shipment", result["air_shipment"])
			
			# Test 3: Verify charges were populated
			print("\n3. Testing charge population...")
			if air_shipment.charges:
				print(f"   ✓ Charges populated: {len(air_shipment.charges)}")
				for idx, charge in enumerate(air_shipment.charges, 1):
					print(f"      Charge {idx}: {charge.item_code} - {charge.charge_basis} - {charge.rate} {charge.currency}")
			else:
				print("   ✗ No charges found")
			
			# Test 4: Test charge calculation
			print("\n4. Testing charge calculation...")
			if air_shipment.charges:
				charge = air_shipment.charges[0]
				charge.calculate_charge_amount()
				print(f"   ✓ Base Amount: {charge.base_amount}")
				print(f"   ✓ Total Amount: {charge.total_amount}")
			
			# Test 5: Test recalculate all charges
			print("\n5. Testing recalculate all charges...")
			air_shipment.weight = 150
			air_shipment.save()
			result = air_shipment.recalculate_all_charges()
			if result.get("success"):
				print(f"   ✓ Charges recalculated: {result.get('charges_recalculated')}")
			
			# Cleanup
			air_shipment.delete()
			print(f"   ✓ Air Shipment deleted: {result.get('air_shipment')}")
		
		# Cleanup
		sales_quote.delete()
		print(f"   ✓ Sales Quote deleted: {sales_quote.name}")
		
	except Exception as e:
		print(f"   ✗ Error: {str(e)}")
		import traceback
		traceback.print_exc()
	
	print("\n" + "=" * 80)
	print("Test completed!")
	print("=" * 80)


if __name__ == "__main__":
	test_air_freight_pricing()

