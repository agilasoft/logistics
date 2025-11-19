from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Set

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

# Import shared helpers from common
from .common import (
    _get_job_scope, _fetch_job_order_items, _safe_meta_fieldnames,
    _get_item_rules, _query_available_candidates, _order_candidates,
    _greedy_allocate, _append_job_items, _row_is_already_posted,
    _mark_row_posted, _maybe_set_staging_area_on_row,
    _posting_datetime, _insert_ledger_entry, _validate_status_for_action,
    _set_sl_status_by_balance, _set_hu_status_by_balance,
    _get_allocation_level_limit, _filter_locations_by_level
)

# Import from putaway module
from .putaway import _hu_anchored_putaway_from_orders as _hu_anchored_putaway_from_orders_advanced

# Import from pick module for pick allocation logic
from .pick import _filter_candidates_by_hu_priority, _generate_pick_allocation_note, _append_job_items_with_notes


@frappe.whitelist()
def initiate_vas_pick(warehouse_job: str, clear_existing: int = 1):
    """VAS → Build pick rows for BOM components using same policies as standard picks."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Initiate VAS Pick can only run for Warehouse Job Type = VAS."))
    if (job.reference_order_type or "").strip() != "VAS Order" or not job.reference_order:
        frappe.throw(_("This VAS job must reference a VAS Order."))

    company, branch = _get_job_scope(job)
    if int(clear_existing or 0):
        job.set("items", [])

    vo = frappe.db.get_value("VAS Order", job.reference_order, ["customer", "type"], as_dict=True) or {}
    customer = vo.get("customer")
    vas_type = (vo.get("type") or "").strip()

    jo_items = _fetch_job_order_items(job.name)
    if not jo_items:
        return {"ok": True, "message": _("No parent items on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    skipped: List[str] = []
    warnings: List[str] = []

    def _find_vas_bom(parent_item: str) -> Optional[str]:
        base = {"item": parent_item}
        if vas_type: base["vas_order_type"] = vas_type
        if customer:
            r = frappe.get_all("Warehouse Item VAS BOM", filters={**base, "customer": customer},
                               fields=["name"], limit=1, ignore_permissions=True)
            if r: return r[0]["name"]
        r = frappe.get_all("Warehouse Item VAS BOM", filters=base, fields=["name"], limit=1, ignore_permissions=True)
        return r[0]["name"] if r else None

    for parent in jo_items:
        p_item = parent.get("item")
        p_qty  = flt(parent.get("quantity") or 0)
        if not p_item or p_qty <= 0:
            skipped.append(_("Job Order Row {0}: missing item or non-positive quantity").format(parent.get("name"))); continue

        bom = _find_vas_bom(p_item)
        if not bom:
            skipped.append(_("No VAS BOM for {0} (type={1}, customer={2})").format(p_item, vas_type or "N/A", customer or "N/A")); continue
        # fetch reverse_bom flag
        reverse_bom = 0
        try:
            reverse_bom = int(frappe.db.get_value("Warehouse Item VAS BOM", bom, "reverse_bom") or 0)
        except (ValueError, TypeError) as e:
            frappe.logger().debug(f"Failed to get reverse_bom for VAS BOM {bom}: {str(e)}, using default 0")
            reverse_bom = 0

            skipped.append(_("No VAS BOM for {0} (type={1}, customer={2})").format(p_item, vas_type or "N/A", customer or "N/A"))
            continue

        inputs = frappe.get_all(
            "Customer VAS Item Input",
            filters={"parent": bom, "parenttype": "Warehouse Item VAS BOM"},
            fields=["name", "item", "quantity", "uom", "handling_unit_type"],
            order_by="idx asc", ignore_permissions=True,
        )
        if not inputs:
            skipped.append(_("VAS BOM {0} has no inputs").format(bom)); continue

        for comp in inputs:
            c_item = comp.get("item")
            per    = flt(comp.get("quantity") or 0)
            uom    = comp.get("uom")
            req    = per * p_qty
            if not c_item or req <= 0:
                skipped.append(_("BOM {0} component missing item/quantity (row {1})").format(bom, comp.get("name"))); continue

            rules = _get_item_rules(c_item)
            cand  = _query_available_candidates(item=c_item, company=company, branch=branch)
            ordered = _order_candidates(cand, rules, req)
            allocs  = _greedy_allocate(ordered, req, rules, force_exact=False)

            if not allocs:
                scope_note = []
                if company: scope_note.append(_("Company = {0}").format(company))
                if branch:  scope_note.append(_("Branch = {0}").format(branch))
                scope_text = f" [{', '.join(scope_note)}]" if scope_note else ""
                warnings.append(_("No allocatable stock for VAS component {0} (Row {1}) within scope{2}.")
                                .format(c_item, comp.get("name"), scope_text))

            # Apply reverse_bom: if set (1), we keep POSITIVE; else default NEGATIVE for VAS pick
            final_allocs = []
            sign = 1 if reverse_bom else -1
            for a in allocs:
                q = flt(a.get("qty") or 0)
                if q > 0:
                    b = dict(a); b["qty"] = sign * q
                    final_allocs.append(b)

            c_rows, c_qty = _append_job_items(
                job=job, source_parent=job.name, source_child=f"{parent.get('name')}::{bom}",
                item=c_item, uom=uom, allocations=final_allocs,
            )
            created_rows += c_rows
            created_qty  += c_qty  # negative sum

            details.append({
                "parent_job_order_item": parent.get("name"),
                "parent_item": p_item,
                "component_item": c_item,
                "requested_qty": req,
                "allocated_qty": c_qty,  # negative
                "created_rows": c_rows,
                "short_qty": max(0.0, req + c_qty),
            })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Initiated VAS Pick. Allocated {0} units in {1} row(s).").format(flt(created_qty), int(created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True, "message": msg,
        "created_rows": int(created_rows), "created_qty": flt(created_rows and created_qty or 0),
        "lines": details, "skipped": skipped, "warnings": warnings,
    }


@frappe.whitelist()
def allocate_vas(warehouse_job: str):
    """VAS → Convert Orders rows into Items rows (combination of Pick and Putaway tasks).
    
    Uses VAS BOM to determine which items to pick and which to putaway:
    - Pick items: BOM components (or parent item if reverse_bom is checked)
    - Putaway items: Parent item (or BOM components if reverse_bom is checked)
    
    This function combines pick allocation (for items to be picked from current locations)
    and putaway allocation (for items to be putaway from staging).
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Allocate VAS can only run for Warehouse Job Type = VAS."))
    if int(job.docstatus or 0) != 0:
        frappe.throw(_("Allocate VAS must be run before submission."))
    if (job.reference_order_type or "").strip() != "VAS Order" or not job.reference_order:
        frappe.throw(_("This VAS job must reference a VAS Order."))

    # Clear existing items before allocation
    job.set("items", [])
    job.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.logger().info(f"Cleared existing items from job {warehouse_job}")

    # Get VAS Order info for BOM lookup
    vo = frappe.db.get_value("VAS Order", job.reference_order, ["customer", "type"], as_dict=True) or {}
    customer = vo.get("customer")
    vas_type = (vo.get("type") or "").strip()

    # Get original orders
    original_orders = _fetch_job_order_items(job.name)
    if not original_orders:
        return {
            "ok": True,
            "message": _("No order items found to allocate."),
            "created_rows": 0,
            "created_qty": 0,
            "lines": [],
            "warnings": []
        }

    # Get job scope (no progress messages during allocation)
    company, branch = _get_job_scope(job)

    # Find VAS BOM for each order item and expand based on reverse_bom flag
    def _find_vas_bom(parent_item: str) -> Optional[str]:
        base = {"item": parent_item}
        if vas_type: base["vas_order_type"] = vas_type
        if customer:
            r = frappe.get_all("Warehouse Item VAS BOM", filters={**base, "customer": customer},
                               fields=["name"], limit=1, ignore_permissions=True)
            if r: 
                frappe.logger().info(f"Found VAS BOM {r[0]['name']} for item {parent_item} with customer {customer}")
                return r[0]["name"]
        r = frappe.get_all("Warehouse Item VAS BOM", filters=base, fields=["name"], limit=1, ignore_permissions=True)
        if r:
            frappe.logger().info(f"Found VAS BOM {r[0]['name']} for item {parent_item} without customer filter")
            return r[0]["name"]
        frappe.logger().warning(f"No VAS BOM found for item {parent_item} (type={vas_type or 'N/A'}, customer={customer or 'N/A'})")
        return None

    # Expand orders based on VAS BOM
    expanded_orders: List[Dict[str, Any]] = []
    skipped: List[str] = []
    warnings: List[str] = []
    bom_processed_count = 0
    bom_expanded_count = 0

    for parent in original_orders:
        p_item = parent.get("item")
        p_qty = flt(parent.get("quantity") or 0)
        if not p_item or p_qty <= 0:
            skipped.append(_("Job Order Row {0}: missing item or non-positive quantity").format(parent.get("name")))
            continue

        bom = _find_vas_bom(p_item)
        if not bom:
            # No BOM found - use parent item as-is (fallback to original behavior)
            expanded_orders.append(parent)
            warnings.append(_("No VAS BOM found for {0} (type={1}, customer={2}). Using parent item directly.")
                           .format(p_item, vas_type or "N/A", customer or "N/A"))
            frappe.logger().info(f"Using parent item {p_item} directly (no BOM found)")
            continue

        bom_processed_count += 1
        # Get reverse_bom flag
        reverse_bom = 0
        try:
            reverse_bom = int(frappe.db.get_value("Warehouse Item VAS BOM", bom, "reverse_bom") or 0)
            frappe.logger().info(f"VAS BOM {bom} has reverse_bom={reverse_bom} for item {p_item}")
        except (ValueError, TypeError) as e:
            frappe.logger().debug(f"Failed to get reverse_bom for VAS BOM {bom}: {str(e)}, using default 0")
            reverse_bom = 0

        # Get BOM inputs (components)
        inputs = frappe.get_all(
            "Customer VAS Item Input",
            filters={"parent": bom, "parenttype": "Warehouse Item VAS BOM"},
            fields=["name", "item", "quantity", "uom", "handling_unit_type"],
            order_by="idx asc", ignore_permissions=True,
        )
        
        if not inputs:
            skipped.append(_("VAS BOM {0} has no inputs").format(bom))
            frappe.logger().warning(f"VAS BOM {bom} has no inputs - using parent item only")
            # If no inputs, just use parent item
            expanded_orders.append(parent)
            continue

        frappe.logger().info(f"Expanding item {p_item} (qty={p_qty}) into parent + {len(inputs)} BOM components from BOM {bom} (reverse_bom={reverse_bom})")
        
        # Always include both parent and components
        # The reverse_bom flag determines the sign (positive/negative) in the allocation
        
        # Add parent item with VAS action based on reverse_bom
        # reverse_bom = 0: parent is putaway (positive qty), components are picked (negative qty)
        # reverse_bom = 1: parent is picked (negative qty), components are putaway (positive qty)
        parent_row = parent.copy()
        parent_row["_vas_bom"] = bom
        parent_row["_vas_is_parent"] = True
        parent_row["_vas_reverse_bom"] = reverse_bom
        # Set VAS action: "Pick" if reverse_bom=1, "Putaway" if reverse_bom=0
        parent_row["_vas_action"] = "Pick" if reverse_bom == 1 else "Putaway"
        # Parent quantity: negative if Pick, positive if Putaway
        parent_row["_vas_quantity"] = -p_qty if reverse_bom == 1 else p_qty
        expanded_orders.append(parent_row)
        frappe.logger().info(f"  -> Parent: {p_item} (qty={p_qty}, action={'Pick' if reverse_bom == 1 else 'Putaway'}, signed_qty={-p_qty if reverse_bom == 1 else p_qty})")

        # Add BOM components with opposite action
        for comp in inputs:
            c_item = comp.get("item")
            per = flt(comp.get("quantity") or 0)
            req = per * p_qty
            if not c_item or req <= 0:
                skipped.append(_("BOM {0} component missing item/quantity (row {1})").format(bom, comp.get("name")))
                continue

            # Create expanded order row based on parent but with BOM component details
            expanded_row = parent.copy()
            expanded_row["item"] = c_item
            expanded_row["quantity"] = req
            if comp.get("uom"):
                expanded_row["uom"] = comp.get("uom")
            # Set handling_unit_type from BOM component (overrides parent's handling unit requirement)
            if comp.get("handling_unit_type"):
                expanded_row["handling_unit_type"] = comp.get("handling_unit_type")
                # Clear parent's specific handling_unit if component has handling_unit_type requirement
                # This ensures allocation follows BOM component's handling_unit_type, not parent's handling_unit
                expanded_row["handling_unit"] = None  # Always clear for components with handling_unit_type
                frappe.logger().info(f"  -> Component {c_item}: Set handling_unit_type={comp.get('handling_unit_type')}, cleared handling_unit")
            # Preserve source reference
            expanded_row["_vas_bom"] = bom
            expanded_row["_vas_parent_item"] = p_item
            expanded_row["_vas_parent_qty"] = p_qty
            expanded_row["_vas_is_component"] = True
            expanded_row["_vas_reverse_bom"] = reverse_bom
            # Components have opposite action from parent
            expanded_row["_vas_action"] = "Putaway" if reverse_bom == 1 else "Pick"
            # Component quantity: negative if Pick, positive if Putaway
            expanded_row["_vas_quantity"] = -req if reverse_bom == 0 else req
            expanded_orders.append(expanded_row)
            bom_expanded_count += 1
            frappe.logger().info(f"  -> Component: {c_item} (qty={req}, per={per}, action={'Putaway' if reverse_bom == 1 else 'Pick'}, signed_qty={-req if reverse_bom == 0 else req})")

    frappe.logger().info(f"VAS BOM processing: {bom_processed_count} BOMs processed, {bom_expanded_count} components created, {len(expanded_orders)} total expanded orders")

    # Temporarily create expanded order items in database for allocation
    # Store original order item names to restore later
    original_order_names = [o.get("name") for o in original_orders if o.get("name")]
    temp_order_names = []
    
    try:
        if expanded_orders:
            frappe.logger().info(f"Replacing {len(original_order_names)} original orders with {len(expanded_orders)} expanded orders")
            # Delete original order items temporarily
            if original_order_names:
                frappe.db.delete("Warehouse Job Order Items", {"name": ["in", original_order_names]})
                frappe.db.commit()
            
            # Store VAS action and quantity mapping for order items (by item+quantity+hu to identify unique rows)
            vas_action_map = {}
            vas_quantity_map = {}  # Store signed quantities
            
            # Create expanded order items
            for exp_order in expanded_orders:
                # Get VAS action (Pick or Putaway) and signed quantity
                vas_action = exp_order.get("_vas_action", "Putaway")  # Default to Putaway
                signed_qty = exp_order.get("_vas_quantity", flt(exp_order.get("quantity") or 0))
                base_qty = abs(signed_qty)
                
                # Get handling_unit and handling_unit_type, ensuring None is properly handled
                exp_hu = exp_order.get("handling_unit")
                exp_hu_type = exp_order.get("handling_unit_type")
                
                # For components with handling_unit_type from BOM, ensure handling_unit is None
                if exp_hu_type and exp_order.get("_vas_is_component"):
                    exp_hu = None  # Force None for BOM components with handling_unit_type
                    frappe.logger().info(f"Creating order item for component {exp_order.get('item')}: handling_unit_type={exp_hu_type}, handling_unit=None (cleared for BOM component)")
                
                order_doc = frappe.get_doc({
                    "doctype": "Warehouse Job Order Items",
                    "parent": job.name,
                    "parenttype": "Warehouse Job",
                    "parentfield": "orders",
                    "item": exp_order.get("item"),
                    "quantity": base_qty,  # Store absolute quantity in order
                    "uom": exp_order.get("uom"),
                    "handling_unit": exp_hu,  # Use explicitly cleared value
                    "handling_unit_type": exp_hu_type,
                    "serial_no": exp_order.get("serial_no"),
                    "batch_no": exp_order.get("batch_no"),
                })
                order_doc.insert(ignore_permissions=True)
                temp_order_names.append(order_doc.name)
                
                # Store VAS action and signed quantity mapping using order item name as key
                # This is more reliable than item+quantity+hu since the name is unique and stable
                vas_action_map[order_doc.name] = vas_action
                vas_quantity_map[order_doc.name] = signed_qty  # Store signed quantity
                frappe.logger().info(f"Stored VAS action '{vas_action}' and signed qty {signed_qty} for order item {order_doc.name}")
            
            # Store the action and quantity maps in job object for later use
            job._vas_action_map = vas_action_map
            job._vas_quantity_map = vas_quantity_map
            frappe.logger().info(f"Stored VAS action map with {len(vas_action_map)} entries: {list(vas_action_map.items())[:3]}")
            frappe.logger().info(f"Stored VAS quantity map with {len(vas_quantity_map)} entries: {list(vas_quantity_map.items())[:3]}")
            
            frappe.db.commit()
            # Reload job to get new orders
            job.reload()
            # Restore maps after reload (they're lost during reload)
            job._vas_action_map = vas_action_map
            job._vas_quantity_map = vas_quantity_map
            frappe.logger().info(f"Restored VAS action and quantity maps after reload")
            frappe.logger().info(f"Created {len(temp_order_names)} temporary expanded order items")
        else:
            frappe.logger().warning("No expanded orders to process - this should not happen")
            warnings.append(_("No expanded orders were created. Check BOM configuration."))
        
        # Split orders into pick and putaway items based on vas_action
        # Pick items need pick allocation (find in current locations)
        # Putaway items need putaway allocation (find in staging)
        pick_order_names = []
        putaway_order_names = []
        
        for order_name, vas_action in vas_action_map.items():
            if vas_action == "Pick":
                pick_order_names.append(order_name)
            else:
                putaway_order_names.append(order_name)
        
        frappe.logger().info(f"Split orders: {len(pick_order_names)} pick items, {len(putaway_order_names)} putaway items")
        
        total_created_rows = 0
        total_created_qty = 0.0
        all_details = []
        
        try:
            # Allocate pick items using pick logic (find in current storage locations)
            if pick_order_names:
                frappe.logger().info(f"Allocating {len(pick_order_names)} pick items using pick allocation logic")
                pick_orders = [o for o in _fetch_job_order_items(job.name) if o.get("name") in pick_order_names]
                
                staging_area = getattr(job, "staging_area", None)
                level_limit_label = _get_allocation_level_limit()
                
                for row in pick_orders:
                    item = row.get("item")
                    req_qty = flt(row.get("quantity") or 0)
                    if not item or req_qty <= 0:
                        continue
                    
                    # Log order row handling unit info for debugging
                    row_hu = row.get("handling_unit")
                    row_hu_type = row.get("handling_unit_type")
                    frappe.logger().info(f"Pick allocation for item {item}: handling_unit={row_hu}, handling_unit_type={row_hu_type}")
                    
                    # Get signed quantity from map
                    signed_qty = vas_quantity_map.get(row.get("name"), -req_qty)  # Default to negative for pick
                    
                    fixed_serial = row.get("serial_no") or None
                    fixed_batch = row.get("batch_no") or None
                    rules = _get_item_rules(item)
                    
                    # Find items in current storage locations (not staging)
                    if fixed_serial or fixed_batch:
                        candidates = _query_available_candidates(item=item, batch_no=fixed_batch, serial_no=fixed_serial,
                                                                 company=company, branch=branch)
                    else:
                        candidates = _query_available_candidates(item=item, company=company, branch=branch)
                    
                    # Filter by allocation level (same path as staging up to configured level)
                    candidates = _filter_locations_by_level(candidates, staging_area, level_limit_label)
                    
                    # Apply handling unit priority hierarchy
                    candidates = _filter_candidates_by_hu_priority(candidates, row, company, branch)
                    
                    if fixed_serial or fixed_batch:
                        allocations = _greedy_allocate(candidates, req_qty, rules, force_exact=True)
                    else:
                        # Order candidates while maintaining HU priority
                        def priority_key(c: Dict[str, Any]) -> Tuple:
                            hu_priority = c.get("_hu_priority", 999)
                            first_seen = c.get("first_seen")
                            last_seen = c.get("last_seen")
                            expiry = c.get("expiry_date")
                            method = (rules.get("picking_method") or "FIFO").upper()
                            
                            if method == "FEFO":
                                base_key = ((0, expiry) if expiry else (1, now_datetime()),)
                            elif method == "LEFO":
                                if expiry:
                                    base_key = ((0, -get_datetime(expiry).timestamp()),)
                                else:
                                    base_key = ((1, -get_datetime("1900-01-01").timestamp()),)
                            elif method in ("LIFO", "FMFO"):
                                ls = last_seen or get_datetime("1900-01-01")
                                base_key = ((-ls.timestamp()),)
                            else:  # FIFO
                                fs = first_seen or now_datetime()
                                base_key = ((fs.timestamp()),)
                            
                            return (hu_priority,) + base_key
                        
                        ordered = sorted(candidates, key=priority_key)
                        allocations = _greedy_allocate(ordered, req_qty, rules, force_exact=False)
                    
                    if not allocations:
                        # Build detailed reason for why no locations were found
                        reasons = []
                        scope_note = []
                        
                        if company: scope_note.append(_("Company = {0}").format(company))
                        if branch:  scope_note.append(_("Branch = {0}").format(branch))
                        if level_limit_label and staging_area:
                            scope_note.append(_("Within {0} of staging {1}").format(level_limit_label, staging_area))
                        
                        # Check if candidates were found before filtering
                        if not candidates:
                            reasons.append(_("No stock available for item '{0}'").format(item))
                            if fixed_serial:
                                reasons.append(_("with serial number '{0}'").format(fixed_serial))
                            if fixed_batch:
                                reasons.append(_("with batch '{0}'").format(fixed_batch))
                            if company or branch:
                                reasons.append(_("in scope: {0}").format(", ".join(scope_note)))
                        else:
                            # Candidates were found but filtered out
                            reasons.append(_("Stock found but filtered out by allocation level limit"))
                            if level_limit_label and staging_area:
                                reasons.append(_("Requires locations within {0} of staging area '{1}'").format(level_limit_label, staging_area))
                            reasons.append(_("Found {0} candidate location(s) but none within level limit").format(len(candidates)))
                        
                        reason_text = ". ".join(reasons) if reasons else _("No allocatable stock found")
                        scope_text = f" [{', '.join(scope_note)}]" if scope_note else ""
                        warnings.append(_("No allocatable stock for Pick Item {0} (Row {1}){2}. Reason: {3}")
                                        .format(item, row.get("idx"), scope_text, reason_text))
                    
                    # Convert allocations to use signed quantity (negative for pick)
                    signed_allocations = []
                    for a in allocations:
                        signed_a = dict(a)
                        signed_a["qty"] = -abs(flt(a.get("qty", 0)))  # Make negative for pick
                        signed_allocations.append(signed_a)
                    
                    # Generate allocation notes
                    allocated_qty = sum(abs(flt(a.get("qty", 0))) for a in allocations)
                    allocation_note = _generate_pick_allocation_note(
                        order_row=row,
                        allocations=allocations,
                        item=item,
                        requested_qty=req_qty,
                        allocated_qty=allocated_qty,
                        company=company
                    )
                    
                    # Append job items with VAS action and signed quantity
                    jf = _safe_meta_fieldnames("Warehouse Job Item")
                    for a in signed_allocations:
                        payload = {
                            "location": a.get("location"),
                            "handling_unit": a.get("handling_unit"),
                            "item": item,
                            "quantity": a.get("qty"),  # Negative for pick
                            "serial_no": a.get("serial_no"),
                            "batch_no": a.get("batch_no"),
                        }
                        if "vas_action" in jf:
                            payload["vas_action"] = "Pick"
                        if "allocation_notes" in jf and allocation_note:
                            payload["allocation_notes"] = allocation_note
                        if "uom" in jf and row.get("uom"):
                            payload["uom"] = row.get("uom")
                        job.append("items", payload)
                        total_created_rows += 1
                        total_created_qty += a.get("qty")  # Negative qty
                    
                    all_details.append({
                        "job_order_item": row["name"],
                        "item": item,
                        "requested_qty": req_qty,
                        "created_rows": len(signed_allocations),
                        "created_qty": sum(a.get("qty") for a in signed_allocations),
                        "action": "Pick"
                    })
            
            # Allocate putaway items using putaway logic (find in staging)
            if putaway_order_names:
                frappe.logger().info(f"Allocating {len(putaway_order_names)} putaway items using putaway allocation logic")
                # Temporarily delete pick items from database so putaway allocator only processes putaway items
                # The putaway allocator fetches from database, so we need to filter there
                pick_order_names_to_hide = [name for name in vas_action_map.keys() if name not in putaway_order_names]
                if pick_order_names_to_hide:
                    # Store pick order data before deleting
                    pick_orders_data = []
                    for name in pick_order_names_to_hide:
                        order_data = frappe.db.get_value("Warehouse Job Order Items", name, 
                                                        ["item", "quantity", "uom", "handling_unit", 
                                                         "handling_unit_type", "serial_no", "batch_no"], 
                                                        as_dict=True)
                        if order_data:
                            order_data["name"] = name
                            pick_orders_data.append(order_data)
                    
                    frappe.db.delete("Warehouse Job Order Items", {"name": ["in", pick_order_names_to_hide]})
                    frappe.db.commit()
                    frappe.logger().info(f"Temporarily hid {len(pick_order_names_to_hide)} pick items from database")
                
                try:
                    putaway_rows, putaway_qty, putaway_details, putaway_warnings = _hu_anchored_putaway_from_orders_advanced(job)
                    warnings.extend(putaway_warnings)
                    total_created_rows += putaway_rows
                    total_created_qty += putaway_qty
                    all_details.extend(putaway_details)
                finally:
                    # Restore pick items
                    if pick_order_names_to_hide and pick_orders_data:
                        for order_data in pick_orders_data:
                            order_doc = frappe.get_doc({
                                "doctype": "Warehouse Job Order Items",
                                "parent": job.name,
                                "parenttype": "Warehouse Job",
                                "parentfield": "orders",
                                "item": order_data.get("item"),
                                "quantity": order_data.get("quantity"),
                                "uom": order_data.get("uom"),
                                "handling_unit": order_data.get("handling_unit"),
                                "handling_unit_type": order_data.get("handling_unit_type"),
                                "serial_no": order_data.get("serial_no"),
                                "batch_no": order_data.get("batch_no"),
                            })
                            order_doc.insert(ignore_permissions=True)
                        frappe.db.commit()
                        frappe.logger().info(f"Restored {len(pick_orders_data)} pick items to database")
            
            frappe.logger().info(f"VAS allocation completed: {total_created_rows} rows, {total_created_qty} qty")
            
            # IMPORTANT: Save items to database BEFORE restoring orders
            # Otherwise job.reload() will lose the unsaved items
            frappe.logger().info(f"Saving {len(job.items)} items to database before restoring orders")
            job.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"Items saved successfully")
            
        except Exception as e:
            frappe.logger().error(f"Error during allocation for job {job.name}: {str(e)}", exc_info=True)
            frappe.throw(_("Error during allocation: {0}").format(str(e)))
        
    finally:
        # Restore original orders
        if temp_order_names:
            # Delete temporary expanded order items
            frappe.db.delete("Warehouse Job Order Items", {"name": ["in", temp_order_names]})
            frappe.db.commit()
            
            # Restore original order items
            if original_order_names:
                # Re-insert original orders
                for orig_order in original_orders:
                    order_doc = frappe.get_doc({
                        "doctype": "Warehouse Job Order Items",
                        "parent": job.name,
                        "parenttype": "Warehouse Job",
                        "parentfield": "orders",
                        "item": orig_order.get("item"),
                        "quantity": orig_order.get("quantity"),
                        "uom": orig_order.get("uom"),
                        "handling_unit": orig_order.get("handling_unit"),
                        "handling_unit_type": orig_order.get("handling_unit_type"),
                        "serial_no": orig_order.get("serial_no"),
                        "batch_no": orig_order.get("batch_no"),
                    })
                    order_doc.insert(ignore_permissions=True)
                frappe.db.commit()
            
            # Reload job to get restored orders (items are already saved)
            job.reload()
            frappe.logger().info(f"Restored original orders, job reloaded")

    # Add skipped items to warnings
    if skipped:
        warnings.extend(skipped)

    # Create summary message with BOM processing info
    summary_parts = []
    if bom_processed_count > 0:
        summary_parts.append(_("{0} VAS BOM(s) processed").format(bom_processed_count))
    if bom_expanded_count > 0:
        summary_parts.append(_("{0} BOM component(s) expanded").format(bom_expanded_count))
    
    summary_msg = _("Prepared {0} VAS item row(s) (Pick + Putaway) totaling {1}.").format(int(total_created_rows), flt(total_created_qty))
    if summary_parts:
        summary_msg += " " + " | ".join(summary_parts)
    if warnings:
        summary_msg += " " + _("Notes") + ": " + " | ".join(warnings[:5])  # Limit warnings in message

    return {
        "ok": True,
        "message": summary_msg,
        "created_rows": int(total_created_rows),
        "created_qty": flt(total_created_qty),
        "lines": all_details,
        "warnings": warnings,
    }


