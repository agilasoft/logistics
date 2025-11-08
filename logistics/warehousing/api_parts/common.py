from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import date, timedelta
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate
import json
from frappe.utils import get_datetime, now
from typing import TypedDict

def _get_default_currency(company: Optional[str] = None) -> str:
    """Get default currency for company or system default from ERPNext."""
    try:
        if company:
            # Get currency from ERPNext Company
            currency = frappe.db.get_value("Company", company, "default_currency")
            if currency:
                return currency
        
        # Fallback to system default currency from Global Defaults
        currency = frappe.db.get_single_value("Global Defaults", "default_currency")
        if currency:
            return currency
            
        # Final fallback - get first company's currency
        first_company = frappe.db.get_value("Company", filters={"enabled": 1}, fieldname="name")
        if first_company:
            currency = frappe.db.get_value("Company", first_company, "default_currency")
            if currency:
                return currency
                
        # Ultimate fallback
        return "USD"
    except Exception as e:
        frappe.logger().debug(f"Failed to get default currency: {str(e)}")
        return "USD"

def _hu_location_fields() -> List[str]:
    """Return plausible location fieldnames present on Handling Unit."""
    hf = _safe_meta_fieldnames("Handling Unit")
    return [fn for fn in ("location", "storage_location") if fn in hf]

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

def _row_destination_location(it) -> Optional[str]:
    fld = _dest_loc_fieldname_for_putaway()
    return getattr(it, fld, None)

def _hu_fields():
    return _safe_meta_fieldnames("Handling Unit")

def _hu_balance(hu: Optional[str]) -> float:
    if not hu: return 0.0
    r = frappe.db.sql("SELECT COALESCE(SUM(quantity),0) FROM `tabWarehouse Stock Ledger` WHERE handling_unit=%s", (hu,))
    return float(r[0][0] if r else 0.0)

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

def _get_allocation_level_limit() -> Optional[str]:
    """Return the label (e.g., 'Aisle') set in Warehouse Settings, else None."""
    try:
        company = frappe.defaults.get_user_default("Company")
        val = frappe.db.get_value("Warehouse Settings", company, "allocation_level_limit")
        val = (val or "").strip()
        return val or None
    except Exception:
        return None

def _get_allow_emergency_fallback() -> bool:
    """Return True if emergency fallback is allowed in Warehouse Settings, else False."""
    try:
        company = frappe.defaults.get_user_default("Company")
        val = frappe.db.get_value("Warehouse Settings", company, "allow_emergency_fallback")
        return bool(val)
    except Exception:
        return False

def _get_split_quantity_decimal_precision() -> int:
    """Return the split quantity decimal precision from Warehouse Settings, default to 2."""
    try:
        company = frappe.defaults.get_user_default("Company")
        val = frappe.db.get_value("Warehouse Settings", company, "split_quantity_decimal_precision")
        if val is not None:
            return int(val)
        return 2  # Default precision
    except Exception:
        return 2  # Default precision

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

def _filter_locations_by_level(candidates: List[Dict[str, Any]], staging_area: Optional[str], limit_label: Optional[str]) -> List[Dict[str, Any]]:
    if not (staging_area and limit_label):
        return candidates
    out: List[Dict[str, Any]] = []
    for c in candidates:
        loc = c.get("storage_location") or c.get("location")
        if _match_upto_limit(staging_area, loc, limit_label):
            out.append(c)
    return out

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

def _maybe_set_staging_area_on_row(row: Any, staging_area: Optional[str]) -> None:
    if not staging_area:
        return
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    if "staging_area" in jf and not getattr(row, "staging_area", None):
        setattr(row, "staging_area", staging_area)

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

_LEVEL_ORDER = ["site", "building", "zone", "aisle", "bay", "level"]

_LEVEL_LABEL_TO_FIELD = {
    "Site": "site", "Building": "building", "Zone": "zone",
    "Aisle": "aisle", "Bay": "bay", "Level": "level",
}

CTX_FLAG = {
    "inbound":   "inbound_charge",
    "outbound":  "outbound_charge",
    "transfer":  "transfer_charge",
    "vas":       "vas_charge",
    "storage":   "storage_charge",
    "stocktake": "stocktake_charge",
}

