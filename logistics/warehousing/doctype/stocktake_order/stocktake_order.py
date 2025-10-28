# Copyright (c) 2025, www.agilasoft.com
# For license information, please see license.txt

from typing import Any, Dict, List, Optional, Set, Tuple

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.data import flt


# -----------------------------------------------------------------------------
# Meta helper
# -----------------------------------------------------------------------------
def _safe_meta_fieldnames(doctype: str) -> Set[str]:
    meta = frappe.get_meta(doctype)
    out: Set[str] = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None) or (df.get("fieldname") if isinstance(df, dict) else None)
        if fn:
            out.add(fn)
    return out


def _get_item_uom(item: Optional[str]) -> Optional[str]:
    if not item:
        return None
    return frappe.db.get_value("Warehouse Item", item, "uom")


# -----------------------------------------------------------------------------
# Controller (kept minimal)
# -----------------------------------------------------------------------------
class StocktakeOrder(Document):
    pass


# -----------------------------------------------------------------------------
# Public API: Get Count Items (no quantity)
# -----------------------------------------------------------------------------
@frappe.whitelist()
def stocktake_get_count_items(
    stocktake_order: str,
    customer: Optional[str] = None,
    company: Optional[str] = None,
    branch: Optional[str] = None,
    storage_type: Optional[str] = None,
    only_active: int = 1,
    limit_rows: int = 1000,
    clear_existing: int = 1,
    do_update: int = 1,
):
    """
    Populate Stocktake Order -> items with a unique list of items based on filters:
      - Customer (blank = no filter)
      - Company / Branch
      - Storage Type (only applied if Warehouse Item has such a field)
      - Only Active (filters disabled items if Warehouse Item has 'disabled')

    NOTES:
      • No quantity is added here (counting done in Warehouse Job).
      • If clear_existing=1, existing child rows are removed first.
      • Duplicates are avoided when not clearing.
    """
    if not stocktake_order:
        frappe.throw(_("Stocktake Order is required."))

    doc = frappe.get_doc("Stocktake Order", stocktake_order)

    warnings: List[str] = []
    wi_fields = _safe_meta_fieldnames("Warehouse Item")

    # Build Warehouse Item filters gently (only for fields that exist)
    wi_filters: Dict[str, Any] = {}

    customer = (customer or "").strip() or None
    company = (company or "").strip() or None
    branch = (branch or "").strip() or None
    storage_type = (storage_type or "").strip() or None
    only_active = 1 if int(only_active or 0) else 0
    limit_rows = max(1, int(limit_rows or 1000))

    if customer and ("customer" in wi_fields):
        wi_filters["customer"] = customer
    elif customer and ("customer" not in wi_fields):
        warnings.append(_("Customer filter ignored: 'customer' field not found on Warehouse Item."))

    # Company and Branch filters are not applicable to Warehouse Item by design
    # These filters are handled at the Storage Location/Handling Unit level instead
    if company and ("company" in wi_fields):
        wi_filters["company"] = company
    # Note: No warning for company filter as it's not expected on Warehouse Item

    if branch and ("branch" in wi_fields):
        wi_filters["branch"] = branch
    # Note: No warning for branch filter as it's not expected on Warehouse Item

    if storage_type:
        if "storage_type" in wi_fields:
            wi_filters["storage_type"] = storage_type
        else:
            warnings.append(_("Storage Type filter ignored: 'storage_type' field not found on Warehouse Item."))

    if only_active and ("disabled" in wi_fields):
        wi_filters["disabled"] = 0

    # Fetch candidate items (unique)
    candidates = frappe.get_all(
        "Warehouse Item",
        filters=wi_filters,
        fields=["name as item", "uom"],
        limit=limit_rows,
        order_by="modified desc",
        ignore_permissions=True,
    ) or []

    # Clear existing child rows if requested
    if int(clear_existing or 0):
        doc.set("items", [])

    # Prepare existing set to avoid duplicates if not clearing
    existing_items = set()
    for r in (doc.items or []):
        code = getattr(r, "item", None)
        if code:
            existing_items.add(code)

    # Child schema-awareness
    child_dt = "Stocktake Order Item"
    cf = _safe_meta_fieldnames(child_dt)
    has_uom = "uom" in cf
    has_desc = "description" in cf

    added = 0
    for row in candidates:
        code = row.get("item")
        if not code or code in existing_items:
            continue

        payload: Dict[str, Any] = {"item": code}

        # UOM: prefer Warehouse Item.uom when child supports UOM
        if has_uom:
            payload["uom"] = row.get("uom") or _get_item_uom(code) or None

        # Description if field exists (optional fetch to avoid large selects)
        if has_desc:
            desc = frappe.db.get_value("Warehouse Item", code, "description")
            if desc:
                payload["description"] = desc

        doc.append("items", payload)
        existing_items.add(code)
        added += 1

    if int(do_update or 0):
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    msg = _("Fetched {0} item(s).").format(int(added))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True,
        "message": msg,
        "added": added,
        "total_requested": len(candidates),
        "warnings": warnings,
    }

