from __future__ import annotations
from .common import *  # shared helpers
from .common import _sl_fields, _get_job_scope, _safe_meta_fieldnames, _get_allocation_level_limit, _fetch_job_order_items, _hu_consolidation_violations, _assert_hu_in_job_scope, _assert_location_in_job_scope, _select_dest_for_hu  # explicit imports
from .capacity_management import CapacityManager, CapacityValidationError

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

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
       Now includes comprehensive capacity validation."""
    exclude_locations = exclude_locations or []
    slf = _sl_fields()
    status_filter = "AND sl.status IN ('Available','In Use')" if ("status" in slf) else ""

    # Consolidation bins that already contain this item (not staging)
    cons = frappe.db.sql(
        f"""
        SELECT l.storage_location AS location,
               IFNULL(sl.bin_priority, 999999) AS bin_priority,
               IFNULL(st.picking_rank, 999999) AS storage_type_rank
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabStorage Type`   st ON st.name = sl.storage_type
        WHERE l.item = %s
          AND IFNULL(sl.staging_area, 0) = 0
          {status_filter}
          {("AND l.storage_location NOT IN (" + ", ".join(["%s"]*len(exclude_locations)) + ")") if exclude_locations else ""}
          AND (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch  = %s)
        GROUP BY l.storage_location, sl.bin_priority, st.picking_rank
        HAVING SUM(l.quantity) > 0
        ORDER BY storage_type_rank ASC, bin_priority ASC, sl.name ASC
        """,
        tuple([item] + exclude_locations + [company, company, branch, branch]),
        as_dict=True,
    ) or []
    cons_set = {c["location"] for c in cons}

    # Other valid bins (not staging), excluding already chosen consolidation bins
    others = frappe.db.sql(
        f"""
        SELECT sl.name AS location,
               IFNULL(sl.bin_priority, 999999) AS bin_priority,
               IFNULL(st.picking_rank, 999999) AS storage_type_rank
        FROM `tabStorage Location` sl
        LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
        WHERE IFNULL(sl.staging_area, 0) = 0
          {status_filter}
          {("AND sl.name NOT IN (" + ", ".join(["%s"]*len(exclude_locations)) + ")") if exclude_locations else ""}
          AND (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch  = %s)
        ORDER BY storage_type_rank ASC, bin_priority ASC, sl.name ASC
        """,
        tuple(exclude_locations + [company, company, branch, branch]),
        as_dict=True,
    ) or []
    others = [r for r in others if r["location"] not in cons_set]

    # Combine all candidates
    all_candidates = cons + others
    
    # Apply capacity validation to filter out locations that can't accommodate the item
    capacity_manager = CapacityManager()
    validated_candidates = []
    
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
                # Log capacity violations for debugging
                violations = capacity_validation.get("validation_results", {}).get("violations", [])
                if violations:
                    frappe.logger().info(f"Capacity validation failed for {candidate['location']}: {violations}")
                    
        except CapacityValidationError as e:
            # Log capacity validation errors
            frappe.logger().info(f"Capacity validation error for {candidate['location']}: {str(e)}")
            continue
        except Exception as e:
            # Log other errors but don't fail the entire process
            frappe.logger().error(f"Unexpected error validating capacity for {candidate['location']}: {str(e)}")
            continue
    
    return validated_candidates


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
    """Select destination for HU with comprehensive capacity validation"""
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
        
        # Filter by allocation level limit
        if staging_area and level_limit_label:
            candidates = _filter_locations_by_level(candidates, staging_area, level_limit_label)
        
        # Filter out used locations
        available_candidates = [c for c in candidates if c["location"] not in used_locations]
        
        if not available_candidates:
            return None
        
        # Sort by capacity utilization (prefer locations with lower utilization)
        def capacity_sort_key(candidate):
            utilization = candidate.get("capacity_utilization", {})
            # Use volume utilization as primary sort key, then weight, then HU count
            volume_util = utilization.get("volume", 0)
            weight_util = utilization.get("weight", 0)
            hu_util = utilization.get("handling_units", 0)
            return (volume_util, weight_util, hu_util, candidate.get("bin_priority", 999999))
        
        available_candidates.sort(key=capacity_sort_key)
        
        return available_candidates[0]["location"] if available_candidates else None
        
    except Exception as e:
        frappe.logger().error(f"Error selecting destination with capacity validation: {str(e)}")
        return None


def _hu_anchored_putaway_from_orders(job: Any) -> Tuple[int, float, List[Dict[str, Any]], List[str]]:
    """Impose HU → single destination; unique location per HU; warnings for violations."""
    company, branch = _get_job_scope(job)
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    dest_loc_field = "location" if "location" in jf else ("to_location" if "to_location" in jf else None)

    orders = _fetch_job_order_items(job.name)
    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not orders:
        return created_rows, created_qty, details, warnings

    # Allocation Level Limit context
    staging_area = getattr(job, "staging_area", None)
    level_limit_label = _get_allocation_level_limit()

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
            # last resort: try again allowing reuse (but still honoring level limit)
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
            warnings.append(_("HU {0}: no destination location available in scope.").format(hu))
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
    """Prepare putaway rows from Orders with HU anchoring & allocation-level rules."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Putaway":
        frappe.throw(_("Allocate Putaway can only run for Warehouse Job Type = Putaway."))

    created_rows, created_qty, details, warnings = _hu_anchored_putaway_from_orders(job)

    job.save(ignore_permissions=True)
    frappe.db.commit()

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

