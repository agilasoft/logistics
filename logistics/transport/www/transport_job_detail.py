# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime, formatdate
from typing import Dict, Any, List, Optional


def get_context(context):
    """Get context for transport job detail page"""
    
    # Get job name from URL
    job_name = frappe.form_dict.get('name')
    if not job_name:
        frappe.throw(_("Transport Job not found"), frappe.PermissionError)
    
    # Get customer from request
    customer = get_customer_from_request()
    if not customer:
        frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
    
    # Get transport job
    try:
        job = frappe.get_doc("Transport Job", job_name)
        
        # Check if customer has access to this job
        if job.customer != customer:
            frappe.throw(_("You don't have permission to view this transport job"), frappe.PermissionError)
            
    except frappe.DoesNotExistError:
        frappe.throw(_("Transport Job not found"), frappe.PermissionError)
    
    # Get customer info
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        customer_email = customer_doc.email_id
    except:
        customer_name = "Unknown Customer"
        customer_email = ""
    
    # Get job details
    job_data = get_job_details(job)
    
    # Check if any leg has "Started" status to show vehicle location
    show_vehicle_location = False
    if job_data and job_data.get('legs'):
        for leg in job_data['legs']:
            if leg.get('status') == 'Started':
                show_vehicle_location = True
                break
    
    # Get transport settings for map configuration
    try:
        transport_settings = frappe.get_single("Transport Settings")
        map_renderer = getattr(transport_settings, 'map_renderer', 'OpenStreetMap')
    except:
        map_renderer = 'OpenStreetMap'
    
    context.update({
        "job": job_data,
        "customer_id": customer,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "title": f"Transport Job {job_name}",
        "page_title": f"Transport Job {job_name}",
        "map_renderer": map_renderer,
        "show_vehicle_tracking": show_vehicle_location,
        "show_route_map": show_vehicle_location,
        "parents": [
            {"label": "Transport Jobs", "route": "/transport-portal"}
        ]
    })
    
    return context


def get_customer_from_request():
    """Extract customer from request parameters"""
    # Try URL parameter first
    customer = frappe.form_dict.get('customer')
    if customer:
        return customer
    
    # Try session variable
    customer = frappe.session.get('customer')
    if customer:
        return customer
    
    # Try user email
    user = frappe.session.user
    if user and user != "Guest":
        customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"],
            limit=1
        )
        if customers:
            return customers[0].name
    
    return None


