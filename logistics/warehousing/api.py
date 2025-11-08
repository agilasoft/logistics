# Copyright (c) 2025, www.agilasoft.com
from __future__ import annotations

from datetime import timedelta, date
# For license information, please see license.txt


from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import date, timedelta

import frappe

def _get_default_company_safe() -> Optional[str]:
    """Return a default Company using a version-safe fallback chain."""
    # Try frappe.db.get_default (available on v15)
    try:
        val = frappe.db.get_default("company")
        if val:
            return val
    except Exception as e:
        frappe.logger().debug(f"Failed to get company from frappe.db.get_default: {str(e)}")
    
    # Try frappe.defaults.get_user_default (older patterns)
    try:
        val = frappe.defaults.get_user_default("company")
        if val:
            return val
    except Exception as e:
        frappe.logger().debug(f"Failed to get company from frappe.defaults.get_user_default: {str(e)}")
    
    # Try Global Defaults doctype
    try:
        return frappe.db.get_value("Global Defaults", "Global Defaults", "default_company")
    except Exception as e:
        frappe.logger().debug(f"Failed to get company from Global Defaults: {str(e)}")
        return None
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

# Import functions from api_parts modules
from .api_parts.common import _select_dest_for_hu, _filter_locations_by_level, _get_allocation_level_limit, _get_allow_emergency_fallback, _fetch_job_order_items, _hu_consolidation_violations, _get_job_scope, _safe_meta_fieldnames, _get_item_storage_type_prefs, _get_replenish_policy_flags, _sl_fields, _match_upto_limit, _ensure_batch, _get_item_uom, _find_child_table_field, _wjo_fields, _ops_time_fields, get_warehouse_job_overview
from .api_parts.putaway import _putaway_candidate_locations, allocate_putaway, post_putaway, allocate_vas_putaway
from .api_parts.pick import allocate_pick, post_pick, initiate_vas_pick
from .api_parts.ops import populate_job_operations, create_sales_invoice_from_job, update_job_operations_times
from .api_parts.transfer import allocate_move

# =============================================================================
# Meta helpers
# =============================================================================

def _safe_meta_fieldnames(doctype: str) -> set:
    """Return set of fieldnames for a DocType using version-stable APIs."""
    meta = frappe.get_meta(doctype)
    fieldnames = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None) or (df.get("fieldname") if isinstance(df, dict) else None)
        if fn:
            fieldnames.add(fn)
    return fieldnames


# _find_child_table_field moved to api_parts/common.py


def _hu_location_fields() -> List[str]:
    """Return plausible location fieldnames present on Handling Unit."""
    hf = _safe_meta_fieldnames("Handling Unit")
    return [fn for fn in ("location", "storage_location") if fn in hf]


# =============================================================================
# Scope helpers (Company / Branch)
# =============================================================================

def _get_job_scope(job: Any) -> Tuple[Optional[str], Optional[str]]:
    """Extract Company/Branch from the Warehouse Job if present."""
    jf = _safe_meta_fieldnames("Warehouse Job")
    company = getattr(job, "company", None) if "company" in jf else None
    branch  = getattr(job, "branch", None)  if "branch"  in jf else None
    return (company or None, branch or None)


def _get_location_scope(location: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Fetch Company/Branch for a Storage Location (if such fields exist)."""
    if not location:
        return (None, None)
    lf = _safe_meta_fieldnames("Storage Location")
    fields = []
    if "company" in lf: fields.append("company")
    if "branch"  in lf: fields.append("branch")
    if not fields:
        return (None, None)
    row = frappe.db.get_value("Storage Location", location, fields, as_dict=True) or {}
    return (row.get("company"), row.get("branch"))


def _get_handling_unit_scope(hu_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Fetch Company/Branch for a Handling Unit (if such fields exist)."""
    if not hu_name:
        return (None, None)
    hf = _safe_meta_fieldnames("Handling Unit")
    fields = []
    if "company" in hf: fields.append("company")
    if "branch"  in hf: fields.append("branch")
    if not fields:
        return (None, None)
    row = frappe.db.get_value("Handling Unit", hu_name, fields, as_dict=True) or {}
    return (row.get("company"), row.get("branch"))


def _same_scope(job_company: Optional[str], job_branch: Optional[str],
                entity_company: Optional[str], entity_branch: Optional[str]) -> bool:
    """ True iff entity matches job scope for any specified scope dimension.
    - If job_company is set, entity_company must match (or be None when the entity lacks the field).
    - If job_branch is set, entity_branch must match (or be None when the entity lacks the field).
    """
    if job_company and (entity_company not in (None, job_company)):
        return False
    if job_branch and (entity_branch not in (None, job_branch)):
        return False
    return True

# =============================================================================
# SCAN-DRIVEN POSTING: location/HU barcode support + partial posting
# =============================================================================

# --- barcode resolution ------------------------------------------------------

def _barcode_fields(doctype: str) -> List[str]:
    """Return plausible barcode-like fields present on a DocType."""
    f = _safe_meta_fieldnames(doctype)
    order = ["barcode", "qr_code", "code"]
    return [x for x in order if x in f]

def _resolve_by_barcode(doctype: str, scanned: str) -> Optional[str]:
    """Try to resolve a scanned string to a doc name by (1) exact name, (2) barcode-like fields."""
    if not scanned:
        return None
    # 1) direct name match
    if frappe.db.exists(doctype, scanned):
        return scanned
    # 2) barcode-like fields
    for bf in _barcode_fields(doctype):
        name = frappe.db.get_value(doctype, {bf: scanned}, "name")
        if name:
            return name
    return None

def _resolve_scanned_location(scanned: Optional[str]) -> Optional[str]:
    return _resolve_by_barcode("Storage Location", (scanned or "").strip()) if scanned else None

def _resolve_scanned_hu(scanned: Optional[str]) -> Optional[str]:
    return _resolve_by_barcode("Handling Unit", (scanned or "").strip()) if scanned else None

# --- row helpers -------------------------------------------------------------

def _dest_loc_fieldname_for_putaway() -> str:
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    return "to_location" if "to_location" in jf else "location"

def _row_destination_location(it) -> Optional[str]:
    fld = _dest_loc_fieldname_for_putaway()
    return getattr(it, fld, None)

def _action_key(action: str) -> str:
    """Map to the posting flag key already used in your file."""
    a = (action or "").strip().lower()
    if a in ("pick", "picking"):
        return "pick"
    if a in ("putaway", "put-away", "put"):
        return "putaway"
    if a in ("release", "ship", "stage_out", "unstage"):
        # Reuse 'staging' key when that flag exists, else 'release'
        return "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "release"
    if a in ("receiving", "receive", "stage_in", "inbound"):
        return "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "receiving"
    return a

def _row_already_posted_for_action(it, action_key: str) -> bool:
    # Reuse your existing flag logic
    return _row_is_already_posted(it, action_key)

def _split_job_item_for_partial(job, it, qty_to_post: float):
    """Split a child row so we can post a partial while keeping the remainder unposted."""
    qty_to_post = abs(flt(qty_to_post or 0))
    whole = abs(flt(getattr(it, "quantity", 0)))
    if qty_to_post <= 0 or qty_to_post >= whole:
        return it  # nothing to split or full row; post as-is

    jf = _safe_meta_fieldnames("Warehouse Job Item")

    # Decrease original
    setattr(it, "quantity", flt(whole - qty_to_post))

    # Build new row payload
    payload: Dict[str, Any] = {
        "item": getattr(it, "item", None),
        "quantity": qty_to_post,
        "serial_no": getattr(it, "serial_no", None) or None,
        "batch_no": getattr(it, "batch_no", None) or None,
        "handling_unit": getattr(it, "handling_unit", None) or None,
    }
    if "uom" in jf: payload["uom"] = getattr(it, "uom", None) or None

    # preserve locations (source / destination)
    if "location" in jf and getattr(it, "location", None):
        payload["location"] = getattr(it, "location")
    dest_f = _dest_loc_fieldname_for_putaway()
    if dest_f in jf and getattr(it, dest_f, None):
        payload[dest_f] = getattr(it, dest_f)

    # preserve staging_area/source_row/source_parent if present
    for f in ("staging_area", "source_row", "source_parent"):
        if f in jf and getattr(it, f, None):
            payload[f] = getattr(it, f)

    newrow = job.append("items", payload)
    return newrow

def _iter_candidate_rows(job, action_key: str, loc: Optional[str], hu: Optional[str], item: Optional[str]) -> List[Any]:
    """
    Filter job.items to rows that match a scanned Location / HU / Item and are not yet posted for the action.
    - pick:   match row.location == loc (if given) and row.handling_unit == hu (if given)
    - putaway: match row.dest == loc (if given) and row.handling_unit == hu (if given)
    - receiving: match row.handling_unit == hu and item (if given)
    - release:   match row.handling_unit == hu and item (if given)
    """
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    is_pick = (action_key == "pick")
    is_put  = (action_key == "putaway")
    is_recv = (action_key in ("staging", "receiving"))  # stage-in
    is_rel  = (action_key in ("staging", "release")) and not is_recv  # stage-out

    out: List[Any] = []
    for it in (job.items or []):
        if _row_already_posted_for_action(it, action_key):
            continue

        # HU filter
        if hu and (getattr(it, "handling_unit", None) or None) != hu:
            continue

        # Item filter (optional)
        if item and (getattr(it, "item", None) or None) != item:
            continue

        if is_pick:
            src = getattr(it, "location", None)
            if loc and src != loc:
                continue
        elif is_put:
            dest = _row_destination_location(it)
            if loc and dest != loc:
                continue
        elif is_recv:
            # No location on row; we stage into job.staging_area. HU or item is the filter.
            pass
        elif is_rel:
            # Releasing from staging by HU or item
            pass

        out.append(it)

    # Keep user order (idx asc)
    out.sort(key=lambda r: getattr(r, "idx", 999999))
    return out

# =============================================================================
# STATUS HELPERS
# =============================================================================

def _sl_fields():
    return _safe_meta_fieldnames("Storage Location")

def _hu_fields():
    return _safe_meta_fieldnames("Handling Unit")

def _get_sl(name: Optional[str]):
    return frappe.get_doc("Storage Location", name) if name and frappe.db.exists("Storage Location", name) else None

def _get_hu(name: Optional[str]):
    return frappe.get_doc("Handling Unit", name) if name and frappe.db.exists("Handling Unit", name) else None

def _sl_balance(loc: Optional[str]) -> float:
    if not loc: return 0.0
    r = frappe.db.sql("SELECT COALESCE(SUM(quantity),0) FROM `tabWarehouse Stock Ledger` WHERE storage_location=%s", (loc,))
    return float(r[0][0] if r else 0.0)

def _hu_balance(hu: Optional[str]) -> float:
    if not hu: return 0.0
    r = frappe.db.sql("SELECT COALESCE(SUM(quantity),0) FROM `tabWarehouse Stock Ledger` WHERE handling_unit=%s", (hu,))
    return float(r[0][0] if r else 0.0)

def _validate_status_for_action(*, action: str, location: Optional[str], handling_unit: Optional[str]):
    """Block movements using Under Maintenance / Inactive entities."""
    slf, huf = _sl_fields(), _hu_fields()
    if handling_unit and ("status" in huf):
        hu = _get_hu(handling_unit)
        if hu and (hu.status in ("Under Maintenance", "Inactive")):
            frappe.throw(_("Handling Unit {0} status is {1}. Not allowed for {2}.")
                         .format(handling_unit, hu.status, action))
    if location and ("status" in slf):
        sl = _get_sl(location)
        if sl and (sl.status in ("Under Maintenance", "Inactive")):
            frappe.throw(_("Location {0} status is {1}. Not allowed for {2}.")
                         .format(location, sl.status, action))

def _set_sl_status_by_balance(loc: Optional[str]) -> None:
    if not loc: return
    slf = _sl_fields()
    if "status" not in slf: return
    sl = _get_sl(loc)
    if not sl: return
    cur = getattr(sl, "status", "Available")
    if cur in ("Under Maintenance", "Inactive"):
        return  # never auto-flip these
    desired = "In Use" if _sl_balance(loc) > 0 else "Available"
    if cur != desired:
        sl.db_set("status", desired, commit=False)

def _set_hu_status_by_balance(hu: Optional[str], *, after_release: bool = False) -> None:
    if not hu: return
    huf = _hu_fields()
    if "status" not in huf: return
    doc = _get_hu(hu)
    if not doc: return
    bal = _hu_balance(hu)
    if bal > 0:
        desired = "In Use"
    else:
        mark_inactive = bool(getattr(doc, "mark_inactive_on_release", 0)) if "mark_inactive_on_release" in huf else False
        desired = ("Inactive" if (after_release and mark_inactive) else "Available")
    if getattr(doc, "status", None) != desired:
        doc.db_set("status", desired, commit=False)

# =============================================================================
# Scope assertions (Company / Branch)
# =============================================================================

def _assert_location_in_job_scope(location: Optional[str], job_company: Optional[str],
                                  job_branch: Optional[str], ctx: str = "Location"):
    if not location:
        return
    lc, lb = _get_location_scope(location)
    if not _same_scope(job_company, job_branch, lc, lb):
        frappe.throw(_("{0} {1} is out of scope for Company/Branch on this Job.").format(ctx, location))


def _assert_hu_in_job_scope(hu: Optional[str], job_company: Optional[str],
                            job_branch: Optional[str], ctx: str = "Handling Unit"):
    if not hu:
        return
    hc, hb = _get_handling_unit_scope(hu)
    if not _same_scope(job_company, job_branch, hc, hb):
        frappe.throw(_("{0} {1} is out of scope for Company/Branch on this Job.").format(ctx, hu))


# =============================================================================
# Warehouse Settings → Allocation Level Limit
# =============================================================================

_LEVEL_ORDER = ["site", "building", "zone", "aisle", "bay", "level"]
_LEVEL_LABEL_TO_FIELD = {
    "Site": "site", "Building": "building", "Zone": "zone",
    "Aisle": "aisle", "Bay": "bay", "Level": "level",
}

def _get_allocation_level_limit() -> Optional[str]:
    """Return the label (e.g., 'Aisle') set in Warehouse Settings, else None."""
    try:
        val = frappe.db.get_single_value("Warehouse Settings", "allocation_level_limit")
        val = (val or "").strip()
        return val or None
    except Exception as e:
        frappe.logger().debug(f"Failed to get allocation_level_limit from Warehouse Settings: {str(e)}")
        return None

def _existing_level_fields() -> List[str]:
    slf = _safe_meta_fieldnames("Storage Location")
    return [f for f in _LEVEL_ORDER if f in slf]

def _level_path_for_location(location: Optional[str]) -> Dict[str, Optional[str]]:
    """Return {field: value} for hierarchical level fields that exist."""
    out: Dict[str, Optional[str]] = {}
    if not location:
        return out
    fields = _existing_level_fields()
    if not fields:
        return out
    row = frappe.db.get_value("Storage Location", location, fields, as_dict=True) or {}
    for f in fields:
        out[f] = (row.get(f) or None)
    return out

def _match_upto_limit(staging_loc: Optional[str], candidate_loc: Optional[str], limit_label: Optional[str]) -> bool:
    """True if candidate matches staging path up to the configured limit (if any)."""
    if not (staging_loc and candidate_loc and limit_label):
        return True  # no restriction
    limit_field = _LEVEL_LABEL_TO_FIELD.get(limit_label)
    if not limit_field:
        return True
    fields = _existing_level_fields()
    if not fields or limit_field not in fields:
        return True

    s_path = _level_path_for_location(staging_loc)
    c_path = _level_path_for_location(candidate_loc)

    # compare from top until we reach the limit_field (inclusive)
    for f in fields:
        if s_path.get(f) and c_path.get(f):
            if s_path[f] != c_path[f]:
                return False
        # stop when we hit the configured limit level
        if f == limit_field:
            break
    return True


# =============================================================================
# Contract charge util
# =============================================================================

CTX_FLAG = {
    "inbound":   "inbound_charge",
    "outbound":  "outbound_charge",
    "transfer":  "transfer_charge",
    "vas":       "vas_charge",
    "storage":   "storage_charge",
    "stocktake": "stocktake_charge",
}

@frappe.whitelist()
def get_contract_charge(contract: str, item_code: str, context: str):
    """Return first matching Warehouse Contract Item row for contract+item+context."""
    if not contract or not item_code:
        return {}
    ctx = (context or "").strip().lower()
    base = {"parent": contract, "parenttype": "Warehouse Contract", "item_charge": item_code}
    filters = dict(base)
    flag = CTX_FLAG.get(ctx)
    if flag:
        filters[flag] = 1
    fields = ["rate", "currency", "uom"]
    rows = frappe.get_all("Warehouse Contract Item", filters=filters, fields=fields, limit=1, ignore_permissions=True)
    if not rows and flag:
        rows = frappe.get_all("Warehouse Contract Item", filters=base, fields=fields, limit=1, ignore_permissions=True)
    return rows[0] if rows else {}


# =============================================================================
# Serial / Batch helpers
# =============================================================================

def _first_token(text: Optional[str]) -> str:
    if not text:
        return ""
    for sep in (",", "\n", "\r"):
        text = text.replace(sep, " ")
    return " ".join([t for t in text.split(" ") if t]).strip()


def _get_item_uom(item: Optional[str]) -> Optional[str]:
    if not item:
        return None
    return frappe.db.get_value("Warehouse Item", item, "uom")


def _ensure_serial(serial_code: Optional[str], item: Optional[str] = None, customer: Optional[str] = None) -> str:
    if not serial_code:
        return ""
    if frappe.db.exists("Warehouse Serial", serial_code):
        return serial_code
    doc = frappe.new_doc("Warehouse Serial")
    doc.serial_no = serial_code  # autoname=field:serial_no
    if hasattr(doc, "item_code") and item:
        doc.item_code = item
    if hasattr(doc, "customer") and customer:
        doc.customer = customer
    doc.insert()
    return doc.name


# Function moved to api_parts/common.py


# =============================================================================
# Create Serials/Batches for INBOUND ORDER
# =============================================================================

@frappe.whitelist()
def create_serial_and_batch_for_inbound(inbound_order: str):
    if not inbound_order:
        frappe.throw(_("Inbound Order is required"))
    customer = None
    try:
        parent = frappe.get_doc("Inbound Order", inbound_order)
        customer = getattr(parent, "customer", None)
    except Exception as e:
        frappe.logger().debug(f"Failed to get customer from Inbound Order {inbound_order}: {str(e)}")

    rows = frappe.get_all(
        "Inbound Order Item",
        filters={"parent": inbound_order, "parenttype": "Inbound Order"},
        fields=[
            "name", "item", "uom",
            "serial_tracking", "serial_no", "serial_no_text",
            "batch_tracking", "batch_no", "batch_no_text", "batch_expiry",
        ],
        order_by="idx asc",
    )

    created_serial = linked_serial = 0
    created_batch  = linked_batch  = 0
    updated_batch_uom = 0
    skipped = 0
    errors: List[str] = []

    for r in rows:
        try:
            to_set: Dict[str, Any] = {}
            row_uom = r.uom or _get_item_uom(r.item)

            if int(r.serial_tracking or 0):
                existing = (r.serial_no or "").strip()
                code = _first_token(r.serial_no_text or "")
                if not existing:
                    if code:
                        if frappe.db.exists("Warehouse Serial", code):
                            to_set["serial_no"] = code; linked_serial += 1
                        else:
                            to_set["serial_no"] = _ensure_serial(code, r.item, customer); created_serial += 1
                    else:
                        skipped += 1

            if int(r.batch_tracking or 0):
                existing_b = (r.batch_no or "").strip()
                code_b = _first_token(r.batch_no_text or "")
                if not existing_b:
                    if code_b:
                        if frappe.db.exists("Warehouse Batch", code_b):
                            if row_uom:
                                current_uom = frappe.db.get_value("Warehouse Batch", code_b, "batch_uom")
                                if not current_uom:
                                    frappe.db.set_value("Warehouse Batch", code_b, "batch_uom", row_uom)
                                    updated_batch_uom += 1
                            to_set["batch_no"] = code_b; linked_batch += 1
                        else:
                            to_set["batch_no"] = _ensure_batch(code_b, r.item, customer, r.batch_expiry, row_uom)
                            created_batch += 1
                    else:
                        skipped += 1

            if to_set:
                frappe.db.set_value("Inbound Order Item", r.name, to_set)
        except Exception as e:
            errors.append(f"Row {r.name}: {e}")

    return {
        "created": {"serial": created_serial, "batch": created_batch},
        "linked":  {"serial": linked_serial,  "batch": linked_batch},
        "updated": {"batch_uom": updated_batch_uom},
        "skipped": skipped,
        "errors": errors,
    }


# =============================================================================
# Data access (orders) + item rules
# =============================================================================

def _fetch_job_order_items(job_name: str) -> List[Dict[str, Any]]:
    """Only request fields that are standard across scenarios."""
    return frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job_name, "parenttype": "Warehouse Job"},
        fields=["name", "parent", "item", "quantity", "uom", "serial_no", "batch_no", "handling_unit", "handling_unit_type",
                "length", "width", "height", "volume", "weight", "volume_uom", "weight_uom", "dimension_uom"],
        order_by="idx asc",
        ignore_permissions=True,
    ) or []


