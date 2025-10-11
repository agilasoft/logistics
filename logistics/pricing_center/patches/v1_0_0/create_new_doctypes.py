import frappe

def execute():
    """Create new DocTypes for Pricing Center functionality"""
    
    print("Creating new DocTypes for Pricing Center...")
    
    try:
        # Create Transport Lane DocType
        create_transport_lane_doctype()
        
        # Create Zip Code Zone Mapping DocType
        create_zip_code_zone_mapping_doctype()
        
        # Create Transport Zone DocType
        create_transport_zone_doctype()
        
        # Create supporting DocTypes
        create_supporting_doctypes()
        
        print("New DocTypes created successfully!")
        
    except Exception as e:
        print(f"New DocTypes creation failed: {str(e)}")
        frappe.log_error(f"New DocTypes creation failed: {str(e)}")
        raise

def create_transport_lane_doctype():
    """Create Transport Lane DocType"""
    
    if frappe.db.exists("DocType", "Transport Lane"):
        print("Transport Lane DocType already exists!")
        return
    
    doctype = frappe.new_doc("DocType")
    doctype.name = "Transport Lane"
    doctype.module = "Pricing Center"
    doctype.istable = 1
    doctype.editable_grid = 1
    
    # Define fields
    fields = [
        {
            "fieldname": "lane_sequence",
            "fieldtype": "Int",
            "label": "Lane Sequence",
            "reqd": 1
        },
        {
            "fieldname": "origin",
            "fieldtype": "Link",
            "label": "Origin",
            "options": "Location",
            "reqd": 1
        },
        {
            "fieldname": "destination",
            "fieldtype": "Link",
            "label": "Destination",
            "options": "Location",
            "reqd": 1
        },
        {
            "fieldname": "origin_zone",
            "fieldtype": "Link",
            "label": "Origin Zone",
            "options": "Transport Zone",
            "read_only": 1
        },
        {
            "fieldname": "destination_zone",
            "fieldtype": "Link",
            "label": "Destination Zone",
            "options": "Transport Zone",
            "read_only": 1
        },
        {
            "fieldname": "distance_km",
            "fieldtype": "Float",
            "label": "Distance (km)",
            "precision": "2"
        },
        {
            "fieldname": "vehicle_type",
            "fieldtype": "Link",
            "label": "Vehicle Type",
            "options": "Vehicle Type",
            "reqd": 1
        },
        {
            "fieldname": "billing_method",
            "fieldtype": "Select",
            "label": "Billing Method",
            "options": "Per Volume\nPer Weight\nPer Trip (FTL)\nPer Distance\nPer Pallet",
            "reqd": 1
        },
        {
            "fieldname": "quantity",
            "fieldtype": "Float",
            "label": "Quantity",
            "reqd": 1,
            "precision": "3"
        },
        {
            "fieldname": "rate",
            "fieldtype": "Currency",
            "label": "Rate",
            "reqd": 1,
            "precision": "2"
        },
        {
            "fieldname": "base_amount",
            "fieldtype": "Currency",
            "label": "Base Amount",
            "read_only": 1,
            "precision": "2"
        },
        {
            "fieldname": "discount_percentage",
            "fieldtype": "Percent",
            "label": "Discount %",
            "precision": "2"
        },
        {
            "fieldname": "discount_amount",
            "fieldtype": "Currency",
            "label": "Discount Amount",
            "read_only": 1,
            "precision": "2"
        },
        {
            "fieldname": "surcharge_amount",
            "fieldtype": "Currency",
            "label": "Surcharge Amount",
            "precision": "2"
        },
        {
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "label": "Total Amount",
            "read_only": 1,
            "precision": "2",
            "bold": 1
        },
        {
            "fieldname": "currency",
            "fieldtype": "Link",
            "label": "Currency",
            "options": "Currency",
            "reqd": 1
        },
        {
            "fieldname": "tariff_rate",
            "fieldtype": "Currency",
            "label": "Tariff Rate",
            "read_only": 1,
            "precision": "2"
        },
        {
            "fieldname": "tariff_source",
            "fieldtype": "Data",
            "label": "Tariff Source",
            "read_only": 1
        }
    ]
    
    # Add fields
    for field_data in fields:
        doctype.append("fields", field_data)
    
    doctype.save()
    frappe.db.commit()
    print("Transport Lane DocType created successfully!")

