# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime
from typing import Dict, Any, List, Optional


def get_context(context):
    """Get context for transport portal web page"""
    
    # Get customer from request
    customer = get_customer_from_request()
    
    if not customer:
        frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
    
    # Get customer info
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        customer_email = customer_doc.email_id
    except Exception:
        customer_name = "Unknown Customer"
        customer_email = ""
    
    # Get transport jobs for customer
    jobs = get_customer_jobs(customer)
    
    # Check if any job has legs with "Started" status to show vehicle tracking
    show_vehicle_tracking = False
    for job in jobs:
        if job.get('legs'):
            for leg in job['legs']:
                if leg.get('status') == 'Started':
                    show_vehicle_tracking = True
                    break
        if show_vehicle_tracking:
            break
    
    # Get transport settings for map configuration
    try:
        transport_settings = frappe.get_single("Transport Settings")
        map_renderer = getattr(transport_settings, 'map_renderer', 'OpenStreetMap')
    except Exception:
        map_renderer = 'OpenStreetMap'
    
    context.update({
        "customer_id": customer,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "jobs": jobs,
        "total_jobs": len(jobs),
        "title": f"Transport Jobs - {customer_name}",
        "page_title": "Transport Jobs Portal",
        "map_renderer": map_renderer,
        "show_vehicle_tracking": show_vehicle_tracking,
        "show_route_map": show_vehicle_tracking
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
    
    # Try user email - improved logic
    user = frappe.session.user
    if user and user != "Guest":
        # Method 1: Check Portal Users field in Customer doctype
        try:
            portal_users = frappe.get_all(
                "Portal User",
                filters={"user": user},
                fields=["parent"],
                limit=1
            )
            if portal_users:
                return portal_users[0].parent
        except Exception as e:
            frappe.log_error(f"Error checking portal users: {str(e)}", "Transport Portal")
        
        # Method 2: Direct email match in Customer
        customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"],
            limit=1
        )
        if customers:
            return customers[0].name
        
        # Method 3: Through Contact links
        contact = frappe.get_value("Contact", {"email_id": user}, "name")
        if contact:
            # Get customer links from contact
            customer_links = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parent": contact,
                    "link_doctype": "Customer"
                },
                fields=["link_name"],
                limit=1
            )
            if customer_links:
                return customer_links[0].link_name
        
        # Method 4: Check if user has Customer role and find through contact
        try:
            if "Customer" in frappe.get_roles():
                contact_name = frappe.get_value("Contact", {"email_id": user}, "name")
                if contact_name:
                    customer_links = frappe.get_all(
                        "Dynamic Link",
                        filters={
                            "parent": contact_name,
                            "link_doctype": "Customer"
                        },
                        fields=["link_name"],
                        limit=1
                    )
                    if customer_links:
                        return customer_links[0].link_name
        except Exception as e:
            frappe.log_error(f"Error in customer detection: {str(e)}", "Transport Portal")
    
    return None


def get_customer_jobs(customer):
    """Get transport jobs for customer"""
    try:
        # Check jobs for this specific customer
        jobs = frappe.get_all(
            "Transport Job",
            filters={"customer": customer},
            fields=[
                "name", "customer", "booking_date", "vehicle_type", 
                "load_type", "customer_ref_no", "transport_order", "company",
                "hazardous", "refrigeration", "container_type", "container_no"
            ],
            order_by="booking_date desc"
        )
        
        # Get legs and vehicle info for each job
        for job in jobs:
            job["legs"] = get_job_legs(job["name"])
            job["vehicle"] = get_job_vehicle(job["name"])
            
            # Set job status based on legs status
            job["status"] = get_job_status_from_legs(job["legs"])
            
            # Convert date objects to strings for JSON serialization
            if job.get("booking_date"):
                job["booking_date"] = str(job["booking_date"])
        
        return jobs
        
    except Exception as e:
        frappe.log_error(f"Error getting customer jobs: {str(e)}", "Transport Portal")
        return []


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
                "drop_window_end", "order"
            ],
            order_by="`order` asc"
        )
        
        # Get facility names, locations, and convert date objects to strings
        for leg in legs:
            if leg["facility_from"] and leg["facility_type_from"]:
                try:
                    facility_from_doc = frappe.get_doc(leg["facility_type_from"], leg["facility_from"])
                    leg["facility_from_name"] = facility_from_doc.get("name") or leg["facility_from"]
                    # Get facility location if available
                    if hasattr(facility_from_doc, 'latitude') and hasattr(facility_from_doc, 'longitude'):
                        leg["facility_from_location"] = {
                            "lat": float(facility_from_doc.latitude),
                            "lng": float(facility_from_doc.longitude)
                        }
                except Exception:
                    leg["facility_from_name"] = leg["facility_from"]
            else:
                leg["facility_from_name"] = leg["facility_from"]
                
            if leg["facility_to"] and leg["facility_type_to"]:
                try:
                    facility_to_doc = frappe.get_doc(leg["facility_type_to"], leg["facility_to"])
                    leg["facility_to_name"] = facility_to_doc.get("name") or leg["facility_to"]
                    # Get facility location if available
                    if hasattr(facility_to_doc, 'latitude') and hasattr(facility_to_doc, 'longitude'):
                        leg["facility_to_location"] = {
                            "lat": float(facility_to_doc.latitude),
                            "lng": float(facility_to_doc.longitude)
                        }
                except Exception:
                    leg["facility_to_name"] = leg["facility_to"]
            else:
                leg["facility_to_name"] = leg["facility_to"]
            
            # Convert date objects to strings for JSON serialization
            for field in ["pick_window_start", "pick_window_end", "drop_window_start", "drop_window_end"]:
                if leg.get(field):
                    leg[field] = str(leg[field])
        
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
            "run_sheet": run_sheet_name
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting job vehicle: {str(e)}", "Transport Portal")
        return None


def get_vehicle_position(vehicle_name):
    """Get current vehicle position"""
    try:
        vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
        
        if vehicle.last_telematics_lat and vehicle.last_telematics_lon:
            return {
                "lat": float(vehicle.last_telematics_lat),
                "lng": float(vehicle.last_telematics_lon),
                "timestamp": str(vehicle.last_telematics_ts) if vehicle.last_telematics_ts else None,
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


def get_job_status_from_legs(legs):
    """Determine job status based on legs status"""
    if not legs:
        return "Draft"
    
    # Check if any leg is started
    started_legs = [leg for leg in legs if leg.get('status') == 'Started']
    if started_legs:
        return "In Progress"
    
    # Check if all legs are completed
    completed_legs = [leg for leg in legs if leg.get('status') == 'Completed']
    if len(completed_legs) == len(legs):
        return "Completed"
    
    # Check if any leg is planned
    planned_legs = [leg for leg in legs if leg.get('status') == 'Planned']
    if planned_legs:
        return "Planned"
    
    # Default status
    return "Draft"