def _get_item_rules(item: str) -> Dict[str, Any]:
    # honor your Warehouse Item fields
    sql = """
        SELECT picking_method,
               IFNULL(single_lot_preference, 0)    AS single_lot_preference,
               IFNULL(full_unit_first, 0)          AS full_unit_first,
               IFNULL(nearest_location_first, 0)   AS nearest_location_first,
               IFNULL(primary_pick_face_first, 0)  AS primary_pick_face_first,
               IFNULL(quality_grade_priority, 0)   AS quality_grade_priority,
               IFNULL(storage_type_preference, 0)  AS storage_type_preference
        FROM `tabWarehouse Item`
        WHERE name = %s
    """
    row = frappe.db.sql(sql, (item,), as_dict=True)
    if not row:
        return {
            "picking_method": "FIFO",
            "single_lot_preference": 0,
            "full_unit_first": 0,
            "nearest_location_first": 1,
            "primary_pick_face_first": 0,
            "quality_grade_priority": 0,
            "storage_type_preference": 1,
        }
    return row[0]

def _get_item_consolidation_policy(item: str) -> Dict[str, int]:
    """Use Warehouse Item fields to drive consolidation/mix behavior.

    NOTE: Avoid SQL expressions (e.g., IFNULL(...)) in frappe.db.get_value(fields=[])
    on Frappe v15 due to a QB parse bug. Fetch raw fields and coerce in Python.
    """
    if not item:
        return {
            "lot_consolidation": 0,
            "allow_mix_with_other_customers": 0,
            "customer": None,
        }

    # Only request fields that exist (keeps this robust to custom schemas)
    wif = _safe_meta_fieldnames("Warehouse Item")
    want = [f for f in ("lot_consolidation", "allow_mix_with_other_customers", "customer") if f in wif]

    row = {}
    if want:
        # get_value with a list of PLAIN fieldnames (no SQL functions/aliases)
        row = frappe.db.get_value("Warehouse Item", item, want, as_dict=True) or {}

    lot = row.get("lot_consolidation")
    mix = row.get("allow_mix_with_other_customers")
    cust = row.get("customer")

    # Coerce to ints with safe defaults
    try:
        lot = int(lot) if lot is not None else 0
    except (ValueError, TypeError) as e:
        frappe.logger().debug(f"Failed to convert lot_consolidation to int: {str(e)}, using default 0")
        lot = 0

    try:
        mix = int(mix) if mix is not None else 0
    except (ValueError, TypeError) as e:
        frappe.logger().debug(f"Failed to convert allow_mix_with_other_customers to int: {str(e)}, using default 0")
        mix = 0

    return {
        "lot_consolidation": lot,
        "allow_mix_with_other_customers": mix,
        "customer": cust,
    }


# =============================================================================
# Availability query (scoped by Company/Branch) with status & HU filters
# =============================================================================

