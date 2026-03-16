#!/usr/bin/env python3
"""
Test script to verify volume and chargeable weight calculations for Air Booking Packages.
This script can be used to check calculations for a specific Air Booking document.
"""

import frappe
from frappe.utils import flt

def check_air_booking_calculations(air_booking_name):
    """Check volume and chargeable weight calculations for an Air Booking."""
    
    try:
        # Get the Air Booking document
        abk = frappe.get_doc("Air Booking", air_booking_name)
        
        print("=" * 80)
        print(f"Air Booking: {abk.name}")
        print("=" * 80)
        print(f"Volume: {abk.volume}")
        print(f"Weight: {abk.weight}")
        print(f"Chargeable: {abk.chargeable}")
        print(f"Volume to Weight Factor Type: {abk.volume_to_weight_factor_type}")
        print(f"Custom Divisor: {abk.custom_volume_to_weight_divisor}")
        print(f"Airline: {abk.airline}")
        print(f"Company: {abk.company}")
        print(f"Override Volume Weight: {getattr(abk, 'override_volume_weight', False)}")
        
        # Get divisor
        divisor = abk.get_volume_to_weight_divisor()
        print(f"Divisor used: {divisor}")
        
        # Calculate expected chargeable weight for header
        if abk.volume and divisor:
            volume_weight = flt(abk.volume) * (1000000.0 / divisor)
            print(f"Volume Weight: {volume_weight}")
        else:
            volume_weight = 0
        
        if abk.weight and volume_weight:
            expected_chargeable = max(flt(abk.weight), volume_weight)
        elif abk.weight:
            expected_chargeable = flt(abk.weight)
        elif volume_weight:
            expected_chargeable = volume_weight
        else:
            expected_chargeable = 0
        
        print(f"Expected Chargeable: {expected_chargeable}")
        print(f"Actual Chargeable: {abk.chargeable}")
        match = abs(flt(abk.chargeable or 0) - expected_chargeable) < 0.01
        print(f"Header Match: {match}")
        if not match:
            print(f"  ⚠️  MISMATCH: Expected {expected_chargeable}, got {abk.chargeable}")
        
        print("\n" + "=" * 80)
        print("PACKAGES:")
        print("=" * 80)
        
        # Get packages (chargeable weight is computed on parent only)
        packages = frappe.get_all("Air Booking Packages", 
            filters={"parent": air_booking_name, "parenttype": "Air Booking"},
            fields=["name", "length", "width", "height", "dimension_uom", "volume", "volume_uom", 
                    "weight", "weight_uom", "no_of_packs"],
            order_by="idx")
        
        if not packages:
            print("No packages found.")
            return
        
        total_issues = 0
        
        for pkg_data in packages:
            pkg = frappe.get_doc("Air Booking Packages", pkg_data.name)
            print(f"\nPackage: {pkg.name} (idx: {pkg.idx})")
            print(f"  No of Packs: {pkg.no_of_packs}")
            print(f"  Dimensions: {pkg.length} x {pkg.width} x {pkg.height} {pkg.dimension_uom}")
            print(f"  Volume: {pkg.volume} {pkg.volume_uom}")
            print(f"  Weight: {pkg.weight} {pkg.weight_uom}")
            
            # Verify volume calculation from dimensions
            if pkg.length and pkg.width and pkg.height:
                from logistics.utils.measurements import calculate_volume_from_dimensions, get_default_uoms
                dimension_uom = pkg.dimension_uom
                volume_uom = pkg.volume_uom
                company = abk.company
                if not dimension_uom or not volume_uom:
                    defaults = get_default_uoms(company=company)
                    dimension_uom = dimension_uom or defaults.get("dimension")
                    volume_uom = volume_uom or defaults.get("volume")
                
                expected_volume = calculate_volume_from_dimensions(
                    length=pkg.length,
                    width=pkg.width,
                    height=pkg.height,
                    dimension_uom=dimension_uom,
                    volume_uom=volume_uom,
                    company=company,
                )
                print(f"  Expected Volume (from dimensions): {expected_volume} {volume_uom}")
                volume_match = abs(flt(pkg.volume or 0) - expected_volume) < 0.01
                print(f"  Volume Match: {volume_match}")
                if not volume_match:
                    print(f"    ⚠️  VOLUME MISMATCH: Expected {expected_volume}, got {pkg.volume}")
                    total_issues += 1
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        if total_issues == 0:
            print("✅ All calculations are correct!")
        else:
            print(f"⚠️  Found {total_issues} calculation issue(s)")
        
    except frappe.DoesNotExistError:
        print(f"❌ Air Booking '{air_booking_name}' not found.")
        print("\nAvailable Air Booking documents:")
        docs = frappe.get_all("Air Booking", 
            fields=["name", "volume", "weight", "chargeable"],
            limit=10,
            order_by="creation desc")
        for doc in docs:
            print(f"  - {doc.name}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        air_booking_name = sys.argv[1]
    else:
        air_booking_name = "ABK-000000132"
    
    frappe.init(site="all")
    frappe.connect()
    
    check_air_booking_calculations(air_booking_name)
    
    frappe.destroy()
