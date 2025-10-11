import frappe

def execute():
    """Update Sales Quote Transport with comprehensive cargo details and multiple lanes support"""
    
    print("Starting Sales Quote Transport enhancements...")
    
    try:
        # Update Sales Quote Transport DocType
        update_sales_quote_transport_doctype()
        
        # Update Sales Quote main DocType
        update_sales_quote_main_doctype()
        
        print("Sales Quote Transport enhancements completed successfully!")
        
    except Exception as e:
        print(f"Sales Quote Transport enhancements failed: {str(e)}")
        frappe.log_error(f"Sales Quote Transport enhancements failed: {str(e)}")
        raise

def update_sales_quote_transport_doctype():
    """Update Sales Quote Transport DocType with new fields"""
    
    if not frappe.db.exists("DocType", "Sales Quote Transport"):
        print("Sales Quote Transport DocType not found!")
        return
    
    doctype = frappe.get_doc("DocType", "Sales Quote Transport")
    doctype.module = "Pricing Center"
    
    # Define new fields to add
    new_fields = [
        {
            "fieldname": "service_description",
            "fieldtype": "Data",
            "label": "Service Description",
            "fetch_from": "item_code.item_name"
        },
        {
            "fieldname": "billing_method",
            "fieldtype": "Select",
            "label": "Billing Method",
            "options": "Per Volume\nPer Weight\nPer Trip (FTL)\nPer Distance\nPer Pallet",
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
            "fieldname": "duration_min",
            "fieldtype": "Int",
            "label": "Duration (minutes)"
        },
        {
            "fieldname": "weight",
            "fieldtype": "Float",
            "label": "Weight",
            "precision": "3"
        },
        {
            "fieldname": "weight_uom",
            "fieldtype": "Link",
            "label": "Weight UOM",
            "options": "UOM"
        },
        {
            "fieldname": "volume",
            "fieldtype": "Float",
            "label": "Volume",
            "precision": "3"
        },
        {
            "fieldname": "volume_uom",
            "fieldtype": "Link",
            "label": "Volume UOM",
            "options": "UOM"
        },
        {
            "fieldname": "pallets",
            "fieldtype": "Int",
            "label": "Pallets"
        },
        {
            "fieldname": "cargo_type",
            "fieldtype": "Link",
            "label": "Cargo Type",
            "options": "Cargo Type"
        },
        {
            "fieldname": "commodity",
            "fieldtype": "Data",
            "label": "Commodity"
        },
        {
            "fieldname": "equipment_required",
            "fieldtype": "Link",
            "label": "Equipment Required",
            "options": "Equipment Type"
        },
        {
            "fieldname": "cargo_value",
            "fieldtype": "Currency",
            "label": "Cargo Value",
            "precision": "2"
        },
        {
            "fieldname": "insurance_required",
            "fieldtype": "Check",
            "label": "Insurance Required",
            "default": 0
        },
        {
            "fieldname": "hazardous",
            "fieldtype": "Check",
            "label": "Hazardous",
            "default": 0
        },
        {
            "fieldname": "refrigeration",
            "fieldtype": "Check",
            "label": "Refrigeration",
            "default": 0
        },
        {
            "fieldname": "special_handling",
            "fieldtype": "Text",
            "label": "Special Handling Instructions"
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
    
    # Add new fields
    existing_fieldnames = [field.fieldname for field in doctype.fields]
    
    for field_data in new_fields:
        if field_data["fieldname"] not in existing_fieldnames:
            doctype.append("fields", field_data)
            print(f"Added field: {field_data['fieldname']}")
    
    # Save the updated DocType
    doctype.save()
    frappe.db.commit()
    print("Sales Quote Transport DocType updated successfully!")

def update_sales_quote_main_doctype():
    """Update main Sales Quote DocType to include transport lanes"""
    
    if not frappe.db.exists("DocType", "Sales Quote"):
        print("Sales Quote DocType not found!")
        return
    
    doctype = frappe.get_doc("DocType", "Sales Quote")
    
    # Check if transport_lanes field already exists
    existing_fieldnames = [field.fieldname for field in doctype.fields]
    
    if "transport_lanes" not in existing_fieldnames:
        # Add transport_lanes child table
        transport_lanes_field = {
            "fieldname": "transport_lanes",
            "fieldtype": "Table",
            "label": "Transport Lanes",
            "options": "Transport Lane"
        }
        
        doctype.append("fields", transport_lanes_field)
        print("Added transport_lanes field to Sales Quote")
    
    # Save the updated DocType
    doctype.save()
    frappe.db.commit()
    print("Sales Quote main DocType updated successfully!")

