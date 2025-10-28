# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Any, Optional
import json

@frappe.whitelist()
def get_warehouse_dashboard_data(company: Optional[str] = None, branch: Optional[str] = None, warehouse_job: Optional[str] = None) -> Dict[str, Any]:
    """Get data for warehouse dashboard including handling units, locations, and gate passes"""
    
    # Input validation
    if company and not frappe.db.exists("Company", company):
        frappe.throw(_("Invalid Company: {0}").format(company))
    
    if branch and not frappe.db.exists("Branch", branch):
        frappe.throw(_("Invalid Branch: {0}").format(branch))
    
    if warehouse_job and not frappe.db.exists("Warehouse Job", warehouse_job):
        frappe.throw(_("Invalid Warehouse Job: {0}").format(warehouse_job))
    
    # Get handling units with their current stock
    handling_units = get_handling_units_data(company, branch, warehouse_job)
    
    # Get storage locations with their status
    storage_locations = get_storage_locations_data(company, branch)
    
    # Get warehouse map data
    warehouse_map = get_warehouse_map_data(company, branch)
    
    # Get gate passes data (filtered by warehouse job if provided)
    gate_passes = get_gate_passes_data(company, branch, warehouse_job)
    
    result = {
        "handling_units": handling_units,
        "storage_locations": storage_locations,
        "warehouse_map": warehouse_map,
        "gate_passes": gate_passes
    }
    
    return result