def create_zip_code_zone_mapping_doctype():
    """Create Zip Code Zone Mapping DocType"""
    
    if frappe.db.exists("DocType", "Zip Code Zone Mapping"):
        print("Zip Code Zone Mapping DocType already exists!")
        return
    
    doctype = frappe.new_doc("DocType")
    doctype.name = "Zip Code Zone Mapping"
    doctype.module = "Transport"
    doctype.is_submittable = 0
    
    # Define fields
    fields = [
        {
            "fieldname": "zip_code",
            "fieldtype": "Data",
            "label": "Zip Code",
            "reqd": 1,
            "unique": 1
        },
        {
            "fieldname": "postal_code",
            "fieldtype": "Data",
            "label": "Postal Code",
            "description": "Alternative postal code format"
        },
        {
            "fieldname": "transport_zone",
            "fieldtype": "Link",
            "label": "Transport Zone",
            "options": "Transport Zone",
            "reqd": 1
        },
        {
            "fieldname": "zone_priority",
            "fieldtype": "Int",
            "label": "Zone Priority",
            "default": 1,
            "description": "Priority for zone assignment (1 = highest)"
        },
        {
            "fieldname": "country",
            "fieldtype": "Link",
            "label": "Country",
            "options": "Country",
            "reqd": 1
        },
        {
            "fieldname": "state_province",
            "fieldtype": "Data",
            "label": "State/Province"
        },
        {
            "fieldname": "city",
            "fieldtype": "Data",
            "label": "City"
        },
        {
            "fieldname": "zone_type",
            "fieldtype": "Select",
            "label": "Zone Type",
            "options": "Urban\nSuburban\nRural\nRemote",
            "default": "Urban"
        },
        {
            "fieldname": "delivery_time_days",
            "fieldtype": "Int",
            "label": "Standard Delivery Time (Days)",
            "default": 1
        },
        {
            "fieldname": "enabled",
            "fieldtype": "Check",
            "label": "Enabled",
            "default": 1
        },
        {
            "fieldname": "notes",
            "fieldtype": "Text",
            "label": "Notes"
        }
    ]
    
    # Add fields
    for field_data in fields:
        doctype.append("fields", field_data)
    
    doctype.save()
    frappe.db.commit()
    print("Zip Code Zone Mapping DocType created successfully!")

def create_transport_zone_doctype():
    """Create Transport Zone DocType"""
    
    if frappe.db.exists("DocType", "Transport Zone"):
        print("Transport Zone DocType already exists!")
        return
    
    doctype = frappe.new_doc("DocType")
    doctype.name = "Transport Zone"
    doctype.module = "Transport"
    doctype.is_submittable = 0
    
    # Define fields
    fields = [
        {
            "fieldname": "zone_name",
            "fieldtype": "Data",
            "label": "Zone Name",
            "reqd": 1
        },
        {
            "fieldname": "zone_code",
            "fieldtype": "Data",
            "label": "Zone Code",
            "reqd": 1,
            "unique": 1
        },
        {
            "fieldname": "description",
            "fieldtype": "Text",
            "label": "Description"
        },
        {
            "fieldname": "enabled",
            "fieldtype": "Check",
            "label": "Enabled",
            "default": 1
        },
        {
            "fieldname": "zone_type",
            "fieldtype": "Select",
            "label": "Zone Type",
            "options": "Geographic\nService Area\nDelivery Zone\nPickup Zone\nUrban\nSuburban\nRural\nRemote",
            "default": "Geographic"
        },
        {
            "fieldname": "country",
            "fieldtype": "Link",
            "label": "Country",
            "options": "Country"
        },
        {
            "fieldname": "zip_code_range_from",
            "fieldtype": "Data",
            "label": "Zip Code Range From",
            "description": "Starting zip code for range"
        },
        {
            "fieldname": "zip_code_range_to",
            "fieldtype": "Data",
            "label": "Zip Code Range To",
            "description": "Ending zip code for range"
        },
        {
            "fieldname": "zone_priority",
            "fieldtype": "Int",
            "label": "Zone Priority",
            "default": 1,
            "description": "Priority for zone assignment (1 = highest)"
        },
        {
            "fieldname": "delivery_time_days",
            "fieldtype": "Int",
            "label": "Standard Delivery Time (Days)",
            "default": 1
        }
    ]
    
    # Add fields
    for field_data in fields:
        doctype.append("fields", field_data)
    
    doctype.save()
    frappe.db.commit()
    print("Transport Zone DocType created successfully!")

