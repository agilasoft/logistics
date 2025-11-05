# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months
from typing import Dict, List, Any

def get_context(context):
    context.no_cache = 1
    
    # Get sustainability settings
    context.settings = frappe.get_single("Sustainability Settings")
    
    # Get aggregated sustainability data
    context.sustainability_data = get_sustainability_dashboard_data()
    
    return context

@frappe.whitelist()
def get_sustainability_dashboard_data():
    """Get comprehensive sustainability data for dashboard"""
    try:
        from logistics.sustainability.api.data_aggregation import get_aggregated_metrics, get_aggregated_carbon_footprint, get_aggregated_energy_consumption
        
        # Get data for last 12 months
        from_date = add_months(getdate(), -12)
        to_date = getdate()
        
        filters = {
            "from_date": from_date,
            "to_date": to_date
        }
        
        # Get aggregated data
        metrics = get_aggregated_metrics(filters)
        carbon_data = get_aggregated_carbon_footprint(filters)
        energy_data = get_aggregated_energy_consumption(filters)
        
        # Get module-wise breakdown
        module_breakdown = get_module_breakdown(filters)
        
        # Get recent sustainability records
        recent_records = get_recent_sustainability_records()
        
        # Get sustainability goals progress
        goals_progress = get_sustainability_goals_progress()
        
        return {
            "metrics": metrics,
            "carbon_footprint": carbon_data,
            "energy_consumption": energy_data,
            "module_breakdown": module_breakdown,
            "recent_records": recent_records,
            "goals_progress": goals_progress
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting sustainability dashboard data: {e}", "Sustainability Dashboard Error")
        return {}

def get_module_breakdown(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Get sustainability data breakdown by module"""
    try:
        modules = ["Transport", "Warehousing", "Air Freight", "Sea Freight", "Customs", "Job Management"]
        breakdown = {}
        
        for module in modules:
            module_filters = filters.copy()
            module_filters["module"] = module
            
            # Get carbon footprint for this module
            carbon_data = frappe.db.sql(f"""
                SELECT 
                    SUM(total_emissions) as total_emissions,
                    COUNT(*) as record_count
                FROM `tabCarbon Footprint`
                WHERE module = %(module)s
                AND date >= %(from_date)s
                AND date <= %(to_date)s
            """, module_filters, as_dict=True)
            
            # Get energy consumption for this module
            energy_data = frappe.db.sql(f"""
                SELECT 
                    SUM(consumption_value) as total_consumption,
                    SUM(carbon_footprint) as total_carbon,
                    COUNT(*) as record_count
                FROM `tabEnergy Consumption`
                WHERE module = %(module)s
                AND date >= %(from_date)s
                AND date <= %(to_date)s
            """, module_filters, as_dict=True)
            
            breakdown[module] = {
                "carbon_emissions": flt(carbon_data[0].total_emissions) if carbon_data else 0,
                "energy_consumption": flt(energy_data[0].total_consumption) if energy_data else 0,
                "energy_carbon": flt(energy_data[0].total_carbon) if energy_data else 0,
                "carbon_records": carbon_data[0].record_count if carbon_data else 0,
                "energy_records": energy_data[0].record_count if energy_data else 0
            }
        
        return breakdown
        
    except Exception as e:
        frappe.log_error(f"Error getting module breakdown: {e}", "Sustainability Dashboard Error")
        return {}

def get_recent_sustainability_records(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent sustainability records"""
    try:
        # Get recent carbon footprint records
        carbon_records = frappe.db.sql(f"""
            SELECT 
                name,
                module,
                total_emissions,
                date,
                reference_doctype,
                reference_docname
            FROM `tabCarbon Footprint`
            ORDER BY date DESC, modified DESC
            LIMIT %(limit)s
        """, {"limit": limit}, as_dict=True)
        
        # Get recent energy consumption records
        energy_records = frappe.db.sql(f"""
            SELECT 
                name,
                module,
                consumption_value,
                energy_type,
                date,
                reference_doctype,
                reference_docname
            FROM `tabEnergy Consumption`
            ORDER BY date DESC, modified DESC
            LIMIT %(limit)s
        """, {"limit": limit}, as_dict=True)
        
        # Combine and sort records
        all_records = []
        for record in carbon_records:
            record["type"] = "Carbon Footprint"
            record["value"] = record["total_emissions"]
            record["unit"] = "kg CO2e"
            all_records.append(record)
        
        for record in energy_records:
            record["type"] = "Energy Consumption"
            record["value"] = record["consumption_value"]
            record["unit"] = record.get("energy_type", "kWh")
            all_records.append(record)
        
        # Sort by date and return top records
        all_records.sort(key=lambda x: x.get("date", ""), reverse=True)
        return all_records[:limit]
        
    except Exception as e:
        frappe.log_error(f"Error getting recent sustainability records: {e}", "Sustainability Dashboard Error")
        return []

def get_sustainability_goals_progress() -> List[Dict[str, Any]]:
    """Get sustainability goals and their progress"""
    try:
        goals = frappe.get_all("Sustainability Goals", 
            fields=["name", "goal_name", "goal_type", "target_value", "current_progress", "status", "target_date"],
            filters={"status": ["in", ["Active", "Draft"]]},
            order_by="target_date ASC"
        )
        
        return goals
        
    except Exception as e:
        frappe.log_error(f"Error getting sustainability goals: {e}", "Sustainability Dashboard Error")
        return []

@frappe.whitelist()
def get_sustainability_chart_data(module: str = None, metric_type: str = None, period: str = "12months"):
    """Get data for sustainability charts"""
    try:
        # Calculate date range based on period
        if period == "12months":
            from_date = add_months(getdate(), -12)
        elif period == "6months":
            from_date = add_months(getdate(), -6)
        elif period == "3months":
            from_date = add_months(getdate(), -3)
        else:
            from_date = add_months(getdate(), -12)
        
        to_date = getdate()
        
        # Build filters
        filters = {
            "from_date": from_date,
            "to_date": to_date
        }
        
        if module:
            filters["module"] = module
        if metric_type:
            filters["metric_type"] = metric_type
        
        # Get carbon footprint data by month
        carbon_data = frappe.db.sql(f"""
            SELECT 
                DATE_FORMAT(date, '%%Y-%%m') as month,
                SUM(total_emissions) as total_emissions
            FROM `tabCarbon Footprint`
            WHERE date >= %(from_date)s
            AND date <= %(to_date)s
            {f"AND module = %(module)s" if module else ""}
            GROUP BY DATE_FORMAT(date, '%%Y-%%m')
            ORDER BY month
        """, filters, as_dict=True)
        
        # Get energy consumption data by month
        energy_data = frappe.db.sql(f"""
            SELECT 
                DATE_FORMAT(date, '%%Y-%%m') as month,
                SUM(consumption_value) as total_consumption,
                SUM(carbon_footprint) as total_carbon
            FROM `tabEnergy Consumption`
            WHERE date >= %(from_date)s
            AND date <= %(to_date)s
            {f"AND module = %(module)s" if module else ""}
            GROUP BY DATE_FORMAT(date, '%%Y-%%m')
            ORDER BY month
        """, filters, as_dict=True)
        
        return {
            "carbon_footprint": carbon_data,
            "energy_consumption": energy_data
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting sustainability chart data: {e}", "Sustainability Dashboard Error")
        return {"carbon_footprint": [], "energy_consumption": []}