def _safe_meta_fieldnames(doctype: str) -> set:
    """Return set of fieldnames for a DocType using version-stable APIs."""
    meta = frappe.get_meta(doctype)
    fieldnames = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None) or (df.get("fieldname") if isinstance(df, dict) else None)
        if fn:
            fieldnames.add(fn)
    return fieldnames

def _find_child_table_field(parent_doctype: str, child_doctype: str) -> Optional[str]:
    """Find the fieldname of the Table field on parent that points to child_doctype."""
    meta = frappe.get_meta(parent_doctype)
    for df in meta.get("fields", []) or []:
        if (getattr(df, "fieldtype", None) or df.get("fieldtype")) == "Table":
            opts = getattr(df, "options", None) or df.get("options")
            if opts == child_doctype:
                return getattr(df, "fieldname", None) or df.get("fieldname")
    return None

def _get_job_scope(job: Any) -> Tuple[Optional[str], Optional[str]]:
    """Extract Company/Branch from the Warehouse Job if present."""
    jf = _safe_meta_fieldnames("Warehouse Job")
    company = getattr(job, "company", None) if "company" in jf else None
    branch  = getattr(job, "branch", None)  if "branch"  in jf else None
    return (company or None, branch or None)

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

def _sl_fields():
    return _safe_meta_fieldnames("Storage Location")

def _get_sl(name: Optional[str]):
    return frappe.get_doc("Storage Location", name) if name and frappe.db.exists("Storage Location", name) else None

def _get_hu(name: Optional[str]):
    return frappe.get_doc("Handling Unit", name) if name and frappe.db.exists("Handling Unit", name) else None

def _sl_balance(loc: Optional[str]) -> float:
    if not loc: return 0.0
    r = frappe.db.sql("SELECT COALESCE(SUM(quantity),0) FROM `tabWarehouse Stock Ledger` WHERE storage_location=%s", (loc,))
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