def _query_available_candidates(
    item: str,
    batch_no: Optional[str] = None,
    serial_no: Optional[str] = None,
    company: Optional[str] = None,
    branch: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Aggregate positive availability from Warehouse Stock Ledger, scoped by Company/Branch."""
    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    # status filters
    sl_status = "AND sl.status IN ('Available','In Use')" if ("status" in slf) else ""
    hu_block  = "AND COALESCE(hu.status,'Available') NOT IN ('Under Maintenance','Inactive')" if ("status" in huf) else ""

    conds = []
    params: List[Any] = [item, batch_no, batch_no, serial_no, serial_no]

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)):
        conds.append("COALESCE(hu.company, sl.company, l.company) = %s")
        params.append(company)
    if branch and (("branch" in slf) or ("branch" in huf) or ("branch" in llf)):
        conds.append("COALESCE(hu.branch, sl.branch, l.branch) = %s")
        params.append(branch)

    scope_sql = (" AND " + " AND ".join(conds)) if conds else ""

    sql = f"""
        SELECT
            l.storage_location,
            l.handling_unit,
            l.batch_no,
            l.serial_no,
            SUM(l.quantity) AS available_qty,
            MIN(l.posting_date) AS first_seen,
            MAX(l.posting_date) AS last_seen,
            b.expiry_date AS expiry_date,
            COALESCE(ws.quality_grade, b.quality_grade) AS quality_grade,
            IFNULL(sl.bin_priority, 999999) AS bin_priority,
            IFNULL(st.picking_rank, 999999) AS storage_type_rank
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabStorage Type`   st ON st.name = sl.storage_type
        LEFT JOIN `tabHandling Unit`  hu ON hu.name = l.handling_unit
        LEFT JOIN `tabWarehouse Batch`  b ON b.name = l.batch_no
        LEFT JOIN `tabWarehouse Serial` ws ON ws.name = l.serial_no
        WHERE l.item = %s
          AND (%s IS NULL OR l.batch_no = %s)
          AND (%s IS NULL OR l.serial_no = %s)
          {scope_sql}
          {sl_status}
          {hu_block}
        GROUP BY l.storage_location, l.handling_unit, l.batch_no, l.serial_no
        HAVING SUM(l.quantity) > 0
    """
    return frappe.db.sql(sql, tuple(params), as_dict=True) or []


# =============================================================================
# Ordering & Allocation utilities
# =============================================================================

def _order_candidates(
    candidates: List[Dict[str, Any]],
    rules: Dict[str, Any],
    required_qty: float,
) -> List[Dict[str, Any]]:
    method = (rules.get("picking_method") or "FIFO").upper()

    def base_order_key(c: Dict[str, Any]) -> Tuple:
        first_seen = c.get("first_seen")
        last_seen  = c.get("last_seen")
        expiry     = c.get("expiry_date")
        if method == "FEFO":  # earliest expiry first
            return ((0, expiry) if expiry else (1, now_datetime()),)
        if method == "LEFO":  # latest expiry first
            if expiry:
                return ((0, -get_datetime(expiry).timestamp()),)
            return ((1, -get_datetime("1900-01-01").timestamp()),)
        if method in ("LIFO", "FMFO"):
            ls = last_seen or get_datetime("1900-01-01")
            return ((-ls.timestamp()),)
        fs = first_seen or now_datetime()
        return ((fs.timestamp()),)

    def can_fill(c: Dict[str, Any]) -> int:
        return 1 if flt(c.get("available_qty")) >= required_qty else 0

    def hu_present(c: Dict[str, Any]) -> int:
        return 1 if c.get("handling_unit") else 0

    def full_key(c: Dict[str, Any]) -> Tuple:
        k = []
        k.extend(list(base_order_key(c)))
        if int(rules.get("single_lot_preference") or 0):
            k.append((-can_fill(c),))
        if int(rules.get("full_unit_first") or 0):
            k.append((-hu_present(c),))
        k.append((-can_fill(c),))
        if int(rules.get("nearest_location_first") or 0):
            k.append((int(c.get("bin_priority") or 999999),))
        if int(rules.get("storage_type_preference") or 0) or int(rules.get("primary_pick_face_first") or 0):
            k.append((int(c.get("storage_type_rank") or 999999),))
        if int(rules.get("quality_grade_priority") or 0):
            k.append((-(int(c.get("quality_grade") or 0)),))
        k.append((-flt(c.get("available_qty") or 0.0),))
        return tuple(k)

    return sorted(candidates, key=full_key)


def _greedy_allocate(
    candidates: List[Dict[str, Any]],
    required_qty: float,
    rules: Dict[str, Any],
    force_exact: bool = False,
) -> List[Dict[str, Any]]:
    remaining = flt(required_qty)
    out: List[Dict[str, Any]] = []
    for c in candidates:
        if remaining <= 0:
            break
        avail = max(0.0, flt(c.get("available_qty") or 0.0))
        if avail <= 0:
            continue
        take = min(avail, remaining)
        if take <= 0:
            continue
        out.append({
            "location": c.get("storage_location"),
            "handling_unit": c.get("handling_unit"),
            "batch_no": c.get("batch_no"),
            "serial_no": c.get("serial_no"),
            "qty": take,
        })
        remaining -= take
    return out


def _append_job_items(
    job: Any,
    source_parent: str,
    source_child: str,
    item: str,
    uom: Optional[str],
    allocations: List[Dict[str, Any]],
    order_data: Optional[Dict[str, Any]] = None,
) -> Tuple[int, float]:
    created_rows = 0
    created_qty = 0.0

    job_company, job_branch = _get_job_scope(job)
    job_item_fields = _safe_meta_fieldnames("Warehouse Job Item")
    has_uom_field    = "uom" in job_item_fields
    has_source_row   = "source_row" in job_item_fields
    has_source_parent= "source_parent" in job_item_fields

    for a in allocations:
        qty = flt(a.get("qty") or 0)
        if qty == 0:
            continue
        loc = a.get("location")
        hu  = a.get("handling_unit")

        _assert_location_in_job_scope(loc, job_company, job_branch)
        _assert_hu_in_job_scope(hu, job_company, job_branch)

        payload = {
            "location": loc,
            "handling_unit": hu,
            "item": item,
            "quantity": qty,
            "serial_no": a.get("serial_no"),
            "batch_no": a.get("batch_no"),
        }
        if has_uom_field and uom:
            payload["uom"] = uom
        if has_source_row:
            payload["source_row"] = source_child
        if has_source_parent:
            payload["source_parent"] = source_parent

        # Override with order-specific physical dimensions if available
        if order_data:
            if "length" in job_item_fields and order_data.get("length"):
                payload["length"] = flt(order_data.get("length"))
            if "width" in job_item_fields and order_data.get("width"):
                payload["width"] = flt(order_data.get("width"))
            if "height" in job_item_fields and order_data.get("height"):
                payload["height"] = flt(order_data.get("height"))
            if "volume" in job_item_fields and order_data.get("volume"):
                payload["volume"] = flt(order_data.get("volume"))
            if "weight" in job_item_fields and order_data.get("weight"):
                payload["weight"] = flt(order_data.get("weight"))
            if "volume_uom" in job_item_fields and order_data.get("volume_uom"):
                payload["volume_uom"] = order_data.get("volume_uom")
            if "weight_uom" in job_item_fields and order_data.get("weight_uom"):
                payload["weight_uom"] = order_data.get("weight_uom")
            if "dimension_uom" in job_item_fields and order_data.get("dimension_uom"):
                payload["dimension_uom"] = order_data.get("dimension_uom")

        job.append("items", payload)
        created_rows += 1
        created_qty  += qty

    return created_rows, created_qty


# =============================================================================
# Putaway candidate locations (policy) — exclude staging locations & status
# =============================================================================


# Functions moved to api_parts/common.py
# ALLOWED/PREFERRED storage-type filter + pick_face preference applied below
# Function moved to api_parts/putaway.py


# Function moved to api_parts/common.py


# Function moved to api_parts/pick.py








    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Allocated {0} units across {1} pick rows.").format(flt(total_created_qty), int(total_created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True, "message": msg,
        "created_rows": total_created_rows, "created_qty": total_created_qty,
        "lines": details, "warnings": warnings,
    }


# =============================================================================
# HU-anchored PUTAWAY from orders
# - one HU = one destination location (across all its rows)
# - different HUs must NOT share destination location in the same allocation
# - respects Allocation Level Limit vs staging
# - alerts when HU mixes items not allowed to consolidate per Warehouse Item
# =============================================================================

def _hu_consolidation_violations(hu: str, items_in_hu: Set[str]) -> List[str]:
    """Return messages if HU has items that shouldn't be consolidated together."""
    msgs: List[str] = []
    if len(items_in_hu) <= 1:
        return msgs
    # If any item has lot_consolidation == 0 → don't mix different items in a single HU
    blocking: List[str] = []
    for it in items_in_hu:
        pol = _get_item_consolidation_policy(it)
        if int(pol.get("lot_consolidation") or 0) == 0:
            blocking.append(it)
    if blocking:
        msgs.append(_("HU {0}: contains multiple items but these items disallow consolidation: {1}")
                    .format(hu, ", ".join(sorted(blocking))))
    # Mixing customers (from Warehouse Item.customer) inside same HU, when any item disallows mix-with-other-customers
    customers = set()
    items_by_customer: Dict[str, List[str]] = {}
    disallow_mix = False
    for it in items_in_hu:
        pol = _get_item_consolidation_policy(it)
        cust = pol.get("customer") or ""
        customers.add(cust)
        items_by_customer.setdefault(cust, []).append(it)
        if int(pol.get("allow_mix_with_other_customers") or 0) == 0:
            disallow_mix = True
    if disallow_mix and len(customers) > 1:
        parts = [f"{k or 'N/A'}: {', '.join(v)}" for k, v in items_by_customer.items()]
        msgs.append(_("HU {0}: mixes items from different customers while mixing is disallowed → {1}").format(hu, " | ".join(parts)))
    return msgs


# Function moved to api_parts/common.py


def _hu_anchored_putaway_from_orders(job: Any) -> Tuple[int, float, List[Dict[str, Any]], List[str]]:
    """Impose HU → single destination; unique location per HU; warnings for violations."""
    company, branch = _get_job_scope(job)
    
    # Inform user about the allocation process
    frappe.msgprint(f"Starting putaway allocation for job {job.name}")
    frappe.msgprint(f"Job scope: Company={company or 'Any'}, Branch={branch or 'Any'}")
    
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    dest_loc_field = "location" if "location" in jf else ("to_location" if "to_location" in jf else None)

    orders = _fetch_job_order_items(job.name)
    
    # No need to show processing steps
    
    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not orders:
        frappe.msgprint("No order items found to process")
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

    # No need to show grouping steps

    if rows_without_hu:
        warning_msg = _("Some order rows have no Handling Unit; operator must supply HU for putaway.")
        warnings.append(warning_msg)
        frappe.msgprint(f"⚠️ WARNING: {warning_msg}")

    used_locations: Set[str] = set()  # ensure different HUs don't share the same destination

    for hu, rows in by_hu.items():
        
        # Inform user about HU processing
        frappe.msgprint(f"Processing handling unit {hu} with {len(rows)} items")
        
        # pick a representative item (first row) to get a good destination; then apply to all rows for this HU
        rep_item = None
        for rr in rows:
            if rr.get("item"):
                rep_item = rr["item"]; break
        if not rep_item:
            frappe.msgprint(f"Warning: HU {hu} has no valid items, skipping")
            warnings.append(_("HU {0}: has rows without item; skipped.").format(hu))
            continue

        # choose destination for this HU (must be unique and match level limit)

        dest = _select_dest_for_hu(
            item=rep_item, company=company, branch=branch,
            staging_area=staging_area, level_limit_label=level_limit_label,
            used_locations=used_locations, exclude_locations=exclude
        )

        
        # No need to show individual destination results
        
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
            warning_msg = _("HU {0}: no destination location available in scope.").format(hu)
            warnings.append(warning_msg)
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

    # Show only essential final results
    if warnings:
        failed_hus = [w for w in warnings if "HU" in w and "no destination" in w]
        frappe.msgprint(f"✅ Completed: {created_rows} rows, {created_qty} units")
        frappe.msgprint(f"⚠️ {len(failed_hus)} handling units failed allocation")
    else:
        frappe.msgprint(f"✅ Completed: {created_rows} rows, {created_qty} units")

    return created_rows, created_qty, details, warnings


# =============================================================================
# Allocate PUTAWAY from orders (policy + scoped, staging excluded) — HU anchored
# =============================================================================



# =============================================================================
# MOVE allocation from orders (scoped validations)
# =============================================================================

@frappe.whitelist()
def allocate_move(warehouse_job: str, clear_existing: int = 1):
    """Populate Items with paired move rows based on Orders; validates scope."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Move":
        frappe.throw(_("Warehouse Job must be of type 'Move' to allocate moves from Orders."))

    company, branch = _get_job_scope(job)
    if int(clear_existing or 0):
        job.set("items", [])

    created_pairs = 0
    skipped: List[str] = []

    for r in (job.orders or []):
        qty = abs(flt(getattr(r, "quantity", 0)))
        from_loc = getattr(r, "storage_location_from", None)
        to_loc   = getattr(r, "storage_location_to", None)
        hu_from  = getattr(r, "handling_unit_from", None)
        hu_to    = getattr(r, "handling_unit_to", None)

        if not from_loc or not to_loc:
            skipped.append(f"Row {getattr(r, 'idx', '?')}: missing From/To location"); continue
        if qty <= 0:
            skipped.append(f"Row {getattr(r, 'idx', '?')}: quantity must be > 0"); continue

        _assert_location_in_job_scope(from_loc, company, branch, ctx=_("From Location"))
        _assert_location_in_job_scope(to_loc, company, branch,   ctx=_("To Location"))
        _assert_hu_in_job_scope(hu_from, company, branch, ctx=_("From HU"))
        _assert_hu_in_job_scope(hu_to,   company, branch, ctx=_("To HU"))

        common = {
            "item": getattr(r, "item", None),
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        job.append("items", {**common, "location": from_loc, "handling_unit": hu_from or None, "quantity": -qty})
        job.append("items", {**common, "location": to_loc,   "handling_unit": hu_to   or None, "quantity":  qty})
        created_pairs += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": _("Allocated {0} move pair(s).").format(created_pairs), "created_pairs": created_pairs, "skipped": skipped}


# =============================================================================
# VAS actions (scoped)
# =============================================================================

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
            fields=["name", "item", "quantity", "uom"],
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


# =============================================================================
# STOCKTAKE: Fetch Count Sheet
# =============================================================================

@frappe.whitelist()
def warehouse_job_fetch_count_sheet(warehouse_job: str, clear_existing: int = 1):
    """Build Count Sheet for items present in Orders; respects Job scope."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("Fetch Count Sheet is only available for Warehouse Job Type = Stocktake."))

    order_items = frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job.name, "parenttype": "Warehouse Job"},
        fields=["distinct item AS item"],
        ignore_permissions=True,
    )
    item_list = [r["item"] for r in order_items if (r.get("item") or "").strip()]
    item_set  = set(item_list)
    if not item_set:
        return {"ok": True, "message": _("No items found in Orders. Add items in the Orders table first."), "created_rows": 0}

    company, branch = _get_job_scope(job)

    if int(clear_existing or 0):
        # Delete existing count rows from database first
        frappe.db.delete("Warehouse Job Count", {"parent": job.name, "parenttype": "Warehouse Job"})
        frappe.db.commit()
        # Clear counts from the document
        job.set("counts", [])
        # Reload the job to ensure counts are cleared
        job.reload()

    # optional sync from Stocktake Order header
    if (job.reference_order_type or "").strip() == "Stocktake Order" and getattr(job, "reference_order", None):
        so_meta = _safe_meta_fieldnames("Stocktake Order")
        desired = ["count_type", "blind_count", "qa_required", "stocktake_days_past_zero"]
        fields_to_fetch = [f for f in desired if f in so_meta]
        if fields_to_fetch:
            so = frappe.db.get_value("Stocktake Order", job.reference_order, fields_to_fetch, as_dict=True) or {}
            for k in fields_to_fetch:
                v = so.get(k)
                if v not in (None, "") and not getattr(job, k, None):
                    setattr(job, k, v)

    # Set count_date if not already set (count_date is not in Stocktake Order, so set it when fetching count sheet)
    if not getattr(job, "count_date", None):
        job.count_date = now_datetime()

    # Get stocktake_days_past_zero from Warehouse Job first, then fall back to Warehouse Settings
    stocktake_days_past_zero = 0
    # First try to get from the job
    if hasattr(job, "stocktake_days_past_zero") and getattr(job, "stocktake_days_past_zero", None) is not None:
        stocktake_days_past_zero = int(getattr(job, "stocktake_days_past_zero") or 0)
    # If not set in job, fall back to Warehouse Settings
    if stocktake_days_past_zero == 0 and company:
        try:
            stocktake_days_past_zero = int(frappe.db.get_value("Warehouse Settings", company, "stocktake_days_past_zero") or 0)
        except:
            stocktake_days_past_zero = 0

    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    conds = ["l1.item IN ({})".format(", ".join(["%s"] * len(item_set)))]
    params: List[Any] = list(item_set)

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)) :
        conds.append("COALESCE(hu1.company, sl1.company, l1.company) = %s"); params.append(company)
    if branch and  (("branch"  in slf) or ("branch"  in huf) or ("branch"  in llf)):
        conds.append("COALESCE(hu1.branch,  sl1.branch,  l1.branch)  = %s"); params.append(branch)

    # Get current stock using end_qty from the last entry for each item/location/handling_unit/batch/serial combination
    # Also include items with zero stock if their last transaction is within stocktake_days_past_zero days
    having_clause = "system_qty > 0"
    if stocktake_days_past_zero > 0:
        # Include zero stock items if last transaction is within the specified days
        having_clause = f"system_qty > 0 OR (system_qty = 0 AND last_posting_date >= DATE_SUB(CURDATE(), INTERVAL {stocktake_days_past_zero} DAY))"
    
    aggregates = frappe.db.sql("""
        SELECT DISTINCT
               l1.item, 
               l1.storage_location, 
               l1.handling_unit, 
               l1.batch_no, 
               l1.serial_no,
               (SELECT l2.end_qty 
                FROM `tabWarehouse Stock Ledger` l2
                LEFT JOIN `tabStorage Location` sl2 ON sl2.name = l2.storage_location
                LEFT JOIN `tabHandling Unit` hu2 ON hu2.name = l2.handling_unit
                WHERE l2.item = l1.item 
                  AND l2.storage_location = l1.storage_location
                  AND IFNULL(l2.handling_unit, '') = IFNULL(l1.handling_unit, '')
                  AND IFNULL(l2.batch_no, '') = IFNULL(l1.batch_no, '')
                  AND IFNULL(l2.serial_no, '') = IFNULL(l1.serial_no, '')
                  AND COALESCE(hu2.company, sl2.company, l2.company) = COALESCE(hu1.company, sl1.company, l1.company)
                  AND COALESCE(hu2.branch, sl2.branch, l2.branch) = COALESCE(hu1.branch, sl1.branch, l1.branch)
                ORDER BY l2.posting_date DESC, l2.creation DESC
                LIMIT 1) AS system_qty,
               (SELECT l2.posting_date 
                FROM `tabWarehouse Stock Ledger` l2
                LEFT JOIN `tabStorage Location` sl2 ON sl2.name = l2.storage_location
                LEFT JOIN `tabHandling Unit` hu2 ON hu2.name = l2.handling_unit
                WHERE l2.item = l1.item 
                  AND l2.storage_location = l1.storage_location
                  AND IFNULL(l2.handling_unit, '') = IFNULL(l1.handling_unit, '')
                  AND IFNULL(l2.batch_no, '') = IFNULL(l1.batch_no, '')
                  AND IFNULL(l2.serial_no, '') = IFNULL(l1.serial_no, '')
                  AND COALESCE(hu2.company, sl2.company, l2.company) = COALESCE(hu1.company, sl1.company, l1.company)
                  AND COALESCE(hu2.branch, sl2.branch, l2.branch) = COALESCE(hu1.branch, sl1.branch, l1.branch)
                ORDER BY l2.posting_date DESC, l2.creation DESC
                LIMIT 1) AS last_posting_date
        FROM `tabWarehouse Stock Ledger` l1
        LEFT JOIN `tabStorage Location` sl1 ON sl1.name = l1.storage_location
        LEFT JOIN `tabHandling Unit` hu1 ON hu1.name = l1.handling_unit
        WHERE """ + ' AND '.join(conds) + """
        HAVING """ + having_clause, tuple(params), as_dict=True) or []

    # zero-stock placeholders
    loc_params, loc_conds = [], []
    if company and ("company" in slf): loc_conds.append("sl.company = %s"); loc_params.append(company)
    if branch  and ("branch"  in slf): loc_conds.append("sl.branch  = %s"); loc_params.append(branch)
    loc_where = ("WHERE " + " AND ".join(loc_conds)) if loc_conds else ""
    locations = frappe.db.sql(f"SELECT sl.name AS name FROM `tabStorage Location` sl {loc_where}",
                              tuple(loc_params), as_dict=True) or []

    hu_params, hu_conds = [], []
    if company and ("company" in huf): hu_conds.append("hu.company = %s"); hu_params.append(company)
    if branch  and ("branch"  in huf): hu_conds.append("hu.branch  = %s");  hu_params.append(branch)
    hu_where = ("WHERE " + " AND ".join(hu_conds)) if hu_conds else ""
    hus = frappe.db.sql(f"SELECT hu.name AS name FROM `tabHandling Unit` hu {hu_where}",
                        tuple(hu_params), as_dict=True) or []

    existing_keys = set()
    for r in (job.counts or []):
        k = (r.item or "", r.location or "", r.handling_unit or "", r.batch_no or "", r.serial_no or "")
        existing_keys.add(k)

    created_rows = 0
    blind = int(getattr(job, "blind_count", 0) or 0)

    def _append_count_row(item: str, location: Optional[str], handling_unit: Optional[str],
                          batch_no: Optional[str], serial_no: Optional[str], sys_qty: Optional[float]):
        nonlocal created_rows
        key = (item or "", location or "", handling_unit or "", batch_no or "", serial_no or "")
        if key in existing_keys:
            return
        payload = {
            "item": item,
            "location": location,
            "handling_unit": handling_unit,
            "batch_no": batch_no,
            "serial_no": serial_no,
            "system_count": (None if blind else flt(sys_qty or 0)),
            "actual_quantity": None,
            "blind_count": blind,
        }
        job.append("counts", payload)
        existing_keys.add(key)
        created_rows += 1

    # Only create count rows for items that actually exist in stock ledger
    for a in aggregates:
        if a.get("item") not in item_set: continue
        _append_count_row(a.get("item"), a.get("storage_location"), a.get("handling_unit"),
                          a.get("batch_no"), a.get("serial_no"), flt(a.get("system_qty") or 0))

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg_bits = [_("Created {0} count line(s).").format(created_rows)]
    if created_rows == 0:
        msg_bits.append(_("No stock found in ledger for items in Orders matching the job scope (Company: {0}, Branch: {1}).").format(company or "Any", branch or "Any"))
    if blind: msg_bits.append(_("Blind: system counts hidden"))
    if company: msg_bits.append(_("Company: {0}").format(company))
    if branch:  msg_bits.append(_("Branch: {0}").format(branch))

    return {"ok": True, "message": " | ".join(msg_bits), "created_rows": created_rows,
            "header": {"count_date": getattr(job, "count_date", None),
                       "count_type": getattr(job, "count_type", None),
                       "blind_count": blind,
                       "qa_required": int(getattr(job, "qa_required", 0) or 0)}}




# =============================================================================
# CREATE → JOB OPERATIONS
# =============================================================================


# =============================================================================
# Create Sales Invoice from Warehouse Job Charges
# =============================================================================

# create_sales_invoice_from_job moved to api_parts/ops.py


# =============================================================================
# PERIODIC BILLING (charges + invoice)
# =============================================================================
# (unchanged from your previous version; omitted here for brevity if not used)
# =============================================================================
# ... keep your existing Periodic Billing helpers/functions ...
# =============================================================================


# =============================================================================
# LEDGER POSTING — per-row dedupe + timestamps + status enforcement
# =============================================================================

def _posting_datetime(job: Any):
    dt = getattr(job, "job_open_date", None)
    return get_datetime(dt) if dt else now_datetime()


def _ledger_has_field(fieldname: str) -> bool:
    return fieldname in _safe_meta_fieldnames("Warehouse Stock Ledger")


def _insert_ledger_entry(
    job: Any,
    *,
    item: str,
    qty: float,
    location: Optional[str],
    handling_unit: Optional[str],
    batch_no: Optional[str],
    serial_no: Optional[str],
    posting_dt,
):
    company, branch = _get_job_scope(job)
    if not company or not branch:
        frappe.throw(_("Company and Branch must be set on the Warehouse Job."))

    _assert_location_in_job_scope(location, company, branch)
    _assert_hu_in_job_scope(handling_unit, company, branch)

    led = frappe.new_doc("Warehouse Stock Ledger")
    led.posting_date     = posting_dt
    if _ledger_has_field("warehouse_job"): led.warehouse_job = job.name
    led.item             = item
    led.storage_location = location
    if _ledger_has_field("handling_unit"): led.handling_unit = handling_unit or None
    if _ledger_has_field("serial_no"):     led.serial_no     = serial_no or None
    if _ledger_has_field("batch_no"):      led.batch_no      = batch_no or None
    led.quantity         = qty
    if _ledger_has_field("company"): led.company = company
    if _ledger_has_field("branch"):  led.branch  = branch
    led.insert(ignore_permissions=True)


def _row_flag_fields() -> Dict[str, Tuple[str, str]]:
    """Map action -> (flag_field, timestamp_field) IF they exist on child row."""
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    out: Dict[str, Tuple[str, str]] = {}
    pairs = {
        "pick":       ("pick_posted",       "pick_posted_at"),
        "staging":    ("staging_posted",    "staging_posted_at"),
        "putaway":    ("putaway_posted",    "putaway_posted_at"),
        "release":    ("release_posted",    "release_posted_at"),
        "receiving":  ("receiving_posted",  "receiving_posted_at"),
    }
    for action, pair in pairs.items():
        f, t = pair
        if f in jf:
            out[action] = (f, t if t in jf else "")
    return out


def _row_is_already_posted(row: Any, action: str) -> bool:
    flags = _row_flag_fields()
    if action not in flags:
        return False
    f, _ts = flags[action]
    return bool(getattr(row, f, 0))


def _mark_row_posted(row: Any, action: str, when) -> None:
    flags = _row_flag_fields()
    if action not in flags:
        return
    f, t = flags[action]
    setattr(row, f, 1)
    if t:
        setattr(row, t, when)


def _maybe_set_staging_area_on_row(row: Any, staging_area: Optional[str]) -> None:
    if not staging_area:
        return
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    if "staging_area" in jf and not getattr(row, "staging_area", None):
        setattr(row, "staging_area", staging_area)


def _post_one(job, action_key: str, it, qty_to_post: float, posting_dt) -> Tuple[int, int]:
    """
    Perform the exact ledger motions for a single row and mark flags.
    Returns: (#out_entries, #in_entries) written.
    """
    staging_area = getattr(job, "staging_area", None)
    item  = getattr(it, "item", None)
    hu    = getattr(it, "handling_unit", None)
    bn    = getattr(it, "batch_no", None)
    sn    = getattr(it, "serial_no", None)
    qty   = abs(flt(qty_to_post or 0))

    if qty <= 0 or not item:
        return (0, 0)

    out_ct = in_ct = 0

    if action_key == "pick":
        src = getattr(it, "location", None)
        if not staging_area or not src:
            return (0, 0)
        _validate_status_for_action(action="Pick", location=src, handling_unit=hu)
        _validate_status_for_action(action="Pick", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=src,          handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt); out_ct += 1
        _insert_ledger_entry(job, item=item, qty=+qty, location=staging_area,  handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt); in_ct  += 1
        _maybe_set_staging_area_on_row(it, staging_area)
        _mark_row_posted(it, "pick", posting_dt)

    elif action_key == "putaway":
        if not staging_area:
            return (0, 0)
        dest = _row_destination_location(it)
        if not dest:
            return (0, 0)
        _validate_status_for_action(action="Putaway", location=staging_area, handling_unit=hu)
        _validate_status_for_action(action="Putaway", location=dest,         handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area, handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt); out_ct += 1
        _insert_ledger_entry(job, item=item, qty=+qty, location=dest,         handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt); in_ct  += 1
        _mark_row_posted(it, "putaway", posting_dt)

    elif action_key in ("staging", "receiving"):  # stage IN (receiving)
        if not staging_area:
            return (0, 0)
        _validate_status_for_action(action="Receiving", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=+qty, location=staging_area, handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt); in_ct  += 1
        _mark_row_posted(it, action_key, posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)

    elif action_key in ("release",):  # stage OUT (release)
        if not staging_area:
            return (0, 0)
        _validate_status_for_action(action="Release", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area, handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt); out_ct += 1
        _mark_row_posted(it, action_key, posting_dt)

    return (out_ct, in_ct)

@frappe.whitelist()
def post_items_by_scan(
    warehouse_job: str,
    action: str,
    location_code: Optional[str] = None,
    handling_unit_code: Optional[str] = None,
    qty: Optional[float] = None,
    item: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Scan-driven posting for Warehouse Job.
    - action: 'receiving' | 'pick' | 'putaway' | 'release'
    - location_code: scanned Storage Location barcode/name (source for Pick, destination for Putaway)
    - handling_unit_code: scanned HU barcode/name (filters candidate rows)
    - qty: optional partial quantity to post; if omitted, posts all matching rows
    - item: optional item filter when scanning HU that contains multiple items

    Returns summary of ledger entries and rows affected.
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    action_key = _action_key(action)

    # Resolve scanned codes
    loc = _resolve_scanned_location(location_code) if location_code else None
    hu  = _resolve_scanned_hu(handling_unit_code) if handling_unit_code else None

    # Company/Branch scope safety
    company, branch = _get_job_scope(job)
    _assert_location_in_job_scope(loc, company, branch, ctx=_("Scanned Location"))
    _assert_hu_in_job_scope(hu, company, branch, ctx=_("Scanned Handling Unit"))

    # Collect candidates
    candidates = _iter_candidate_rows(job, action_key, loc, hu, item)
    if not candidates:
        return {"ok": True, "message": _("No matching rows for scan."), "out_entries": 0, "in_entries": 0, "posted_rows": 0, "posted_qty": 0.0}

    # Determine how much to post
    total_match_qty = sum([abs(flt(getattr(r, "quantity", 0))) for r in candidates])
    to_post = abs(flt(qty or total_match_qty))
    if to_post <= 0:
        return {"ok": True, "message": _("Nothing to post (qty=0)."), "out_entries": 0, "in_entries": 0, "posted_rows": 0, "posted_qty": 0.0}

    posting_dt = _posting_datetime(job)

    out_ct = in_ct = posted_rows = 0
    remaining = to_post

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()
    staging_area = getattr(job, "staging_area", None)

    for r in candidates:
        if remaining <= 0:
            break
        row_qty = abs(flt(getattr(r, "quantity", 0)))
        if row_qty <= 0:
            continue

        portion = min(row_qty, remaining)
        # Split if needed
        target_row = _split_job_item_for_partial(job, r, portion)
        o, i = _post_one(job, action_key, target_row, portion, posting_dt)
        out_ct += o; in_ct += i
        posted_rows += 1
        remaining -= portion

        # track affected locations/HUs for status updates
        hu = getattr(target_row, "handling_unit", None)
        if hu: affected_hus.add(hu)
        if action_key == "pick":
            if getattr(target_row, "location", None): affected_locs.add(getattr(target_row, "location"))
            if staging_area: affected_locs.add(staging_area)
        elif action_key == "putaway":
            dest = _row_destination_location(target_row)
            if staging_area: affected_locs.add(staging_area)
            if dest: affected_locs.add(dest)
        elif action_key in ("staging", "receiving", "release"):
            if staging_area: affected_locs.add(staging_area)

    job.save(ignore_permissions=True)

    # Recompute statuses
    for l in affected_locs:
        _set_sl_status_by_balance(l)
    # receiving/release differ for HU inactive flag
    after_release = (action_key == "release")
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=after_release)

    frappe.db.commit()

    done = to_post - remaining
    msg_map = {
        "pick":    _("Pick posted by scan: {0} rows, {1} qty."),
        "putaway": _("Putaway posted by scan: {0} rows, {1} qty."),
        "staging": _("Staging updated by scan: {0} rows, {1} qty."),
        "receiving": _("Receiving posted by scan: {0} rows, {1} qty."),
        "release": _("Release posted by scan: {0} rows, {1} qty."),
    }
    msg = msg_map.get(action_key, _("Posted by scan: {0} rows, {1} qty.")).format(int(posted_rows), flt(done))

    return {
        "ok": True,
        "message": msg,
        "action": action_key,
        "posted_rows": int(posted_rows),
        "posted_qty": flt(done),
        "out_entries": int(out_ct),
        "in_entries": int(in_ct),
        "scanned": {"location": loc, "handling_unit": hu, "item": item},
    }


@frappe.whitelist()
def post_receiving(warehouse_job: str) -> Dict[str, Any]:
    """Putaway step 1: In to Staging (+ABS(qty)) per item row; marks staging/receiving posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created = 0
    skipped: List[str] = []

    action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "receiving"

    for it in (job.items or []):
        if _row_is_already_posted(it, action_key):
            skipped.append(_("Item Row {0}: staging already posted.").format(getattr(it, "idx", "?"))); continue
        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Receiving", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        _mark_row_posted(it, action_key, posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)
        created += 1

    job.save(ignore_permissions=True)

    # status recompute
    _set_sl_status_by_balance(staging_area)
    seen_hus = {getattr(r, "handling_unit", None) for r in (job.items or []) if getattr(r, "handling_unit", None)}
    for h in seen_hus:
        _set_hu_status_by_balance(h, after_release=False)

    frappe.db.commit()

    msg = _("Receiving posted into staging: {0} entry(ies).").format(created)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "created": created, "skipped": skipped}


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


@frappe.whitelist()
def post_pick(warehouse_job: str) -> Dict[str, Any]:
    """Pick step: Out from Location (−ABS) + In to Staging (+ABS); marks pick_posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created_out = created_in = 0
    skipped: List[str] = []

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()

    for it in (job.items or []):
        if _row_is_already_posted(it, "pick"):
            skipped.append(_("Item Row {0}: pick already posted.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        loc  = getattr(it, "location", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or not loc or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Pick", location=loc,          handling_unit=hu)
        _validate_status_for_action(action="Pick", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=loc,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1

        _insert_ledger_entry(job, item=item, qty=qty,  location=staging_area,
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

    msg = _("Pick posted: {0} OUT from location, {1} IN to staging.").format(created_out, created_in)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_location": created_out, "in_to_staging": created_in, "skipped": skipped}


@frappe.whitelist()
def post_release(warehouse_job: str) -> Dict[str, Any]:
    """Release step: Out from Staging (−ABS); marks staging/release posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created = 0
    skipped: List[str] = []

    affected_hus: Set[str] = set()

    action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "release"

    for it in (job.items or []):
        if _row_is_already_posted(it, action_key):
            skipped.append(_("Item Row {0}: staging already released.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Release", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        _mark_row_posted(it, action_key, posting_dt)
        created += 1

        if hu: affected_hus.add(hu)

    job.save(ignore_permissions=True)

    _set_sl_status_by_balance(staging_area)
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=True)

    frappe.db.commit()

    msg = _("Release posted: {0} OUT from staging.").format(created)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "created": created, "skipped": skipped}


# =============================================================================
# Global validator (optional)
# =============================================================================

def _validate_job_locations_in_scope(job: Any):
    """Call from hooks.py on Warehouse Job validate to ensure manual entries stay in scope."""
    company, branch = _get_job_scope(job)
    if not (company or branch):
        return

    for it in (job.items or []):
        loc = getattr(it, "location", None) or getattr(it, "to_location", None)
        hu  = getattr(it, "handling_unit", None)
        _assert_location_in_job_scope(loc, company, branch, ctx=_("Item Location"))
        _assert_hu_in_job_scope(hu,  company, branch, ctx=_("Item Handling Unit"))

    for orow in (job.orders or []):
        _assert_location_in_job_scope(getattr(orow, "storage_location_from", None), company, branch, ctx=_("From Location"))
        _assert_location_in_job_scope(getattr(orow, "storage_location_to",   None), company, branch, ctx=_("To Location"))
        _assert_hu_in_job_scope(getattr(orow, "handling_unit_from", None), company, branch, ctx=_("From Handling Unit"))
        _assert_hu_in_job_scope(getattr(orow, "handling_unit_to",   None), company, branch, ctx=_("To Handling Unit"))


# =============================================================================
# Warehouse Job — submit-time completeness validation
# =============================================================================

def _get_child_rows(job: Any, child_doctype: str, fallback_fieldname: Optional[str] = None) -> Tuple[List[Any], Optional[str]]:
    """Return (rows, fieldname) for a child table on Warehouse Job."""
    fn = _find_child_table_field("Warehouse Job", child_doctype) or fallback_fieldname
    rows = list(getattr(job, fn, []) or []) if fn else []
    return rows, fn

def _dest_loc_fieldname_for_items() -> Optional[str]:
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    if "to_location" in jf: return "to_location"
    if "location"    in jf: return "location"
    return None

def _validate_job_completeness(job: Any, *, on_submit: bool = False) -> None:
    """Block submit if core tables are empty or if rows are missing critical fields."""
    errors: List[str] = []

    job_type = (getattr(job, "type", "") or "").strip()
    item_rows, items_fieldname = _get_child_rows(job, "Warehouse Job Item", fallback_fieldname="items")
    op_rows,   ops_fieldname   = _get_child_rows(job, "Warehouse Job Operations")

    # Enforce operation sequencing across entire table
    try:
        seq_errs = _validate_ops_sequencing(job, op_rows)
        errors.extend(seq_errs)
    except Exception as e:
        errors.append(_("Sequencing validation error: {0}").format(e))
    ch_rows,   charges_fieldname = _get_child_rows(job, "Warehouse Job Charges", fallback_fieldname="charges")

    if on_submit:
        # For Stocktake jobs, allow empty items if populate adjustment has been triggered
        if not item_rows and job_type != "Stocktake":
            errors.append(_("Items table is empty. Add at least one item row."))
        elif not item_rows and job_type == "Stocktake":
            # Check if populate adjustment has been triggered
            populate_triggered = getattr(job, "populate_adjustment_triggered", False)
            if not populate_triggered:
                errors.append(_("Items table is empty. Either add items manually or use 'Populate Adjustments' button."))
        if not op_rows:
            errors.append(_("Operations table is empty. Add at least one operation row."))
        if not ch_rows:
            errors.append(_("Charges table is empty. Add at least one charge row."))

    it_fields = _safe_meta_fieldnames("Warehouse Job Item")
    has_loc      = "location" in it_fields
    has_to_loc   = "to_location" in it_fields
    has_hu       = "handling_unit" in it_fields
    dest_field   = _dest_loc_fieldname_for_items()

    for r in item_rows:
        row_errs: List[str] = []
        idx = getattr(r, "idx", None) or "?"

        item = (getattr(r, "item", None) or "").strip()
        qty  = getattr(r, "quantity", None)
        if not item:
            row_errs.append(_("item"))
        if job_type != "Stocktake" and (qty in (None, "") or flt(qty) == 0):
            row_errs.append(_("quantity (non-zero)"))

        if job_type == "Pick" or (job_type == "VAS" and flt(qty or 0) < 0):
            if has_loc and not getattr(r, "location", None):
                row_errs.append(_("location (source)"))
        elif job_type == "Putaway" or (job_type == "VAS" and flt(qty or 0) > 0):
            if dest_field and not getattr(r, dest_field, None):
                row_errs.append(_("destination ({0})").format(dest_field.replace("_", " ")))
        elif job_type == "Move":
            if has_loc and not getattr(r, "location", None):
                row_errs.append(_("location"))
        elif job_type == "Stocktake":
            loc_ok = (has_loc and getattr(r, "location", None))
            hu_ok  = (has_hu and getattr(r, "handling_unit", None))
            if not (loc_ok or hu_ok):
                row_errs.append(_("location or handling unit"))

        if row_errs:
            errors.append(_("Item row {0}: missing {1}.").format(idx, ", ".join(row_errs)))

    op_fields = _safe_meta_fieldnames("Warehouse Job Operations")
    has_op_qty = "quantity" in op_fields
    for r in op_rows:
        idx = getattr(r, "idx", None) or "?"
        op_code  = (getattr(r, "operation", None) or "").strip()
        if not op_code:
            errors.append(_("Operation row {0}: Operation is required.").format(idx))
        if has_op_qty and (getattr(r, "quantity", None) in (None, "")):
            errors.append(_("Operation row {0}: Quantity is required.").format(idx))

    ch_fields = _safe_meta_fieldnames("Warehouse Job Charges")
    has_qty   = "quantity" in ch_fields
    has_rate  = "rate" in ch_fields
    has_total = "total" in ch_fields

    for r in ch_rows:
        idx = getattr(r, "idx", None) or "?"
        code = (getattr(r, "item_code", None) or getattr(r, "item", None) or "").strip()
        if not code:
            errors.append(_("Charge row {0}: Item is required.").format(idx))
            continue

        qty   = flt(getattr(r, "quantity", 0.0)) if has_qty   else 0.0
        rate  = flt(getattr(r, "rate", 0.0))     if has_rate  else 0.0
        total = flt(getattr(r, "total", 0.0))    if has_total else 0.0

        if not ((qty > 0 and rate > 0) or (total > 0) or (rate > 0)):
            errors.append(_("Charge row {0}: set Quantity & Rate, or Total (or at least a positive Rate).").format(idx))

    try:
        _validate_job_locations_in_scope(job)
    except Exception as e:
        errors.append(str(e))

    if errors:
        msg = _("Cannot submit Warehouse Job due to validation errors:") + "\n- " + "\n- ".join(errors)
        frappe.throw(msg)

def warehouse_job_before_submit(doc, method=None):
    """Hook: called on before_submit of Warehouse Job."""
    # Skip validation during allocation process
    if hasattr(doc, '_skip_validation') and doc._skip_validation:
        return
    _validate_job_completeness(doc, on_submit=True)



# --- Location status check: does NOT block submit (client decides) ----------
@frappe.whitelist()
def check_item_location_statuses(warehouse_job: str) -> Dict[str, Any]:
    """Report Storage Locations referenced on the job whose status != 'Available'.
    Returns data for a client-side confirmation. Never throws/block-submits."""
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))

    job = frappe.get_doc("Warehouse Job", warehouse_job)

    sl_fields = _safe_meta_fieldnames("Storage Location")
    if "status" not in sl_fields:
        return {
            "ok": True,
            "has_warnings": False,
            "affected_locations": [],
            "lines": [],
            "message": _("Storage Location has no Status field on this site; no location-status checks were applied."),
        }

    it_fields = _safe_meta_fieldnames("Warehouse Job Item")
    has_loc = "location" in it_fields
    has_to  = "to_location" in it_fields

    locs: Set[str] = set()
    for it in (job.items or []):
        if has_loc:
            v = (getattr(it, "location", None) or "").strip()
            if v: locs.add(v)
        if has_to:
            v = (getattr(it, "to_location", None) or "").strip()
            if v: locs.add(v)

    if not locs:
        return {"ok": True, "has_warnings": False, "affected_locations": [], "lines": [], "message": _("No item rows reference a storage location.")}

    rows = frappe.get_all(
        "Storage Location",
        filters={"name": ["in", list(locs)]},
        fields=["name", "status"],
        ignore_permissions=True,
    ) or []
    status_by = {r["name"]: (r.get("status") or "Available") for r in rows}
    offenders = {name for name, st in status_by.items() if st != "Available"}

    if not offenders:
        return {"ok": True, "has_warnings": False, "affected_locations": [], "lines": [], "message": _("All referenced locations are Available.")}

    details: List[Dict[str, Any]] = []
    for it in (job.items or []):
        idx = getattr(it, "idx", None) or "?"
        item_code = getattr(it, "item", None)
        qty = flt(getattr(it, "quantity", 0))
        if has_loc:
            loc = (getattr(it, "location", None) or "").strip()
            if loc and loc in offenders:
                details.append({"row_idx": idx, "field": "location", "location": loc, "status": status_by.get(loc, "Unknown"), "item": item_code, "qty": qty})
        if has_to:
            dest = (getattr(it, "to_location", None) or "").strip()
            if dest and dest in offenders:
                details.append({"row_idx": idx, "field": "to_location", "location": dest, "status": status_by.get(dest, "Unknown"), "item": item_code, "qty": qty})

    affected_sorted = sorted(offenders)
    msg = _("Some locations referenced on this job are not Available: {0}. Continue submitting?").format(", ".join(affected_sorted))
    return {"ok": True, "has_warnings": True, "affected_locations": affected_sorted, "lines": details, "message": msg}

# =============================================================================
# PERIODIC BILLING (charges + invoice)
# =============================================================================

@frappe.whitelist()
def create_sales_invoice_from_periodic_billing(
    periodic_billing: Optional[str] = None,
    warehouse_job: Optional[str] = None,
    customer: Optional[str] = None,
    company: Optional[str] = None,
    posting_date: Optional[str] = None,
    cost_center: Optional[str] = None,
    branch: Optional[str] = None,  # NEW: allow explicit override
) -> Dict[str, Any]:
    """
    Create a Sales Invoice from:
      - Periodic Billing (preferred when called from PB form), or
      - Warehouse Job (delegates to create_sales_invoice_from_job).
    Ensures company and branch are populated from PB (or overrides).
    """

    # Backward path: delegate to job-based function when warehouse_job provided
    if warehouse_job:
        # Best effort: propagate branch to Sales Invoice if your SI DocType supports it
        out = create_sales_invoice_from_job(
            warehouse_job=warehouse_job,
            customer=customer,
            company=company,
            posting_date=posting_date,
            cost_center=cost_center,
        )
        try:
            if branch:
                si_name = out.get("sales_invoice")
                if si_name and "branch" in _safe_meta_fieldnames("Sales Invoice"):
                    frappe.db.set_value("Sales Invoice", si_name, "branch", branch)
        except Exception as e:
            frappe.logger().debug(f"Failed to set branch on Sales Invoice {si_name}: {str(e)}")
        return out

    if not periodic_billing:
        frappe.throw(_("Either periodic_billing or warehouse_job must be provided."))

    # Load PB header (source of truth for company/branch unless overridden)
    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    pbf = _safe_meta_fieldnames("Periodic Billing")

    # Resolve header values
    customer = customer or (getattr(pb, "customer", None) if "customer" in pbf else None)
    company  = company  or (getattr(pb, "company",  None) if "company"  in pbf else None)
    branch   = branch   or (getattr(pb, "branch",   None) if "branch"   in pbf else None)

    if not customer:
        frappe.throw(_("Customer is required (set it on Periodic Billing or pass it here)."))
    if not company:
        frappe.throw(_("Company is required (set it on Periodic Billing or pass it here)."))

    # Discover PB charges table/fields
    charges_field = _find_child_table_field("Periodic Billing", "Periodic Billing Charge") or "charges"
    charges = list(getattr(pb, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in {0}.").format(_("Periodic Billing Charges")))

    cf = _safe_meta_fieldnames("Periodic Billing Charge")
    row_has_currency = "currency" in cf
    row_has_rate     = "rate" in cf
    row_has_total    = "total" in cf
    row_has_uom      = "uom" in cf
    row_has_itemname = "item_name" in cf
    row_has_qty      = "quantity" in cf

    currencies: Set[str] = set()
    valid_rows: List[Dict[str, Any]] = []

    for ch in charges:
        # Tolerate either item_code or item on the PB row
        item_code = (getattr(ch, "item_code", None) or getattr(ch, "item", None) or "").strip()
        if not item_code:
            continue

        qty   = flt(getattr(ch, "quantity", 0.0)) if row_has_qty   else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if row_has_rate  else 0.0
        total = flt(getattr(ch, "total", 0.0))    if row_has_total else 0.0
        uom   = (getattr(ch, "uom", None) or None) if row_has_uom else None
        item_name = (getattr(ch, "item_name", None) or None) if row_has_itemname else None
        curr  = (getattr(ch, "currency", None) or "").strip() if row_has_currency else ""

        if row_has_currency and curr:
            currencies.add(curr)

        # Normalize qty/rate/total
        if qty and not rate and total:
            rate = total / qty
        if (not qty or qty == 0) and total and not rate:
            qty, rate = 1.0, total
        if not qty and not rate and not total:
            continue

        valid_rows.append({
            "item_code": item_code,
            "item_name": item_name,
            "qty": flt(qty) if qty else (1.0 if (total or rate) else 0.0),
            "rate": flt(rate) if rate else (flt(total) if (not qty and total) else 0.0),
            "uom": uom,
            "currency": curr or None,
        })

    if not valid_rows:
        frappe.throw(_("No valid charge rows to invoice."))

    # Single-currency check (if currency present on rows)
    chosen_currency = None
    if row_has_currency:
        currencies = {c for c in currencies if c}
        if len(currencies) > 1:
            frappe.throw(_("All charge rows must have the same currency. Found: {0}").format(", ".join(sorted(currencies))))
        chosen_currency = (list(currencies)[0] if currencies else None)

    # Build Sales Invoice
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company  = company
    if posting_date: si.posting_date = posting_date

    # NEW: set branch on header if the field exists
    sif = _safe_meta_fieldnames("Sales Invoice")
    if branch and "branch" in sif:
        setattr(si, "branch", branch)

    # Link back to PB or add remark
    if "periodic_billing" in sif:
        setattr(si, "periodic_billing", pb.name)
    else:
        base_remarks = (getattr(si, "remarks", "") or "").strip()
        note = _("Auto-created from Periodic Billing {0}").format(pb.name)
        si.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    if chosen_currency and "currency" in sif:
        si.currency = chosen_currency

    # Append items (also set branch per row if the field exists)
    sif_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    item_has_branch = "branch" in sif_item_fields

    for r in valid_rows:
        row_payload = {"item_code": r["item_code"], "qty": r["qty"] or 0.0, "rate": r["rate"] or 0.0}
        if "uom" in sif_item_fields and r.get("uom"): row_payload["uom"] = r["uom"]
        if "item_name" in sif_item_fields and r.get("item_name"): row_payload["item_name"] = r["item_name"]
        if cost_center and "cost_center" in sif_item_fields: row_payload["cost_center"] = cost_center
        if item_has_branch and branch: row_payload["branch"] = branch
        si.append("items", row_payload)

    si.insert()
    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name}

@frappe.whitelist()
def get_warehouse_job(name: str):
    return frappe.get_doc("Warehouse Job", name).as_dict()
    
    
# ============================================================
# SCAN PAGE HELPERS (resolve job, overview, ops time updates)
# ============================================================

import json
from frappe.utils import get_datetime, now
from typing import TypedDict

def _wj_fields():
    return _safe_meta_fieldnames("Warehouse Job")

# _wjo_fields moved to api_parts/common.py

@frappe.whitelist()
def resolve_warehouse_job(scanned: str) -> dict:
    """
    Resolve a scanned string (QR/barcode/name) to a Warehouse Job name.
    Uses: direct name match, then barcode-like fields.
    """
    scanned = (scanned or "").strip()
    if not scanned:
        return {"ok": False, "message": _("Nothing scanned.")}
    # Direct name
    if frappe.db.exists("Warehouse Job", scanned):
        return {"ok": True, "name": scanned}

    # Barcode-like fields on Warehouse Job (reuse core helper)
    for bf in _barcode_fields("Warehouse Job"):
        name = frappe.db.get_value("Warehouse Job", {bf: scanned}, "name")
        if name:
            return {"ok": True, "name": name}

    return {"ok": False, "message": _("No Warehouse Job found for: {0}").format(scanned)}

# get_warehouse_job_overview moved to api_parts/common.py
# update_job_operations_times moved to api_parts/ops.py

@frappe.whitelist()
def post_job_by_scan(
    warehouse_job: str,
    action: str,
    location_code: str = None,
    handling_unit_code: str = None,
    qty: float = None,
    item: str = None,
) -> dict:
    """
    Thin wrapper to your existing scan-driven poster for the desk page.
    """
    return post_items_by_scan(
        warehouse_job=warehouse_job,
        action=action,
        location_code=location_code,
        handling_unit_code=handling_unit_code,
        qty=qty,
        item=item,
    )

# --- helpers for ops date fields (supports start_datetime/end_datetime OR start_date/end_date) ---
# _ops_time_fields moved to api_parts/common.py


# --- sequencing helpers for Warehouse Job Operations ---
def _wjo_order_value(row: Any) -> int:
    """Return sequence key for an operations row, using 'order' if present, else idx."""
    try:
        v = getattr(row, "order", None)
        return int(v) if (v not in (None, "",)) else int(getattr(row, "idx", 0) or 0)
    except (ValueError, TypeError, AttributeError) as e:
        frappe.logger().debug(f"Failed to get order value from row: {str(e)}, using idx")
        return int(getattr(row, "idx", 0) or 0)

def _wjo_is_completed(row: Any) -> bool:
    """An operation is considered completed if it has end time OR positive actual_hours."""
    fields = _safe_meta_fieldnames("Warehouse Job Operations")
    start_f, end_f = _ops_time_fields()
    try:
        if "actual_hours" in fields and flt(getattr(row, "actual_hours", 0) or 0) > 0:
            return True
        if end_f and end_f in fields and getattr(row, end_f, None):
            return True
    except (AttributeError, TypeError) as e:
        frappe.logger().debug(f"Failed to check completion status for row: {str(e)}")
    return False

def _assert_prior_ops_completed(job: Any, ops_fieldname: str, current_row: Any) -> None:
    """Raise if any operation with lower 'order' (or idx fallback) is not completed."""
    rows = list(getattr(job, ops_fieldname, []) or [])
    # sort rows with stable key (order, idx)
    sorted_rows = sorted(rows, key=lambda r: (_wjo_order_value(r), getattr(r, "idx", 0) or 0))
    cur_key = (_wjo_order_value(current_row), getattr(current_row, "idx", 0) or 0)
    for r in sorted_rows:
        key = (_wjo_order_value(r), getattr(r, "idx", 0) or 0)
        if key < cur_key and not _wjo_is_completed(r):
            # Build readable names
            cur_name = (getattr(current_row, "operation", None) or getattr(current_row, "name", None) or "?")
            prev_name = (getattr(r, "operation", None) or getattr(r, "name", None) or "?")
            frappe.throw(_("Operation sequencing rule: '{0}' cannot start/finish before prior operation '{1}' is completed.").format(cur_name, prev_name))

def _validate_ops_sequencing(job: Any, ops_rows: List[Any]) -> List[str]:
    """Return list of sequencing errors across the whole table (for before_submit)."""
    errs: List[str] = []
    rows = list(ops_rows or [])
    if not rows:
        return errs
    fields = _safe_meta_fieldnames("Warehouse Job Operations")
    start_f, end_f = _ops_time_fields()
    sorted_rows = sorted(rows, key=lambda r: (_wjo_order_value(r), getattr(r, "idx", 0) or 0))
    # Find first incomplete; no later row should have start/end/actual
    first_incomplete_idx = None
    for i, r in enumerate(sorted_rows):
        if not _wjo_is_completed(r):
            first_incomplete_idx = i
            break
    if first_incomplete_idx is None:
        return errs  # all good
    # If any later row shows progress, flag
    for j in range(first_incomplete_idx + 1, len(sorted_rows)):
        r = sorted_rows[j]
        started = bool(start_f and getattr(r, start_f, None))
        ended   = bool(end_f and getattr(r, end_f, None))
        has_act = "actual_hours" in fields and flt(getattr(r, "actual_hours", 0) or 0) > 0
        if started or ended or has_act:
            later = (getattr(r, "operation", None) or getattr(r, "name", None) or "?")
            prior = (getattr(sorted_rows[first_incomplete_idx], "operation", None) or getattr(sorted_rows[first_incomplete_idx], "name", None) or "?")
            errs.append(_("Operation sequencing violated: later operation '{0}' shows progress while prior '{1}' is not completed.").format(later, prior))
    return errs


# Legacy compatibility function - redirects to the comprehensive billing implementation
@frappe.whitelist()
def periodic_billing_get_charges_legacy(customer: Optional[str] = None,
                                 from_date: Optional[str] = None,
                                 to_date: Optional[str] = None,
                                 job: Optional[str] = None) -> Dict[str, Any]:
    """Legacy compatibility function - use periodic_billing_get_charges instead."""
    # This function is kept for backward compatibility but should not be used
    # The main implementation is now in logistics.warehousing.billing.periodic_billing_get_charges
    return {"charges": [], "filters": {"customer": customer, "from_date": from_date, "to_date": to_date, "job": job}, "meta": {"deprecated": True}}

# =============================================================================
# PERIODIC BILLING (charges + invoice)
# =============================================================================

def _pb__charges_fieldname() -> Optional[str]:
    return _find_child_table_field("Periodic Billing", "Periodic Billing Charges")


def _pb__find_customer_contract(customer: Optional[str]) -> Optional[str]:
    if not customer:
        return None
    wf = _safe_meta_fieldnames("Warehouse Contract")
    cond = {"docstatus": 1}
    if "customer" in wf:
        cond["customer"] = customer
    rows = frappe.get_all("Warehouse Contract", filters=cond, fields=["name"], limit=1, ignore_permissions=True)
    if rows:
        return rows[0]["name"]
    cond["docstatus"] = 0
    rows = frappe.get_all("Warehouse Contract", filters=cond, fields=["name"], limit=1, ignore_permissions=True)
    return rows[0]["name"] if rows else None


def _pb__get_storage_contract_item(contract: Optional[str]) -> Optional[Dict[str, Any]]:
    if not contract:
        return None
    fields = ["item_charge AS item_code", "rate", "currency", "billing_time_unit", "billing_time_multiplier", "minimum_billing_time"]
    rows = frappe.get_all(
        "Warehouse Contract Item",
        filters={"parent": contract, "parenttype": "Warehouse Contract", "storage_charge": 1},
        fields=fields, limit=1, ignore_permissions=True,
    )
    return rows[0] if rows else None


def _pb__distinct_hus_for_customer(customer: str, date_to: str, company: Optional[str] = None, branch: Optional[str] = None) -> List[str]:
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")
    wjf = _safe_meta_fieldnames("Warehouse Job")
    params: List[Any] = [date_to]
    joins: List[str] = []
    conds: List[str] = ["l.handling_unit IS NOT NULL", "l.posting_date <= %s"]
    ##__PB_COMPANY_BRANCH__
    if "customer" in llf:
        conds.append("l.customer = %s"); params.append(customer)
    elif "customer" in huf:
        joins.append("LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit")
        conds.append("hu.customer = %s"); params.append(customer)
    elif "customer" in wjf:
        joins.append("LEFT JOIN `tabWarehouse Job Item` ji ON ji.handling_unit = l.handling_unit")
        joins.append("LEFT JOIN `tabWarehouse Job` j ON j.name = ji.parent")
        conds.append("j.customer = %s"); params.append(customer)
        # Optional company/branch scoping
    slf = _safe_meta_fieldnames("Warehouse Stock Ledger")
    if company and "company" in slf:
        conds.append("l.company = %s"); params.append(company)
    if branch and "branch" in slf:
        conds.append("l.branch = %s"); params.append(branch)
    sql = f"""
        SELECT DISTINCT l.handling_unit
        FROM `tabWarehouse Stock Ledger` l
        {' '.join(joins)}
        WHERE {' AND '.join(conds)}
    """
    rows = frappe.db.sql(sql, tuple(params), as_dict=True) or []
    return [r["handling_unit"] for r in rows if r.get("handling_unit")]


def _pb__hu_opening_balance(hu: str, date_from: str) -> float:
    row = frappe.db.sql(
        "SELECT IFNULL(SUM(quantity),0) AS bal FROM `tabWarehouse Stock Ledger` WHERE handling_unit=%s AND posting_date < %s",
        (hu, date_from), as_dict=True,
    )
    return flt(row[0]["bal"] if row else 0.0)


def _pb__hu_daily_deltas(hu: str, date_from: str, date_to: str) -> Dict[date, float]:
    rows = frappe.db.sql(
        """
        SELECT DATE(posting_date) AS d, IFNULL(SUM(quantity),0) AS qty
        FROM `tabWarehouse Stock Ledger`
        WHERE handling_unit=%s AND posting_date BETWEEN %s AND %s
        GROUP BY DATE(posting_date)
        """,
        (hu, date_from, date_to), as_dict=True,
    ) or []
    out = {}
    for r in rows:
        out[getdate(r["d"])] = flt(r["qty"] or 0.0)
    return out


def _pb__count_used_days(hu: str, date_from: str, date_to: str) -> int:
    start = getdate(date_from)
    end   = getdate(date_to)
    cur = _pb__hu_opening_balance(hu, date_from)
    deltas = _pb__hu_daily_deltas(hu, date_from, date_to)
    used = 0
    d = start
    one = timedelta(days=1)
    while d <= end:
        cur = cur + flt(deltas.get(d, 0.0))
        if cur > 0:
            used += 1
        d += one
    return used


# Redirect to comprehensive billing implementation
@frappe.whitelist()
def periodic_billing_get_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    """Redirect to the comprehensive billing implementation in billing.py"""
    from logistics.warehousing.billing import periodic_billing_get_charges as billing_get_charges
    return billing_get_charges(periodic_billing, clear_existing)


@frappe.whitelist()
def create_sales_invoice_from_periodic_billing(
    periodic_billing: str,
    posting_date: Optional[str] = None,
    company: Optional[str] = None,
    cost_center: Optional[str] = None,
) -> Dict[str, Any]:
    if not periodic_billing:
        frappe.throw(_("periodic_billing is required"))

    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    pbf = _safe_meta_fieldnames("Periodic Billing")
    customer  = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to   = getattr(pb, "date_to", None)
    pb_company = getattr(pb, "company", None) if "company" in pbf else None
    pb_branch  = getattr(pb, "branch", None) if "branch" in pbf else None
    profit_center = getattr(pb, "profit_center", None) if "profit_center" in pbf else None
    pb_cost_center = getattr(pb, "cost_center", None) if "cost_center" in pbf else None
    job_costing_number = getattr(pb, "job_costing_number", None) if "job_costing_number" in pbf else None
    
    if not customer:
        frappe.throw(_("Customer is required on Periodic Billing."))
    if not (date_from and date_to):
        frappe.throw(_("Date From and Date To are required on Periodic Billing."))

    charges_field = _find_child_table_field("Periodic Billing", "Periodic Billing Charges")
    if not charges_field:
        frappe.throw(_("Periodic Billing has no child table for 'Periodic Billing Charges'."))
    charges = list(getattr(pb, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in Periodic Billing Charges."))

    company = company or pb_company or _get_default_company_safe()
    if not company:
        frappe.throw(_("Company is required (pass it in, or set a Default Company)."))
    
    cost_center = cost_center or pb_cost_center

    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company  = company
    if posting_date: si.posting_date = posting_date

    sif = _safe_meta_fieldnames("Sales Invoice")
    if pb_branch and "branch" in sif:
        setattr(si, "branch", pb_branch)
    if profit_center and "profit_center" in sif:
        setattr(si, "profit_center", profit_center)
    if cost_center and "cost_center" in sif:
        setattr(si, "cost_center", cost_center)
    if job_costing_number and "job_costing_number" in sif:
        setattr(si, "job_costing_number", job_costing_number)
    if "periodic_billing" in sif:
        setattr(si, "periodic_billing", pb.name)

    base_remarks = (getattr(si, "remarks", "") or "").strip()
    notes = [
        _("Auto-created from Periodic Billing {0}").format(pb.name),
        _("Period: {0} to {1}").format(date_from, date_to),
    ]
    si.remarks = (base_remarks + ("\n" if base_remarks else "") + "\n".join(notes)).strip()

    sif_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    cf = _safe_meta_fieldnames("Periodic Billing Charges")
    row_has_uom      = "uom" in cf
    row_has_itemname = "item_name" in cf
    row_has_qty      = "quantity" in cf
    row_has_rate     = "rate" in cf
    row_has_total    = "total" in cf

    created_rows = 0
    for ch in charges:
        item_code = getattr(ch, "item", None) or getattr(ch, "item_code", None)
        if not item_code:
            continue
        qty   = flt(getattr(ch, "quantity", 0.0)) if row_has_qty   else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if row_has_rate  else 0.0
        total = flt(getattr(ch, "total", 0.0))    if row_has_total else 0.0
        uom   = (getattr(ch, "uom", None) or None) if row_has_uom else None
        item_name = (getattr(ch, "item_name", None) or None) if row_has_itemname else None

        if qty and not rate and total: rate = total / qty
        if (not qty or qty == 0) and total and not rate: qty, rate = 1.0, total
        if not qty and not rate and not total: continue

        row_payload = {"item_code": item_code, "qty": qty or 0.0, "rate": rate or (total if (not qty and total) else 0.0)}
        if "uom" in sif_item_fields and uom: row_payload["uom"] = uom
        if "item_name" in sif_item_fields and item_name: row_payload["item_name"] = item_name
        if cost_center and "cost_center" in sif_item_fields: row_payload["cost_center"] = cost_center
        if pb_branch and "branch" in sif_item_fields: row_payload["branch"] = pb_branch
        if profit_center and "profit_center" in sif_item_fields: row_payload["profit_center"] = profit_center
        # Tag job_costing_number to storage charges (all items from periodic billing are storage charges)
        if job_costing_number and "job_costing_number" in sif_item_fields: row_payload["job_costing_number"] = job_costing_number
        si.append("items", row_payload)
        created_rows += 1

    if created_rows == 0:
        frappe.throw(_("No valid Periodic Billing Charges to create Sales Invoice items."))

    si.insert()
    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name, "created_rows": created_rows}


# =============================================================================
# PERIODIC BILLING (charges + invoice)
# =============================================================================

from datetime import timedelta, date
from frappe.utils import getdate, flt

def _pb__charges_fieldname() -> Optional[str]:
    return _find_child_table_field("Periodic Billing", "Periodic Billing Charges")


def _pb__find_customer_contract(customer: Optional[str]) -> Optional[str]:
    if not customer:
        return None
    wf = _safe_meta_fieldnames("Warehouse Contract")
    cond = {"docstatus": 1}
    if "customer" in wf:
        cond["customer"] = customer
    rows = frappe.get_all("Warehouse Contract", filters=cond, fields=["name"], limit=1, ignore_permissions=True)
    if rows:
        return rows[0]["name"]
    cond["docstatus"] = 0
    rows = frappe.get_all("Warehouse Contract", filters=cond, fields=["name"], limit=1, ignore_permissions=True)
    return rows[0]["name"] if rows else None


def _pb__get_storage_contract_item(contract: Optional[str]) -> Optional[Dict[str, Any]]:
    if not contract:
        return None
    fields = ["item_charge AS item_code", "rate", "currency", "billing_time_unit", "billing_time_multiplier", "minimum_billing_time"]
    rows = frappe.get_all(
        "Warehouse Contract Item",
        filters={"parent": contract, "parenttype": "Warehouse Contract", "storage_charge": 1},
        fields=fields, limit=1, ignore_permissions=True,
    )
    return rows[0] if rows else None


def _pb__distinct_hus_for_customer(customer: str, date_to: str, company: Optional[str] = None, branch: Optional[str] = None) -> List[str]:
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")
    wjf = _safe_meta_fieldnames("Warehouse Job")
    params: List[Any] = [date_to]
    joins: List[str] = []
    conds: List[str] = ["l.handling_unit IS NOT NULL", "l.posting_date <= %s"]
    if "customer" in llf:
        conds.append("l.customer = %s"); params.append(customer)
    elif "customer" in huf:
        joins.append("LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit")
        conds.append("hu.customer = %s"); params.append(customer)
    elif "customer" in wjf:
        joins.append("LEFT JOIN `tabWarehouse Job Item` ji ON ji.handling_unit = l.handling_unit")
        joins.append("LEFT JOIN `tabWarehouse Job` j ON j.name = ji.parent")
        conds.append("j.customer = %s"); params.append(customer)

    # Optional company/branch scoping
    if "company" in llf and company:
        conds.append("l.company = %s"); params.append(company)
    if "branch" in llf and branch:
        conds.append("l.branch = %s"); params.append(branch)

    sql = f"""
        SELECT DISTINCT l.handling_unit
        FROM `tabWarehouse Stock Ledger` l
        {' '.join(joins)}
        WHERE {' AND '.join(conds)}
    """
    rows = frappe.db.sql(sql, tuple(params), as_dict=True) or []
    return [r["handling_unit"] for r in rows if r.get("handling_unit")]


def _pb__hu_opening_balance(hu: str, date_from: str) -> float:
    row = frappe.db.sql(
        "SELECT IFNULL(SUM(quantity),0) AS bal FROM `tabWarehouse Stock Ledger` WHERE handling_unit=%s AND posting_date < %s",
        (hu, date_from), as_dict=True,
    )
    return flt(row[0]["bal"] if row else 0.0)


def _pb__hu_daily_deltas(hu: str, date_from: str, date_to: str) -> Dict[date, float]:
    rows = frappe.db.sql(
        """
        SELECT DATE(posting_date) AS d, IFNULL(SUM(quantity),0) AS qty
        FROM `tabWarehouse Stock Ledger`
        WHERE handling_unit=%s AND posting_date BETWEEN %s AND %s
        GROUP BY DATE(posting_date)
        """,
        (hu, date_from, date_to), as_dict=True,
    ) or []
    out: Dict[date, float] = {}
    for r in rows:
        out[getdate(r["d"])] = flt(r["qty"] or 0.0)
    return out


def _pb__count_used_days(hu: str, date_from: str, date_to: str) -> int:
    start = getdate(date_from)
    end   = getdate(date_to)
    cur = _pb__hu_opening_balance(hu, date_from)
    deltas = _pb__hu_daily_deltas(hu, date_from, date_to)
    used = 0
    d = start
    one = timedelta(days=1)
    while d <= end:
        cur = cur + flt(deltas.get(d, 0.0))
        if cur > 0:
            used += 1
        d += one
    return used


# This duplicate implementation has been removed - using billing.py version instead


@frappe.whitelist()
def create_sales_invoice_from_periodic_billing(
    periodic_billing: str,
    posting_date: Optional[str] = None,
    company: Optional[str] = None,
    cost_center: Optional[str] = None,
) -> Dict[str, Any]:
    if not periodic_billing:
        frappe.throw(_("periodic_billing is required"))

    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    customer  = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to   = getattr(pb, "date_to", None)
    pb_company = getattr(pb, "company", None)
    pb_branch  = getattr(pb, "branch", None)
    if not customer:
        frappe.throw(_("Customer is required on Periodic Billing."))
    if not (date_from and date_to):
        frappe.throw(_("Date From and Date To are required on Periodic Billing."))

    charges_field = _find_child_table_field("Periodic Billing", "Periodic Billing Charges")
    if not charges_field:
        frappe.throw(_("Periodic Billing has no child table for 'Periodic Billing Charges'."))
    charges = list(getattr(pb, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in Periodic Billing Charges."))

    company = company or pb_company or _get_default_company_safe()
    if not company:
        frappe.throw(_("Company is required (pass it in, or set a Default Company)."))

    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company  = company
    if posting_date: si.posting_date = posting_date

    sif = _safe_meta_fieldnames("Sales Invoice")
    if pb_branch and "branch" in sif:
        setattr(si, "branch", pb_branch)
    if "periodic_billing" in sif:
        setattr(si, "periodic_billing", pb.name)

    base_remarks = (getattr(si, "remarks", "") or "").strip()
    notes = [
        _("Auto-created from Periodic Billing {0}").format(pb.name),
        _("Period: {0} to {1}").format(date_from, date_to),
    ]
    si.remarks = (base_remarks + ("\n" if base_remarks else "") + "\n".join(notes)).strip()

    sif_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    cf = _safe_meta_fieldnames("Periodic Billing Charges")
    row_has_uom      = "uom" in cf
    row_has_itemname = "item_name" in cf
    row_has_qty      = "quantity" in cf
    row_has_rate     = "rate" in cf
    row_has_total    = "total" in cf

    created_rows = 0
    for ch in charges:
        item_code = getattr(ch, "item", None) or getattr(ch, "item_code", None)
        if not item_code:
            continue
        qty   = flt(getattr(ch, "quantity", 0.0)) if row_has_qty   else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if row_has_rate  else 0.0
        total = flt(getattr(ch, "total", 0.0))    if row_has_total else 0.0
        uom   = (getattr(ch, "uom", None) or None) if row_has_uom else None
        item_name = (getattr(ch, "item_name", None) or None) if row_has_itemname else None

        if qty and not rate and total: rate = total / qty
        if (not qty or qty == 0) and total and not rate: qty, rate = 1.0, total
        if not qty and not rate and not total: continue

        row_payload = {"item_code": item_code, "qty": qty or 0.0, "rate": rate or (total if (not qty and total) else 0.0)}
        if "uom" in sif_item_fields and uom: row_payload["uom"] = uom
        if "item_name" in sif_item_fields and item_name: row_payload["item_name"] = item_name
        if cost_center and "cost_center" in sif_item_fields: row_payload["cost_center"] = cost_center
        si.append("items", row_payload)
        created_rows += 1

    if created_rows == 0:
        frappe.throw(_("No valid Periodic Billing Charges to create Sales Invoice items."))

    si.insert()

    # --- After creating Sales Invoice, update Periodic Billing + charges ---
    # Parent: set PB.sales_invoice if field exists
    pbf = _safe_meta_fieldnames("Periodic Billing")
    if "sales_invoice" in pbf:
        try:
            setattr(pb, "sales_invoice", si.name)
        except (AttributeError, TypeError) as e:
            frappe.logger().debug(f"Failed to set sales_invoice on Periodic Billing: {str(e)}")

    # Children: mark invoiced=1 and link SI if fields exist
    cf_fields = _safe_meta_fieldnames("Periodic Billing Charges")
    ch_rows = list(getattr(pb, charges_field, []) or [])
    updated_pb_rows = 0
    for ch in ch_rows:
        if "invoiced" in cf_fields:
            try:
                setattr(ch, "invoiced", 1)
            except (AttributeError, TypeError) as e:
                frappe.logger().debug(f"Failed to set invoiced on Periodic Billing Charges: {str(e)}")
        if "sales_invoice" in cf_fields:
            try:
                setattr(ch, "sales_invoice", si.name)
            except (AttributeError, TypeError) as e:
                frappe.logger().debug(f"Failed to set sales_invoice on Periodic Billing Charges: {str(e)}")
        updated_pb_rows += 1

    try:
        pb.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.logger().error(f"Failed to save Periodic Billing after creating Sales Invoice: {str(e)}")
        frappe.throw(_("Failed to update Periodic Billing after creating Sales Invoice. Please check the logs."))

    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name, "created_rows": created_rows, "updated_pb_rows": updated_pb_rows}

