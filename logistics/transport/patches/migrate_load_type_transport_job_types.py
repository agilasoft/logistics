# -*- coding: utf-8 -*-
"""
Migration script to populate Load Type transport job type boolean flags
based on existing business rules.

Migration Rules:
- FCL → container = 1, others = 0
- LCL, LTL, FTL, LSE → non_container = 1, others = 0
- ULD → all transport job flags = 0
- Other load types → non_container = 1 (default for transport load types)
"""

import frappe


def execute():
    """Migrate Load Type transport job type flags."""
    
    # Get all Load Types
    load_types = frappe.get_all("Load Type", fields=["name", "load_type_name", "transport"])
    
    for load_type in load_types:
        load_type_name = load_type.get("load_type_name", "").upper()
        is_transport = load_type.get("transport", 0)
        
        # Initialize all flags to 0
        updates = {
            "container": 0,
            "non_container": 0,
            "special": 0,
            "oversized": 0,
            "multimodal": 0,
            "heavy_haul": 0
        }
        
        # Apply migration rules
        if load_type_name == "FCL":
            updates["container"] = 1
        elif load_type_name in ["LCL", "LTL", "FTL", "LSE"]:
            updates["non_container"] = 1
        elif load_type_name == "ULD":
            # ULD → all flags = 0 (already set above)
            pass
        elif is_transport:
            # Default for other transport load types → non_container = 1
            updates["non_container"] = 1
        
        # Update the Load Type
        try:
            frappe.db.set_value("Load Type", load_type["name"], updates)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                f"Error migrating Load Type {load_type['name']}: {str(e)}",
                "Load Type Migration Error"
            )
    
    frappe.msgprint("Load Type transport job type flags migration completed.")