def _existing_level_fields() -> List[str]:
    slf = _safe_meta_fieldnames("Storage Location")
    return [f for f in _LEVEL_ORDER if f in slf]

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
    except Exception:
        lot = 0

    try:
        mix = int(mix) if mix is not None else 0
    except Exception:
        mix = 0

    return {
        "lot_consolidation": lot,
        "allow_mix_with_other_customers": mix,
        "customer": cust,
    }

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
          AND IFNULL(sl.staging_area, 0) = 0
          AND (%s IS NULL OR l.batch_no = %s)
          AND (%s IS NULL OR l.serial_no = %s)
          {scope_sql}
          {sl_status}
          {hu_block}
        GROUP BY l.storage_location, l.handling_unit, l.batch_no, l.serial_no
        HAVING SUM(l.quantity) > 0
    """
    return frappe.db.sql(sql, tuple(params), as_dict=True) or []

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

def _select_dest_for_hu(
    item: str,
    company: Optional[str],
    branch: Optional[str],
    staging_area: Optional[str],
    level_limit_label: Optional[str],
    used_locations: Set[str],
    exclude_locations: Optional[List[str]],
) -> Optional[str]:
    from .putaway import _putaway_candidate_locations
    candidates = _putaway_candidate_locations(item=item, company=company, branch=branch, exclude_locations=exclude_locations or [])
    # filter by allocation level (same path as staging)
    filtered = []
    for r in candidates:
        loc = r["location"]
        if loc in used_locations:
            continue
        if _match_upto_limit(staging_area, loc, level_limit_label):
            filtered.append(r)
    return filtered[0]["location"] if filtered else None

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
        if qty in (None, "") or flt(qty) == 0:
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
    _validate_job_completeness(doc, on_submit=True)

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
        except Exception:
            pass
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
    profit_center = getattr(pb, "profit_center", None) if "profit_center" in pbf else None
    cost_center = cost_center or (getattr(pb, "cost_center", None) if "cost_center" in pbf else None)
    job_costing_number = getattr(pb, "job_costing_number", None) if "job_costing_number" in pbf else None

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

    # Set company, branch, profit_center, cost_center, and job_costing_number on header if fields exist
    sif = _safe_meta_fieldnames("Sales Invoice")
    if branch and "branch" in sif:
        setattr(si, "branch", branch)
    if profit_center and "profit_center" in sif:
        setattr(si, "profit_center", profit_center)
    if cost_center and "cost_center" in sif:
        setattr(si, "cost_center", cost_center)
    if job_costing_number and "job_costing_number" in sif:
        setattr(si, "job_costing_number", job_costing_number)

    # Link back to PB or add remark
    if "periodic_billing" in sif:
        setattr(si, "periodic_billing", pb.name)
    else:
        base_remarks = (getattr(si, "remarks", "") or "").strip()
        note = _("Auto-created from Periodic Billing {0}").format(pb.name)
        si.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    if chosen_currency and "currency" in sif:
        si.currency = chosen_currency

    # Append items (also set branch, profit_center, cost_center, and job_costing_number per row if fields exist)
    sif_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    item_has_branch = "branch" in sif_item_fields
    item_has_profit_center = "profit_center" in sif_item_fields
    item_has_cost_center = "cost_center" in sif_item_fields
    item_has_job_costing_number = "job_costing_number" in sif_item_fields

    for r in valid_rows:
        row_payload = {"item_code": r["item_code"], "qty": r["qty"] or 0.0, "rate": r["rate"] or 0.0}
        if "uom" in sif_item_fields and r.get("uom"): row_payload["uom"] = r["uom"]
        if "item_name" in sif_item_fields and r.get("item_name"): row_payload["item_name"] = r["item_name"]
        if cost_center and item_has_cost_center: row_payload["cost_center"] = cost_center
        if item_has_branch and branch: row_payload["branch"] = branch
        if profit_center and item_has_profit_center: row_payload["profit_center"] = profit_center
        # Tag job_costing_number to storage charges (all items from periodic billing are storage charges)
        if job_costing_number and item_has_job_costing_number: row_payload["job_costing_number"] = job_costing_number
        si.append("items", row_payload)

    si.insert()
    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name}

@frappe.whitelist()
def get_warehouse_job(name: str):
    return frappe.get_doc("Warehouse Job", name).as_dict()

def _wj_fields():
    return _safe_meta_fieldnames("Warehouse Job")

def _wjo_fields():
    return _safe_meta_fieldnames("Warehouse Job Operations")

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

@frappe.whitelist()
def get_warehouse_job_overview(warehouse_job: str) -> dict:
    """
    Return core header and operations summary for the scan page.
    Safe-field aware to work across schema variations.
    """
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))

    job = frappe.get_doc("Warehouse Job", warehouse_job)
    jf  = _wj_fields()

    header = {
        "name": job.name,
        "type": getattr(job, "type", None),
        "status": getattr(job, "status", None) if "status" in jf else None,
        "docstatus": int(getattr(job, "docstatus", 0) or 0),
        "customer": getattr(job, "customer", None) if "customer" in jf else None,
        "company": getattr(job, "company", None) if "company" in jf else None,
        "branch": getattr(job, "branch", None) if "branch" in jf else None,
        "staging_area": getattr(job, "staging_area", None) if "staging_area" in jf else None,
        "job_open_date": getattr(job, "job_open_date", None) if "job_open_date" in jf else None,
    }

    # Operations (child table may be named "Warehouse Job Operations")
    ops_fn = _find_child_table_field("Warehouse Job", "Warehouse Job Operations")
    ops_rows = []
    if ops_fn:
        childf = _wjo_fields()
        # Pre-compute which fields exist
        has = lambda f: (f in childf)
        for r in getattr(job, ops_fn, []) or []:
            row = {
                "name": getattr(r, "name", None),
                "idx": getattr(r, "idx", None),
                "operation": getattr(r, "operation", None) if has("operation") else None,
                "description": getattr(r, "description", None) if has("description") else None,
                "quantity": float(getattr(r, "quantity", 0) or 0) if has("quantity") else None,
                "unit_std_hours": float(getattr(r, "unit_std_hours", 0) or 0) if has("unit_std_hours") else None,
                "total_std_hours": float(getattr(r, "total_std_hours", 0) or 0) if has("total_std_hours") else None,
                "actual_hours": float(getattr(r, "actual_hours", 0) or 0) if has("actual_hours") else None,
                "start_date": getattr(r, "start_date", None) if has("start_date") else None,
                "end_date": getattr(r, "end_date", None) if has("end_date") else None,
            }
            ops_rows.append(row)

    return {"ok": True, "header": header, "operations": ops_rows}

def _ops_time_fields():
    f = _safe_meta_fieldnames("Warehouse Job Operations")
    start_f = "start_datetime" if "start_datetime" in f else ("start_date" if "start_date" in f else None)
    end_f   = "end_datetime"   if "end_datetime"   in f else ("end_date"   if "end_date"   in f else None)
    return start_f, end_f

def _get_replenish_policy_flags(item: Optional[str]) -> Tuple[bool, bool]:
    """Return (replenish_mode, pick_face_first) based on Warehouse Settings and item rules.
    - Replenish mode if Warehouse Settings.replenishment_policy in ['replenish','replenishment','pick face first','pick_face_first']
    - pick_face_first if Warehouse Item rules has primary_pick_face_first=1
    Best-effort; silently ignores missing fields/doctype.
    """
    replen = False
    try:
        policy = frappe.db.get_single_value("Warehouse Settings", "replenishment_policy")
        if policy and isinstance(policy, str):
            replen = policy.strip().lower() in ("replenish", "replenishment", "pick face first", "pick_face_first")
    except Exception:
        replen = False

    pick_face_first = False
    try:
        rules = _get_item_rules(item) if item else {}
        pick_face_first = bool(int(rules.get("primary_pick_face_first") or 0))
    except Exception:
        pick_face_first = False

    return replen, pick_face_first

def _get_item_storage_type_prefs(item: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Return (preferred_storage_type, allowed_storage_types[]) for the item.
    preferred_storage_type: Link to Storage Type (single), may be None
    allowed_storage_types:  List from child table 'Warehouse Item Storage Type' (field 'storage_type'), may be empty
    """
    preferred = None
    allowed: List[str] = []
    if not item:
        return preferred, allowed

    # Read preferred storage type from Warehouse Item
    try:
        preferred = frappe.db.get_value("Warehouse Item", item, "preferred_storage_type")
    except Exception:
        preferred = None

    # Read allowed storage types child rows
    try:
        rows = frappe.get_all(
            "Warehouse Item Storage Type",
            filters={"parent": item, "parenttype": "Warehouse Item"},
            fields=["storage_type"],
            ignore_permissions=True,
        ) or []
        for r in rows:
            st = (r.get("storage_type") or "").strip()
            if st:
                allowed.append(st)
        # De-duplicate preserving order
        seen = set()
        allowed = [x for x in allowed if not (x in seen or seen.add(x))]
    except Exception:
        allowed = []

    return preferred, allowed

def _ensure_batch(
    batch_code: Optional[str],
    item: Optional[str] = None,
    customer: Optional[str] = None,
    expiry: Optional[str] = None,
    uom: Optional[str] = None,
) -> str:
    if not batch_code:
        return ""
    if frappe.db.exists("Warehouse Batch", batch_code):
        if uom:
            current_uom = frappe.db.get_value("Warehouse Batch", batch_code, "batch_uom")
            if not current_uom:
                frappe.db.set_value("Warehouse Batch", batch_code, "batch_uom", uom)
        return batch_code
    doc = frappe.new_doc("Warehouse Batch")
    doc.batch_no = batch_code  # autoname=field:batch_no
    if hasattr(doc, "item_code") and item:
        doc.item_code = item
    if hasattr(doc, "customer") and customer:
        doc.customer = customer
    if hasattr(doc, "expiry_date") and expiry:
        doc.expiry_date = expiry
    if hasattr(doc, "batch_uom") and uom:
        doc.batch_uom = uom
    doc.insert()
    return doc.name
