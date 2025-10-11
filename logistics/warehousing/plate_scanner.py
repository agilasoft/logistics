import frappe
from frappe import _
from frappe.utils import get_datetime, today, now_datetime
import re


@frappe.whitelist()
def search_plate_number(plate_no):
    """Wrapper method for the JavaScript call"""
    result = search_plate(plate_no)
    
    # Transform the result to match what the frontend expects
    if result.get("found") and result.get("entries"):
        transformed_entries = []
        for entry in result["entries"]:
            
            transformed_entries.append({
                "doctype": entry["document_type"],
                "reference": entry["document_name"],
                "docking": entry.get("dock_door", "N/A"),
                "status": entry.get("status", "unknown"),
                "customer": entry.get("customer"),
                "eta": entry.get("eta"),
                "plate_no": entry.get("plate_no"),
                "vehicle_type": entry.get("vehicle_type", "TRUCK")
            })
        return transformed_entries
    else:
        return []


@frappe.whitelist(allow_guest=True)
def search_plate(plate_number):
    """
    Search for plate number in all relevant doctypes
    Returns docking details and access permission
    """
    try:
        # Clean and validate plate number
        plate_number = clean_plate_number(plate_number)
        
        if not plate_number:
            return {
                "found": False,
                "message": "Invalid plate number format",
                "entries": []
            }
        
        # Search in different doctypes
        results = {
            "found": False,
            "plate_number": plate_number,
            "entries": [],
            "search_time": now_datetime().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Search in Warehouse Job Docks
        warehouse_job_results = search_warehouse_job_docks(plate_number)
        results["entries"].extend(warehouse_job_results)
        
        # Search in Inbound Order Docks
        inbound_order_results = search_inbound_order_docks(plate_number)
        results["entries"].extend(inbound_order_results)
        
        # Search in Release Order Docks
        release_order_results = search_release_order_docks(plate_number)
        results["entries"].extend(release_order_results)
        
        # Search in Transport Jobs
        transport_job_results = search_transport_jobs(plate_number)
        results["entries"].extend(transport_job_results)
        
        # Determine if found
        results["found"] = len(results["entries"]) > 0
        
        # Add access control logic
        results = add_access_control(results)
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Plate scanner error: {str(e)}", "Plate Scanner")
        return {
            "found": False,
            "error": str(e),
            "entries": []
        }


def clean_plate_number(plate_number):
    """Clean and standardize plate number"""
    if not plate_number:
        return None
    
    # Remove spaces and convert to uppercase
    cleaned = re.sub(r'\s+', '', str(plate_number).upper())
    
    # Basic validation - should contain letters and numbers
    if re.match(r'^[A-Z0-9]{3,10}$', cleaned):
        return cleaned
    
    return None


def search_warehouse_job_docks(plate_number):
    """Search plate number in Warehouse Job Dock entries"""
    try:
        # Query warehouse jobs with docks containing the plate number
        query = """
            SELECT DISTINCT
                wj.name as warehouse_job,
                wj.type as job_type,
                wj.customer,
                wj.docstatus,
                wj.job_open_date,
                wjd.name as dock_name,
                wjd.dock_door,
                wjd.eta,
                wjd.transport_company,
                wjd.vehicle_type,
                wjd.plate_no,
                wj.notes
            FROM `tabWarehouse Job` wj
            INNER JOIN `tabWarehouse Job Dock` wjd ON wj.name = wjd.parent
            WHERE wjd.plate_no = %s
            AND wj.docstatus < 2
            ORDER BY wj.creation DESC
        """
        
        results = frappe.db.sql(query, (plate_number,), as_dict=True)
        
        entries = []
        for row in results:
            entry = {
                "document_type": "Warehouse Job",
                "document_name": row.warehouse_job,
                "job_type": row.job_type,
                "customer": row.customer,
                "dock_door": row.dock_door,
                "eta": row.eta.strftime("%Y-%m-%d %H:%M") if row.eta else None,
                "transport_company": row.transport_company,
                "vehicle_type": row.vehicle_type,
                "plate_no": row.plate_no,
                "docstatus": row.docstatus,
                "job_open_date": row.job_open_date.strftime("%Y-%m-%d") if row.job_open_date else None,
                "notes": row.notes,
                "status": "pending"  # Will be updated by access control
            }
            entries.append(entry)
        
        return entries
        
    except Exception as e:
        frappe.log_error(f"Error searching warehouse job docks: {str(e)}", "Plate Scanner")
        return []


def search_inbound_order_docks(plate_number):
    """Search plate number in Inbound Order Dock entries"""
    try:
        query = """
            SELECT DISTINCT
                io.name as inbound_order,
                io.customer,
                io.docstatus,
                io.posting_date,
                iod.name as dock_name,
                iod.dock_door,
                iod.eta,
                iod.transport_company,
                iod.vehicle_type,
                iod.plate_no,
                io.notes
            FROM `tabInbound Order` io
            INNER JOIN `tabInbound Order Dock` iod ON io.name = iod.parent
            WHERE iod.plate_no = %s
            AND io.docstatus < 2
            ORDER BY io.creation DESC
        """
        
        results = frappe.db.sql(query, (plate_number,), as_dict=True)
        
        entries = []
        for row in results:
            entry = {
                "document_type": "Inbound Order",
                "document_name": row.inbound_order,
                "customer": row.customer,
                "dock_door": row.dock_door,
                "eta": row.eta.strftime("%Y-%m-%d %H:%M") if row.eta else None,
                "transport_company": row.transport_company,
                "vehicle_type": row.vehicle_type,
                "plate_no": row.plate_no,
                "docstatus": row.docstatus,
                "posting_date": row.posting_date.strftime("%Y-%m-%d") if row.posting_date else None,
                "notes": row.notes,
                "status": "pending"  # Will be updated by access control
            }
            entries.append(entry)
        
        return entries
        
    except Exception as e:
        frappe.log_error(f"Error searching inbound order docks: {str(e)}", "Plate Scanner")
        return []


def search_release_order_docks(plate_number):
    """Search plate number in Release Order Dock entries"""
    try:
        query = """
            SELECT DISTINCT
                ro.name as release_order,
                ro.customer,
                ro.docstatus,
                ro.posting_date,
                rod.name as dock_name,
                rod.dock_door,
                rod.eta,
                rod.transport_company,
                rod.vehicle_type,
                rod.plate_no,
                ro.notes
            FROM `tabRelease Order` ro
            INNER JOIN `tabRelease Order Dock` rod ON ro.name = rod.parent
            WHERE rod.plate_no = %s
            AND ro.docstatus < 2
            ORDER BY ro.creation DESC
        """
        
        results = frappe.db.sql(query, (plate_number,), as_dict=True)
        
        entries = []
        for row in results:
            entry = {
                "document_type": "Release Order",
                "document_name": row.release_order,
                "customer": row.customer,
                "dock_door": row.dock_door,
                "eta": row.eta.strftime("%Y-%m-%d %H:%M") if row.eta else None,
                "transport_company": row.transport_company,
                "vehicle_type": row.vehicle_type,
                "plate_no": row.plate_no,
                "docstatus": row.docstatus,
                "posting_date": row.posting_date.strftime("%Y-%m-%d") if row.posting_date else None,
                "notes": row.notes,
                "status": "pending"  # Will be updated by access control
            }
            entries.append(entry)
        
        return entries
        
    except Exception as e:
        frappe.log_error(f"Error searching release order docks: {str(e)}", "Plate Scanner")
        return []


def search_transport_jobs(plate_number):
    """Search plate number in Transport Job entries (using container_no field)"""
    try:
        query = """
            SELECT DISTINCT
                tj.name as transport_job,
                tj.customer,
                tj.docstatus,
                tj.booking_date,
                tj.transport_order,
                tj.vehicle_type,
                tj.container_no,
                tj.hazardous,
                tj.refrigeration,
                tj.notes
            FROM `tabTransport Job` tj
            WHERE tj.container_no = %s
            AND tj.docstatus < 2
            ORDER BY tj.creation DESC
        """
        
        results = frappe.db.sql(query, (plate_number,), as_dict=True)
        
        entries = []
        for row in results:
            entry = {
                "document_type": "Transport Job",
                "document_name": row.transport_job,
                "customer": row.customer,
                "dock_door": "N/A",
                "eta": None,
                "transport_company": None,
                "vehicle_type": row.vehicle_type,
                "plate_no": row.container_no,
                "docstatus": row.docstatus,
                "booking_date": row.booking_date.strftime("%Y-%m-%d") if row.booking_date else None,
                "notes": row.notes,
                "hazardous": row.hazardous,
                "refrigeration": row.refrigeration,
                "transport_order": row.transport_order,
                "status": "pending"  # Will be updated by access control
            }
            entries.append(entry)
        
        return entries
        
    except Exception as e:
        frappe.log_error(f"Error searching transport jobs: {str(e)}", "Plate Scanner")
        return []


def add_access_control(results):
    """Add access control logic based on document status and business rules"""
    try:
        for entry in results["entries"]:
            # Determine access status based on document status and business rules
            
            # Rule 1: Submitted documents (docstatus = 1) are generally allowed
            if entry["docstatus"] == 1:
                entry["status"] = "allowed"
                entry["access_reason"] = "Document is submitted and active"
            
            # Rule 2: Draft documents (docstatus = 0) need approval
            elif entry["docstatus"] == 0:
                entry["status"] = "pending"
                entry["access_reason"] = "Document is in draft status - requires approval"
            
            # Rule 3: Cancelled documents (docstatus = 2) are denied
            elif entry["docstatus"] == 2:
                entry["status"] = "denied"
                entry["access_reason"] = "Document is cancelled"
            
            # Rule 4: Check if ETA is valid (not past due by more than 24 hours)
            if entry.get("eta"):
                eta_datetime = get_datetime(entry["eta"])
                current_time = now_datetime()
                time_diff = (current_time - eta_datetime).total_seconds()
                
                # If ETA is more than 24 hours past, mark as pending for review
                if time_diff > 86400:  # 24 hours in seconds
                    if entry["status"] == "allowed":
                        entry["status"] = "pending"
                        entry["access_reason"] = "ETA is overdue - requires manual review"
            
            # Rule 5: Special handling for hazardous materials
            if entry.get("hazardous"):
                if entry["status"] == "allowed":
                    entry["status"] = "pending"
                    entry["access_reason"] = "Hazardous materials - requires special approval"
            
            # Rule 6: Add security notes for denied access
            if entry["status"] == "denied":
                entry["security_alert"] = True
                entry["access_reason"] = "Access denied - document not active"
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in access control: {str(e)}", "Plate Scanner")
        return results


@frappe.whitelist(allow_guest=True)
def get_plate_scan_history(limit=10):
    """Get recent plate scan history (for admin purposes)"""
    try:
        # This would typically be stored in a separate log table
        # For now, return a simple response
        return {
            "message": "Scan history feature not implemented yet",
            "scans": []
        }
    except Exception as e:
        frappe.log_error(f"Error getting scan history: {str(e)}", "Plate Scanner")
        return {"error": str(e)}


@frappe.whitelist()
def log_plate_scan(plate_number, scan_result, user_ip=None):
    """Log plate scan for audit purposes"""
    try:
        # Create audit log entry
        log_entry = frappe.get_doc({
            "doctype": "Plate Scan Log",
            "plate_number": plate_number,
            "scan_result": scan_result,
            "user_ip": user_ip or frappe.local.request.environ.get('REMOTE_ADDR'),
            "user_agent": frappe.local.request.environ.get('HTTP_USER_AGENT'),
            "scan_time": now_datetime()
        })
        
        # Only insert if the doctype exists
        if frappe.db.exists("DocType", "Plate Scan Log"):
            log_entry.insert(ignore_permissions=True)
            frappe.db.commit()
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"Error logging plate scan: {str(e)}", "Plate Scanner")
        return {"error": str(e)}

