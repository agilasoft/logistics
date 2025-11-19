from __future__ import annotations
from .common import *  # shared helpers
from .common import _sl_fields, _get_job_scope, _safe_meta_fieldnames, _get_allocation_level_limit, _get_allow_emergency_fallback, _get_split_quantity_decimal_precision, _fetch_job_order_items, _hu_consolidation_violations, _assert_hu_in_job_scope, _assert_location_in_job_scope, _select_dest_for_hu, _filter_locations_by_level, _get_item_storage_type_prefs  # explicit imports
from .capacity_management import CapacityManager, CapacityValidationError

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate
from typing import List, Dict, Any, Optional, Tuple, Set

def _get_location_overflow_enabled(company: Optional[str]) -> bool:
    """Check if location overflow is enabled in warehouse settings"""
    if not company:
        return False
    try:
        settings = frappe.get_doc("Warehouse Settings", company)
        return getattr(settings, "enable_location_overflow", False)
    except (frappe.DoesNotExistError, AttributeError):
        return False


def _get_hu_storage_location_size(handling_unit: str) -> int:
    """Get the storage location size for a handling unit (number of locations it occupies)"""
    if not handling_unit:
        return 1
    try:
        size = frappe.db.get_value("Handling Unit", handling_unit, "storage_location_size")
        return int(size) if size and size > 0 else 1
    except (frappe.DoesNotExistError, (ValueError, TypeError)):
        return 1


def _select_multiple_destinations_for_hu(
    item: str,
    quantity: float,
    company: Optional[str],
    branch: Optional[str],
    staging_area: Optional[str],
    level_limit_label: Optional[str],
    used_locations: Set[str],
    exclude_locations: Optional[List[str]],
    handling_unit: Optional[str],
    num_locations: int
) -> List[str]:
    """Select multiple destination locations for a handling unit when location overflow is enabled.
    
    Args:
        item: Item code
        quantity: Total quantity to allocate
        company: Company filter
        branch: Branch filter
        staging_area: Staging area
        level_limit_label: Allocation level limit
        used_locations: Set of already used locations
        exclude_locations: Locations to exclude
        handling_unit: Handling unit name
        num_locations: Number of locations needed
        
    Returns:
        List of location names (may be fewer than num_locations if not enough available)
    """
    if num_locations <= 1:
        # Fall back to single location selection
        dest = _select_dest_for_hu_with_capacity_validation(
            item=item,
            quantity=quantity,
            company=company,
            branch=branch,
            staging_area=staging_area,
            level_limit_label=level_limit_label,
            used_locations=used_locations,
            exclude_locations=exclude_locations,
            handling_unit=handling_unit
        )
        return [dest] if dest else []
    
    selected_locations = []
    remaining_locations_needed = num_locations
    
    # Calculate quantity per location
    quantity_per_location = quantity / num_locations
    
    # Get candidate locations (use direct call since this function may be called before cache is set up)
    candidates = _putaway_candidate_locations(
        item=item, company=company, branch=branch,
        exclude_locations=exclude_locations, quantity=quantity_per_location, handling_unit=handling_unit
    )
    
    # Filter by level limit if applicable
    if staging_area and level_limit_label:
        candidates = _filter_locations_by_level(candidates, staging_area, level_limit_label)
    
    # Filter out used locations
    available_candidates = [c for c in candidates if c["location"] not in used_locations]
    
    # Get HU type for priority filtering
    handling_unit_type = None
    if handling_unit:
        try:
            handling_unit_type = frappe.db.get_value("Handling Unit", handling_unit, "type")
        except Exception:
            pass
    
    # Apply priority filtering
    available_candidates = _filter_locations_by_priority(
        available_candidates,
        handling_unit=handling_unit,
        handling_unit_type=handling_unit_type,
        item=item,
        company=company,
        branch=branch
    )
    
    # Select locations up to num_locations
    for candidate in available_candidates:
        if remaining_locations_needed <= 0:
            break
        
        location = candidate.get("location")
        if location and location not in selected_locations:
            selected_locations.append(location)
            used_locations.add(location)
            remaining_locations_needed -= 1
    
    frappe.logger().info(f"Selected {len(selected_locations)} locations for HU {handling_unit} (requested: {num_locations})")
    return selected_locations


def _validate_storage_type_restrictions(item: str, company: Optional[str], branch: Optional[str]) -> Dict[str, Any]:
    """Validate storage type restrictions for an item and return detailed information about available locations.
    
    Args:
        item: Item code to validate
        company: Company filter
        branch: Branch filter
        
    Returns:
        Dict with validation results including available locations and detailed error messages
    """
    try:
        # Get item's storage type preferences
        preferred_storage_type, allowed_storage_types = _get_item_storage_type_prefs(item)
        
        # Build storage type filter for SQL query to avoid querying all locations
        storage_type_filter = ""
        storage_type_params = []
        if allowed_storage_types:
            # Only query locations with allowed storage types
            placeholders = ", ".join(["%s"] * len(allowed_storage_types))
            storage_type_filter = f"AND sl.storage_type IN ({placeholders})"
            storage_type_params = allowed_storage_types
        elif preferred_storage_type:
            # Only query locations with preferred storage type
            storage_type_filter = "AND sl.storage_type = %s"
            storage_type_params = [preferred_storage_type]
        
        # Get available storage locations with storage type filtering in SQL
        slf = _sl_fields()
        status_filter = "AND sl.status IN ('Available','In Use')" if ("status" in slf) else ""
        
        # Build parameters list
        query_params = []
        if company:
            query_params.append(company)
        if branch:
            query_params.append(branch)
        query_params.extend(storage_type_params)
        
        # Build WHERE clause for company/branch
        company_filter = "AND sl.company = %s" if company else ""
        branch_filter = "AND sl.branch = %s" if branch else ""
        
        all_locations = frappe.db.sql(
            f"""
            SELECT sl.name AS location,
                   sl.storage_type,
                   st.description AS storage_type_description,
                   sl.company,
                   sl.branch
            FROM `tabStorage Location` sl
            LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
            WHERE IFNULL(sl.staging_area, 0) = 0
              {status_filter}
              {company_filter}
              {branch_filter}
              {storage_type_filter}
            ORDER BY sl.name ASC
            """,
            tuple(query_params),
            as_dict=True,
        ) or []
        
        # Filter locations by storage type restrictions
        valid_locations = []
        invalid_locations = []
        
        for loc in all_locations:
            storage_type = loc.get("storage_type")
            if not storage_type:
                invalid_locations.append({
                    "location": loc["location"],
                    "reason": "No storage type assigned",
                    "storage_type": None
                })
                continue
                
            # Check if storage type is allowed
            if allowed_storage_types:
                if storage_type in allowed_storage_types:
                    valid_locations.append(loc)
                else:
                    invalid_locations.append({
                        "location": loc["location"],
                        "reason": f"Storage type '{storage_type}' not in allowed types",
                        "storage_type": storage_type,
                        "allowed_types": allowed_storage_types
                    })
            elif preferred_storage_type:
                if storage_type == preferred_storage_type:
                    valid_locations.append(loc)
                else:
                    invalid_locations.append({
                        "location": loc["location"],
                        "reason": f"Storage type '{storage_type}' does not match preferred type '{preferred_storage_type}'",
                        "storage_type": storage_type,
                        "preferred_type": preferred_storage_type
                    })
            else:
                # No storage type restrictions - all locations are valid
                valid_locations.append(loc)
        
        # Generate detailed error message if no valid locations found
        error_details = []
        if not valid_locations:
            if allowed_storage_types:
                error_details.append(f"Item '{item}' requires storage types: {', '.join(allowed_storage_types)}")
            elif preferred_storage_type:
                error_details.append(f"Item '{item}' requires storage type: {preferred_storage_type}")
            
            if invalid_locations:
                error_details.append(f"Found {len(invalid_locations)} locations with incompatible storage types:")
                for inv_loc in invalid_locations[:5]:  # Show first 5 examples
                    error_details.append(f"  - {inv_loc['location']}: {inv_loc['reason']}")
                if len(invalid_locations) > 5:
                    error_details.append(f"  ... and {len(invalid_locations) - 5} more locations")
            
            # Check if there are any locations at all
            if not all_locations:
                error_details.append("No storage locations found in the specified company/branch scope")
            elif len(all_locations) > 0:
                error_details.append(f"Total locations available: {len(all_locations)}, but none match storage type requirements")
        
        return {
            "valid": len(valid_locations) > 0,
            "valid_locations": valid_locations,
            "invalid_locations": invalid_locations,
            "total_locations": len(all_locations),
            "error_details": error_details,
            "item_storage_requirements": {
                "preferred_storage_type": preferred_storage_type,
                "allowed_storage_types": allowed_storage_types
            }
        }
        
    except Exception as e:
        frappe.logger().error(f"Error validating storage type restrictions for item {item}: {str(e)}")
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}",
            "valid_locations": [],
            "invalid_locations": [],
            "total_locations": 0,
            "error_details": [f"Validation failed: {str(e)}"]
        }

def _dest_loc_fieldname_for_putaway() -> str:
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    return "to_location" if "to_location" in jf else "location"

