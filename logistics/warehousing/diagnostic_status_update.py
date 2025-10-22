# -*- coding: utf-8 -*-
"""
Diagnostic script to identify storage location status update issues.
This script helps identify why some storage locations with quantity are still tagged as "Available".
"""

import frappe
from frappe import _


@frappe.whitelist()
def diagnose_storage_location_status(location_name: str = None) -> dict:
    """
    Diagnose storage location status update issues.
    
    Args:
        location_name: Specific location to check, or None for all locations with issues
    
    Returns:
        Dictionary with diagnostic information
    """
    try:
        # Get all storage locations with quantity but status = "Available"
        if location_name:
            locations = [{"name": location_name}]
        else:
            locations = frappe.db.sql("""
                SELECT sl.name, sl.status, COALESCE(bal.qty, 0) as qty
                FROM `tabStorage Location` sl
                LEFT JOIN (
                    SELECT storage_location, SUM(COALESCE(quantity, 0)) AS qty
                    FROM `tabWarehouse Stock Ledger`
                    GROUP BY storage_location
                ) bal ON bal.storage_location = sl.name
                WHERE sl.status = 'Available' 
                AND COALESCE(bal.qty, 0) > 0
                ORDER BY bal.qty DESC
                LIMIT 20
            """, as_dict=True)
        
        results = {
            "total_locations_checked": len(locations),
            "locations_with_issues": [],
            "summary": {}
        }
        
        for loc in locations:
            location_name = loc["name"]
            diagnostic_info = _analyze_location_status(location_name)
            results["locations_with_issues"].append(diagnostic_info)
        
        # Generate summary
        results["summary"] = _generate_summary(results["locations_with_issues"])
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in diagnose_storage_location_status: {str(e)}")
        return {"error": str(e)}


def _analyze_location_status(location_name: str) -> dict:
    """Analyze a specific storage location for status issues."""
    
    # Get current location info
    location = frappe.get_doc("Storage Location", location_name)
    
    # Calculate balance using the same logic as _sl_balance
    balance_result = frappe.db.sql(
        "SELECT COALESCE(SUM(quantity),0) FROM `tabWarehouse Stock Ledger` WHERE storage_location=%s", 
        (location_name,)
    )
    calculated_balance = float(balance_result[0][0] if balance_result else 0.0)
    
    # Get recent ledger entries
    recent_entries = frappe.db.sql("""
        SELECT posting_date, item, quantity, warehouse_job, handling_unit
        FROM `tabWarehouse Stock Ledger`
        WHERE storage_location = %s
        ORDER BY posting_date DESC, creation DESC
        LIMIT 10
    """, (location_name,), as_dict=True)
    
    # Check if status field exists
    sl_fields = _safe_meta_fieldnames("Storage Location")
    has_status_field = "status" in sl_fields
    
    # Check recent status updates
    status_history = frappe.db.sql("""
        SELECT modified, status
        FROM `tabStorage Location`
        WHERE name = %s
        ORDER BY modified DESC
        LIMIT 5
    """, (location_name,), as_dict=True)
    
    return {
        "location_name": location_name,
        "current_status": location.status,
        "calculated_balance": calculated_balance,
        "has_status_field": has_status_field,
        "should_be_status": "In Use" if calculated_balance > 0 else "Available",
        "status_mismatch": location.status != ("In Use" if calculated_balance > 0 else "Available"),
        "recent_ledger_entries": recent_entries,
        "status_history": status_history,
        "analysis": _analyze_status_issue(location, calculated_balance, has_status_field)
    }


def _analyze_status_issue(location, calculated_balance, has_status_field) -> str:
    """Analyze why the status might not be updating correctly."""
    
    issues = []
    
    if not has_status_field:
        issues.append("Storage Location doctype doesn't have a 'status' field")
    
    if location.status in ("Under Maintenance", "Inactive"):
        issues.append(f"Location status is '{location.status}' - status updates are blocked for these statuses")
    
    if calculated_balance > 0 and location.status == "Available":
        issues.append("Location has quantity but status is 'Available' - should be 'In Use'")
    
    if calculated_balance == 0 and location.status == "In Use":
        issues.append("Location has no quantity but status is 'In Use' - should be 'Available'")
    
    # Check if there are any recent ledger entries that might not have triggered status update
    recent_entries = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabWarehouse Stock Ledger`
        WHERE storage_location = %s
        AND creation > DATE_SUB(NOW(), INTERVAL 1 HOUR)
    """, (location.name,), as_dict=True)
    
    if recent_entries[0].count > 0:
        issues.append(f"Found {recent_entries[0].count} recent ledger entries that may not have triggered status update")
    
    return "; ".join(issues) if issues else "No obvious issues found"


def _generate_summary(locations_with_issues) -> dict:
    """Generate summary of issues found."""
    
    total_issues = len(locations_with_issues)
    status_mismatches = sum(1 for loc in locations_with_issues if loc["status_mismatch"])
    missing_status_field = sum(1 for loc in locations_with_issues if not loc["has_status_field"])
    
    return {
        "total_locations_with_issues": total_issues,
        "locations_with_status_mismatch": status_mismatches,
        "locations_missing_status_field": missing_status_field,
        "recommendations": _get_recommendations(locations_with_issues)
    }


def _get_recommendations(locations_with_issues) -> list:
    """Get recommendations based on the analysis."""
    
    recommendations = []
    
    if any(not loc["has_status_field"] for loc in locations_with_issues):
        recommendations.append("Ensure Storage Location doctype has a 'status' field")
    
    if any(loc["status_mismatch"] for loc in locations_with_issues):
        recommendations.append("Run status update for affected locations")
        recommendations.append("Check if _set_sl_status_by_balance is being called after ledger entries")
    
    if any("recent ledger entries" in loc["analysis"] for loc in locations_with_issues):
        recommendations.append("Investigate why recent ledger entries didn't trigger status updates")
    
    return recommendations


@frappe.whitelist()
def fix_storage_location_status(location_name: str = None) -> dict:
    """
    Fix storage location status based on current balance.
    
    Args:
        location_name: Specific location to fix, or None for all locations with issues
    """
    try:
        if location_name:
            locations = [location_name]
        else:
            # Get all locations with status mismatch
            locations = frappe.db.sql("""
                SELECT sl.name
                FROM `tabStorage Location` sl
                LEFT JOIN (
                    SELECT storage_location, SUM(COALESCE(quantity, 0)) AS qty
                    FROM `tabWarehouse Stock Ledger`
                    GROUP BY storage_location
                ) bal ON bal.storage_location = sl.name
                WHERE (sl.status = 'Available' AND COALESCE(bal.qty, 0) > 0)
                   OR (sl.status = 'In Use' AND COALESCE(bal.qty, 0) = 0)
            """, as_dict=True)
            locations = [loc["name"] for loc in locations]
        
        fixed_count = 0
        errors = []
        
        for loc_name in locations:
            try:
                # Use the existing _set_sl_status_by_balance function
                from logistics.warehousing.api import _set_sl_status_by_balance
                _set_sl_status_by_balance(loc_name)
                fixed_count += 1
            except Exception as e:
                errors.append(f"Error fixing {loc_name}: {str(e)}")
        
        frappe.db.commit()
        
        return {
            "fixed_count": fixed_count,
            "total_processed": len(locations),
            "errors": errors,
            "message": f"Fixed status for {fixed_count} locations"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in fix_storage_location_status: {str(e)}")
        return {"error": str(e)}


def _safe_meta_fieldnames(doctype: str) -> list:
    """Safely get field names for a doctype."""
    try:
        return frappe.get_meta(doctype).get_fieldnames()
    except:
        return []
