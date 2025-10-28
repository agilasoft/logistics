from __future__ import annotations
from .common import *  # shared helpers
from .common import _sl_fields, _get_job_scope, _safe_meta_fieldnames, _get_allocation_level_limit, _get_allow_emergency_fallback, _fetch_job_order_items, _hu_consolidation_violations, _assert_hu_in_job_scope, _assert_location_in_job_scope, _select_dest_for_hu, _filter_locations_by_level, _get_item_storage_type_prefs  # explicit imports
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
    handling_unit: str
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

    if rows_without_hu:
        warnings.append(_("Some order rows have no Handling Unit; operator must supply HU for putaway."))
    
    # Add warning about emergency fallback setting
    if level_limit_label and not allow_emergency_fallback:
        warnings.append(_("Emergency fallback is disabled. Items will only be allocated within {0} of staging area.").format(level_limit_label))

    used_locations: Set[str] = set()  # ensure different HUs don't share the same destination

    for hu, rows in by_hu.items():
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
        
        if not dest:
            # Try fallback selection without capacity validation
            frappe.logger().info(f"No capacity-validated location found for HU {hu}, trying fallback selection")
            dest = _select_dest_for_hu_fallback(
                item=rep_item, company=company, branch=branch,
                staging_area=staging_area, level_limit_label=level_limit_label,
                used_locations=used_locations, exclude_locations=exclude
            )
            
            if dest:
                warnings.append(_("HU {0}: using fallback location {1} (capacity validation bypassed).")
                                .format(hu, dest))
        
        if not dest:
            # Last resort: try again allowing reuse (but still honoring level limit)
            fallback = _select_dest_for_hu(
                item=rep_item, company=company, branch=branch,
                staging_area=staging_area, level_limit_label=level_limit_label,
                used_locations=set(), exclude_locations=exclude
            )
            if fallback:
                warnings.append(_("HU {0}: no free destination matching rules; reusing {1} already assigned to another HU.")
                                .format(hu, fallback))
                dest = fallback
        
        if not dest:
            # Emergency bypass: try without level filtering (only if allowed)
            if _get_allow_emergency_fallback():
                frappe.logger().warning(f"Emergency bypass: trying without level filtering for HU {hu}")
                emergency_dest = _select_dest_for_hu_emergency(
                    item=rep_item, company=company, branch=branch,
                    used_locations=used_locations, exclude_locations=exclude
                )
                if emergency_dest:
                    warnings.append(_("HU {0}: using emergency location {1} (level filtering bypassed).")
                                    .format(hu, emergency_dest))
                    dest = emergency_dest
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

        # append putaway rows for each original order line, but pin the HU and destination
        for rr in rows:
            qty = flt(rr.get("quantity") or 0)
            if qty <= 0:
                continue
            item = rr.get("item")
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

            _assert_hu_in_job_scope(hu, company, branch, ctx=_("Handling Unit"))
            _assert_location_in_job_scope(dest, company, branch, ctx=_("Destination Location"))

            job.append("items", payload)
            created_rows += 1
            created_qty  += qty

            details.append({"order_row": rr.get("name"), "item": item, "qty": qty, "dest_location": dest, "dest_handling_unit": hu})

    return created_rows, created_qty, details, warnings

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