# apps/logistics/logistics/warehousing/doctype/stocktake_order/stocktake_order.py
# Copyright (c) 2025, www.agilasoft.com
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate


class StocktakeOrder(Document):
    pass


@frappe.whitelist()
def make_warehouse_job(source_name: str, target_doc=None):
    """
    Create a Warehouse Job (Stocktake) from a submitted Stocktake Order.
    Guard rails:
      - Allowed only when Stocktake Order is SUBMITTED (docstatus = 1)
    Mapping:
      - Header → Warehouse Job (type=Stocktake, company/branch/date)
      - Items  → Warehouse Job Order Items (no quantity)
      - Charges→ Warehouse Job Charges
      - Reference fields for traceability
    """
    source = frappe.get_doc("Stocktake Order", source_name)
    if int(source.docstatus or 0) != 1:
        frappe.throw("Create Warehouse Job is allowed only after submitting the Stocktake Order.")

    def set_missing_values(src, target):
        # Header defaults
        target.type = "Stocktake"
        target.job_open_date = getattr(src, "date", None) or nowdate()
        target.company = getattr(src, "company", None)
        target.branch = getattr(src, "branch", None)
        target.customer = src.customer
        target.warehouse_contract = src.contract

        # Traceability
        target.reference_order_type = "Stocktake Order"
        target.reference_order = src.name

        # Helpful context (optional)
        blips = []
        if getattr(src, "type", None):
            blips.append(f"Stocktake Type: {src.type}")
        if getattr(src, "blind_count", None) is not None:
            blips.append(f"Blind Count: {'Yes' if int(src.blind_count or 0) else 'No'}")
        if getattr(src, "qa_required", None) is not None:
            blips.append(f"QA Required: {'Yes' if int(src.qa_required or 0) else 'No'}")
        if getattr(src, "planned_date", None):
            blips.append(f"Planned: {src.planned_date}")
        if getattr(src, "customer", None):
            blips.append(f"Customer: {src.customer}")
        if blips:
            note = " / ".join(blips)
            target.notes = (target.notes + "\n" if getattr(target, "notes", "") else "") + note

    def update_order(src_row, tgt_row, src_parent):
        # Item basics
        tgt_row.item = getattr(src_row, "item", None)
        if hasattr(tgt_row, "item_name"):
            setattr(tgt_row, "item_name", getattr(src_row, "description", None))
        if hasattr(tgt_row, "description"):
            setattr(tgt_row, "description", getattr(src_row, "description", None))
        tgt_row.uom = getattr(src_row, "uom", None)

        # Handling/packing
        if hasattr(tgt_row, "handling_unit_type"):
            tgt_row.handling_unit_type = getattr(src_row, "handling_unit_type", None)
        tgt_row.handling_unit = getattr(src_row, "handling_unit", None)

        # Tracking flags / ids when supported
        for fld in ("sku_tracking", "serial_tracking", "batch_tracking"):
            if hasattr(src_row, fld) and hasattr(tgt_row, fld):
                setattr(tgt_row, fld, getattr(src_row, fld))
        for f_src, f_dst in (("serial_no", "serial_no"), ("batch_no", "batch_no")):
            if hasattr(src_row, f_src) and hasattr(tgt_row, f_dst):
                setattr(tgt_row, f_dst, getattr(src_row, f_src))
        # NOTE: No quantity on stocktake orders

    def update_charge(src_row, tgt_row, src_parent):
        if hasattr(tgt_row, "item_code"):
            tgt_row.item_code = getattr(src_row, "item_code", None) or getattr(src_row, "charge_item", None)
        for fld in ("uom", "quantity", "currency", "rate", "total"):
            if hasattr(tgt_row, fld) and hasattr(src_row, fld):
                setattr(tgt_row, fld, getattr(src_row, fld))

    doc = get_mapped_doc(
        "Stocktake Order",
        source_name,
        {
            "Stocktake Order": {
                "doctype": "Warehouse Job",
                "field_map": {
                    "name": "reference_order",
                },
                "field_no_map": [
                    "naming_series"
                ]
            },
            "Stocktake Order Item": {
                "doctype": "Warehouse Job Order Items",
                "postprocess": update_order,
            },
            "Stocktake Order Charges": {
                "doctype": "Warehouse Job Charges",
                "postprocess": update_charge,
            },
        },
        target_doc,
        set_missing_values,
    )
    
    # Save the job before returning
    doc.save()
    frappe.db.commit()
    
    return doc