def create_supporting_doctypes():
    """Create supporting DocTypes"""
    
    # Create Cargo Type DocType
    if not frappe.db.exists("DocType", "Cargo Type"):
        create_cargo_type_doctype()
    
    # Create Equipment Type DocType
    if not frappe.db.exists("DocType", "Equipment Type"):
        create_equipment_type_doctype()

def create_cargo_type_doctype():
    """Create Cargo Type DocType"""
    doctype = frappe.new_doc("DocType")
    doctype.name = "Cargo Type"
    doctype.module = "Transport"
    doctype.is_submittable = 0
    
    fields = [
        {
            "fieldname": "cargo_type_name",
            "fieldtype": "Data",
            "label": "Cargo Type Name",
            "reqd": 1,
            "unique": 1
        },
        {
            "fieldname": "description",
            "fieldtype": "Text",
            "label": "Description"
        },
        {
            "fieldname": "hazardous",
            "fieldtype": "Check",
            "label": "Hazardous",
            "default": 0
        },
        {
            "fieldname": "refrigeration_required",
            "fieldtype": "Check",
            "label": "Refrigeration Required",
            "default": 0
        },
        {
            "fieldname": "special_handling",
            "fieldtype": "Check",
            "label": "Special Handling Required",
            "default": 0
        },
        {
            "fieldname": "enabled",
            "fieldtype": "Check",
            "label": "Enabled",
            "default": 1
        }
    ]
    
    for field_data in fields:
        doctype.append("fields", field_data)
    
    doctype.save()
    frappe.db.commit()
    print("Cargo Type DocType created successfully!")

def create_equipment_type_doctype():
    """Create Equipment Type DocType"""
    doctype = frappe.new_doc("DocType")
    doctype.name = "Equipment Type"
    doctype.module = "Transport"
    doctype.is_submittable = 0
    
    fields = [
        {
            "fieldname": "equipment_type_name",
            "fieldtype": "Data",
            "label": "Equipment Type Name",
            "reqd": 1,
            "unique": 1
        },
        {
            "fieldname": "description",
            "fieldtype": "Text",
            "label": "Description"
        },
        {
            "fieldname": "capacity_weight",
            "fieldtype": "Float",
            "label": "Capacity Weight (kg)",
            "precision": "2"
        },
        {
            "fieldname": "capacity_volume",
            "fieldtype": "Float",
            "label": "Capacity Volume (CBM)",
            "precision": "2"
        },
        {
            "fieldname": "special_requirements",
            "fieldtype": "Text",
            "label": "Special Requirements"
        },
        {
            "fieldname": "enabled",
            "fieldtype": "Check",
            "label": "Enabled",
            "default": 1
        }
    ]
    
    for field_data in fields:
        doctype.append("fields", field_data)
    
    doctype.save()
    frappe.db.commit()
    print("Equipment Type DocType created successfully!")

