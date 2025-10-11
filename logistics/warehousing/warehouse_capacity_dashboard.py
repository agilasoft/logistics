# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Warehouse Capacity Dashboard
============================

Comprehensive dashboard for warehouse capacity management, providing real-time
insights, forecasting, and optimization recommendations.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate
from .api_parts.capacity_management import CapacityManager
from .api_parts.capacity_forecasting import CapacityForecaster
from .api_parts.capacity_optimization import CapacityOptimizer


@frappe.whitelist()
def get_capacity_dashboard_data(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive capacity dashboard data
    
    Args:
        company: Company filter
        branch: Branch filter
        site: Site filter
        building: Building filter
        zone: Zone filter
        
    Returns:
        Dict with dashboard data including metrics, alerts, and recommendations
    """
    try:
        # Initialize managers
        capacity_manager = CapacityManager()
        forecaster = CapacityForecaster()
        optimizer = CapacityOptimizer()
        
        # Get current capacity status
        current_status = _get_current_capacity_status(company, branch, site, building, zone)
        
        # Get capacity utilization metrics
        utilization_metrics = _get_utilization_metrics(company, branch, site, building, zone)
        
        # Get capacity alerts
        capacity_alerts = _get_capacity_alerts(company, branch, site, building, zone)
        
        # Get optimization recommendations
        optimization_data = optimizer.optimize_warehouse_capacity(
            company, branch, site, building, zone, "balanced"
        )
        
        # Get capacity forecast (7-day)
        forecast_data = forecaster.generate_capacity_forecast(
            company=company, branch=branch, forecast_days=7, include_seasonality=True
        )
        
        # Get capacity analytics
        analytics_data = forecaster.get_capacity_analytics(
            company=company, branch=branch, period_days=30
        )
        
        return {
            "current_status": current_status,
            "utilization_metrics": utilization_metrics,
            "capacity_alerts": capacity_alerts,
            "optimization_data": optimization_data,
            "forecast_data": forecast_data,
            "analytics_data": analytics_data,
            "generated_at": now_datetime(),
            "dashboard_version": "2.0"
        }
        
    except Exception as e:
        frappe.log_error(f"Capacity dashboard error: {str(e)}")
        return {"error": str(e)}


def _get_current_capacity_status(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """Get current capacity status across all locations"""
    try:
        # Build filters
        filters = {}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        if site:
            filters["site"] = site
        if building:
            filters["building"] = building
        if zone:
            filters["zone"] = zone
        
        # Get storage locations
        locations = frappe.get_all(
            "Storage Location",
            filters=filters,
            fields=[
                "name", "site", "building", "zone", "aisle", "bay", "level",
                "max_volume", "max_weight", "max_hu_slot",
                "current_volume", "current_weight", "utilization_percentage",
                "status", "storage_type"
            ]
        )
        
        # Calculate summary statistics
        total_locations = len(locations)
        if total_locations == 0:
            return {
                "total_locations": 0,
                "average_utilization": 0,
                "capacity_status": "no_data"
            }
        
        # Calculate utilization statistics
        utilizations = [flt(loc.utilization_percentage) for loc in locations if loc.utilization_percentage]
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        
        # Categorize locations
        critical_locations = [loc for loc in locations if flt(loc.utilization_percentage) >= 95]
        high_utilization = [loc for loc in locations if 85 <= flt(loc.utilization_percentage) < 95]
        medium_utilization = [loc for loc in locations if 50 <= flt(loc.utilization_percentage) < 85]
        low_utilization = [loc for loc in locations if flt(loc.utilization_percentage) < 50]
        
        # Calculate capacity metrics
        total_max_volume = sum(flt(loc.max_volume) for loc in locations)
        total_max_weight = sum(flt(loc.max_weight) for loc in locations)
        total_max_hu_slots = sum(flt(loc.max_hu_slot) for loc in locations)
        
        total_current_volume = sum(flt(loc.current_volume) for loc in locations)
        total_current_weight = sum(flt(loc.current_weight) for loc in locations)
        
        # Calculate overall utilization
        volume_utilization = (total_current_volume / total_max_volume * 100) if total_max_volume > 0 else 0
        weight_utilization = (total_current_weight / total_max_weight * 100) if total_max_weight > 0 else 0
        
        return {
            "total_locations": total_locations,
            "average_utilization": avg_utilization,
            "critical_locations_count": len(critical_locations),
            "high_utilization_count": len(high_utilization),
            "medium_utilization_count": len(medium_utilization),
            "low_utilization_count": len(low_utilization),
            "critical_locations": critical_locations,
            "high_utilization_locations": high_utilization,
            "medium_utilization_locations": medium_utilization,
            "low_utilization_locations": low_utilization,
            "overall_volume_utilization": volume_utilization,
            "overall_weight_utilization": weight_utilization,
            "capacity_status": _determine_capacity_status(avg_utilization, len(critical_locations))
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting current capacity status: {str(e)}")
        return {"error": str(e)}


def _get_utilization_metrics(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed utilization metrics"""
    try:
        # Get historical utilization data (last 30 days)
        end_date = getdate()
        start_date = frappe.utils.add_days(end_date, -30)
        
        # Build filters for historical data
        filters = {}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        
        # Get daily utilization data
        utilization_data = frappe.db.sql("""
            SELECT 
                DATE(l.posting_date) as date,
                COUNT(DISTINCT l.storage_location) as active_locations,
                AVG(sl.utilization_percentage) as avg_utilization,
                MAX(sl.utilization_percentage) as max_utilization,
                MIN(sl.utilization_percentage) as min_utilization
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
            WHERE l.posting_date >= %s AND l.posting_date <= %s
            {filters}
            GROUP BY DATE(l.posting_date)
            ORDER BY DATE(l.posting_date)
        """.format(
            filters=" AND " + " AND ".join([f"sl.{k} = %s" for k in filters.keys()]) if filters else ""
        ), 
        [start_date, end_date] + list(filters.values()),
        as_dict=True)
        
        # Calculate trend metrics
        if utilization_data:
            recent_avg = sum(d["avg_utilization"] for d in utilization_data[-7:]) / 7
            older_avg = sum(d["avg_utilization"] for d in utilization_data[:7]) / 7
            trend = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
            growth_rate = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        else:
            trend = "no_data"
            growth_rate = 0
            recent_avg = 0
        
        return {
            "trend": trend,
            "growth_rate": growth_rate,
            "recent_average": recent_avg,
            "historical_data": utilization_data,
            "peak_utilization": max([d["max_utilization"] for d in utilization_data]) if utilization_data else 0,
            "low_utilization": min([d["min_utilization"] for d in utilization_data]) if utilization_data else 0
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting utilization metrics: {str(e)}")
        return {"error": str(e)}


def _get_capacity_alerts(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get capacity alerts and warnings"""
    try:
        alerts = []
        
        # Build filters
        filters = {}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        if site:
            filters["site"] = site
        if building:
            filters["building"] = building
        if zone:
            filters["zone"] = zone
        
        # Get locations with high utilization
        high_utilization_locations = frappe.get_all(
            "Storage Location",
            filters={**filters, "utilization_percentage": [">=", 85]},
            fields=["name", "site", "building", "zone", "utilization_percentage", "max_volume", "max_weight", "max_hu_slot"]
        )
        
        # Generate alerts
        for location in high_utilization_locations:
            utilization = flt(location.utilization_percentage)
            
            if utilization >= 95:
                alerts.append({
                    "type": "critical",
                    "title": f"Critical Capacity Alert",
                    "message": f"Location {location.name} is at {utilization:.1f}% capacity",
                    "location": location.name,
                    "utilization": utilization,
                    "action_required": "Immediate capacity planning needed",
                    "priority": "high"
                })
            elif utilization >= 85:
                alerts.append({
                    "type": "warning",
                    "title": f"High Utilization Warning",
                    "message": f"Location {location.name} is at {utilization:.1f}% capacity",
                    "location": location.name,
                    "utilization": utilization,
                    "action_required": "Monitor and plan capacity optimization",
                    "priority": "medium"
                })
        
        # Get locations with capacity alerts enabled
        alert_enabled_locations = frappe.get_all(
            "Storage Location",
            filters={**filters, "enable_capacity_alerts": 1},
            fields=["name", "volume_alert_threshold", "weight_alert_threshold", "utilization_alert_threshold"]
        )
        
        # Check for threshold-based alerts
        for location in alert_enabled_locations:
            location_doc = frappe.get_doc("Storage Location", location.name)
            
            # Check volume threshold
            if (location_doc.current_volume and location_doc.max_volume and 
                location_doc.current_volume / location_doc.max_volume * 100 >= flt(location.volume_alert_threshold)):
                alerts.append({
                    "type": "volume_alert",
                    "title": f"Volume Threshold Alert",
                    "message": f"Location {location.name} volume utilization exceeded threshold",
                    "location": location.name,
                    "threshold": flt(location.volume_alert_threshold),
                    "action_required": "Review volume allocation",
                    "priority": "medium"
                })
            
            # Check weight threshold
            if (location_doc.current_weight and location_doc.max_weight and 
                location_doc.current_weight / location_doc.max_weight * 100 >= flt(location.weight_alert_threshold)):
                alerts.append({
                    "type": "weight_alert",
                    "title": f"Weight Threshold Alert",
                    "message": f"Location {location.name} weight utilization exceeded threshold",
                    "location": location.name,
                    "threshold": flt(location.weight_alert_threshold),
                    "action_required": "Review weight distribution",
                    "priority": "medium"
                })
        
        return sorted(alerts, key=lambda x: x["priority"] == "high", reverse=True)
        
    except Exception as e:
        frappe.log_error(f"Error getting capacity alerts: {str(e)}")
        return []


def _determine_capacity_status(avg_utilization: float, critical_count: int) -> str:
    """Determine overall capacity status"""
    if critical_count > 0:
        return "critical"
    elif avg_utilization >= 85:
        return "high"
    elif avg_utilization >= 70:
        return "medium"
    elif avg_utilization >= 50:
        return "normal"
    else:
        return "low"


@frappe.whitelist()
def update_all_capacity_metrics(
    company: Optional[str] = None,
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """Update capacity metrics for all locations"""
    try:
        capacity_manager = CapacityManager()
        
        # Build filters
        filters = {}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        
        # Get all storage locations
        locations = frappe.get_all(
            "Storage Location",
            filters=filters,
            fields=["name"]
        )
        
        updated_count = 0
        errors = []
        
        for location in locations:
            try:
                result = capacity_manager.update_capacity_metrics(location.name)
                if "error" not in result:
                    updated_count += 1
                else:
                    errors.append(f"Location {location.name}: {result['error']}")
            except Exception as e:
                errors.append(f"Location {location.name}: {str(e)}")
        
        return {
            "total_locations": len(locations),
            "updated_count": updated_count,
            "error_count": len(errors),
            "errors": errors,
            "updated_at": now_datetime()
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating capacity metrics: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def get_capacity_summary_report(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """Generate comprehensive capacity summary report"""
    try:
        # Get dashboard data
        dashboard_data = get_capacity_dashboard_data(company, branch, site, building, zone)
        
        # Extract key metrics
        current_status = dashboard_data.get("current_status", {})
        utilization_metrics = dashboard_data.get("utilization_metrics", {})
        capacity_alerts = dashboard_data.get("capacity_alerts", [])
        optimization_data = dashboard_data.get("optimization_data", {})
        
        # Generate summary
        summary = {
            "total_locations": current_status.get("total_locations", 0),
            "average_utilization": current_status.get("average_utilization", 0),
            "capacity_status": current_status.get("capacity_status", "unknown"),
            "critical_locations": current_status.get("critical_locations_count", 0),
            "high_utilization_locations": current_status.get("high_utilization_count", 0),
            "trend": utilization_metrics.get("trend", "unknown"),
            "growth_rate": utilization_metrics.get("growth_rate", 0),
            "active_alerts": len(capacity_alerts),
            "optimization_score": optimization_data.get("optimization_score", 0),
            "recommendations_count": len(optimization_data.get("recommendations", [])),
            "generated_at": now_datetime()
        }
        
        return summary
        
    except Exception as e:
        frappe.log_error(f"Error generating capacity summary report: {str(e)}")
        return {"error": str(e)}
