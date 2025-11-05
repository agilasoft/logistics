from __future__ import annotations
from .common import *  # shared helpers
from .common import _sl_fields, _get_job_scope, _safe_meta_fieldnames, _get_allocation_level_limit, _get_allow_emergency_fallback, _get_split_quantity_decimal_precision, _fetch_job_order_items, _hu_consolidation_violations, _assert_hu_in_job_scope, _assert_location_in_job_scope, _select_dest_for_hu, _filter_locations_by_level, _get_item_storage_type_prefs  # explicit imports
from .capacity_management import CapacityManager, CapacityValidationError

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

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
        
        # Get all available storage locations (without storage type filtering first)
        slf = _sl_fields()
        status_filter = "AND sl.status IN ('Available','In Use')" if ("status" in slf) else ""
        
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
              AND (%s IS NULL OR sl.company = %s)
              AND (%s IS NULL OR sl.branch = %s)
            ORDER BY sl.name ASC
            """,
            (company, company, branch, branch),
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
    capacity_manager = CapacityManager()
    validated_candidates = []
    fallback_candidates = []  # For locations that fail capacity validation but might still work
    
    for candidate in all_candidates:
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
            else:
                # Store as fallback candidate for later use if no valid candidates found
                violations = capacity_validation.get("validation_results", {}).get("violations", [])
                candidate["capacity_valid"] = False
                candidate["capacity_violations"] = violations
                fallback_candidates.append(candidate)
                
                # Log capacity violations for debugging
                if violations:
                    frappe.logger().info(f"Capacity validation failed for {candidate['location']}: {violations}")
                    
        except CapacityValidationError as e:
            # Log capacity validation errors but keep as fallback
            frappe.logger().info(f"Capacity validation error for {candidate['location']}: {str(e)}")
            candidate["capacity_valid"] = False
            candidate["capacity_error"] = str(e)
            fallback_candidates.append(candidate)
        except Exception as e:
            # Log other errors but keep as fallback
            frappe.logger().error(f"Unexpected error validating capacity for {candidate['location']}: {str(e)}")
            candidate["capacity_valid"] = False
            candidate["capacity_error"] = str(e)
            fallback_candidates.append(candidate)
    
    # If no validated candidates found, use fallback candidates with warnings
    if not validated_candidates and fallback_candidates:
        frappe.logger().warning(f"No capacity-validated locations found for item {item}, using fallback candidates")
        # Sort fallback candidates by priority and return them
        fallback_candidates.sort(key=lambda x: (x.get("storage_type_rank", 999999), x.get("bin_priority", 999999)))
        return fallback_candidates[:5]  # Return top 5 fallback candidates
    
    return validated_candidates


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
        
        # Improved sorting algorithm that prioritizes consolidation bins
        def enhanced_sort_key(candidate):
            # Priority 1: Consolidation bins (locations with existing stock)
            is_consolidation = candidate.get("current_quantity", 0) > 0
            
            # Priority 2: Capacity validation status
            capacity_valid = candidate.get("capacity_valid", False)
            
            # Priority 3: Capacity utilization (lower is better)
            utilization = candidate.get("capacity_utilization", {})
            volume_util = utilization.get("volume", 0)
            weight_util = utilization.get("weight", 0)
            hu_util = utilization.get("handling_units", 0)
            
            # Priority 4: Storage type and bin priority
            storage_type_rank = candidate.get("storage_type_rank", 999999)
            bin_priority = candidate.get("bin_priority", 999999)
            
            # Return tuple for sorting: (consolidation_priority, capacity_valid, utilization, storage_priority)
            return (
                not is_consolidation,  # False (0) for consolidation bins, True (1) for empty bins
                not capacity_valid,   # False (0) for valid capacity, True (1) for invalid
                volume_util,          # Lower volume utilization is better
                weight_util,          # Lower weight utilization is better
                hu_util,              # Lower HU utilization is better
                storage_type_rank,    # Lower storage type rank is better
                bin_priority          # Lower bin priority is better
            )
        
        # Sort candidates using enhanced sorting
        available_candidates.sort(key=enhanced_sort_key)
        
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
    
    # Build filters
    filters = {"status": ["in", ["Available", "In Use"]]}
    if company:
        filters["company"] = company
    if branch:
        filters["branch"] = branch
    
    # Get handling units with capacity data
    hus = frappe.get_all(
        "Handling Unit",
        filters=filters,
        fields=[
            "name", "type", "status", "company", "branch",
            "max_volume", "max_weight", "current_volume", "current_weight",
            "capacity_uom", "weight_uom"
        ],
        order_by="name asc"
    ) or []
    
    # Filter out excluded HUs
    available_hus = [hu for hu in hus if hu["name"] not in exclude_hus]
    
    # Calculate available capacity for each HU
    for hu in available_hus:
        hu["available_volume"] = max(0, flt(hu.get("max_volume", 0)) - flt(hu.get("current_volume", 0)))
        hu["available_weight"] = max(0, flt(hu.get("max_weight", 0)) - flt(hu.get("current_weight", 0)))
    
    return available_hus


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
    
    # Find available handling units
    available_hus = _find_available_handling_units(company, branch, exclude_hus=used_hus)
    
    if not available_hus:
        warnings.append(_("No available handling units found for allocation. Orders without HU will be skipped."))
        return allocations, warnings
    
    # Sort available HUs by available capacity (descending) to prioritize HUs with more space
    available_hus.sort(key=lambda x: (x.get("available_volume", 0) + x.get("available_weight", 0)), reverse=True)
    
    # Create a map to track HU capacity usage (for incremental updates during allocation)
    hu_capacity_map: Dict[str, Dict[str, float]] = {}
    for hu in available_hus:
        hu_current_usage = capacity_manager._get_handling_unit_current_usage(hu["name"])
        hu_capacity_map[hu["name"]] = {
            "current_volume": hu_current_usage["volume"],
            "current_weight": hu_current_usage["weight"],
            "max_volume": flt(hu.get("max_volume", 0)),
            "max_weight": flt(hu.get("max_weight", 0))
        }
    
    # Process each order row
    for order_row in orders_without_hu:
        item = order_row.get("item")
        if not item:
            continue
        
        required_qty = flt(order_row.get("quantity", 0))
        if required_qty <= 0:
            continue
        
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
                        # Generate narrative log for HU allocation
                        allocation_note = _generate_hu_allocation_note(
                            order_row, hu["name"], qty_to_allocate, 
                            max_fitting_qty, remaining_qty, has_capacity_constraints,
                            hu_cap, per_unit_volume, per_unit_weight
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
    per_unit_weight: float
) -> str:
    """Generate narrative log for handling unit allocation."""
    item = order_row.get("item", "Unknown Item")
    original_qty = flt(order_row.get("quantity", 0))
    
    note_parts = []
    note_parts.append(f"Handling Unit Allocation: {hu_name}")
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
    location_details: Optional[Dict[str, Any]] = None
) -> str:
    """Generate narrative log for location allocation."""
    note_parts = []
    note_parts.append(f"Location Allocation: {location}")
    if hu:
        note_parts.append(f"  • Handling Unit: {hu}")
    else:
        note_parts.append(f"  • Handling Unit: None (unallocated)")
    note_parts.append(f"  • Item: {item}")
    note_parts.append(f"  • Quantity: {quantity} units")
    note_parts.append(f"  • Selection Method: {selection_method}")
    
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

    # Group by HU
    by_hu: Dict[str, List[Dict[str, Any]]] = {}
    rows_without_hu: List[Dict[str, Any]] = []
    for r in orders:
        hu = (r.get("handling_unit") or "").strip()
        if hu:
            by_hu.setdefault(hu, []).append(r)
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
                        candidates = _putaway_candidate_locations(
                            item=item, company=company, branch=branch,
                            exclude_locations=exclude, quantity=qty, handling_unit=None
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
                        location_details=location_selection_details
                    )
                else:
                    # No location found - add note explaining why
                    location_note = "Location Allocation: NOT ALLOCATED\n"
                    location_note += "  • Reason: No suitable storage location found within scope\n"
                    location_note += "  • Possible causes: No locations available, capacity constraints, or level limit restrictions\n"
                    location_note += "  • Action Required: Review location availability or adjust allocation level limits"
                
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
        
        # Log detailed information for debugging
        frappe.logger().info(f"Processing HU {hu} with item {rep_item}, quantity {total_quantity}")
        frappe.logger().info(f"HU {hu} - Company: {company}, Branch: {branch}")
        frappe.logger().info(f"HU {hu} - Staging: {staging_area}, Level limit: {level_limit_label}")
        frappe.logger().info(f"HU {hu} - Used locations: {list(used_locations)}")
        frappe.logger().info(f"HU {hu} - Exclude locations: {exclude}")
        
        # Track location selection details for narrative logging
        location_selection_method = ""
        location_selection_details: Optional[Dict[str, Any]] = None
        
        # Try capacity-validated selection first
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
            location_selection_method = "Capacity-validated selection"
            # Get location details for narrative after selection
            try:
                candidates = _putaway_candidate_locations(
                    item=rep_item, company=company, branch=branch,
                    exclude_locations=exclude, quantity=total_quantity, handling_unit=hu
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
                location_selection_details = None
        
        if not dest:
            # Try fallback selection without capacity validation
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
                # Try to get location details for narrative
                try:
                    candidates = _putaway_candidate_locations(
                        item=rep_item, company=company, branch=branch,
                        exclude_locations=exclude, quantity=total_quantity, handling_unit=hu
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
        
        if not dest:
            # Last resort: try again allowing reuse (but still honoring level limit)
            fallback = _select_dest_for_hu(
                item=rep_item, company=company, branch=branch,
                staging_area=staging_area, level_limit_label=level_limit_label,
                used_locations=set(), exclude_locations=exclude
            )
            if fallback:
                location_selection_method = "Location reuse (already assigned to another HU)"
                warnings.append(_("HU {0}: no free destination matching rules; reusing {1} already assigned to another HU.")
                                .format(hu, fallback))
                dest = fallback
                # Try to get location details for narrative
                try:
                    candidates = _putaway_candidate_locations(
                        item=rep_item, company=company, branch=branch,
                        exclude_locations=exclude, quantity=total_quantity, handling_unit=hu
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
        
        if not dest:
            # Emergency bypass: try without level filtering (only if allowed)
            if _get_allow_emergency_fallback():
                frappe.logger().warning(f"Emergency bypass: trying without level filtering for HU {hu}")
                emergency_dest = _select_dest_for_hu_emergency(
                    item=rep_item, company=company, branch=branch,
                    used_locations=used_locations, exclude_locations=exclude
                )
                if emergency_dest:
                    location_selection_method = "Emergency selection (level filtering bypassed)"
                    warnings.append(_("HU {0}: using emergency location {1} (level filtering bypassed).")
                                    .format(hu, emergency_dest))
                    dest = emergency_dest
                    # Try to get location details for narrative
                    try:
                        candidates = _putaway_candidate_locations(
                            item=rep_item, company=company, branch=branch,
                            exclude_locations=exclude, quantity=total_quantity, handling_unit=hu
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
            else:
                frappe.logger().warning(f"Emergency fallback disabled - no destination found for HU {hu} within level limit")

        if not dest:
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
                debug_candidates = _putaway_candidate_locations(
                    item=rep_item, company=company, branch=branch,
                    exclude_locations=exclude, quantity=total_quantity, handling_unit=hu
                )
                frappe.logger().error(f"Failed to find destination for HU {hu} with item {rep_item}")
                frappe.logger().error(f"Debug: Found {len(debug_candidates)} total candidates")
                if debug_candidates:
                    frappe.logger().error(f"Debug: Available locations: {[c['location'] for c in debug_candidates[:5]]}")
                
                warnings.append(_("HU {0}: no destination location available in scope (capacity or other constraints).").format(hu))
            continue

        # mark used to avoid assigning the same location to a different HU
        used_locations.add(dest)

        # consolidation warnings for this HU
        items_in_hu = { (rr.get("item") or "").strip() for rr in rows if (rr.get("item") or "").strip() }
        for msg in _hu_consolidation_violations(hu, items_in_hu):
            warnings.append(msg)

        # Generate location allocation note
        location_note = ""
        if dest:
            location_note = _generate_location_allocation_note(
                hu=hu,
                location=dest,
                item=rep_item,
                quantity=total_quantity,
                selection_method=location_selection_method or "Standard selection",
                location_details=location_selection_details
            )
        
        # append putaway rows for each original order line, but pin the HU and destination
        for rr in rows:
            qty = flt(rr.get("quantity") or 0)
            if qty <= 0:
                continue
            item = rr.get("item")
            
            # Combine HU allocation note (if available) with location allocation note
            hu_note = rr.get("_hu_allocation_note", "")
            allocation_notes = []
            
            if hu_note:
                allocation_notes.append(hu_note)
            if location_note:
                allocation_notes.append(location_note)
            
            combined_allocation_note = "\n\n".join(allocation_notes) if allocation_notes else ""
            
            payload = {
                "item": item,
                "quantity": qty,
                "serial_no": rr.get("serial_no") or None,
                "batch_no": rr.get("batch_no") or None,
                "handling_unit": hu,
            }
            if dest_loc_field:
                payload[dest_loc_field] = dest
            if "uom" in jf and rr.get("uom"):
                payload["uom"] = rr.get("uom")
            if "source_row" in jf:
                payload["source_row"] = rr.get("name")
            if "source_parent" in jf:
                payload["source_parent"] = job.name
            
            # Add allocation notes if field exists
            if "allocation_notes" in jf and combined_allocation_note:
                payload["allocation_notes"] = combined_allocation_note

            # Override with order-specific physical dimensions if available
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

            _assert_hu_in_job_scope(hu, company, branch, ctx=_("Handling Unit"))
            _assert_location_in_job_scope(dest, company, branch, ctx=_("Destination Location"))

            job.append("items", payload)
            created_rows += 1
            created_qty  += qty

            details.append({"order_row": rr.get("name"), "item": item, "qty": qty, "dest_location": dest, "dest_handling_unit": hu})

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
    Now includes strict storage type validation with detailed error messages."""
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
    storage_type_warnings = []
    unique_items = list(set(order.get("item") for order in orders if order.get("item")))
    
    if unique_items:
        # Get comprehensive validation summary
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
    
    created_rows, created_qty, details, warnings = _hu_anchored_putaway_from_orders(job)
    
    # Add storage type warnings to the main warnings list
    warnings.extend(storage_type_warnings)
    
    frappe.logger().info(f"=== ALLOCATE PUTAWAY COMPLETED: {created_rows} rows, {created_qty} qty ===")

    # Save items directly to database without triggering hooks
    # This bypasses all validation hooks that might interfere
    try:
        # Get available fields in Warehouse Job Item
        from .common import _safe_meta_fieldnames
        item_fields = _safe_meta_fieldnames("Warehouse Job Item")
        
        # Save the job items directly to the database
        for item in job.items:
            if item.get("__islocal") or not item.get("name"):
                # Build dynamic SQL based on available fields
                columns = ["name", "parent", "parentfield", "parenttype", "idx", "item", "quantity", "location", "handling_unit", "uom", "serial_no", "batch_no", "creation", "modified", "modified_by", "owner", "docstatus"]
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
                    frappe.utils.now(),
                    frappe.utils.now(),
                    frappe.session.user,
                    frappe.session.user,
                    0
                ]
                
                # Add optional fields if they exist
                if "source_row" in item_fields:
                    columns.append("source_row")
                    values.append(getattr(item, 'source_row', None))
                
                if "source_parent" in item_fields:
                    columns.append("source_parent")
                    values.append(getattr(item, 'source_parent', None))
                
                if "allocation_notes" in item_fields:
                    columns.append("allocation_notes")
                    values.append(getattr(item, 'allocation_notes', None))
                
                # Build and execute SQL
                columns_str = ", ".join(columns)
                placeholders = ", ".join(["%s"] * len(values))
                
                frappe.db.sql(f"""
                    INSERT INTO `tabWarehouse Job Item` 
                    ({columns_str})
                    VALUES ({placeholders})
                """, tuple(values))
        
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
    """VAS → Convert Orders rows into Items rows (Putaway tasks) on the same job."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Initiate VAS Putaway can only run for Warehouse Job Type = VAS."))
    if int(job.docstatus or 0) != 0:
        frappe.throw(_("Initiate VAS Putaway must be run before submission."))

    # Clear existing items before allocation
    job.set("items", [])
    job.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.logger().info(f"Cleared existing items from job {warehouse_job}")

    # Delegate to HU-anchored allocator (it already handles warnings)
    created_rows, created_qty, details, warnings = _hu_anchored_putaway_from_orders(job)

    job.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "ok": True,
        "message": _("Prepared {0} putaway item row(s) totaling {1}.").format(int(created_rows), flt(created_qty)),
        "created_rows": created_rows, "created_qty": created_qty,
        "lines": details, "warnings": warnings,
    }

@frappe.whitelist()
def post_putaway(warehouse_job: str) -> Dict[str, Any]:
    """Putaway step 2: Out from Staging (−ABS) + In to Destination (+ABS); marks putaway_posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

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