@frappe.whitelist()
def post_vas_pick(warehouse_job: str) -> Dict[str, Any]:
    """VAS Pick: Out from Location (−ABS) + In to Staging (+ABS); only processes items with vas_action='Pick' (negative quantity)."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Post VAS Pick can only run for Warehouse Job Type = VAS."))
    
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    created_out = created_in = 0
    skipped: List[str] = []

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()

    for it in (job.items or []):
        # Only process items with vas_action='Pick' (these have negative quantities)
        vas_action = getattr(it, "vas_action", None)
        if vas_action != "Pick":
            continue
            
        if _row_is_already_posted(it, "pick"):
            skipped.append(_("Item Row {0}: pick already posted.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        loc  = getattr(it, "location", None)
        qty  = flt(getattr(it, "quantity", 0))  # Can be negative
        abs_qty = abs(qty)
        if not item or not loc or abs_qty == 0:
            skipped.append(_("Item Row {0}: missing item, location, or zero quantity.").format(getattr(it, "idx", "?")))
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Pick", location=loc,          handling_unit=hu)
        _validate_status_for_action(action="Pick", location=staging_area, handling_unit=hu)

        # Out from location (negative)
        _insert_ledger_entry(job, item=item, qty=-abs_qty, location=loc,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1

        # In to staging (positive)
        _insert_ledger_entry(job, item=item, qty=abs_qty,  location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_in += 1

        _mark_row_posted(it, "pick", posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)

        affected_locs.add(loc)
        affected_locs.add(staging_area)
        if hu: affected_hus.add(hu)

    job.save(ignore_permissions=True)

    for l in affected_locs:
        _set_sl_status_by_balance(l)
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=False)

    frappe.db.commit()

    msg = _("VAS Pick posted: {0} OUT from locations, {1} IN to staging.").format(created_out, created_in)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_location": created_out, "in_to_staging": created_in, "skipped": skipped}


@frappe.whitelist()
def post_vas(warehouse_job: str) -> Dict[str, Any]:
    """VAS Operation: Negative for BOM items (components), Positive for parent item. This is the VAS transformation itself."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Post VAS can only run for Warehouse Job Type = VAS."))
    
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    created_negative = created_positive = 0
    skipped: List[str] = []

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()

    for it in (job.items or []):
        # Skip if pick or putaway already posted (VAS operation happens after pick, before putaway)
        if _row_is_already_posted(it, "pick") or _row_is_already_posted(it, "putaway"):
            continue

        item = getattr(it, "item", None)
        qty  = flt(getattr(it, "quantity", 0))  # Can be negative or positive
        if not item or qty == 0:
            continue
        
        # VAS operation: negative qty = consume BOM items, positive qty = produce parent item
        # All VAS operations happen in staging area
        loc = staging_area
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="VAS", location=loc, handling_unit=hu)

        # Post the quantity as-is (negative for BOM items, positive for parent)
        _insert_ledger_entry(job, item=item, qty=qty, location=loc,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        
        if qty < 0:
            created_negative += 1
        else:
            created_positive += 1

        affected_locs.add(loc)
        if hu: affected_hus.add(hu)

    job.save(ignore_permissions=True)

    for l in affected_locs:
        _set_sl_status_by_balance(l)
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=False)

    frappe.db.commit()

    msg = _("VAS operation posted: {0} negative (BOM items consumed), {1} positive (parent items produced).").format(created_negative, created_positive)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "negative_qty": created_negative, "positive_qty": created_positive, "skipped": skipped}


