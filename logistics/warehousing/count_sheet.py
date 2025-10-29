# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


# =============================================================================
# COUNT SHEET INTERFACE API
# =============================================================================

@frappe.whitelist()
def get_warehouse_job_count_data(warehouse_job: str):
    """Get count data for warehouse job interface"""
    try:
        job = frappe.get_doc("Warehouse Job", warehouse_job)
        if job.type != "Stocktake":
            return {"error": "Only Stocktake jobs are supported"}
        
        # Get count data
        counts = frappe.get_all(
            "Warehouse Job Count",
            filters={"parent": warehouse_job, "parenttype": "Warehouse Job"},
            fields=["name", "location", "handling_unit", "item", 
                   "system_count", "actual_quantity", "serial_no", "batch_no", "counted"]
        )
        
        # Group by location
        locations = {}
        items = []
        
        for count in counts:
            location_key = count.get("location", "No Location")
            handling_unit = count.get("handling_unit", "")
            
            # Get item details from linked Item doctype
            item_code = count.get("item")
            item_name = ""
            uom = "EA"  # Default UOM
            
            if item_code:
                try:
                    item_doc = frappe.get_doc("Warehouse Item", item_code)
                    item_name = item_doc.item_name or ""
                    uom = item_doc.uom or "EA"
                except:
                    # If item not found, use defaults
                    item_name = item_code
                    uom = "EA"
            
            # Add to locations
            if location_key not in locations:
                locations[location_key] = {
                    "name": location_key,
                    "handling_unit": handling_unit,
                    "counted": False,
                    "total_items": 0,
                    "counted_items": 0
                }
            
            locations[location_key]["total_items"] += 1
            if count.get("counted"):
                locations[location_key]["counted_items"] += 1
                locations[location_key]["counted"] = True
            
            # Add to items
            items.append({
                "name": count.get("name"),
                "location": location_key,
                "handling_unit": handling_unit,
                "item": item_code,
                "item_name": item_name,
                "uom": uom,
                "system_count": count.get("system_count", 0),
                "actual_quantity": count.get("actual_quantity"),
                "blind_count": job.blind_count,
                "serial_no": count.get("serial_no"),
                "batch_no": count.get("batch_no"),
                "counted": count.get("counted", 0)
            })
        
        return {
            "locations": list(locations.values()),
            "items": items,
            "job_info": {
                "name": job.name,
                "type": job.type,
                "blind_count": job.blind_count,
                "count_date": job.count_date
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting warehouse job count data: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def save_count_data(warehouse_job: str, item_name: str, actual_count: float):
    """Save actual count for an item"""
    try:
        # Update the count record
        frappe.db.set_value("Warehouse Job Count", item_name, "actual_quantity", actual_count)
        frappe.db.set_value("Warehouse Job Count", item_name, "counted", 1)
        frappe.db.commit()
        
        return {"success": True, "message": "Count saved successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error saving count data: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def get_count_summary(warehouse_job: str):
    """Get count summary for warehouse job"""
    try:
        job = frappe.get_doc("Warehouse Job", warehouse_job)
        if job.type != "Stocktake":
            return {"error": "Only Stocktake jobs are supported"}
        
        # Get count statistics
        total_items = frappe.db.count("Warehouse Job Count", {"parent": warehouse_job})
        counted_items = frappe.db.count("Warehouse Job Count", {
            "parent": warehouse_job,
            "actual_quantity": ["!=", None]
        })
        pending_items = total_items - counted_items
        
        # Get location statistics
        locations = frappe.db.sql("""
            SELECT location, 
                   COUNT(*) as total_items,
                   COUNT(CASE WHEN actual_quantity IS NOT NULL THEN 1 END) as counted_items
            FROM `tabWarehouse Job Count`
            WHERE parent = %s
            GROUP BY location
        """, (warehouse_job,), as_dict=True)
        
        return {
            "total_items": total_items,
            "counted_items": counted_items,
            "pending_items": pending_items,
            "completion_percentage": round((counted_items / total_items * 100) if total_items > 0 else 0, 2),
            "locations": locations
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting count summary: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def bulk_save_counts(warehouse_job: str, count_data: list):
    """Save multiple counts at once"""
    try:
        for item in count_data:
            frappe.db.set_value("Warehouse Job Count", item["name"], "actual_quantity", item["actual_count"])
        
        frappe.db.commit()
        
        return {"success": True, "message": f"Saved {len(count_data)} counts successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error saving bulk counts: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def reset_count_data(warehouse_job: str, location: str = None):
    """Reset count data for a location or entire job"""
    try:
        filters = {"parent": warehouse_job}
        if location:
            filters["location"] = location
            
        frappe.db.sql("""
            UPDATE `tabWarehouse Job Count`
            SET actual_quantity = NULL, counted = 0
            WHERE parent = %s
        """, (warehouse_job,))
        
        frappe.db.commit()
        
        return {"success": True, "message": "Count data reset successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error resetting count data: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def reset_single_count(warehouse_job: str, item_name: str):
    """Reset count data for a single item"""
    try:
        # Update the count record
        frappe.db.set_value("Warehouse Job Count", item_name, "actual_quantity", None)
        frappe.db.set_value("Warehouse Job Count", item_name, "counted", 0)
        frappe.db.commit()
        
        return {"success": True, "message": "Count reset successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error resetting single count: {str(e)}")
        return {"error": str(e)}
