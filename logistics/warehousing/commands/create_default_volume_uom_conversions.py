# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Bench Command: Create Default Volume UOM Conversion Records
================================================================

This command creates default Dimension Volume UOM Conversion records for
common UOM combinations.

Usage:
    bench --site your-site execute logistics.warehousing.commands.create_default_volume_uom_conversions.create_default_conversions
"""

import frappe


def create_default_conversions():
    """Create default Dimension Volume UOM Conversion records"""
    
    print("🚀 Creating default Dimension Volume UOM Conversion records...")
    
    # Default conversions to create
    default_conversions = [
        {
            "dimension_uom": "CM",
            "volume_uom": "CBM",
            "conversion_factor": 0.000001,
            "description": "Convert cubic centimeters to cubic meters (1 cm³ = 0.000001 m³)",
            "is_standard": 1,
            "enabled": 1
        },
        {
            "dimension_uom": "M",
            "volume_uom": "CBM",
            "conversion_factor": 1.0,
            "description": "Convert cubic meters to cubic meters (1 m³ = 1 m³)",
            "is_standard": 1,
            "enabled": 1
        },
        {
            "dimension_uom": "MM",
            "volume_uom": "CBM",
            "conversion_factor": 0.000000001,
            "description": "Convert cubic millimeters to cubic meters (1 mm³ = 0.000000001 m³)",
            "is_standard": 1,
            "enabled": 1
        },
        {
            "dimension_uom": "IN",
            "volume_uom": "CFT",
            "conversion_factor": 0.000578704,
            "description": "Convert cubic inches to cubic feet (1 in³ = 1/1728 ft³ ≈ 0.000578704 ft³)",
            "is_standard": 1,
            "enabled": 1
        },
        {
            "dimension_uom": "FT",
            "volume_uom": "CFT",
            "conversion_factor": 1.0,
            "description": "Convert cubic feet to cubic feet (1 ft³ = 1 ft³)",
            "is_standard": 1,
            "enabled": 1
        },
        {
            "dimension_uom": "CM",
            "volume_uom": "CM3",
            "conversion_factor": 1.0,
            "description": "Convert cubic centimeters to cubic centimeters (1 cm³ = 1 cm³)",
            "is_standard": 1,
            "enabled": 1
        }
    ]
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    for conv_data in default_conversions:
        try:
            # Check if conversion already exists
            dimension_uom = conv_data["dimension_uom"]
            volume_uom = conv_data["volume_uom"]
            
            existing = frappe.db.exists(
                "Dimension Volume UOM Conversion",
                {
                    "dimension_uom": dimension_uom,
                    "volume_uom": volume_uom
                }
            )
            
            if existing:
                print(f"  ℹ️  Conversion {dimension_uom} → {volume_uom} already exists, skipping")
                skipped_count += 1
                continue
            
            # Check if UOMs exist
            if not frappe.db.exists("UOM", dimension_uom):
                print(f"  ⚠️  Dimension UOM '{dimension_uom}' does not exist, skipping conversion")
                error_count += 1
                continue
            
            if not frappe.db.exists("UOM", volume_uom):
                print(f"  ⚠️  Volume UOM '{volume_uom}' does not exist, skipping conversion")
                error_count += 1
                continue
            
            # Create conversion record
            conversion_doc = frappe.get_doc({
                "doctype": "Dimension Volume UOM Conversion",
                **conv_data
            })
            conversion_doc.insert(ignore_permissions=True)
            created_count += 1
            print(f"  ✅ Created conversion: {dimension_uom} → {volume_uom} (factor: {conv_data['conversion_factor']})")
            
        except Exception as e:
            print(f"  ❌ Error creating conversion {dimension_uom} → {volume_uom}: {str(e)}")
            error_count += 1
            frappe.log_error(
                f"Error creating Dimension Volume UOM Conversion: {str(e)}",
                "Create Default Conversions Error"
            )
    
    frappe.db.commit()
    
    print(f"\n✅ Default conversions creation completed!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Errors: {error_count}")


if __name__ == "__main__":
    create_default_conversions()