def _putaway_candidate_locations(
    item: str,
    company: Optional[str],
    branch: Optional[str],
    exclude_locations: Optional[List[str]] = None,
    quantity: float = 1.0,
    handling_unit: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return candidate locations preferring consolidation bins first, then others.
       Excludes staging locations and honors status filters.
       Now includes comprehensive capacity validation with improved fallback logic.
       STRICTLY validates allowed_storage_type for items."""
    exclude_locations = exclude_locations or []
    slf = _sl_fields()
    status_filter = "AND sl.status IN ('Available','In Use')" if ("status" in slf) else ""

    # Get item's allowed storage types for strict validation
    preferred_storage_type, allowed_storage_types = _get_item_storage_type_prefs(item)
    
    # Build storage type filter for SQL queries
    storage_type_filter = ""
    storage_type_params = []
    if allowed_storage_types:
        # Only allow locations with storage types that are in the item's allowed list
        placeholders = ", ".join(["%s"] * len(allowed_storage_types))
        storage_type_filter = f"AND sl.storage_type IN ({placeholders})"
        storage_type_params = allowed_storage_types
    elif preferred_storage_type:
        # If no allowed types but has preferred, use preferred type
        storage_type_filter = "AND sl.storage_type = %s"
        storage_type_params = [preferred_storage_type]

    # Consolidation bins that already contain this item (not staging)
    # Build parameters correctly
    params = [item]
    if exclude_locations:
        params.extend(exclude_locations)
    params.extend([company, company, branch, branch])
    params.extend(storage_type_params)  # Add storage type parameters
    
    cons = frappe.db.sql(
        f"""
        SELECT l.storage_location AS location,
               IFNULL(sl.bin_priority, 999999) AS bin_priority,
               IFNULL(st.picking_rank, 999999) AS storage_type_rank,
               SUM(l.quantity) AS current_quantity,
               sl.storage_type
        FROM `tabWarehouse Stock Ledger` l
        INNER JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
        WHERE l.item = %s
          AND IFNULL(sl.staging_area, 0) = 0
          {status_filter}
          {("AND l.storage_location NOT IN (" + ", ".join(["%s"]*len(exclude_locations)) + ")") if exclude_locations else ""}
          AND (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch  = %s)
          {storage_type_filter}
        GROUP BY l.storage_location, sl.bin_priority, st.picking_rank, sl.storage_type
        HAVING SUM(l.quantity) > 0
        ORDER BY storage_type_rank ASC, bin_priority ASC, sl.name ASC
        """,
        tuple(params),
        as_dict=True,
    ) or []
    cons_set = {c["location"] for c in cons}

    # Other valid bins (not staging), excluding already chosen consolidation bins
    # Build parameters correctly for second query
    others_params = []
    if exclude_locations:
        others_params.extend(exclude_locations)
    others_params.extend([company, company, branch, branch])
    others_params.extend(storage_type_params)  # Add storage type parameters
    
    # Build the NOT IN clause for consolidation locations
    cons_exclusion = ""
    if cons_set:
        cons_exclusion = "AND sl.name NOT IN %s"
        others_params.append(tuple(cons_set))
    
    others = frappe.db.sql(
        f"""
        SELECT sl.name AS location,
               IFNULL(sl.bin_priority, 999999) AS bin_priority,
               IFNULL(st.picking_rank, 999999) AS storage_type_rank,
               0 AS current_quantity,
               sl.storage_type
        FROM `tabStorage Location` sl
        LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
        WHERE IFNULL(sl.staging_area, 0) = 0
          {status_filter}
          {("AND sl.name NOT IN (" + ", ".join(["%s"]*len(exclude_locations)) + ")") if exclude_locations else ""}
          AND (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch  = %s)
          {storage_type_filter}
          {cons_exclusion}
        ORDER BY storage_type_rank ASC, bin_priority ASC, sl.name ASC
        """,
        tuple(others_params),
        as_dict=True,
    ) or []

    # Combine all candidates
    all_candidates = cons + others
    
    # Apply capacity validation to filter out locations that can't accommodate the item
    # OPTIMIZATION: Limit validation to top 20 candidates to improve performance
    # If we find valid candidates early, we can stop validating the rest
    capacity_manager = CapacityManager()
    validated_candidates = []
    fallback_candidates = []  # For locations that fail capacity validation but might still work
    
    # Limit candidates to validate for performance (validate top 20, or all if less than 20)
    max_candidates_to_validate = min(20, len(all_candidates))
    candidates_to_validate = all_candidates[:max_candidates_to_validate]
    
    # Get item capacity data once (cached in capacity_manager)
    try:
        item_data = capacity_manager._get_item_capacity_data(item)
        required_capacity = capacity_manager._calculate_required_capacity(item_data, quantity, handling_unit)
    except Exception as e:
        frappe.logger().warning(f"Error getting item capacity data for {item}: {str(e)}")
        item_data = None
        required_capacity = None
    
    for candidate in candidates_to_validate:
        try:
            # Validate capacity for this location
            capacity_validation = capacity_manager.validate_storage_capacity(
                location=candidate["location"],
                item=item,
                quantity=quantity,
                handling_unit=handling_unit
            )
            
            # Only include locations that pass capacity validation
            if capacity_validation.get("valid", False):
                candidate["capacity_valid"] = True
                candidate["capacity_utilization"] = capacity_validation.get("validation_results", {}).get("capacity_utilization", {})
                candidate["capacity_warnings"] = capacity_validation.get("validation_results", {}).get("warnings", [])
                validated_candidates.append(candidate)
                
                # OPTIMIZATION: If we found enough valid candidates (5), stop validating
                if len(validated_candidates) >= 5:
                    break
            else:
                # Store as fallback candidate for later use if no valid candidates found
                violations = capacity_validation.get("validation_results", {}).get("violations", [])
                candidate["capacity_valid"] = False
                candidate["capacity_violations"] = violations
                fallback_candidates.append(candidate)
                
                # Log capacity violations for debugging (only for first few)
                if violations and len(fallback_candidates) <= 3:
                    frappe.logger().info(f"Capacity validation failed for {candidate['location']}: {violations}")
                    
        except CapacityValidationError as e:
            # Log capacity validation errors but keep as fallback
            if len(fallback_candidates) <= 3:
                frappe.logger().info(f"Capacity validation error for {candidate['location']}: {str(e)}")
            candidate["capacity_valid"] = False
            candidate["capacity_error"] = str(e)
            fallback_candidates.append(candidate)
        except Exception as e:
            # Log other errors but keep as fallback
            if len(fallback_candidates) <= 3:
                frappe.logger().error(f"Unexpected error validating capacity for {candidate['location']}: {str(e)}")
            candidate["capacity_valid"] = False
            candidate["capacity_error"] = str(e)
            fallback_candidates.append(candidate)
    
    # If we have validated candidates, return them (limit to top 5 for performance)
    if validated_candidates:
        return validated_candidates[:5]
    
    # If no validated candidates found, use fallback candidates with warnings
    if fallback_candidates:
        frappe.logger().warning(f"No capacity-validated locations found for item {item}, using fallback candidates")
        # Sort fallback candidates by priority and return them
        fallback_candidates.sort(key=lambda x: (x.get("storage_type_rank", 999999), x.get("bin_priority", 999999)))
        return fallback_candidates[:5]  # Return top 5 fallback candidates
    
    # If no candidates at all, return empty list
    return []


def _get_storage_type_validation_summary(items: List[str], company: Optional[str], branch: Optional[str]) -> Dict[str, Any]:
    """Get a summary of storage type validation for multiple items.
    
    Args:
        items: List of item codes to validate
        company: Company filter
        branch: Branch filter
        
    Returns:
        Dict with validation summary including overall status and detailed results
    """
    summary = {
        "overall_valid": True,
        "total_items": len(items),
        "valid_items": 0,
        "invalid_items": 0,
        "item_results": {},
        "common_issues": [],
        "recommendations": []
    }
    
    # Track common storage types and issues
    all_storage_types = set()
    common_issues = {}
    
    for item in items:
        validation_result = _validate_storage_type_restrictions(item, company, branch)
        summary["item_results"][item] = validation_result
        
        if validation_result["valid"]:
            summary["valid_items"] += 1
        else:
            summary["invalid_items"] += 1
            summary["overall_valid"] = False
            
            # Track common issues
            for error_detail in validation_result["error_details"]:
                if error_detail not in common_issues:
                    common_issues[error_detail] = 0
                common_issues[error_detail] += 1
        
        # Collect storage types from valid locations
        for loc in validation_result.get("valid_locations", []):
            if loc.get("storage_type"):
                all_storage_types.add(loc["storage_type"])
    
    # Generate recommendations
    if not summary["overall_valid"]:
        summary["common_issues"] = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)
        
        if len(all_storage_types) > 0:
            summary["recommendations"].append(f"Consider creating storage locations with these types: {', '.join(sorted(all_storage_types))}")
        
        # Check if items have conflicting storage type requirements
        item_requirements = {}
        for item, result in summary["item_results"].items():
            if not result["valid"]:
                req = result.get("item_storage_requirements", {})
                allowed = req.get("allowed_storage_types", [])
                preferred = req.get("preferred_storage_type")
                
                if allowed:
                    item_requirements[item] = {"type": "allowed", "values": allowed}
                elif preferred:
                    item_requirements[item] = {"type": "preferred", "values": [preferred]}
        
        # Check for conflicts
        if len(item_requirements) > 1:
            all_required_types = set()
            for req in item_requirements.values():
                all_required_types.update(req["values"])
            
            if len(all_required_types) > len(set().union(*[req["values"] for req in item_requirements.values()])):
                summary["recommendations"].append("Items have conflicting storage type requirements. Consider reviewing item storage type configurations.")
    
    return summary


def _select_dest_for_hu_with_capacity_validation(
    item: str,
    quantity: float,
    company: Optional[str],
    branch: Optional[str],
    staging_area: Optional[str],
    level_limit_label: Optional[str],
    used_locations: Set[str],
    exclude_locations: Optional[List[str]],
    handling_unit: Optional[str] = None
) -> Optional[str]:
    """Select destination for HU with comprehensive capacity validation and improved selection logic"""
    try:
        # Get candidate locations with capacity validation
        candidates = _putaway_candidate_locations(
            item=item,
            company=company,
            branch=branch,
            exclude_locations=exclude_locations,
            quantity=quantity,
            handling_unit=handling_unit
        )
        
        if not candidates:
            frappe.logger().warning(f"No candidate locations found for item {item}")
            return None
        
        # Filter by allocation level limit
        if staging_area and level_limit_label:
            original_count = len(candidates)
            candidates = _filter_locations_by_level(candidates, staging_area, level_limit_label)
            filtered_count = len(candidates)
            frappe.logger().info(f"Level filtering: {original_count} -> {filtered_count} candidates for item {item} (staging: {staging_area}, limit: {level_limit_label})")
            
            if not candidates:
                frappe.logger().warning(f"All candidates filtered out by level limit for item {item}")
                # Try without level filtering as emergency fallback (only if allowed)
                if _get_allow_emergency_fallback():
                    candidates = _putaway_candidate_locations(
                        item=item, company=company, branch=branch,
                        exclude_locations=exclude_locations, quantity=quantity, handling_unit=handling_unit
                    )
                    frappe.logger().info(f"Emergency fallback: {len(candidates)} candidates without level filtering")
                else:
                    frappe.logger().warning(f"Emergency fallback disabled - no candidates available for item {item} within level limit")
        
        # Filter out used locations
        available_candidates = [c for c in candidates if c["location"] not in used_locations]
        
        if not available_candidates:
            frappe.logger().warning(f"No available locations for item {item} after filtering used locations")
            # Log detailed information for debugging
            frappe.logger().info(f"Debug info - Item: {item}, Company: {company}, Branch: {branch}")
            frappe.logger().info(f"Debug info - Staging: {staging_area}, Level limit: {level_limit_label}")
            frappe.logger().info(f"Debug info - Used locations: {list(used_locations)}")
            frappe.logger().info(f"Debug info - Exclude locations: {exclude_locations}")
            frappe.logger().info(f"Debug info - Total candidates before filtering: {len(candidates)}")
            return None
        
        # Apply location priority hierarchy
        # Get HU type if handling_unit is provided
        handling_unit_type = None
        if handling_unit:
            try:
                handling_unit_type = frappe.db.get_value("Handling Unit", handling_unit, "type")
            except Exception:
                pass
        
        # Filter and prioritize locations based on 5-level hierarchy
        available_candidates = _filter_locations_by_priority(
            available_candidates,
            handling_unit=handling_unit,
            handling_unit_type=handling_unit_type,
            item=item,
            company=company,
            branch=branch
        )
        
        # Log selection decision for debugging
        selected_location = available_candidates[0]["location"]
        frappe.logger().info(f"Selected location {selected_location} for item {item} with HU {handling_unit}")
        
        return selected_location
        
    except Exception as e:
        frappe.logger().error(f"Error selecting destination with capacity validation: {str(e)}")
        # Try fallback selection without capacity validation
        try:
            frappe.logger().info(f"Attempting fallback selection for item {item}")
            return _select_dest_for_hu_fallback(
                item, company, branch, staging_area, level_limit_label, 
                used_locations, exclude_locations
            )
        except Exception as fallback_error:
            frappe.logger().error(f"Fallback selection also failed: {str(fallback_error)}")
            return None


def _select_dest_for_hu_fallback(
    item: str,
    company: Optional[str],
    branch: Optional[str],
    staging_area: Optional[str],
    level_limit_label: Optional[str],
    used_locations: Set[str],
    exclude_locations: Optional[List[str]]
) -> Optional[str]:
    """Fallback selection method without capacity validation for emergency cases"""
    try:
        # Use the original putaway candidate logic without capacity validation
        from .common import _putaway_candidate_locations as original_candidate_locations
        
        candidates = original_candidate_locations(
            item=item,
            company=company,
            branch=branch,
            exclude_locations=exclude_locations
        )
        
        if not candidates:
            return None
        
        # Filter by allocation level limit
        if staging_area and level_limit_label:
            original_count = len(candidates)
            candidates = _filter_locations_by_level(candidates, staging_area, level_limit_label)
            filtered_count = len(candidates)
            
            if not candidates and _get_allow_emergency_fallback():
                # Try without level filtering as emergency fallback
                frappe.logger().info(f"Fallback: No candidates after level filtering, trying without level limit")
                candidates = original_candidate_locations(
                    item=item,
                    company=company,
                    branch=branch,
                    exclude_locations=exclude_locations
                )
        
        # Filter out used locations
        available_candidates = [c for c in candidates if c["location"] not in used_locations]
        
        if not available_candidates:
            return None
        
        # Simple sorting by priority
        available_candidates.sort(key=lambda x: (
            x.get("storage_type_rank", 999999),
            x.get("bin_priority", 999999)
        ))
        
        return available_candidates[0]["location"] if available_candidates else None
        
    except Exception as e:
        frappe.logger().error(f"Fallback selection failed: {str(e)}")
        return None


def _select_dest_for_hu_emergency(
    item: str,
    company: Optional[str],
    branch: Optional[str],
    used_locations: Set[str],
    exclude_locations: Optional[List[str]]
) -> Optional[str]:
    """Emergency selection method that bypasses all filtering except basic requirements"""
    try:
        # Get all available storage locations without any filtering
        filters = {
            "staging_area": 0,  # Not staging
            "status": ["in", ["Available", "In Use"]]  # Available status
        }
        
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
            
        locations = frappe.get_all(
            "Storage Location",
            filters=filters,
            fields=["name", "bin_priority", "storage_type"],
            order_by="bin_priority ASC, name ASC"
        )
        
        if not locations:
            return None
            
        # Filter out used and excluded locations
        available = []
        for loc in locations:
            if loc["name"] not in used_locations and loc["name"] not in (exclude_locations or []):
                available.append(loc)
        
        if not available:
            return None
            
        # Return the first available location
        return available[0]["name"]
        
    except Exception as e:
        frappe.logger().error(f"Emergency selection failed: {str(e)}")
        return None


def _find_available_handling_units(
    company: Optional[str],
    branch: Optional[str],
    exclude_hus: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """Find available handling units within company/branch scope."""
    exclude_hus = exclude_hus or set()
    
    # Build WHERE clause and parameters
    where_clauses = ["status IN ('Available', 'In Use')"]
    params = []
    
    if company:
        where_clauses.append("company = %s")
        params.append(company)
    if branch:
        where_clauses.append("branch = %s")
        params.append(branch)
    if exclude_hus:
        placeholders = ", ".join(["%s"] * len(exclude_hus))
        where_clauses.append(f"name NOT IN ({placeholders})")
        params.extend(exclude_hus)
    
    # Use frappe.db.sql() instead of frappe.get_all() to avoid DatabaseQuery.execute(as_dict=True) error
    # in newer Frappe versions
    where_sql = " AND ".join(where_clauses)
    hus = frappe.db.sql(
        f"""
        SELECT name, type, status, company, branch,
               max_volume, max_weight, current_volume, current_weight,
               capacity_uom, weight_uom
        FROM `tabHandling Unit`
        WHERE {where_sql}
        ORDER BY name ASC
        """,
        tuple(params),
        as_dict=True
    ) or []
    
    # Calculate available capacity for each HU
    for hu in hus:
        hu["available_volume"] = max(0, flt(hu.get("max_volume", 0)) - flt(hu.get("current_volume", 0)))
        hu["available_weight"] = max(0, flt(hu.get("max_weight", 0)) - flt(hu.get("current_weight", 0)))
    
    return hus


def _get_putaway_policy(item: str, company: Optional[str] = None) -> str:
    """Get putaway policy description for an item.
    
    Args:
        item: Item code
        company: Optional company for company-level policy
        
    Returns:
        Policy description string
    """
    try:
        # Get item-level putaway policy
        item_policy = frappe.db.get_value("Warehouse Item", item, "putaway_policy")
        if item_policy:
            return f"Item-level: {item_policy}"
        
        # Get company-level putaway policy if company is provided
        if company:
            company_policy = frappe.db.get_value("Company", company, "putaway_policy")
            if company_policy:
                return f"Company-level: {company_policy}"
        
        # Default policy
        return "Default: Nearest Empty"
    except Exception as e:
        frappe.logger().warning(f"Error getting putaway policy for item {item}: {str(e)}")
        return "Default: Nearest Empty"


def _check_hu_contains_item(hu_name: str, item: str) -> bool:
    """Check if a handling unit already contains the specified item.
    
    Args:
        hu_name: Handling unit name
        item: Item code
        
    Returns:
        True if HU contains the item, False otherwise
    """
    try:
        # Check Warehouse Stock Ledger for this HU and item
        result = frappe.db.sql("""
            SELECT SUM(quantity) AS total_qty
            FROM `tabWarehouse Stock Ledger`
            WHERE handling_unit = %s AND item = %s
        """, (hu_name, item), as_dict=True)
        
        if result and result[0].get("total_qty", 0) > 0:
            return True
        return False
    except Exception as e:
        frappe.logger().warning(f"Error checking if HU {hu_name} contains item {item}: {str(e)}")
        return False


def _order_hus_by_putaway_policy(
    hus: List[Dict[str, Any]],
    item: str,
    company: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Order handling units based on putaway policy.
    
    If HUs have priority scores (_hu_priority), they are sorted by priority first,
    then by putaway policy. This allows overflow allocation from lower priority HUs.
    
    Args:
        hus: List of handling unit dictionaries
        item: Item code
        company: Optional company for policy lookup
        
    Returns:
        Ordered list of handling units
    """
    try:
        # Get putaway policy
        policy = frappe.db.get_value("Warehouse Item", item, "putaway_policy")
        if not policy and company:
            policy = frappe.db.get_value("Company", company, "putaway_policy")
        
        if not policy:
            policy = "Nearest Empty"
        
        # Check if HUs have priority scores
        has_priority = any(hu.get("_hu_priority") is not None for hu in hus)
        
        # Define sorting key function
        def sort_key(hu: Dict[str, Any]) -> tuple:
            # First sort by priority (if available), then by putaway policy
            priority = hu.get("_hu_priority", 999)
            
            # Get policy-based sort value
            if policy == "Consolidate Same Item":
                # Prioritize HUs that already contain this item
                contains_item = _check_hu_contains_item(hu["name"], item)
                policy_value = (0 if contains_item else 1)  # 0 = higher priority
            else:
                # For "Nearest Empty" and other policies, sort by available capacity (descending)
                # Use negative value so higher capacity comes first
                available_capacity = -(hu.get("available_volume", 0) + hu.get("available_weight", 0))
                policy_value = available_capacity
            
            # Return tuple: (priority, policy_value)
            # Lower priority number = higher priority
            # Lower policy_value = higher priority (for Consolidate Same Item)
            # For capacity-based policies, negative capacity means higher capacity = higher priority
            return (priority, policy_value)
        
        # Sort by priority first, then by putaway policy
        return sorted(hus, key=sort_key)
        
    except Exception as e:
        frappe.logger().warning(f"Error ordering HUs by putaway policy: {str(e)}")
        # Fallback: sort by priority (if available), then by available capacity
        return sorted(hus, key=lambda x: (
            x.get("_hu_priority", 999),
            -(x.get("available_volume", 0) + x.get("available_weight", 0))
        ))


def _get_hu_current_locations(
    handling_unit: Optional[str] = None,
    handling_unit_type: Optional[str] = None,
    company: Optional[str] = None,
    branch: Optional[str] = None
) -> List[str]:
    """Find locations where a specific handling unit or handling unit type is currently located.
    
    Args:
        handling_unit: Specific handling unit name
        handling_unit_type: Handling unit type
        company: Company filter
        branch: Branch filter
        
    Returns:
        List of location names
    """
    try:
        conditions = []
        params = []
        
        if handling_unit:
            conditions.append("l.handling_unit = %s")
            params.append(handling_unit)
        elif handling_unit_type:
            conditions.append("hu.type = %s")
            params.append(handling_unit_type)
        else:
            return []
        
        # Add company/branch filters
        if company:
            conditions.append("COALESCE(hu.company, sl.company, l.company) = %s")
            params.append(company)
        if branch:
            conditions.append("COALESCE(hu.branch, sl.branch, l.branch) = %s")
            params.append(branch)
        
        where_clause = " AND " + " AND ".join(conditions) if conditions else ""
        
        sql = f"""
            SELECT DISTINCT l.storage_location
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit
            LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
            WHERE l.quantity > 0
              AND l.storage_location IS NOT NULL
              {where_clause}
        """
        
        result = frappe.db.sql(sql, tuple(params), as_dict=True)
        return [row["storage_location"] for row in result if row.get("storage_location")]
    except Exception as e:
        frappe.logger().warning(f"Error getting HU current locations: {str(e)}")
        return []


def _filter_locations_by_priority(
    candidates: List[Dict[str, Any]],
    handling_unit: Optional[str] = None,
    handling_unit_type: Optional[str] = None,
    item: Optional[str] = None,
    company: Optional[str] = None,
    branch: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter and prioritize locations based on a 5-level hierarchy:
    1. Locations where the specific HU is located
    2. Locations where the HU type is located
    3. Specific location preference (if any)
    4. Storage type preference
    5. Putaway policy
    
    Args:
        candidates: List of candidate location dictionaries
        handling_unit: Specific handling unit name
        handling_unit_type: Handling unit type
        item: Item code for policy lookup
        company: Company filter
        branch: Branch filter
        
    Returns:
        Filtered and prioritized list of locations
    """
    if not candidates:
        return []
    
    # Get HU type if handling_unit is provided
    if handling_unit and not handling_unit_type:
        try:
            handling_unit_type = frappe.db.get_value("Handling Unit", handling_unit, "type")
        except Exception:
            pass
    
    # Get locations where HU or HU type is located
    hu_locations = _get_hu_current_locations(
        handling_unit=handling_unit,
        handling_unit_type=handling_unit_type,
        company=company,
        branch=branch
    )
    
    # Categorize candidates by priority level
    level_1 = []  # Specific HU location
    level_2 = []  # HU type location
    level_3 = []  # Other locations
    level_4 = []  # Storage type preference
    level_5 = []  # Putaway policy
    
    for candidate in candidates:
        loc_name = candidate.get("location")
        if not loc_name:
            continue
        
        # Level 1: Specific HU location
        if handling_unit and loc_name in hu_locations:
            # Verify this location actually has this specific HU
            try:
                result = frappe.db.sql("""
                    SELECT COUNT(*) AS cnt
                    FROM `tabWarehouse Stock Ledger`
                    WHERE storage_location = %s AND handling_unit = %s AND quantity > 0
                """, (loc_name, handling_unit), as_dict=True)
                if result and result[0].get("cnt", 0) > 0:
                    level_1.append(candidate)
                    continue
            except Exception:
                pass
        
        # Level 2: HU type location
        if handling_unit_type and loc_name in hu_locations:
            level_2.append(candidate)
            continue
        
        # Level 3: Other locations (will be further prioritized by storage type and policy)
        level_3.append(candidate)
    
    # Order level 3 by storage type preference and putaway policy
    if item:
        level_3 = _order_locations_by_putaway_policy(level_3, item, company)
    
    # Combine all levels in priority order
    prioritized = level_1 + level_2 + level_3
    
    return prioritized


def _order_locations_by_putaway_policy(
    locations: List[Dict[str, Any]],
    item: str,
    company: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Order locations based on putaway policy (for putaway operations only).
    
    Args:
        locations: List of location dictionaries
        item: Item code
        company: Optional company for policy lookup
        
    Returns:
        Ordered list of locations
    """
    try:
        # Get putaway policy
        policy = frappe.db.get_value("Warehouse Item", item, "putaway_policy")
        if not policy and company:
            policy = frappe.db.get_value("Company", company, "putaway_policy")
        
        if not policy:
            policy = "Nearest Empty"
        
        # Order based on putaway policy
        if policy == "Consolidate Same Item":
            # Prioritize locations with existing stock of same item
            ordered = []
            for loc in locations:
                loc_name = loc.get("location")
                if loc_name:
                    try:
                        result = frappe.db.sql("""
                            SELECT SUM(quantity) AS total_qty
                            FROM `tabWarehouse Stock Ledger`
                            WHERE storage_location = %s AND item = %s AND quantity > 0
                        """, (loc_name, item), as_dict=True)
                        if result and result[0].get("total_qty", 0) > 0:
                            ordered.insert(0, loc)  # Add to front
                        else:
                            ordered.append(loc)  # Add to back
                    except Exception:
                        ordered.append(loc)
                else:
                    ordered.append(loc)
            return ordered
        elif policy == "Nearest Empty":
            # Prioritize locations with lower capacity utilization
            return sorted(locations, key=lambda x: (
                x.get("capacity_utilization", {}).get("volume", 100),
                x.get("capacity_utilization", {}).get("weight", 100),
                x.get("bin_priority", 999999)
            ))
        else:
            # Default: sort by bin priority and capacity utilization
            return sorted(locations, key=lambda x: (
                x.get("capacity_utilization", {}).get("volume", 100),
                x.get("bin_priority", 999999)
            ))
    except Exception as e:
        frappe.logger().warning(f"Error ordering locations by putaway policy: {str(e)}")
        # Fallback: sort by bin priority
        return sorted(locations, key=lambda x: x.get("bin_priority", 999999))


def _calculate_required_capacity_for_order(
    order_row: Dict[str, Any],
    capacity_manager: Any
) -> Dict[str, Any]:
    """Calculate required capacity (volume/weight) for an order row."""
    item = order_row.get("item")
    quantity = flt(order_row.get("quantity", 0))
    
    if not item or quantity <= 0:
        return {"volume": 0, "weight": 0, "quantity": 0}
    
    # Get item capacity data
    item_data = capacity_manager._get_item_capacity_data(item)
    
    # Calculate required capacity
    required = capacity_manager._calculate_required_capacity(item_data, quantity, None)
    
    return {
        "volume": required["volume"],
        "weight": required["weight"],
        "quantity": quantity,
        "item_data": item_data
    }


def _allocate_hu_to_orders(
    orders_without_hu: List[Dict[str, Any]],
    company: Optional[str],
    branch: Optional[str],
    capacity_manager: Any,
    used_hus: Set[str]
) -> Tuple[List[Tuple[str, Dict[str, Any], float, str]], List[str]]:
    """
    Allocate handling units to orders without HU, splitting quantities when capacity overflows.
    
    Returns:
        Tuple of (allocations, warnings) where allocations is list of (hu_name, order_row, qty, allocation_note)
    """
    allocations: List[Tuple[str, Dict[str, Any], float, str]] = []
    warnings: List[str] = []
    
    if not orders_without_hu:
        return allocations, warnings
    
    # Get split quantity decimal precision from Warehouse Settings
    split_precision = _get_split_quantity_decimal_precision()
    
    # Find all available handling units once
    all_available_hus = _find_available_handling_units(company, branch, exclude_hus=used_hus)
    
    if not all_available_hus:
        warnings.append(_("No available handling units found for allocation. Orders without HU will be skipped."))
        return allocations, warnings
    
    # Create a map to track HU capacity usage (for incremental updates during allocation)
    # OPTIMIZATION: Batch fetch HU capacity usage in a single query instead of individual queries
    hu_capacity_map: Dict[str, Dict[str, float]] = {}
    if all_available_hus:
        hu_names = [hu["name"] for hu in all_available_hus]
        
        # Batch fetch current usage for all HUs in one query
        batch_usage_data = frappe.db.sql("""
            SELECT 
                l.handling_unit,
                SUM(COALESCE(l.quantity, 0) * COALESCE(wi.volume, 0)) as current_volume,
                SUM(COALESCE(l.quantity, 0) * COALESCE(wi.weight, 0)) as current_weight
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
            WHERE l.handling_unit IN %s AND l.quantity > 0
            GROUP BY l.handling_unit
        """, (hu_names,), as_dict=True)
        
        # Create a lookup map for batch-fetched data
        usage_lookup = {row["handling_unit"]: row for row in batch_usage_data}
        
        # Build capacity map using batch-fetched data
        for hu in all_available_hus:
            hu_name = hu["name"]
            usage = usage_lookup.get(hu_name, {})
            hu_capacity_map[hu_name] = {
                "current_volume": flt(usage.get("current_volume", 0)),
                "current_weight": flt(usage.get("current_weight", 0)),
                "max_volume": flt(hu.get("max_volume", 0)),
                "max_weight": flt(hu.get("max_weight", 0))
            }
    
    # Process each order row with priority hierarchy
    for order_row in orders_without_hu:
        item = order_row.get("item")
        if not item:
            continue
        
        required_qty = flt(order_row.get("quantity", 0))
        if required_qty <= 0:
            continue
        
        # Check for handling_unit_type in order row
        order_handling_unit_type = order_row.get("handling_unit_type")
        
        # Priority hierarchy for HU allocation:
        # 1. Specific HU from order (if specified and valid)
        # 2. HU type from order (if specified)
        # 3. Putaway policy
        
        # Filter and prioritize HUs based on order requirements
        # Priority hierarchy: Filter to order requirements if specified, with fallback to all HUs for overflow
        available_hus = all_available_hus.copy()
        fallback_occurred = False
        fallback_message = None
        
        # Add priority scores to HUs to allow overflow allocation
        for hu in available_hus:
            hu["_hu_priority"] = 999  # Default low priority (for overflow allocation)
        
        # Check for specific handling unit in order (should be handled elsewhere, but check here too)
        order_handling_unit = order_row.get("handling_unit")
        
        if order_handling_unit:
            # Priority 1: Specific handling unit from order
            specific_hu_found = False
            for hu in available_hus:
                if hu.get("name") == order_handling_unit:
                    hu["_hu_priority"] = 1
                    specific_hu_found = True
            
            if not specific_hu_found:
                # Specific HU not found - fallback to all available HUs (putaway policy)
                fallback_occurred = True
                fallback_message = _("Order row {0}: Specified handling unit '{1}' not available. Fallback to putaway policy.").format(order_row.get("name", "?"), order_handling_unit)
                warnings.append(fallback_message)
            
            # Return all HUs with priority scores (priority 1 will be allocated first, then overflow from others)
            # This allows overflow allocation from other handling units if needed
            available_hus = _order_hus_by_putaway_policy(available_hus, item, company)
        elif order_handling_unit_type:
            # Priority 2: Handling unit type from order
            type_filtered_found = False
            for hu in available_hus:
                if hu.get("type") == order_handling_unit_type:
                    hu["_hu_priority"] = 2
                    type_filtered_found = True
            
            if not type_filtered_found:
                # No HUs of specified type - fallback to all available HUs (putaway policy)
                fallback_occurred = True
                fallback_message = _("Order row {0}: No handling units of type '{1}' available. Fallback to putaway policy.").format(order_row.get("name", "?"), order_handling_unit_type)
                warnings.append(fallback_message)
            
            # Return all HUs with priority scores (priority 2 will be allocated first, then overflow from priority 999)
            # This allows overflow allocation from other handling_unit_type if needed
            available_hus = _order_hus_by_putaway_policy(available_hus, item, company)
        else:
            # No type specified, order by putaway policy
            available_hus = _order_hus_by_putaway_policy(available_hus, item, company)
        
        # Store fallback info in order_row for use in allocation notes
        order_row["_fallback_occurred"] = fallback_occurred
        order_row["_fallback_message"] = fallback_message
        
        # Get item capacity data
        item_data = capacity_manager._get_item_capacity_data(item)
        
        # Calculate per-unit volume and weight
        # Try to get from item data
        per_unit_volume = 0
        per_unit_weight = 0
        
        if item_data.get("volume"):
            per_unit_volume = flt(item_data["volume"])
        elif all([item_data.get("length"), item_data.get("width"), item_data.get("height")]):
            per_unit_volume = flt(item_data["length"]) * flt(item_data["width"]) * flt(item_data["height"])
        
        per_unit_weight = flt(item_data.get("weight", 0))
        
        # If no capacity data, allow allocation without capacity constraints
        has_capacity_constraints = per_unit_volume > 0 or per_unit_weight > 0
        
        remaining_qty = required_qty
        
        # Try to allocate to available HUs
        while remaining_qty > 0:
            allocated = False
            
            # Try each available HU
            for hu in available_hus:
                # Check if HU is excluded (from initial used_hus set)
                if hu["name"] in used_hus:
                    continue
                
                hu_cap = hu_capacity_map.get(hu["name"], {})
                
                if has_capacity_constraints:
                    # Calculate available capacity in HU
                    available_volume = max(0, hu_cap["max_volume"] - hu_cap["current_volume"])
                    available_weight = max(0, hu_cap["max_weight"] - hu_cap["current_weight"])
                    
                    # Calculate max quantity that can fit based on volume and weight constraints
                    max_qty_by_volume = available_volume / per_unit_volume if per_unit_volume > 0 else float('inf')
                    max_qty_by_weight = available_weight / per_unit_weight if per_unit_weight > 0 else float('inf')
                    
                    # Take the minimum (most restrictive constraint)
                    max_fitting_qty = min(max_qty_by_volume, max_qty_by_weight)
                    
                    # Round max_fitting_qty using split quantity decimal precision
                    max_fitting_qty = round(max_fitting_qty, split_precision)
                    
                    if max_fitting_qty <= 0:
                        continue  # Skip this HU, it's full
                else:
                    # No capacity constraints, allocate all remaining quantity
                    max_fitting_qty = remaining_qty
                
                if max_fitting_qty > 0:
                    # Allocate as much as possible (up to remaining quantity)
                    qty_to_allocate = min(remaining_qty, max_fitting_qty)
                    
                    # Round qty_to_allocate using split quantity decimal precision
                    qty_to_allocate = round(qty_to_allocate, split_precision)
                    
                    if qty_to_allocate > 0:
                        # Determine allocation method with more descriptive labels
                        order_handling_unit = order_row.get("handling_unit")
                        order_handling_unit_type = order_row.get("handling_unit_type")
                        fallback_occurred = order_row.get("_fallback_occurred", False)
                        fallback_message = order_row.get("_fallback_message")
                        
                        if order_handling_unit and hu["name"] == order_handling_unit:
                            allocation_method = "Order (Specific Handling Unit)"
                        elif order_handling_unit_type:
                            # Check if this HU matches the type
                            try:
                                hu_type = frappe.db.get_value("Handling Unit", hu["name"], "type")
                                if hu_type == order_handling_unit_type:
                                    allocation_method = "Order (Handling Unit Type)"
                                else:
                                    policy = _get_putaway_policy(item, company)
                                    allocation_method = f"Putaway Policy ({policy})"
                            except Exception:
                                policy = _get_putaway_policy(item, company)
                                allocation_method = f"Putaway Policy ({policy})"
                        else:
                            policy = _get_putaway_policy(item, company)
                            allocation_method = f"Putaway Policy ({policy})"
                        
                        # Get putaway policy
                        policy = _get_putaway_policy(item, company)
                        
                        # Generate narrative log for HU allocation
                        allocation_note = _generate_hu_allocation_note(
                            order_row, hu["name"], qty_to_allocate, 
                            max_fitting_qty, remaining_qty, has_capacity_constraints,
                            hu_cap, per_unit_volume, per_unit_weight,
                            allocation_method=allocation_method,
                            policy=policy,
                            fallback_occurred=fallback_occurred,
                            fallback_message=fallback_message
                        )
                        
                        allocations.append((hu["name"], order_row, qty_to_allocate, allocation_note))
                        remaining_qty -= qty_to_allocate
                        
                        # Round remaining_qty using split quantity decimal precision
                        remaining_qty = round(remaining_qty, split_precision)
                        
                        # Update HU capacity usage in our tracking map
                        if has_capacity_constraints:
                            hu_cap["current_volume"] += per_unit_volume * qty_to_allocate
                            hu_cap["current_weight"] += per_unit_weight * qty_to_allocate
                            hu_capacity_map[hu["name"]] = hu_cap
                        
                        allocated = True
                        
                        if remaining_qty <= 0:
                            break
            
            # If we couldn't allocate remaining quantity, break but don't warn here
            # We'll create item rows for unallocated quantities later
            if not allocated and remaining_qty > 0:
                break
        
        # Track unallocated quantities for later processing
        if remaining_qty > 0:
            # Mark this order row as having unallocated quantity
            order_row["_has_unallocated"] = True
            order_row["_unallocated_qty"] = round(remaining_qty, split_precision)
            order_row["_allocated_qty"] = round(required_qty - remaining_qty, split_precision)
    
    return allocations, warnings


def _generate_hu_allocation_note(
    order_row: Dict[str, Any],
    hu_name: str,
    allocated_qty: float,
    max_fitting_qty: float,
    remaining_qty: float,
    has_capacity_constraints: bool,
    hu_capacity: Dict[str, float],
    per_unit_volume: float,
    per_unit_weight: float,
    allocation_method: str = "auto-allocated",
    policy: Optional[str] = None,
    fallback_occurred: bool = False,
    fallback_message: Optional[str] = None
) -> str:
    """Generate narrative log for handling unit allocation.
    
    Args:
        order_row: Order row dictionary
        hu_name: Handling unit name
        allocated_qty: Allocated quantity
        max_fitting_qty: Maximum quantity that fits
        remaining_qty: Remaining quantity
        has_capacity_constraints: Whether capacity constraints apply
        hu_capacity: HU capacity dictionary
        per_unit_volume: Per unit volume
        per_unit_weight: Per unit weight
        allocation_method: How the HU was allocated ("defined in order", "type-limited", "auto-allocated")
        policy: Putaway policy used
    """
    item = order_row.get("item", "Unknown Item")
    original_qty = flt(order_row.get("quantity", 0))
    company = order_row.get("company")
    
    note_parts = []
    note_parts.append(f"Handling Unit Allocation: {hu_name}")
    note_parts.append(f"  • Handling Unit Source: {allocation_method}")
    
    # Indicate fallback if it occurred
    if fallback_occurred and fallback_message:
        note_parts.append(f"  • ⚠️ FALLBACK: {fallback_message}")
    
    # Add more details about the source
    order_handling_unit = order_row.get("handling_unit")
    order_handling_unit_type = order_row.get("handling_unit_type")
    
    if order_handling_unit and hu_name == order_handling_unit:
        note_parts.append(f"    → Taken directly from order (specific handling unit specified)")
    elif order_handling_unit and hu_name != order_handling_unit:
        # Overflow allocation from other handling unit
        policy_desc = policy if policy else _get_putaway_policy(item, company)
        policy_name = policy_desc.split(': ')[-1] if ':' in policy_desc else policy_desc
        note_parts.append(f"    ⚠ Overflow: Allocated from other handling unit '{hu_name}' (order specified '{order_handling_unit}')")
        note_parts.append(f"    Overflow Allocation Method: Using item putaway policy ({policy_name})")
    elif order_handling_unit_type:
        try:
            hu_type = frappe.db.get_value("Handling Unit", hu_name, "type")
            if hu_type == order_handling_unit_type:
                note_parts.append(f"    → Matches handling unit type requirement from order")
            else:
                # Overflow allocation from other handling_unit_type
                policy_desc = policy if policy else _get_putaway_policy(item, company)
                policy_name = policy_desc.split(': ')[-1] if ':' in policy_desc else policy_desc
                note_parts.append(f"    ⚠ Overflow: Allocated from other handling unit type '{hu_type}' (order specified '{order_handling_unit_type}')")
                note_parts.append(f"    Overflow Allocation Method: Using item putaway policy ({policy_name})")
        except Exception:
            note_parts.append(f"    → Selected by putaway policy")
    else:
        note_parts.append(f"    → Selected by putaway policy (no handling unit requirements in order)")
    
    if policy:
        note_parts.append(f"  • Putaway Policy: {policy}")
    else:
        # Get policy if not provided
        policy_desc = _get_putaway_policy(item, company)
        note_parts.append(f"  • Putaway Policy: {policy_desc}")
    
    note_parts.append(f"  • Original Order Quantity: {original_qty} units")
    note_parts.append(f"  • Allocated Quantity: {allocated_qty} units")
    
    if has_capacity_constraints:
        available_vol = max(0, hu_capacity["max_volume"] - hu_capacity["current_volume"])
        available_wt = max(0, hu_capacity["max_weight"] - hu_capacity["current_weight"])
        
        note_parts.append(f"  • HU Capacity Check:")
        note_parts.append(f"    - Available Volume: {available_vol:.3f} (max: {hu_capacity['max_volume']:.3f}, used: {hu_capacity['current_volume']:.3f})")
        note_parts.append(f"    - Available Weight: {available_wt:.2f} (max: {hu_capacity['max_weight']:.2f}, used: {hu_capacity['current_weight']:.2f})")
        
        if per_unit_volume > 0:
            note_parts.append(f"    - Per Unit Volume: {per_unit_volume:.3f}")
        if per_unit_weight > 0:
            note_parts.append(f"    - Per Unit Weight: {per_unit_weight:.2f}")
        
        note_parts.append(f"    - Max Fitting Quantity: {max_fitting_qty:.2f} units")
        
        if allocated_qty < original_qty:
            note_parts.append(f"  • Split Required: {allocated_qty} units allocated, {remaining_qty} units remaining")
    else:
        note_parts.append(f"  • No capacity constraints configured - full quantity allocated")
    
    return "\n".join(note_parts)


def _generate_unallocated_hu_note(
    order_row: Dict[str, Any],
    remaining_qty: float,
    original_qty: float,
    allocated_qty: float
) -> str:
    """Generate narrative log for unallocated quantities (no HU assigned)."""
    item = order_row.get("item", "Unknown Item")
    
    note_parts = []
    note_parts.append(f"Handling Unit Allocation: NOT ALLOCATED")
    note_parts.append(f"  • Original Order Quantity: {original_qty} units")
    note_parts.append(f"  • Allocated to HUs: {allocated_qty} units")
    note_parts.append(f"  • Remaining Unallocated: {remaining_qty} units")
    note_parts.append(f"  • Reason: No available handling units with sufficient capacity")
    note_parts.append(f"  • Action Required: Manual HU assignment or create new handling units")
    
    return "\n".join(note_parts)


def _generate_location_allocation_note(
    hu: str,
    location: str,
    item: str,
    quantity: float,
    selection_method: str,
    location_details: Optional[Dict[str, Any]] = None,
    allocation_policy: Optional[str] = None,
    company: Optional[str] = None
) -> str:
    """Generate narrative log for location allocation.
    
    Args:
        hu: Handling unit name (optional)
        location: Location name
        item: Item code
        quantity: Quantity
        selection_method: How the location was selected
        location_details: Additional location details
        allocation_policy: Location allocation policy used
        company: Company for policy lookup
    """
    note_parts = []
    note_parts.append(f"Location Allocation: {location}")
    if hu:
        note_parts.append(f"  • Handling Unit: {hu}")
    else:
        note_parts.append(f"  • Handling Unit: None (unallocated)")
    note_parts.append(f"  • Item: {item}")
    note_parts.append(f"  • Quantity: {quantity} units")
    note_parts.append(f"  • Selection Method: {selection_method}")
    
    # Add allocation policy information
    if allocation_policy:
        note_parts.append(f"  • Allocation Policy: {allocation_policy}")
    else:
        # Get putaway policy if not provided
        policy_desc = _get_putaway_policy(item, company)
        note_parts.append(f"  • Putaway Policy: {policy_desc}")
    
    # Add location priority information
    if hu:
        # Check if location is where HU is currently located
        hu_locations = _get_hu_current_locations(handling_unit=hu, company=company)
        if location in hu_locations:
            note_parts.append(f"  • Priority: Level 1 (Location where handling unit is currently located)")
        else:
            # Check if location is where HU type is located
            try:
                hu_type = frappe.db.get_value("Handling Unit", hu, "type")
                if hu_type:
                    hu_type_locations = _get_hu_current_locations(handling_unit_type=hu_type, company=company)
                    if location in hu_type_locations:
                        note_parts.append(f"  • Priority: Level 2 (Location where handling unit type is located)")
                    else:
                        note_parts.append(f"  • Priority: Level 3+ (Policy-based selection)")
            except Exception:
                note_parts.append(f"  • Priority: Level 3+ (Policy-based selection)")
    
    if location_details:
        if location_details.get("is_consolidation"):
            note_parts.append(f"  • Consolidation Bin: Yes (contains existing stock of same item)")
        if location_details.get("capacity_utilization"):
            util = location_details["capacity_utilization"]
            if util.get("volume"):
                note_parts.append(f"  • Volume Utilization: {util['volume']:.1f}%")
            if util.get("weight"):
                note_parts.append(f"  • Weight Utilization: {util['weight']:.1f}%")
        if location_details.get("bin_priority"):
            note_parts.append(f"  • Bin Priority: {location_details['bin_priority']}")
    
    return "\n".join(note_parts)


def _hu_anchored_putaway_from_orders(job: Any) -> Tuple[int, float, List[Dict[str, Any]], List[str]]:
    """Impose HU → single destination; unique location per HU; warnings for violations."""
    frappe.logger().info(f"=== HU ANCHORED PUTAWAY STARTED for job {job.name} ===")
    company, branch = _get_job_scope(job)
    frappe.logger().info(f"Job scope: Company={company}, Branch={branch}")
    
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    dest_loc_field = "location" if "location" in jf else ("to_location" if "to_location" in jf else None)

    orders = _fetch_job_order_items(job.name)
    frappe.logger().info(f"Found {len(orders)} order items")
    
    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not orders:
        frappe.logger().info("No orders found, returning empty results")
        return created_rows, created_qty, details, warnings

    # Allocation Level Limit context
    staging_area = getattr(job, "staging_area", None)
    level_limit_label = _get_allocation_level_limit()
    allow_emergency_fallback = _get_allow_emergency_fallback()
    
    # Get split quantity decimal precision from Warehouse Settings
    split_precision = _get_split_quantity_decimal_precision()

    # exclude: locations flagged staging_area == 1 and the job's own staging area
    exclude = []
    if staging_area:
        exclude.append(staging_area)

    # Group by HU and validate specified HUs
    # OPTIMIZATION: Batch fetch all HUs upfront instead of individual queries
    by_hu: Dict[str, List[Dict[str, Any]]] = {}
    rows_without_hu: List[Dict[str, Any]] = []
    
    # Collect all unique HUs from orders
    unique_hus = list(set((r.get("handling_unit") or "").strip() for r in orders if r.get("handling_unit")))
    
    # Batch fetch all HU data in one query
    # Use frappe.db.sql() instead of frappe.get_all() to avoid DatabaseQuery.execute(as_dict=True) error
    # in newer Frappe versions
    hu_dict: Dict[str, Dict[str, Any]] = {}
    if unique_hus:
        placeholders = ", ".join(["%s"] * len(unique_hus))
        hus_data = frappe.db.sql(
            f"""
            SELECT name, status, company, branch
            FROM `tabHandling Unit`
            WHERE name IN ({placeholders})
            """,
            tuple(unique_hus),
            as_dict=True
        )
        hu_dict = {hu["name"]: hu for hu in hus_data}
        frappe.logger().info(f"Batch fetched {len(hu_dict)} handling units out of {len(unique_hus)} requested")
    
    # Validate and group orders by HU
    for r in orders:
        hu = (r.get("handling_unit") or "").strip()
        if hu:
            # Validate specified handling unit using batch-fetched data
            hu_valid = True
            hu_validation_errors = []
            
            # Check if HU exists (using batch data)
            if hu not in hu_dict:
                hu_valid = False
                hu_validation_errors.append(_("Handling unit {0} does not exist").format(hu))
            else:
                hu_data = hu_dict[hu]
                # Check HU status
                if hu_data.get("status") in ("Under Maintenance", "Inactive"):
                    hu_valid = False
                    hu_validation_errors.append(_("Handling unit {0} status is {1}").format(hu, hu_data.get("status")))
                
                # Check HU scope (company/branch)
                if company and hu_data.get("company") and hu_data.get("company") != company:
                    hu_valid = False
                    hu_validation_errors.append(_("Handling unit {0} belongs to company {1}, not {2}").format(hu, hu_data.get("company"), company))
                if branch and hu_data.get("branch") and hu_data.get("branch") != branch:
                    hu_valid = False
                    hu_validation_errors.append(_("Handling unit {0} belongs to branch {1}, not {2}").format(hu, hu_data.get("branch"), branch))
            
            if hu_valid:
                by_hu.setdefault(hu, []).append(r)
            else:
                # Invalid HU - treat as order without HU
                warnings.append(_("Order row {0}: Invalid handling unit '{1}'. {2} Treating as order without HU.")
                           .format(r.get("name", "?"), hu, " ".join(hu_validation_errors)))
                rows_without_hu.append(r)
        else:
            rows_without_hu.append(r)

    # Initialize capacity manager for HU allocation
    capacity_manager = CapacityManager()
    used_hus: Set[str] = set()
    
    # Allocate handling units to orders without HU
    if rows_without_hu:
        frappe.logger().info(f"Found {len(rows_without_hu)} order rows without handling unit. Attempting to allocate HUs.")
        
        # Process orders without HU and allocate HUs
        hu_allocations, hu_warnings = _allocate_hu_to_orders(
            rows_without_hu, company, branch, capacity_manager, used_hus
        )
        warnings.extend(hu_warnings)
        
        # Group allocations by HU and add to by_hu dict
        # Track which order rows have been fully allocated
        # Also track allocation notes for narrative logging
        allocated_order_rows = {}
        hu_allocation_notes: Dict[str, List[str]] = {}  # Track notes per HU
        
        for hu_name, order_row, allocated_qty, allocation_note in hu_allocations:
            order_key = order_row.get("name", id(order_row))
            
            # Track total allocated quantity per order row
            if order_key not in allocated_order_rows:
                allocated_order_rows[order_key] = {
                    "order_row": order_row,
                    "total_allocated": 0,
                    "allocations": []
                }
            
            allocated_order_rows[order_key]["total_allocated"] += allocated_qty
            allocated_order_rows[order_key]["allocations"].append((hu_name, allocated_qty, allocation_note))
            
            # Track allocation notes per HU
            if hu_name not in hu_allocation_notes:
                hu_allocation_notes[hu_name] = []
            hu_allocation_notes[hu_name].append(allocation_note)
        
        # Create allocated rows grouped by HU
        # Also track unallocated quantities to create rows without HU
        unallocated_order_rows: List[Dict[str, Any]] = []
        
        # Track which order rows were processed
        processed_order_keys = set()
        
        for order_key, alloc_info in allocated_order_rows.items():
            processed_order_keys.add(order_key)
            order_row = alloc_info["order_row"]
            original_qty = flt(order_row.get("quantity", 0))
            total_allocated = round(alloc_info["total_allocated"], split_precision)
            
            # Create allocated rows for each HU allocation
            for allocation in alloc_info["allocations"]:
                if len(allocation) == 3:
                    hu_name, allocated_qty, allocation_note = allocation
                else:
                    # Backward compatibility
                    hu_name, allocated_qty = allocation[:2]
                    allocation_note = ""
                
                allocated_row = order_row.copy()
                allocated_row["quantity"] = allocated_qty
                allocated_row["handling_unit"] = hu_name
                allocated_row["_hu_allocation_note"] = allocation_note  # Store temporarily for later use
                by_hu.setdefault(hu_name, []).append(allocated_row)
                used_hus.add(hu_name)
            
            # If quantity was not fully allocated, create row for remainder without HU
            if total_allocated < original_qty:
                remaining_qty = original_qty - total_allocated
                # Round remaining_qty using split quantity decimal precision
                remaining_qty = round(remaining_qty, split_precision)
                unallocated_row = order_row.copy()
                unallocated_row["quantity"] = remaining_qty
                unallocated_row["handling_unit"] = None
                unallocated_row["_unallocated_note"] = _generate_unallocated_hu_note(
                    order_row, remaining_qty, original_qty, total_allocated
                )
                unallocated_order_rows.append(unallocated_row)
                
                warnings.append(
                    _("Order row {0}: Only {1} of {2} units allocated to handling units. {3} units remain unallocated.")
                    .format(order_row.get("name", "?"), total_allocated, original_qty, remaining_qty)
                )
        
        # Check for orders that couldn't be allocated to any HU at all
        for order_row in rows_without_hu:
            order_key = order_row.get("name", id(order_row))
            if order_key not in processed_order_keys:
                # This order row couldn't be allocated to any HU
                original_qty = flt(order_row.get("quantity", 0))
                unallocated_row = order_row.copy()
                unallocated_row["quantity"] = original_qty
                unallocated_row["handling_unit"] = None
                unallocated_row["_unallocated_note"] = _generate_unallocated_hu_note(
                    order_row, original_qty, original_qty, 0
                )
                unallocated_order_rows.append(unallocated_row)
                
                warnings.append(
                    _("Order row {0}: Could not allocate {1} units to any handling unit. No available HUs with sufficient capacity.")
                    .format(order_row.get("name", "?"), original_qty)
                )
        
        # Add unallocated rows to rows_without_hu for location allocation
        if unallocated_order_rows:
            frappe.logger().info(f"Found {len(unallocated_order_rows)} order rows with unallocated quantities")
            for unallocated_row in unallocated_order_rows:
                # Group by empty string (no HU) for location allocation later
                by_hu.setdefault("", []).append(unallocated_row)
        
        if hu_allocations:
            frappe.logger().info(f"Allocated {len(hu_allocations)} handling units to orders without HU")
    
    # Add warning about emergency fallback setting
    if level_limit_label and not allow_emergency_fallback:
        warnings.append(_("Emergency fallback is disabled. Items will only be allocated within {0} of staging area.").format(level_limit_label))

    used_locations: Set[str] = set()  # ensure different HUs don't share the same destination

    # OPTIMIZATION: Cache location candidates per item to avoid redundant queries
    # The same item may be processed multiple times with different HUs
    location_candidates_cache: Dict[Tuple[str, Optional[str], Optional[str], Optional[str]], List[Dict[str, Any]]] = {}
    
    def get_cached_candidates(item: str, company: Optional[str], branch: Optional[str], 
                              exclude_locs: Optional[List[str]], quantity: float, 
                              handling_unit: Optional[str]) -> List[Dict[str, Any]]:
        """Get location candidates with caching. Cache key excludes quantity and handling_unit 
        as they don't affect the base candidate list, only filtering."""
        cache_key = (item, company, branch, tuple(sorted(exclude_locs or [])))
        if cache_key not in location_candidates_cache:
            location_candidates_cache[cache_key] = _putaway_candidate_locations(
                item=item, company=company, branch=branch,
                exclude_locations=exclude_locs, quantity=quantity, handling_unit=handling_unit
            )
            frappe.logger().debug(f"Cached location candidates for item {item}, company {company}, branch {branch}")
        return location_candidates_cache[cache_key]

    for hu, rows in by_hu.items():
        # Handle rows without HU (unallocated quantities)
        if not hu or hu == "":
            # Process unallocated rows - still allocate locations if possible
            for rr in rows:
                item = rr.get("item")
                if not item:
                    continue
                
                qty = flt(rr.get("quantity", 0))
                if qty <= 0:
                    continue
                
                # Try to allocate location even without HU
                dest = _select_dest_for_hu_with_capacity_validation(
                    item=item,
                    quantity=qty,
                    company=company,
                    branch=branch,
                    staging_area=staging_area,
                    level_limit_label=level_limit_label,
                    used_locations=used_locations,
                    exclude_locations=exclude,
                    handling_unit=None  # No HU assigned
                )
                
                if not dest:
                    # Try fallback
                    dest = _select_dest_for_hu_fallback(
                        item=item, company=company, branch=branch,
                        staging_area=staging_area, level_limit_label=level_limit_label,
                        used_locations=used_locations, exclude_locations=exclude
                    )
                
                # Get location details for narrative
                location_selection_method = "Standard selection (no HU)"
                location_selection_details = None
                if dest:
                    try:
                        candidates = get_cached_candidates(
                            item=item, company=company, branch=branch,
                            exclude_locs=exclude, quantity=qty, handling_unit=None
                        )
                        for candidate in candidates:
                            if candidate.get("location") == dest:
                                location_selection_details = {
                                    "is_consolidation": candidate.get("current_quantity", 0) > 0,
                                    "capacity_utilization": candidate.get("capacity_utilization", {}),
                                    "bin_priority": candidate.get("bin_priority", 999999)
                                }
                                break
                    except Exception as e:
                        frappe.logger().warning(f"Error getting location details for narrative: {str(e)}")
                
                # Generate allocation notes
                unallocated_note = rr.get("_unallocated_note", "")
                location_note = ""
                if dest:
                    location_note = _generate_location_allocation_note(
                        hu="",
                        location=dest,
                        item=item,
                        quantity=qty,
                        selection_method=location_selection_method,
                        location_details=location_selection_details,
                        allocation_policy=None,
                        company=company
                    )
                else:
                    # No location found - add note explaining why with detailed reasons
                    location_note = "Location Allocation: NOT ALLOCATED\n"
                    location_note += "  • Reason: No suitable storage location found within scope\n"
                    
                    # Add scope information
                    scope_info = []
                    if company:
                        scope_info.append(f"Company = {company}")
                    if branch:
                        scope_info.append(f"Branch = {branch}")
                    if staging_area and level_limit_label:
                        scope_info.append(f"Within {level_limit_label} of staging {staging_area}")
                    
                    if scope_info:
                        location_note += f"  • Scope: {', '.join(scope_info)}\n"
                    
                    location_note += "  • Possible causes:\n"
                    location_note += "    - No storage locations available matching item storage type requirements\n"
                    location_note += "    - All locations exceed capacity constraints\n"
                    if staging_area and level_limit_label:
                        location_note += f"    - All locations outside allocation level limit ({level_limit_label})\n"
                    location_note += "    - All locations already assigned to other handling units\n"
                    location_note += "  • Action Required: Review location availability, storage type configuration, or adjust allocation level limits"
                
                # Combine notes
                allocation_notes = []
                if unallocated_note:
                    allocation_notes.append(unallocated_note)
                if location_note:
                    allocation_notes.append(location_note)
                combined_allocation_note = "\n\n".join(allocation_notes) if allocation_notes else ""
                
                # Create item row
                payload = {
                    "item": item,
                    "quantity": qty,
                    "serial_no": rr.get("serial_no") or None,
                    "batch_no": rr.get("batch_no") or None,
                    "handling_unit": None,  # No HU assigned
                }
                if dest_loc_field:
                    payload[dest_loc_field] = dest
                if "uom" in jf and rr.get("uom"):
                    payload["uom"] = rr.get("uom")
                if "source_row" in jf:
                    payload["source_row"] = rr.get("name")
                if "source_parent" in jf:
                    payload["source_parent"] = job.name
                if "allocation_notes" in jf and combined_allocation_note:
                    payload["allocation_notes"] = combined_allocation_note
                
                # Copy physical dimensions if available
                if "length" in jf and rr.get("length"):
                    payload["length"] = flt(rr.get("length"))
                if "width" in jf and rr.get("width"):
                    payload["width"] = flt(rr.get("width"))
                if "height" in jf and rr.get("height"):
                    payload["height"] = flt(rr.get("height"))
                if "volume" in jf and rr.get("volume"):
                    payload["volume"] = flt(rr.get("volume"))
                if "weight" in jf and rr.get("weight"):
                    payload["weight"] = flt(rr.get("weight"))
                if "volume_uom" in jf and rr.get("volume_uom"):
                    payload["volume_uom"] = rr.get("volume_uom")
                if "weight_uom" in jf and rr.get("weight_uom"):
                    payload["weight_uom"] = rr.get("weight_uom")
                if "dimension_uom" in jf and rr.get("dimension_uom"):
                    payload["dimension_uom"] = rr.get("dimension_uom")
                
                if dest:
                    _assert_location_in_job_scope(dest, company, branch, ctx=_("Destination Location"))
                    used_locations.add(dest)
                
                job.append("items", payload)
                created_rows += 1
                created_qty += qty
                
                details.append({
                    "order_row": rr.get("name"), 
                    "item": item, 
                    "qty": qty, 
                    "dest_location": dest, 
                    "dest_handling_unit": None
                })
            
            continue  # Skip normal HU processing for unallocated rows
        
        # pick a representative item (first row) to get a good destination; then apply to all rows for this HU
        rep_item = None
        for rr in rows:
            if rr.get("item"):
                rep_item = rr["item"]; break
        if not rep_item:
            warnings.append(_("HU {0}: has rows without item; skipped.").format(hu))
            continue

        # choose destination for this HU (must be unique and match level limit)
        # First get all items in this HU to calculate total capacity requirements
        total_quantity = sum(flt(rr.get("quantity", 0)) for rr in rows)
        
        # Check if location overflow is enabled and get HU storage location size
        location_overflow_enabled = _get_location_overflow_enabled(company)
        storage_location_size = _get_hu_storage_location_size(hu) if location_overflow_enabled else 1
        
        # Log detailed information for debugging
        frappe.logger().info(f"Processing HU {hu} with item {rep_item}, quantity {total_quantity}")
        frappe.logger().info(f"HU {hu} - Company: {company}, Branch: {branch}")
        frappe.logger().info(f"HU {hu} - Staging: {staging_area}, Level limit: {level_limit_label}")
        frappe.logger().info(f"HU {hu} - Used locations: {list(used_locations)}")
        frappe.logger().info(f"HU {hu} - Exclude locations: {exclude}")
        if location_overflow_enabled:
            frappe.logger().info(f"HU {hu} - Location overflow enabled, storage_location_size: {storage_location_size}")
        
        # Track location selection details for narrative logging
        location_selection_method = ""
        location_selection_details: Optional[Dict[str, Any]] = None
        
        # Select destinations (single or multiple based on location overflow)
        dest_locations: List[str] = []
        if location_overflow_enabled and storage_location_size > 1:
            # Use multiple location selection
            dest_locations = _select_multiple_destinations_for_hu(
                item=rep_item,
                quantity=total_quantity,
                company=company,
                branch=branch,
                staging_area=staging_area,
                level_limit_label=level_limit_label,
                used_locations=used_locations,
                exclude_locations=exclude,
                handling_unit=hu,
                num_locations=storage_location_size
            )
            if dest_locations:
                location_selection_method = f"Location overflow allocation ({len(dest_locations)} locations)"
                dest = dest_locations[0]  # Keep dest for backward compatibility in notes
            else:
                dest = None
        else:
            # Use single location selection (original behavior)
            dest = _select_dest_for_hu_with_capacity_validation(
                item=rep_item, 
                quantity=total_quantity,
                company=company, 
                branch=branch,
                staging_area=staging_area, 
                level_limit_label=level_limit_label,
                used_locations=used_locations, 
                exclude_locations=exclude,
                handling_unit=hu
            )
            if dest:
                dest_locations = [dest]
        
        if not dest_locations:
            # Try fallback selection without capacity validation (only for single location mode)
            if not (location_overflow_enabled and storage_location_size > 1):
                frappe.logger().info(f"No capacity-validated location found for HU {hu}, trying fallback selection")
                dest = _select_dest_for_hu_fallback(
                    item=rep_item, company=company, branch=branch,
                    staging_area=staging_area, level_limit_label=level_limit_label,
                    used_locations=used_locations, exclude_locations=exclude
                )
                
                if dest:
                    location_selection_method = "Fallback selection (capacity validation bypassed)"
                    warnings.append(_("HU {0}: using fallback location {1} (capacity validation bypassed).")
                                    .format(hu, dest))
                    dest_locations = [dest]
            
            # Last resort: try again allowing reuse (but still honoring level limit)
            if not dest_locations:
                fallback = _select_dest_for_hu(
                    item=rep_item, company=company, branch=branch,
                    staging_area=staging_area, level_limit_label=level_limit_label,
                    used_locations=set(), exclude_locations=exclude
                )
                if fallback:
                    location_selection_method = "Location reuse (already assigned to another HU)"
                    warnings.append(_("HU {0}: no free destination matching rules; reusing {1} already assigned to another HU.")
                                    .format(hu, fallback))
                    dest_locations = [fallback]
            
            # Emergency bypass: try without level filtering (only if allowed)
            if not dest_locations and _get_allow_emergency_fallback():
                frappe.logger().warning(f"Emergency bypass: trying without level filtering for HU {hu}")
                emergency_dest = _select_dest_for_hu_emergency(
                    item=rep_item, company=company, branch=branch,
                    used_locations=used_locations, exclude_locations=exclude
                )
                if emergency_dest:
                    location_selection_method = "Emergency selection (level filtering bypassed)"
                    warnings.append(_("HU {0}: using emergency location {1} (level filtering bypassed).")
                                    .format(hu, emergency_dest))
                    dest_locations = [emergency_dest]
            elif not dest_locations:
                frappe.logger().warning(f"Emergency fallback disabled - no destination found for HU {hu} within level limit")

        if not dest_locations:
            # Perform detailed storage type validation to provide specific error messages
            validation_result = _validate_storage_type_restrictions(rep_item, company, branch)
            
            if not validation_result["valid"]:
                # Generate detailed error message with storage type restrictions
                error_msg = f"HU {hu}: No storage location found for item {rep_item}. "
                error_msg += " ".join(validation_result["error_details"])
                
                # Add storage type requirements to the message
                requirements = validation_result.get("item_storage_requirements", {})
                if requirements.get("allowed_storage_types"):
                    error_msg += f" Item requires storage types: {', '.join(requirements['allowed_storage_types'])}"
                elif requirements.get("preferred_storage_type"):
                    error_msg += f" Item requires storage type: {requirements['preferred_storage_type']}"
                
                warnings.append(error_msg)
                frappe.logger().error(f"Storage type validation failed for HU {hu}: {error_msg}")
            else:
                # Storage type validation passed but still no destination found
                # This could be due to capacity constraints or other factors
                debug_candidates = get_cached_candidates(
                    item=rep_item, company=company, branch=branch,
                    exclude_locs=exclude, quantity=total_quantity, handling_unit=hu
                )
                frappe.logger().error(f"Failed to find destination for HU {hu} with item {rep_item}")
                frappe.logger().error(f"Debug: Found {len(debug_candidates)} total candidates")
                if debug_candidates:
                    frappe.logger().error(f"Debug: Available locations: {[c['location'] for c in debug_candidates[:5]]}")
                
                # Build detailed reason message
                reason_parts = []
                reason_parts.append(_("HU {0}: no destination location available").format(hu))
                
                if not debug_candidates:
                    reason_parts.append(_("Reason: No candidate locations found"))
                    if company or branch:
                        scope_info = []
                        if company:
                            scope_info.append(_("Company = {0}").format(company))
                        if branch:
                            scope_info.append(_("Branch = {0}").format(branch))
                        reason_parts.append(_("Scope: {0}").format(", ".join(scope_info)))
                else:
                    reason_parts.append(_("Reason: {0} candidate location(s) found but filtered out").format(len(debug_candidates)))
                    if staging_area and level_limit_label:
                        reason_parts.append(_("by allocation level limit (within {0} of staging {1})").format(level_limit_label, staging_area))
                    if used_locations:
                        reason_parts.append(_("or already assigned to other handling units"))
                    reason_parts.append(_("Possible causes: capacity constraints, level limit restrictions, or location conflicts"))
                
                warnings.append(". ".join(reason_parts) + ".")
            continue

        # Mark all used locations to avoid assigning to a different HU
        for loc in dest_locations:
            used_locations.add(loc)

        # consolidation warnings for this HU
        items_in_hu = { (rr.get("item") or "").strip() for rr in rows if (rr.get("item") or "").strip() }
        for msg in _hu_consolidation_violations(hu, items_in_hu):
            warnings.append(msg)

        # Calculate split values for multiple locations
        num_locations = len(dest_locations) if dest_locations else 1
        split_precision = _get_split_quantity_decimal_precision()
        
        # append putaway rows for each original order line, split across locations if needed
        for rr in rows:
            qty = flt(rr.get("quantity") or 0)
            if qty <= 0:
                continue
            item = rr.get("item")
            
            # Calculate split values per location
            qty_per_location = round(qty / num_locations, split_precision) if num_locations > 0 else qty
            volume_per_location = None
            weight_per_location = None
            length_per_location = None
            width_per_location = None
            height_per_location = None
            
            if num_locations > 1:
                # Split volume, weight, and dimensions across locations
                if "volume" in jf and rr.get("volume"):
                    volume_per_location = round(flt(rr.get("volume")) / num_locations, 3)
                if "weight" in jf and rr.get("weight"):
                    weight_per_location = round(flt(rr.get("weight")) / num_locations, 2)
                if "length" in jf and rr.get("length"):
                    length_per_location = round(flt(rr.get("length")) / num_locations, 2)
                if "width" in jf and rr.get("width"):
                    width_per_location = round(flt(rr.get("width")) / num_locations, 2)
                if "height" in jf and rr.get("height"):
                    height_per_location = round(flt(rr.get("height")) / num_locations, 2)
            
            # Create items for each location
            remaining_qty = qty
            for loc_idx, dest_loc in enumerate(dest_locations):
                # Calculate quantity for this location (last location gets remainder to avoid rounding issues)
                if loc_idx == len(dest_locations) - 1:
                    loc_qty = remaining_qty
                else:
                    loc_qty = qty_per_location
                    remaining_qty -= loc_qty
                
                if loc_qty <= 0:
                    continue
                
                # Combine HU allocation note (if available) with location allocation note
                hu_note = rr.get("_hu_allocation_note", "")
                allocation_notes = []
                
                # If no HU note exists but HU is specified in order, create a note
                if not hu_note and hu:
                    hu_note = f"Handling Unit Allocation: {hu}\n  • Handling Unit Source: Order (Specific Handling Unit)\n    → Taken directly from order (specific handling unit specified)"
                    allocation_notes.append(hu_note)
                elif hu_note:
                    allocation_notes.append(hu_note)
                
                # Add location overflow note if multiple locations
                if num_locations > 1:
                    location_overflow_note = f"Location Allocation: {dest_loc}\n  • Location Overflow: Split across {num_locations} locations\n  • Location {loc_idx + 1} of {num_locations}\n  • Quantity: {loc_qty} of {qty} total"
                    allocation_notes.append(location_overflow_note)
                else:
                    # Single location - use standard location note
                    location_note = _generate_location_allocation_note(
                        hu=hu,
                        location=dest_loc,
                        item=rep_item,
                        quantity=loc_qty,
                        selection_method=location_selection_method or "Standard selection",
                        location_details=location_selection_details
                    )
                    if location_note:
                        allocation_notes.append(location_note)
                
                combined_allocation_note = "\n\n".join(allocation_notes) if allocation_notes else ""
                
                # Check for VAS action (Pick or Putaway) and signed quantity for VAS jobs only
                vas_action = None
                signed_qty = None
                job_type = (getattr(job, 'type', '') or '').strip()
                is_vas_job = job_type == "VAS"
                
                if is_vas_job:
                    if hasattr(rr, "vas_action"):
                        vas_action = getattr(rr, "vas_action", None)
                    elif isinstance(rr, dict) and "vas_action" in rr:
                        vas_action = rr.get("vas_action")
                    else:
                        # Try to get from job's action map using order item name as key
                        if hasattr(job, '_vas_action_map') and isinstance(job._vas_action_map, dict):
                            order_item_name = rr.get("name")  # Use order item name as key
                            if order_item_name:
                                vas_action = job._vas_action_map.get(order_item_name)
                                if hasattr(job, '_vas_quantity_map') and isinstance(job._vas_quantity_map, dict):
                                    signed_qty = job._vas_quantity_map.get(order_item_name)
                                if vas_action:
                                    frappe.logger().info(f"Found vas_action '{vas_action}' and signed_qty {signed_qty} for order item {order_item_name}")
                                else:
                                    frappe.logger().debug(f"vas_action not found for order item {order_item_name}. Available keys: {list(job._vas_action_map.keys())[:3]}")
                            else:
                                frappe.logger().warning(f"Order row has no 'name' field: {list(rr.keys())[:5]}")
                        else:
                            # Not a VAS job or no action map
                            pass
                
                # Use signed quantity if available, otherwise use positive qty
                item_quantity = signed_qty if signed_qty is not None else loc_qty
                if signed_qty is not None and num_locations > 1:
                    # Split signed quantity proportionally
                    item_quantity = round(signed_qty * (loc_qty / qty), split_precision) if qty > 0 else signed_qty / num_locations
                
                payload = {
                    "item": item,
                    "quantity": item_quantity,  # Can be negative for pick items
                    "serial_no": rr.get("serial_no") or None,
                    "batch_no": rr.get("batch_no") or None,
                    "handling_unit": hu,
                }
                
                # Set VAS action field only for VAS jobs
                if vas_action and is_vas_job:
                    if "vas_action" in jf:
                        payload["vas_action"] = vas_action
                        frappe.logger().info(f"Set vas_action='{vas_action}' and quantity={item_quantity} for item {item}")
                    else:
                        # Field might not be in meta cache, but try to set it anyway
                        payload["vas_action"] = vas_action
                        frappe.logger().warning(f"vas_action field not found in meta, but attempting to set it anyway. Fieldnames in meta: {sorted(jf)[:10]}...")
                
                # Add note for VAS items (only for VAS jobs)
                if vas_action and is_vas_job:
                    vas_note = f"VAS {vas_action} Item (from BOM)\n  • Parent Item: {rr.get('_vas_parent_item', item)}\n  • Action: {vas_action}\n  • Quantity: {item_quantity} ({'negative' if item_quantity < 0 else 'positive'})"
                    if combined_allocation_note:
                        combined_allocation_note = vas_note + "\n\n" + combined_allocation_note
                    else:
                        combined_allocation_note = vas_note
                
                if dest_loc_field:
                    payload[dest_loc_field] = dest_loc
                if "uom" in jf and rr.get("uom"):
                    payload["uom"] = rr.get("uom")
                if "source_row" in jf:
                    payload["source_row"] = rr.get("name")
                if "source_parent" in jf:
                    payload["source_parent"] = job.name
                
                # Add allocation notes if field exists
                if "allocation_notes" in jf and combined_allocation_note:
                    payload["allocation_notes"] = combined_allocation_note

                # Override with order-specific physical dimensions if available (split if multiple locations)
                if "length" in jf:
                    payload["length"] = length_per_location if length_per_location is not None else flt(rr.get("length"))
                if "width" in jf:
                    payload["width"] = width_per_location if width_per_location is not None else flt(rr.get("width"))
                if "height" in jf:
                    payload["height"] = height_per_location if height_per_location is not None else flt(rr.get("height"))
                if "volume" in jf:
                    payload["volume"] = volume_per_location if volume_per_location is not None else flt(rr.get("volume"))
                if "weight" in jf:
                    payload["weight"] = weight_per_location if weight_per_location is not None else flt(rr.get("weight"))
                if "volume_uom" in jf and rr.get("volume_uom"):
                    payload["volume_uom"] = rr.get("volume_uom")
                if "weight_uom" in jf and rr.get("weight_uom"):
                    payload["weight_uom"] = rr.get("weight_uom")
                if "dimension_uom" in jf and rr.get("dimension_uom"):
                    payload["dimension_uom"] = rr.get("dimension_uom")

                _assert_hu_in_job_scope(hu, company, branch, ctx=_("Handling Unit"))
                _assert_location_in_job_scope(dest_loc, company, branch, ctx=_("Destination Location"))

                job.append("items", payload)
                created_rows += 1
                created_qty += item_quantity  # Can be negative for pick items

                details.append({
                    "order_row": rr.get("name"), 
                    "item": item, 
                    "qty": loc_qty, 
                    "dest_location": dest_loc, 
                    "dest_handling_unit": hu
                })

    return created_rows, created_qty, details, warnings

@frappe.whitelist()
def allocate_handling_units(warehouse_job: str) -> Dict[str, Any]:
    """
    Allocate handling units to orders without HU assignment.
    This function updates order rows directly with handling units and splits items when capacity exceeds.
    
    Args:
        warehouse_job: Name of the Warehouse Job
        
    Returns:
        Dict with allocation results and warnings
    """
    frappe.logger().info(f"=== ALLOCATE HANDLING UNITS STARTED for job {warehouse_job} ===")
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Putaway":
        frappe.throw(_("Allocate Handling Units can only run for Warehouse Job Type = Putaway."))
    
    company, branch = _get_job_scope(job)
    orders = _fetch_job_order_items(job.name)
    
    if not orders:
        return {
            "ok": True,
            "message": _("No order items found to allocate handling units."),
            "allocated_count": 0,
            "updated_rows": 0,
            "new_rows_created": 0,
            "warnings": []
        }
    
    # Initialize capacity manager
    capacity_manager = CapacityManager()
    used_hus: Set[str] = set()
    
    # Find orders without handling units
    orders_without_hu = [r for r in orders if not (r.get("handling_unit") or "").strip()]
    
    if not orders_without_hu:
        return {
            "ok": True,
            "message": _("All order items already have handling units assigned."),
            "allocated_count": 0,
            "updated_rows": 0,
            "new_rows_created": 0,
            "warnings": []
        }
    
    frappe.logger().info(f"Found {len(orders_without_hu)} order rows without handling unit")
    
    # Allocate handling units to orders
    hu_allocations, warnings = _allocate_hu_to_orders(
        orders_without_hu, company, branch, capacity_manager, used_hus
    )
    
    if not hu_allocations:
        return {
            "ok": True,
            "message": _("No handling units could be allocated. {0}").format("; ".join(warnings) if warnings else ""),
            "allocated_count": 0,
            "updated_rows": 0,
            "new_rows_created": 0,
            "warnings": warnings
        }
    
    # Group allocations by order row to handle quantity splitting
    allocations_by_order: Dict[str, List[Tuple[str, float]]] = {}
    for hu_name, order_row, allocated_qty in hu_allocations:
        order_key = order_row.get("name")
        if order_key not in allocations_by_order:
            allocations_by_order[order_key] = []
        allocations_by_order[order_key].append((hu_name, allocated_qty))
    
    # Get order fields for creating new rows
    order_fields = _safe_meta_fieldnames("Warehouse Job Order Items")
    
    # Update order rows with handling units
    # For split quantities, we need to create additional order rows
    updated_count = 0
    new_rows_created = 0
    
    # Track which order rows to remove (we'll replace them with split rows)
    order_rows_to_remove = []
    
    for order_key, allocations in allocations_by_order.items():
        # Find the original order row in the job
        order_row_doc = None
        for order in job.orders:
            if order.name == order_key:
                order_row_doc = order
                break
        
        if not order_row_doc:
            warnings.append(_("Order row {0} not found in job.").format(order_key))
            continue
        
        original_qty = flt(order_row_doc.quantity)
        total_allocated = sum(qty for _, qty in allocations)
        
        if len(allocations) == 1:
            # Single HU allocation - update existing row
            hu_name, allocated_qty = allocations[0]
            order_row_doc.handling_unit = hu_name
            if allocated_qty < original_qty:
                # Split the row - update existing row with allocated qty
                order_row_doc.quantity = allocated_qty
                # Create new row for remainder (without HU)
                remainder_row_data = {
                    "item": order_row_doc.item,
                    "quantity": original_qty - allocated_qty,
                }
                # Copy optional fields if they exist
                if "uom" in order_fields and order_row_doc.uom:
                    remainder_row_data["uom"] = order_row_doc.uom
                if "serial_no" in order_fields and order_row_doc.serial_no:
                    remainder_row_data["serial_no"] = order_row_doc.serial_no
                if "batch_no" in order_fields and order_row_doc.batch_no:
                    remainder_row_data["batch_no"] = order_row_doc.batch_no
                if "length" in order_fields and order_row_doc.length:
                    remainder_row_data["length"] = order_row_doc.length
                if "width" in order_fields and order_row_doc.width:
                    remainder_row_data["width"] = order_row_doc.width
                if "height" in order_fields and order_row_doc.height:
                    remainder_row_data["height"] = order_row_doc.height
                if "volume" in order_fields and order_row_doc.volume:
                    remainder_row_data["volume"] = order_row_doc.volume
                if "weight" in order_fields and order_row_doc.weight:
                    remainder_row_data["weight"] = order_row_doc.weight
                if "volume_uom" in order_fields and order_row_doc.volume_uom:
                    remainder_row_data["volume_uom"] = order_row_doc.volume_uom
                if "weight_uom" in order_fields and order_row_doc.weight_uom:
                    remainder_row_data["weight_uom"] = order_row_doc.weight_uom
                if "dimension_uom" in order_fields and order_row_doc.dimension_uom:
                    remainder_row_data["dimension_uom"] = order_row_doc.dimension_uom
                
                job.append("orders", remainder_row_data)
                new_rows_created += 1
                warnings.append(
                    _("Order row {0}: Split into {1} units (HU: {2}) and {3} units (no HU).")
                    .format(order_key, allocated_qty, hu_name, original_qty - allocated_qty)
                )
            updated_count += 1
        else:
            # Multiple HU allocations - split into multiple rows
            # Mark original row for removal
            order_rows_to_remove.append(order_row_doc)
            
            # Create new rows for each allocation
            for hu_name, allocated_qty in allocations:
                new_row_data = {
                    "item": order_row_doc.item,
                    "quantity": allocated_qty,
                    "handling_unit": hu_name,
                }
                # Copy optional fields if they exist
                if "uom" in order_fields and order_row_doc.uom:
                    new_row_data["uom"] = order_row_doc.uom
                if "serial_no" in order_fields and order_row_doc.serial_no:
                    new_row_data["serial_no"] = order_row_doc.serial_no
                if "batch_no" in order_fields and order_row_doc.batch_no:
                    new_row_data["batch_no"] = order_row_doc.batch_no
                if "length" in order_fields and order_row_doc.length:
                    new_row_data["length"] = order_row_doc.length
                if "width" in order_fields and order_row_doc.width:
                    new_row_data["width"] = order_row_doc.width
                if "height" in order_fields and order_row_doc.height:
                    new_row_data["height"] = order_row_doc.height
                if "volume" in order_fields and order_row_doc.volume:
                    new_row_data["volume"] = order_row_doc.volume
                if "weight" in order_fields and order_row_doc.weight:
                    new_row_data["weight"] = order_row_doc.weight
                if "volume_uom" in order_fields and order_row_doc.volume_uom:
                    new_row_data["volume_uom"] = order_row_doc.volume_uom
                if "weight_uom" in order_fields and order_row_doc.weight_uom:
                    new_row_data["weight_uom"] = order_row_doc.weight_uom
                if "dimension_uom" in order_fields and order_row_doc.dimension_uom:
                    new_row_data["dimension_uom"] = order_row_doc.dimension_uom
                
                job.append("orders", new_row_data)
                new_rows_created += 1
                updated_count += 1
            
            # Create remainder row if needed (without HU)
            if total_allocated < original_qty:
                remainder_row_data = {
                    "item": order_row_doc.item,
                    "quantity": original_qty - total_allocated,
                }
                # Copy optional fields if they exist
                if "uom" in order_fields and order_row_doc.uom:
                    remainder_row_data["uom"] = order_row_doc.uom
                if "serial_no" in order_fields and order_row_doc.serial_no:
                    remainder_row_data["serial_no"] = order_row_doc.serial_no
                if "batch_no" in order_fields and order_row_doc.batch_no:
                    remainder_row_data["batch_no"] = order_row_doc.batch_no
                if "length" in order_fields and order_row_doc.length:
                    remainder_row_data["length"] = order_row_doc.length
                if "width" in order_fields and order_row_doc.width:
                    remainder_row_data["width"] = order_row_doc.width
                if "height" in order_fields and order_row_doc.height:
                    remainder_row_data["height"] = order_row_doc.height
                if "volume" in order_fields and order_row_doc.volume:
                    remainder_row_data["volume"] = order_row_doc.volume
                if "weight" in order_fields and order_row_doc.weight:
                    remainder_row_data["weight"] = order_row_doc.weight
                if "volume_uom" in order_fields and order_row_doc.volume_uom:
                    remainder_row_data["volume_uom"] = order_row_doc.volume_uom
                if "weight_uom" in order_fields and order_row_doc.weight_uom:
                    remainder_row_data["weight_uom"] = order_row_doc.weight_uom
                if "dimension_uom" in order_fields and order_row_doc.dimension_uom:
                    remainder_row_data["dimension_uom"] = order_row_doc.dimension_uom
                
                job.append("orders", remainder_row_data)
                new_rows_created += 1
                warnings.append(
                    _("Order row {0}: Split into {1} units across {2} handling units, {3} units remaining (no HU).")
                    .format(order_key, total_allocated, len(allocations), original_qty - total_allocated)
                )
            else:
                warnings.append(
                    _("Order row {0}: Split into {1} units across {2} handling units.")
                    .format(order_key, total_allocated, len(allocations))
                )
    
    # Remove original rows that were split into multiple rows
    for row_to_remove in order_rows_to_remove:
        job.remove(row_to_remove)
    
    # Save the job with updated order rows
    job.save(ignore_permissions=True)
    frappe.db.commit()
    
    frappe.logger().info(f"Allocated {len(hu_allocations)} handling units to {updated_count} order rows")
    
    message = _("Allocated {0} handling unit(s) to {1} order row(s).").format(len(hu_allocations), updated_count)
    if new_rows_created > 0:
        message += " " + _("Created {0} new order row(s) for quantity splits.").format(new_rows_created)
    
    return {
        "ok": True,
        "message": message,
        "allocated_count": len(hu_allocations),
        "updated_rows": updated_count,
        "new_rows_created": new_rows_created,
        "warnings": warnings
    }

@frappe.whitelist()
def allocate_putaway(warehouse_job: str) -> Dict[str, Any]:
    """Prepare putaway rows from Orders with HU anchoring & allocation-level rules.
    Now includes strict storage type validation with detailed error messages.
    
    Performance optimizations:
    - Storage type validation is skipped for jobs with >10 items (validated during allocation)
    - Capacity validation limited to top 20 candidates per item
    - Early exit when 5 valid candidates are found
    - Batch fetching of HU capacity data instead of individual queries
    - Location candidate caching to avoid redundant queries
    """
    frappe.logger().info(f"=== ALLOCATE PUTAWAY STARTED for job {warehouse_job} ===")
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Putaway":
        frappe.throw(_("Allocate Putaway can only run for Warehouse Job Type = Putaway."))

    # Clear existing items before allocation
    job.set("items", [])
    job.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.logger().info(f"Cleared existing items from job {warehouse_job}")

    frappe.logger().info(f"Job type: {job.type}, Staging area: {getattr(job, 'staging_area', None)}")
    
    # Pre-validate storage type restrictions for all items in the job
    company, branch = _get_job_scope(job)
    orders = _fetch_job_order_items(job.name)
    
    # Check storage type restrictions for all unique items
    # OPTIMIZATION: Only validate if there are few items (<= 10) to avoid performance issues
    # For larger jobs, validation will happen during allocation and errors will be caught then
    storage_type_warnings = []
    unique_items = list(set(order.get("item") for order in orders if order.get("item")))
    
    if unique_items and len(unique_items) <= 10:
        # Get comprehensive validation summary only for small item sets
        validation_summary = _get_storage_type_validation_summary(unique_items, company, branch)
        
        if not validation_summary["overall_valid"]:
            # Add summary warning
            summary_msg = f"Storage type validation failed for {validation_summary['invalid_items']}/{validation_summary['total_items']} items"
            storage_type_warnings.append(summary_msg)
            
            # Add detailed warnings for each invalid item
            for item, result in validation_summary["item_results"].items():
                if not result["valid"]:
                    error_msg = f"Item {item}: {'. '.join(result['error_details'])}"
                    storage_type_warnings.append(error_msg)
                    frappe.logger().warning(f"Storage type validation failed for item {item}: {error_msg}")
            
            # Add recommendations if available
            if validation_summary["recommendations"]:
                for rec in validation_summary["recommendations"]:
                    storage_type_warnings.append(f"Recommendation: {rec}")
                    frappe.logger().info(f"Storage type recommendation: {rec}")
        else:
            frappe.logger().info(f"Storage type validation passed for all {len(unique_items)} items")
    elif unique_items:
        frappe.logger().info(f"Skipping upfront storage type validation for {len(unique_items)} items (performance optimization). Validation will occur during allocation.")
    
    created_rows, created_qty, details, warnings = _hu_anchored_putaway_from_orders(job)
    
    # Add storage type warnings to the main warnings list
    warnings.extend(storage_type_warnings)
    
    frappe.logger().info(f"=== ALLOCATE PUTAWAY COMPLETED: {created_rows} rows, {created_qty} qty ===")

    # Save items directly to database without triggering hooks
    # This bypasses all validation hooks that might interfere
    # OPTIMIZATION: Use bulk INSERT instead of individual INSERT statements
    try:
        # Get available fields in Warehouse Job Item
        from .common import _safe_meta_fieldnames
        item_fields = _safe_meta_fieldnames("Warehouse Job Item")
        
        # Collect all items that need to be inserted
        items_to_insert = [item for item in job.items if item.get("__islocal") or not item.get("name")]
        
        if items_to_insert:
            # Build column list once (same for all items)
            columns = ["name", "parent", "parentfield", "parenttype", "idx", "item", "quantity", "location", "handling_unit", "uom", "serial_no", "batch_no", "creation", "modified", "modified_by", "owner", "docstatus"]
            
            # Add optional fields if they exist
            optional_fields = []
            if "source_row" in item_fields:
                optional_fields.append("source_row")
            if "source_parent" in item_fields:
                optional_fields.append("source_parent")
            if "allocation_notes" in item_fields:
                optional_fields.append("allocation_notes")
            if "volume" in item_fields:
                optional_fields.append("volume")
            if "weight" in item_fields:
                optional_fields.append("weight")
            if "length" in item_fields:
                optional_fields.append("length")
            if "width" in item_fields:
                optional_fields.append("width")
            if "height" in item_fields:
                optional_fields.append("height")
            
            columns.extend(optional_fields)
            columns_str = ", ".join(columns)
            
            # Prepare all values for bulk insert
            all_values = []
            now = frappe.utils.now()
            user = frappe.session.user
            
            for item in items_to_insert:
                values = [
                    item.name or frappe.generate_hash(length=10),
                    job.name,
                    "items", 
                    "Warehouse Job",
                    item.idx,
                    item.item,
                    item.quantity,
                    item.location,
                    item.handling_unit,
                    item.uom,
                    item.serial_no,
                    item.batch_no,
                    now,
                    now,
                    user,
                    user,
                    0
                ]
                
                # Add optional field values
                for field in optional_fields:
                    if field in ["volume", "weight", "length", "width", "height"]:
                        values.append(flt(getattr(item, field, None) or 0))
                    else:
                        values.append(getattr(item, field, None))
                
                all_values.append(tuple(values))
            
            # Execute bulk INSERT
            if all_values:
                placeholders = ", ".join(["%s"] * len(columns))
                # Create VALUES clause with multiple rows: (?,?,?), (?,?,?), ...
                values_placeholder = ", ".join([f"({placeholders})"] * len(all_values))
                
                # Flatten all values into a single list
                flat_values = [val for row in all_values for val in row]
                
                frappe.db.sql(f"""
                    INSERT INTO `tabWarehouse Job Item` 
                    ({columns_str})
                    VALUES {values_placeholder}
                """, tuple(flat_values))
                
                frappe.logger().info(f"Bulk inserted {len(all_values)} job items in a single query")
        
        # Update the job's modified timestamp
        frappe.db.set_value("Warehouse Job", job.name, "modified", frappe.utils.now())
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error saving putaway items: {str(e)}")
        frappe.throw(_("Error saving putaway items: {0}").format(str(e)))

    msg = _("Prepared {0} units across {1} putaway rows (staging excluded).").format(flt(created_qty), int(created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True, "message": msg,
        "created_rows": created_rows, "created_qty": created_qty,
        "lines": details, "warnings": warnings,
    }

@frappe.whitelist()
def allocate_vas_putaway(warehouse_job: str):
    """Legacy function name for backward compatibility.
    
    This function delegates to allocate_vas in vas.py.
    The new function combines pick and putaway allocation for VAS jobs.
    """
    # Import here to avoid circular dependency
    from .vas import allocate_vas
    return allocate_vas(warehouse_job)

@frappe.whitelist()
def post_putaway(warehouse_job: str) -> Dict[str, Any]:
    """Putaway step 2: Out from Staging (−ABS) + In to Destination (+ABS); marks putaway_posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    # Validate capacity limits before posting
    from logistics.warehousing.api_parts.capacity_management import validate_warehouse_job_capacity
    validate_warehouse_job_capacity(job)

    posting_dt = _posting_datetime(job)
    jf = _safe_meta_fieldnames("Warehouse Job Item")

    created_out = created_in = 0
    skipped: List[str] = []

    # enforce: one HU → one destination (if mixing slipped in by manual edits)
    hu_to_dest: Dict[str, str] = {}

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()

    for it in (job.items or []):
        if _row_is_already_posted(it, "putaway"):
            skipped.append(_("Item Row {0}: putaway already posted.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)
        dest = getattr(it, "to_location", None) if "to_location" in jf else getattr(it, "location", None)

        if not dest:
            skipped.append(_("Item Row {0}: missing destination location.").format(getattr(it, "idx", "?"))); continue

        # consistent HU → dest guard
        if hu:
            prev = hu_to_dest.get(hu)
            if prev and prev != dest:
                skipped.append(_("Item Row {0}: HU {1} already anchored to {2}; cannot also put to {3}.")
                               .format(getattr(it, "idx", "?"), hu, prev, dest))
                continue
            hu_to_dest.setdefault(hu, dest)

        _validate_status_for_action(action="Putaway", location=staging_area, handling_unit=hu)
        _validate_status_for_action(action="Putaway", location=dest,         handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1

        _insert_ledger_entry(job, item=item, qty=qty,  location=dest,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_in += 1

        _mark_row_posted(it, "putaway", posting_dt)

        # track affected
        affected_locs.add(staging_area)
        affected_locs.add(dest)
        if hu: affected_hus.add(hu)

    job.save(ignore_permissions=True)

    for l in affected_locs:
        _set_sl_status_by_balance(l)
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=False)

    frappe.db.commit()

    msg = _("Putaway posted: {0} OUT from staging, {1} IN to destinations.").format(created_out, created_in)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_staging": created_out, "in_to_destination": created_in, "skipped": skipped}

