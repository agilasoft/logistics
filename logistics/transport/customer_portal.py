# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, get_datetime
from typing import Dict, Any, List, Optional


@frappe.whitelist(allow_guest=True)
def get_customer_info(customer: str) -> Dict[str, Any]:
    """Get customer information for the portal"""
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        return {
            "customer_name": customer_doc.customer_name,
            "customer_id": customer_doc.name,
            "email": customer_doc.email_id,
            "mobile": customer_doc.mobile_no
        }
    except Exception as e:
        frappe.log_error(f"Error getting customer info: {str(e)}", "Customer Portal")
        return {
            "customer_name": "Unknown Customer",
            "customer_id": customer,
            "email": "",
            "mobile": ""
        }


@frappe.whitelist(allow_guest=True)
def get_customer_jobs(customer: str) -> Dict[str, Any]:
    """Get transport jobs for a specific customer"""
    try:
        # Get transport jobs for the customer
        jobs = frappe.get_all(
            "Transport Job",
            filters={"customer": customer},
            fields=[
                "name", "customer", "booking_date", "status", "vehicle_type", 
                "load_type", "customer_ref_no", "transport_order", "company",
                "hazardous", "refrigeration", "container_type", "container_no"
            ],
            order_by="booking_date desc"
        )
        
        # Get legs for each job
        for job in jobs:
            job["legs"] = get_job_legs(job["name"])
            job["vehicle"] = get_job_vehicle(job["name"])
        
        return {
            "success": True,
            "jobs": jobs,
            "total_jobs": len(jobs)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting customer jobs: {str(e)}", "Customer Portal")
        return {
            "success": False,
            "error": str(e),
            "jobs": [],
            "total_jobs": 0
        }


def get_job_legs(job_name: str) -> List[Dict[str, Any]]:
    """Get transport legs for a specific job"""
    try:
        legs = frappe.get_all(
            "Transport Leg",
            filters={"transport_job": job_name},
            fields=[
                "name", "facility_from", "facility_to", "status", "distance_km",
                "duration_min", "pick_window_start", "pick_window_end",
                "drop_window_start", "drop_window_end", "order"
            ],
            order_by="`order` asc"
        )
        
        # Get facility names
        for leg in legs:
            if leg["facility_from"]:
                facility_from_doc = frappe.get_doc(leg["facility_type_from"], leg["facility_from"])
                leg["facility_from_name"] = facility_from_doc.get("name") or leg["facility_from"]
            else:
                leg["facility_from_name"] = leg["facility_from"]
                
            if leg["facility_to"]:
                facility_to_doc = frappe.get_doc(leg["facility_type_to"], leg["facility_to"])
                leg["facility_to_name"] = facility_to_doc.get("name") or leg["facility_to"]
            else:
                leg["facility_to_name"] = leg["facility_to"]
        
        return legs
        
    except Exception as e:
        frappe.log_error(f"Error getting job legs: {str(e)}", "Customer Portal")
        return []


def get_job_vehicle(job_name: str) -> Optional[Dict[str, Any]]:
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
        frappe.log_error(f"Error getting job vehicle: {str(e)}", "Customer Portal")
        return None


def get_vehicle_position(vehicle_name: str) -> Optional[Dict[str, Any]]:
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
        frappe.log_error(f"Error getting vehicle position: {str(e)}", "Customer Portal")
        return None


def get_vehicle_status(vehicle_name: str) -> str:
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
        frappe.log_error(f"Error getting vehicle status: {str(e)}", "Customer Portal")
        return "Unknown"


@frappe.whitelist(allow_guest=True)
def get_job_details(job_name: str) -> Dict[str, Any]:
    """Get detailed information for a specific transport job"""
    try:
        job = frappe.get_doc("Transport Job", job_name)
        
        # Get all legs with detailed information
        legs = frappe.get_all(
            "Transport Leg",
            filters={"transport_job": job_name},
            fields=[
                "name", "facility_from", "facility_to", "facility_type_from", 
                "facility_type_to", "status", "distance_km", "duration_min",
                "pick_window_start", "pick_window_end", "drop_window_start", 
                "drop_window_end", "order", "pick_address", "drop_address"
            ],
            order_by="`order` asc"
        )
        
        # Get packages
        packages = frappe.get_all(
            "Transport Job Package",
            filters={"parent": job_name},
            fields=["item_name", "quantity", "weight_kg", "volume_m3"]
        )
        
        # Get charges
        charges = frappe.get_all(
            "Transport Job Charge",
            filters={"parent": job_name},
            fields=["charge_type", "amount", "description"]
        )
        
        return {
            "success": True,
            "job": job.as_dict(),
            "legs": legs,
            "packages": packages,
            "charges": charges
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting job details: {str(e)}", "Customer Portal")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def get_vehicle_tracking(vehicle_name: str) -> Dict[str, Any]:
    """Get real-time vehicle tracking information"""
    try:
        from logistics.transport.api_vehicle_tracking import get_vehicle_position
        
        position_data = get_vehicle_position(vehicle_name)
        
        if position_data.get("success"):
            return {
                "success": True,
                "vehicle_name": vehicle_name,
                "position": {
                    "lat": position_data.get("latitude"),
                    "lng": position_data.get("longitude"),
                    "timestamp": position_data.get("timestamp"),
                    "speed_kph": position_data.get("speed_kph"),
                    "ignition": position_data.get("ignition")
                }
            }
        else:
            return {
                "success": False,
                "error": position_data.get("error", "Unable to get vehicle position")
            }
            
    except Exception as e:
        frappe.log_error(f"Error getting vehicle tracking: {str(e)}", "Customer Portal")
        return {
            "success": False,
            "error": str(e)
        }