@frappe.whitelist()
def post_vas_putaway(warehouse_job: str) -> Dict[str, Any]:
    """VAS Putaway: Out from Staging (−ABS) + In to Destination (+ABS); only processes items with vas_action='Putaway' (positive quantity)."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Post VAS Putaway can only run for Warehouse Job Type = VAS."))
    
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    dest_loc_field = "location" if "location" in jf else ("to_location" if "to_location" in jf else None)

    created_out = created_in = 0
    skipped: List[str] = []

    # enforce: one HU → one destination (if mixing slipped in by manual edits)
    hu_to_dest: Dict[str, str] = {}

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()

    for it in (job.items or []):
        # Only process items with vas_action='Putaway' (these have positive quantities)
        vas_action = getattr(it, "vas_action", None)
        if vas_action != "Putaway":
            continue
            
        if _row_is_already_posted(it, "putaway"):
            skipped.append(_("Item Row {0}: putaway already posted.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        qty  = flt(getattr(it, "quantity", 0))  # Should be positive for putaway
        abs_qty = abs(qty)
        if not item or abs_qty == 0:
            skipped.append(_("Item Row {0}: missing item or zero quantity.").format(getattr(it, "idx", "?")))
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

        # Out from staging (negative)
        _insert_ledger_entry(job, item=item, qty=-abs_qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1

        # In to destination (positive)
        _insert_ledger_entry(job, item=item, qty=abs_qty,  location=dest,
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

    msg = _("VAS Putaway posted: {0} OUT from staging, {1} IN to destinations.").format(created_out, created_in)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_staging": created_out, "in_to_destination": created_in, "skipped": skipped}