def get_job_details(job):
    """Get detailed information about a transport job"""
    try:
        # Get job legs
        legs = get_job_legs(job.name)
        
        # Get vehicle information
        vehicle = get_job_vehicle(job.name)
        
        # Get job items if any
        items = get_job_items(job.name)
        
        # Get job documents
        documents = get_job_documents(job.name)
        
        # Get job status history
        status_history = get_job_status_history(job.name)
        
        return {
            "name": job.name,
            "customer": job.customer,
            "booking_date": job.booking_date,
            "status": job.status,
            "vehicle_type": job.vehicle_type,
            "load_type": job.load_type,
            "customer_ref_no": job.customer_ref_no,
            "transport_order": job.transport_order,
            "company": job.company,
            "hazardous": job.hazardous,
            "refrigeration": job.refrigeration,
            "container_type": job.container_type,
            "container_no": job.container_no,
            "remarks": job.remarks,
            "legs": legs,
            "vehicle": vehicle,
            "items": items,
            "documents": documents,
            "status_history": status_history,
            "creation": job.creation,
            "modified": job.modified
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting job details: {str(e)}", "Transport Portal")
        return None


def get_job_legs(job_name):
    """Get transport legs for a specific job"""
    try:
        legs = frappe.get_all(
            "Transport Leg",
            filters={"transport_job": job_name},
            fields=[
                "name", "facility_from", "facility_to", "facility_type_from", 
                "facility_type_to", "status", "distance_km", "duration_min", 
                "pick_window_start", "pick_window_end", "drop_window_start", 
                "drop_window_end", "order", "remarks"
            ],
            order_by="`order` asc"
        )
        
        # Get facility names and details
        for leg in legs:
            if leg["facility_from"] and leg["facility_type_from"]:
                try:
                    facility_from_doc = frappe.get_doc(leg["facility_type_from"], leg["facility_from"])
                    leg["facility_from_name"] = facility_from_doc.get("name") or leg["facility_from"]
                    leg["facility_from_address"] = getattr(facility_from_doc, 'address', '')
                except:
                    leg["facility_from_name"] = leg["facility_from"]
                    leg["facility_from_address"] = ""
            else:
                leg["facility_from_name"] = leg["facility_from"]
                leg["facility_from_address"] = ""
                
            if leg["facility_to"] and leg["facility_type_to"]:
                try:
                    facility_to_doc = frappe.get_doc(leg["facility_type_to"], leg["facility_to"])
                    leg["facility_to_name"] = facility_to_doc.get("name") or leg["facility_to"]
                    leg["facility_to_address"] = getattr(facility_to_doc, 'address', '')
                except:
                    leg["facility_to_name"] = leg["facility_to"]
                    leg["facility_to_address"] = ""
            else:
                leg["facility_to_name"] = leg["facility_to"]
                leg["facility_to_address"] = ""
        
        return legs
        
    except Exception as e:
        frappe.log_error(f"Error getting job legs: {str(e)}", "Transport Portal")
        return []


def get_job_vehicle(job_name):
    """Get vehicle information for a job through run sheet"""
    try:
        # Find run sheet that contains this job
        run_sheet_legs = frappe.get_all(
            "Run Sheet Leg",
            filters={"transport_job": job_name},
            fields=["parent"],
            limit=1
        )
        
        if not run_sheet_legs:
            return None
            
        run_sheet_name = run_sheet_legs[0]["parent"]
        run_sheet = frappe.get_doc("Run Sheet", run_sheet_name)
        
        if not run_sheet.vehicle:
            return None
            
        # Get vehicle details
        vehicle = frappe.get_doc("Transport Vehicle", run_sheet.vehicle)
        
        # Get vehicle position
        position = get_vehicle_position(vehicle.name)
        
        return {
            "name": vehicle.name,
            "plate_number": vehicle.plate_number,
            "vehicle_type": vehicle.vehicle_type,
            "driver_name": run_sheet.driver_name or "Unknown",
            "driver": run_sheet.driver,
            "status": get_vehicle_status(vehicle.name),
            "location": position,
            "run_sheet": run_sheet_name,
            "run_sheet_status": run_sheet.status
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting job vehicle: {str(e)}", "Transport Portal")
        return None


def get_job_items(job_name):
    """Get items for a transport job if any"""
    try:
        # Check if job has items (this would depend on your Transport Job structure)
        # For now, return empty list as Transport Job might not have items
        return []
    except Exception as e:
        frappe.log_error(f"Error getting job items: {str(e)}", "Transport Portal")
        return []


def get_job_documents(job_name):
    """Get documents attached to a transport job"""
    try:
        # Get file attachments
        files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Transport Job",
                "attached_to_name": job_name
            },
            fields=["name", "file_name", "file_url", "creation"],
            order_by="creation desc"
        )
        
        return files
    except Exception as e:
        frappe.log_error(f"Error getting job documents: {str(e)}", "Transport Portal")
        return []


def get_job_status_history(job_name):
    """Get status change history for a transport job"""
    try:
        # Get version history
        versions = frappe.get_all(
            "Version",
            filters={
                "ref_doctype": "Transport Job",
                "docname": job_name
            },
            fields=["name", "creation", "data"],
            order_by="creation desc",
            limit=10
        )
        
        history = []
        for version in versions:
            try:
                data = frappe.parse_json(version.data)
                if data and 'changed' in data:
                    for field, change in data['changed'].items():
                        if field == 'status':
                            history.append({
                                "field": field,
                                "old_value": change[0],
                                "new_value": change[1],
                                "timestamp": version.creation,
                                "user": data.get('user', 'System')
                            })
            except:
                continue
        
        return history
    except Exception as e:
        frappe.log_error(f"Error getting job status history: {str(e)}", "Transport Portal")
        return []


def get_vehicle_position(vehicle_name):
    """Get current vehicle position"""
    try:
        vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
        
        if vehicle.last_telematics_lat and vehicle.last_telematics_lon:
            return {
                "lat": float(vehicle.last_telematics_lat),
                "lng": float(vehicle.last_telematics_lon),
                "timestamp": vehicle.last_telematics_ts,
                "speed_kph": vehicle.last_speed_kph,
                "ignition": vehicle.last_ignition_on
            }
        else:
            # Return default position if no telematics data
            return {
                "lat": 14.5995,  # Default to Manila
                "lng": 120.9842,
                "timestamp": None,
                "speed_kph": 0,
                "ignition": False
            }
            
    except Exception as e:
        frappe.log_error(f"Error getting vehicle position: {str(e)}", "Transport Portal")
        return None


def get_vehicle_status(vehicle_name):
    """Get current vehicle status"""
    try:
        # Check if vehicle is assigned to any active run sheet
        active_run_sheets = frappe.get_all(
            "Run Sheet",
            filters={
                "vehicle": vehicle_name,
                "status": ["in", ["Dispatched", "In-Progress"]]
            },
            fields=["name", "status"],
            limit=1
        )
        
        if active_run_sheets:
            return "In Transit"
        else:
            return "Available"
            
    except Exception as e:
        frappe.log_error(f"Error getting vehicle status: {str(e)}", "Transport Portal")
        return "Unknown"