def get_handling_units_data(company: Optional[str] = None, branch: Optional[str] = None, warehouse_job: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get handling units with their current stock and items"""
    
    try:
        # Build company/branch filters
        filters = {"status": ["in", ["Available", "In Use"]]}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        
        # Get handling units
        handling_units = frappe.get_all(
            "Handling Unit",
            filters=filters,
            fields=[
                "name", "type", "brand", "supplier", "status", 
                "company", "branch", "notes"
            ],
            order_by="name"
        )
    except Exception as e:
        frappe.log_error(f"Error getting handling units data: {str(e)}")
        frappe.throw(_("Failed to retrieve handling units data. Please try again or contact support."))
    
    # Filter by warehouse job if specified
    if warehouse_job:
        try:
            # Get handling units that are associated with this warehouse job
            warehouse_job_hus = frappe.db.sql("""
                SELECT DISTINCT handling_unit 
                FROM `tabWarehouse Job Item` 
                WHERE parent = %s AND handling_unit IS NOT NULL
            """, (warehouse_job,), as_dict=True)
            
            warehouse_job_hu_names = [row.handling_unit for row in warehouse_job_hus]
            handling_units = [hu for hu in handling_units if hu.name in warehouse_job_hu_names]
        except Exception as e:
            frappe.log_error(f"Error filtering handling units by warehouse job: {str(e)}")
            # Continue without filtering rather than failing completely
    
    # Get stock data for each handling unit
    for hu in handling_units:
        try:
            # Get items from warehouse job items table for this handling unit
            stock_data = frappe.db.sql("""
                SELECT 
                    wji.item,
                    wji.quantity,
                    wji.length,
                    wji.width,
                    wji.height,
                    wji.volume,
                    wji.weight
                FROM `tabWarehouse Job Item` wji
                WHERE wji.handling_unit = %s
            """, (hu.name,), as_dict=True)
        except Exception as e:
            frappe.log_error(f"Error getting stock data for handling unit {hu.name}: {str(e)}")
            stock_data = []  # Continue with empty data rather than failing
        
        
        hu["items"] = stock_data
        hu["total_items"] = len(stock_data)
        hu["total_quantity"] = sum(item["quantity"] for item in stock_data)
        
        # Calculate total volume and weight from items
        total_volume = 0
        total_weight = 0
        
        for item in stock_data:
            quantity = item["quantity"] or 0
            
            # Calculate volume - try item volume first, then calculate from dimensions
            item_volume = 0
            if item.get("volume") and item["volume"] > 0:
                item_volume = item["volume"]
            elif all([item.get("length"), item.get("width"), item.get("height")]):
                item_volume = (item["length"] or 0) * (item["width"] or 0) * (item["height"] or 0)
            
            total_volume += item_volume * quantity
            
            # Calculate weight
            item_weight = 0
            if item.get("weight") and item["weight"] > 0:
                item_weight = item["weight"]
                total_weight += item_weight * quantity
            
        
        # Set volume and weight values (use actual calculated values)
        hu["total_volume"] = total_volume
        hu["total_weight"] = total_weight
        
        
        # Get current location of this handling unit
        try:
            location_data = frappe.db.sql("""
                SELECT DISTINCT l.storage_location, sl.site, sl.building, sl.zone, sl.aisle, sl.bay, sl.level
                FROM `tabWarehouse Stock Ledger` l
                LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
                WHERE l.handling_unit = %s AND l.quantity > 0
                ORDER BY l.posting_date DESC
                LIMIT 1
            """, (hu.name,), as_dict=True)
            
            hu["current_location"] = location_data[0] if location_data else None
        except Exception as e:
            frappe.log_error(f"Error getting location data for handling unit {hu.name}: {str(e)}")
            hu["current_location"] = None
    
    return handling_units

def get_storage_locations_data(company: Optional[str] = None, branch: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get storage locations with their current status and occupancy"""
    
    try:
        # Build company/branch filters
        filters = {}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        
        # Get storage locations
        locations = frappe.get_all(
            "Storage Location",
            filters=filters,
            fields=[
                "name", "site", "building", "zone", "aisle", "bay", "level", 
                "location_code", "status", "storage_type", "bin_priority",
                "max_hu_slot", "staging_area", "pick_face"
            ],
            order_by="site, building, zone, aisle, bay, level"
        )
    except Exception as e:
        frappe.log_error(f"Error getting storage locations data: {str(e)}")
        frappe.throw(_("Failed to retrieve storage locations data. Please try again or contact support."))
    
    # Get occupancy data for each location
    for loc in locations:
        try:
            # Get current stock in this location
            stock_data = frappe.db.sql("""
                SELECT 
                    COUNT(DISTINCT l.handling_unit) as hu_count,
                    COUNT(DISTINCT l.item) as item_count,
                    SUM(l.quantity) as total_quantity
                FROM `tabWarehouse Stock Ledger` l
                WHERE l.storage_location = %s AND l.quantity > 0
            """, (loc.name,), as_dict=True)
        except Exception as e:
            frappe.log_error(f"Error getting occupancy data for location {loc.name}: {str(e)}")
            stock_data = []
        
        if stock_data:
            loc["occupancy"] = stock_data[0]
            loc["occupancy"]["utilization"] = (
                (stock_data[0]["hu_count"] / loc["max_hu_slot"] * 100) 
                if loc["max_hu_slot"] and loc["max_hu_slot"] > 0 else 0
            )
        else:
            loc["occupancy"] = {"hu_count": 0, "item_count": 0, "total_quantity": 0, "utilization": 0}
    
    return locations

def get_warehouse_map_data(company: Optional[str] = None, branch: Optional[str] = None) -> Dict[str, Any]:
    """Get warehouse map structure organized by hierarchy"""
    
    # Get the warehouse hierarchy
    hierarchy = frappe.db.sql("""
        SELECT 
            sl.site,
            sl.building,
            sl.zone,
            sl.aisle,
            sl.bay,
            sl.level,
            COUNT(*) as location_count,
            SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as available_count
        FROM `tabStorage Location` sl
        WHERE 1=1
        {company_filter}
        {branch_filter}
        GROUP BY sl.site, sl.building, sl.zone, sl.aisle, sl.bay, sl.level
        ORDER BY sl.site, sl.building, sl.zone, sl.aisle, sl.bay, sl.level
    """.format(
        company_filter="AND sl.company = %s" if company else "",
        branch_filter="AND sl.branch = %s" if branch else ""
    ), 
    ([company] if company else []) + ([branch] if branch else []), 
    as_dict=True)
    
    # Organize into hierarchical structure
    map_data = {}
    for row in hierarchy:
        site = row["site"] or "Unknown"
        building = row["building"] or "Unknown"
        zone = row["zone"] or "Unknown"
        aisle = row["aisle"] or "Unknown"
        bay = row["bay"] or "Unknown"
        level = row["level"] or "Unknown"
        
        if site not in map_data:
            map_data[site] = {}
        if building not in map_data[site]:
            map_data[site][building] = {}
        if zone not in map_data[site][building]:
            map_data[site][building][zone] = {}
        if aisle not in map_data[site][building][zone]:
            map_data[site][building][zone][aisle] = {}
        if bay not in map_data[site][building][zone][aisle]:
            map_data[site][building][zone][aisle][bay] = {}
        
        map_data[site][building][zone][aisle][bay][level] = {
            "location_count": row["location_count"],
            "available_count": row["available_count"],
            "utilization": (row["available_count"] / row["location_count"] * 100) if row["location_count"] > 0 else 0
        }
    
    return map_data

def get_gate_passes_data(company: Optional[str] = None, branch: Optional[str] = None, warehouse_job: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get gate passes data for the dashboard"""
    
    # Build filters
    filters = {}
    if company:
        filters["company"] = company
    if branch:
        filters["branch"] = branch
    if warehouse_job:
        filters["warehouse_job"] = warehouse_job
    
    # Get gate passes
    gate_passes = frappe.get_all(
        "Gate Pass",
        filters=filters,
        fields=[
            "name", "status", "job_type", "dock_door", "eta", "plate_no", 
            "transport_company", "vehicle_type", "driver_name", "driver_contact",
            "gate_pass_date", "gate_pass_time", "actual_in_time", "actual_out_time",
            "authorized_by", "authorized_date", "security_checked_by", "security_check_time",
            "warehouse_job", "reference_order_type", "reference_order"
        ],
        order_by="gate_pass_date DESC, gate_pass_time DESC"
    )
    
    # Add item count for each gate pass
    for gp in gate_passes:
        item_count = frappe.db.count("Gate Pass Item", {"parent": gp.name})
        gp["item_count"] = item_count
        
        # Format dates for display
        if gp.get("eta"):
            gp["eta_formatted"] = frappe.utils.format_datetime(gp["eta"])
        if gp.get("gate_pass_date"):
            gp["gate_pass_date_formatted"] = frappe.utils.format_date(gp["gate_pass_date"])
    
    return gate_passes

@frappe.whitelist()
def get_handling_unit_details(handling_unit: str) -> Dict[str, Any]:
    """Get detailed information about a specific handling unit"""
    
    # Input validation
    if not handling_unit:
        frappe.throw(_("Handling Unit is required"))
    
    if not frappe.db.exists("Handling Unit", handling_unit):
        frappe.throw(_("Invalid Handling Unit: {0}").format(handling_unit))
    
    # Get handling unit basic info
    hu_doc = frappe.get_doc("Handling Unit", handling_unit)
    hu_data = {
        "name": hu_doc.name,
        "type": hu_doc.type,
        "brand": hu_doc.brand,
        "supplier": hu_doc.supplier,
        "status": hu_doc.status,
        "company": hu_doc.company,
        "branch": hu_doc.branch,
        "notes": hu_doc.notes
    }
    
    # Get detailed stock information
    stock_details = frappe.db.sql("""
        SELECT 
            l.item,
            wi.item_name,
            wi.item_code,
            wi.uom,
            l.batch_no,
            l.serial_no,
            l.quantity,
            l.posting_date,
            l.storage_location,
            sl.site,
            sl.building,
            sl.zone,
            sl.aisle,
            sl.bay,
            sl.level
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        WHERE l.handling_unit = %s AND l.quantity > 0
        ORDER BY l.posting_date DESC, l.item
    """, (handling_unit,), as_dict=True)
    
    hu_data["stock_details"] = stock_details
    
    # Get available locations for this handling unit type
    if hu_doc.type:
        available_locations = frappe.db.sql("""
            SELECT 
                sl.name,
                sl.site,
                sl.building,
                sl.zone,
                sl.aisle,
                sl.bay,
                sl.level,
                sl.status,
                sl.storage_type,
                sl.bin_priority
            FROM `tabStorage Location` sl
            WHERE sl.status = 'Available'
            {company_filter}
            {branch_filter}
            ORDER BY sl.bin_priority, sl.site, sl.building, sl.zone, sl.aisle, sl.bay, sl.level
        """.format(
            company_filter="AND sl.company = %s" if hu_doc.company else "",
            branch_filter="AND sl.branch = %s" if hu_doc.branch else ""
        ), 
        ([hu_doc.company] if hu_doc.company else []) + ([hu_doc.branch] if hu_doc.branch else []), 
        as_dict=True)
        
        hu_data["available_locations"] = available_locations
    
    return hu_data

@frappe.whitelist()
def get_location_details(location: str) -> Dict[str, Any]:
    """Get detailed information about a specific storage location"""
    
    # Input validation
    if not location:
        frappe.throw(_("Storage Location is required"))
    
    if not frappe.db.exists("Storage Location", location):
        frappe.throw(_("Invalid Storage Location: {0}").format(location))
    
    # Get location basic info
    loc_doc = frappe.get_doc("Storage Location", location)
    loc_data = {
        "name": loc_doc.name,
        "site": loc_doc.site,
        "building": loc_doc.building,
        "zone": loc_doc.zone,
        "aisle": loc_doc.aisle,
        "bay": loc_doc.bay,
        "level": loc_doc.level,
        "location_code": loc_doc.location_code,
        "status": loc_doc.status,
        "storage_type": loc_doc.storage_type,
        "bin_priority": loc_doc.bin_priority,
        "max_hu_slot": loc_doc.max_hu_slot,
        "staging_area": loc_doc.staging_area,
        "pick_face": loc_doc.pick_face
    }
    
    # Get current stock in this location
    current_stock = frappe.db.sql("""
        SELECT 
            l.handling_unit,
            l.item,
            wi.item_name,
            wi.item_code,
            wi.uom,
            l.batch_no,
            l.serial_no,
            l.quantity,
            l.posting_date
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
        WHERE l.storage_location = %s AND l.quantity > 0
        ORDER BY l.posting_date DESC, l.item
    """, (location,), as_dict=True)
    
    loc_data["current_stock"] = current_stock
    
    # Get handling units currently in this location
    handling_units = frappe.db.sql("""
        SELECT DISTINCT l.handling_unit, hu.type, hu.brand, hu.supplier
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit
        WHERE l.storage_location = %s AND l.handling_unit IS NOT NULL AND l.quantity > 0
    """, (location,), as_dict=True)
    
    loc_data["handling_units"] = handling_units
    
    return loc_data

@frappe.whitelist()
def get_gate_pass_details(gate_pass: str) -> Dict[str, Any]:
    """Get detailed information about a specific gate pass"""
    
    # Input validation
    if not gate_pass:
        frappe.throw(_("Gate Pass is required"))
    
    if not frappe.db.exists("Gate Pass", gate_pass):
        frappe.throw(_("Invalid Gate Pass: {0}").format(gate_pass))
    
    # Get gate pass basic info
    gp_doc = frappe.get_doc("Gate Pass", gate_pass)
    gp_data = {
        "name": gp_doc.name,
        "status": gp_doc.status,
        "job_type": gp_doc.job_type,
        "dock_door": gp_doc.dock_door,
        "eta": gp_doc.eta,
        "plate_no": gp_doc.plate_no,
        "transport_company": gp_doc.transport_company,
        "vehicle_type": gp_doc.vehicle_type,
        "driver_name": gp_doc.driver_name,
        "driver_contact": gp_doc.driver_contact,
        "gate_pass_date": gp_doc.gate_pass_date,
        "gate_pass_time": gp_doc.gate_pass_time,
        "actual_in_time": gp_doc.actual_in_time,
        "actual_out_time": gp_doc.actual_out_time,
        "authorized_by": gp_doc.authorized_by,
        "authorized_date": gp_doc.authorized_date,
        "security_checked_by": gp_doc.security_checked_by,
        "security_check_time": gp_doc.security_check_time,
        "security_notes": gp_doc.security_notes,
        "warehouse_job": gp_doc.warehouse_job,
        "reference_order_type": gp_doc.reference_order_type,
        "reference_order": gp_doc.reference_order,
        "company": gp_doc.company,
        "branch": gp_doc.branch,
        "notes": gp_doc.notes
    }
    
    # Get items in this gate pass
    items = []
    for item in gp_doc.items:
        items.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "qty": item.qty,
            "uom": item.uom,
            "warehouse": item.warehouse,
            "handling_unit": item.handling_unit
        })
    
    gp_data["items"] = items
    gp_data["item_count"] = len(items)
    
    return gp_data
