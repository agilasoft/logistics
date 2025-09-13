# apps/logistics/logistics/warehousing/api.py

from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils.data import flt

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


def _find_child_table_field(parent_doctype: str, child_doctype: str) -> Optional[str]:
    """Find the fieldname of the Table field on parent that points to child_doctype."""
    meta = frappe.get_meta(parent_doctype)
    for df in meta.get("fields", []) or []:
        if (getattr(df, "fieldtype", None) or df.get("fieldtype")) == "Table":
            opts = getattr(df, "options", None) or df.get("options")
            if opts == child_doctype:
                return getattr(df, "fieldname", None) or df.get("fieldname")
    return None


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
    """
    True iff entity matches job scope for any specified scope dimension.
    - If job_company is set, entity_company must match (or be None when the entity lacks the field).
    - If job_branch is set, entity_branch must match (or be None when the entity lacks the field).
    """
    if job_company and (entity_company not in (None, job_company)):
        return False
    if job_branch and (entity_branch not in (None, job_branch)):
        return False
    return True


# =============================================================================
# Scope assertions (Company / Branch)  # NEW
# =============================================================================

def _assert_location_in_job_scope(location: Optional[str], job_company: Optional[str], job_branch: Optional[str], ctx: str = "Location"):
    if not location:
        return
    lc, lb = _get_location_scope(location)
    if not _same_scope(job_company, job_branch, lc, lb):
        frappe.throw(_("{0} {1} is out of scope for Company/Branch on this Job.").format(ctx, location))

def _assert_hu_in_job_scope(hu: Optional[str], job_company: Optional[str], job_branch: Optional[str], ctx: str = "Handling Unit"):
    if not hu:
        return
    hc, hb = _get_handling_unit_scope(hu)
    if not _same_scope(job_company, job_branch, hc, hb):
        frappe.throw(_("{0} {1} is out of scope for Company/Branch on this Job.").format(ctx, hu))


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

    base = {"parent": contract, "parenttype": "Warehouse Contract", "item_charge": item_code}
    filters = dict(base)
    flag = CTX_FLAG.get(context)
    if flag:
        filters[flag] = 1

    fields = ["rate", "currency", "handling_uom", "time_uom", "storage_uom", "storage_charge"]
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
    except Exception:
        pass

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
    created_batch = linked_batch = 0
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
                            to_set["serial_no"] = code
                            linked_serial += 1
                        else:
                            to_set["serial_no"] = _ensure_serial(code, r.item, customer)
                            created_serial += 1
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
                            to_set["batch_no"] = code_b
                            linked_batch += 1
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
        "linked": {"serial": linked_serial, "batch": linked_batch},
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
        fields=[
            "name", "parent",
            "item", "quantity", "uom",
            "serial_no", "batch_no", "handling_unit"
        ],
        order_by="idx asc",
        ignore_permissions=True,
    ) or []


def _get_item_rules(item: str) -> Dict[str, Any]:
    sql = """
        SELECT
            picking_method,
            IFNULL(single_lot_preference, 0) AS single_lot_preference,
            IFNULL(full_unit_first, 0) AS full_unit_first,
            IFNULL(nearest_location_first, 0) AS nearest_location_first,
            IFNULL(primary_pick_face_first, 0) AS primary_pick_face_first,
            IFNULL(quality_grade_priority, 0) AS quality_grade_priority,
            IFNULL(storage_type_preference, 0) AS storage_type_preference
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


# =============================================================================
# Availability query (scoped by Company/Branch)
# =============================================================================

def _query_available_candidates(
    item: str,
    batch_no: Optional[str] = None,
    serial_no: Optional[str] = None,
    company: Optional[str] = None,
    branch: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregate positive availability from 'tabWarehouse Stock Ledger', scoped by Company/Branch if provided.
    Uses COALESCE over HU/Location/Ledger company/branch to be resilient to schema differences.
    """
    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

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
        LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
        LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit
        LEFT JOIN `tabWarehouse Batch` b ON b.name = l.batch_no
        LEFT JOIN `tabWarehouse Serial` ws ON ws.name = l.serial_no
        WHERE l.item = %s
          AND (%s IS NULL OR l.batch_no = %s)
          AND (%s IS NULL OR l.serial_no = %s)
          {scope_sql}
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
        last_seen = c.get("last_seen")
        expiry = c.get("expiry_date")
        if method == "FEFO":
            return ((0, expiry) if expiry else (1, frappe.utils.now_datetime()), )
        if method == "LEFO":
            # Prefer lots that *do* have an expiry; among them, latest expiry first
            return ((0, frappe.utils.get_datetime("1900-01-01")) if expiry else (1, frappe.utils.get_datetime("1900-01-01")), )
        if method in ("LIFO", "FMFO"):
            ls = last_seen or frappe.utils.get_datetime("1900-01-01")
            return ((-ls.timestamp()), )
        fs = first_seen or frappe.utils.now_datetime()
        return ((fs.timestamp()), )

    def can_fill(c: Dict[str, Any]) -> int:
        return 1 if flt(c.get("available_qty")) >= required_qty else 0

    def hu_present(c: Dict[str, Any]) -> int:
        return 1 if c.get("handling_unit") else 0

    def full_key(c: Dict[str, Any]) -> Tuple:
        k = []
        if method == "LEFO":
            expiry = c.get("expiry_date")
            miss = 1 if not expiry else 0
            ts = 0.0
            if expiry:
                ts = frappe.utils.get_datetime(expiry).timestamp()
            k.append((miss, -ts))
        else:
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
) -> Tuple[int, float]:
    created_rows = 0
    created_qty = 0.0

    job_company, job_branch = _get_job_scope(job)  # NEW

    job_item_fields = _safe_meta_fieldnames("Warehouse Job Item")
    has_uom_field     = "uom" in job_item_fields
    has_source_row    = "source_row" in job_item_fields
    has_source_parent = "source_parent" in job_item_fields

    for a in allocations:
        qty = flt(a.get("qty") or 0)
        if qty == 0:
            continue

        loc = a.get("location")
        hu  = a.get("handling_unit")

        # Enforce scope for any provided Location/HU  # NEW
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

        job.append("items", payload)
        created_rows += 1
        created_qty  += qty

    return created_rows, created_qty


# =============================================================================
# Putaway candidate locations (policy)
# =============================================================================

def _putaway_candidate_locations(item: str, company: Optional[str], branch: Optional[str]) -> List[Dict[str, Any]]:
    """
    Candidate destination locations inside the same Company/Branch:
      1) Locations already holding this item (consolidation)
      2) Other locations in scope ordered by Storage Type rank then bin priority
    """
    cons_sql = """
        SELECT
            l.storage_location AS location,
            IFNULL(sl.bin_priority, 999999) AS bin_priority,
            IFNULL(st.picking_rank, 999999) AS storage_type_rank
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
        WHERE l.item = %s
          AND (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch = %s)
        GROUP BY l.storage_location, sl.bin_priority, st.picking_rank
        HAVING SUM(l.quantity) > 0
        ORDER BY storage_type_rank ASC, bin_priority ASC
    """
    cons = frappe.db.sql(cons_sql, (item, company, company, branch, branch), as_dict=True) or []
    cons_locs = {c["location"] for c in cons}

    all_sql = """
        SELECT
            sl.name AS location,
            IFNULL(sl.bin_priority, 999999) AS bin_priority,
            IFNULL(st.picking_rank, 999999) AS storage_type_rank
        FROM `tabStorage Location` sl
        LEFT JOIN `tabStorage Type` st ON st.name = sl.storage_type
        WHERE (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch = %s)
        ORDER BY storage_type_rank ASC, bin_priority ASC
    """
    all_locs = frappe.db.sql(all_sql, (company, company, branch, branch), as_dict=True) or []
    others = [r for r in all_locs if r["location"] not in cons_locs]

    return cons + others


# =============================================================================
# Allocate PICK from orders (scoped)
# =============================================================================

@frappe.whitelist()
def allocate_pick(warehouse_job: str) -> Dict[str, Any]:
    """
    Build pick-lines on Warehouse Job from its OWN 'orders' table, applying
    Company/Branch scope from the Job to availability queries and validations.
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Pick":
        frappe.throw(_("Allocate Picks can only run for Warehouse Job Type = Pick."))

    company, branch = _get_job_scope(job)

    jo_items = _fetch_job_order_items(job.name)
    if not jo_items:
        return {"ok": True, "message": _("No items found on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    total_created_rows = 0
    total_created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for row in jo_items:
        item = row.get("item")
        req_qty = flt(row.get("quantity"))
        if not item or req_qty <= 0:
            continue

        fixed_serial = row.get("serial_no") or None
        fixed_batch  = row.get("batch_no") or None

        rules = _get_item_rules(item)

        if fixed_serial or fixed_batch:
            candidates = _query_available_candidates(
                item=item, batch_no=fixed_batch, serial_no=fixed_serial,
                company=company, branch=branch
            )
            allocations = _greedy_allocate(candidates, req_qty, rules, force_exact=True)
        else:
            candidates = _query_available_candidates(
                item=item, company=company, branch=branch
            )
            ordered     = _order_candidates(candidates, rules, req_qty)
            allocations = _greedy_allocate(ordered, req_qty, rules, force_exact=False)

        if not allocations:
            scope_note = []
            if company: scope_note.append(_("Company = {0}").format(company))
            if branch:  scope_note.append(_("Branch = {0}").format(branch))
            warnings.append(
                _("No allocatable stock for Item {0} (Row {1}) within scope{2}.")
                .format(item, row.get("name"), f" [{', '.join(scope_note)}]" if scope_note else "")
            )

        created_rows, created_qty = _append_job_items(
            job=job,
            source_parent=job.name,
            source_child=row["name"],
            item=item,
            uom=row.get("uom"),
            allocations=allocations,
        )
        total_created_rows += created_rows
        total_created_qty  += created_qty

        details.append({
            "job_order_item": row["name"],
            "item": item,
            "requested_qty": req_qty,
            "created_rows": created_rows,
            "created_qty": created_qty,
            "short_qty": max(0.0, req_qty - abs(created_qty)),
        })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Allocated {0} units across {1} pick rows.").format(flt(total_created_qty), int(total_created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True,
        "message": msg,
        "created_rows": total_created_rows,
        "created_qty": total_created_qty,
        "lines": details,
        "warnings": warnings,
    }


# =============================================================================
# Allocate PUTAWAY from orders (policy + scoped)
# =============================================================================

@frappe.whitelist()
def allocate_putaway(warehouse_job: str) -> Dict[str, Any]:
    """
    Prepare putaway task rows from this job's 'orders' using policy & scope:

      • handling_unit on Orders is the final HU for putaway.
      • Destination location is selected by policy (orders do NOT have storage_location_to):
          1) Consolidate to a location that already holds the item (within Company/Branch)
          2) Otherwise, best-ranked location by Storage Type (picking_rank), then bin_priority
      • Writes destination to Items.location (or Items.to_location if your items use that).
      • Adds warnings when no destination location or handling unit is available.

    No staging logic here.
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Putaway":
        frappe.throw(_("Allocate Putaway can only run for Warehouse Job Type = Putaway."))

    company, branch = _get_job_scope(job)

    jf = _safe_meta_fieldnames("Warehouse Job Item")
    has_uom        = "uom" in jf
    has_to_loc     = "to_location" in jf
    has_single_loc = "location" in jf
    has_source_row = "source_row" in jf
    has_source_par = "source_parent" in jf

    dest_loc_field = "location" if has_single_loc else ("to_location" if has_to_loc else None)

    orders = _fetch_job_order_items(job.name)
    if not orders:
        return {"ok": True, "message": _("No items found on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not dest_loc_field:
        warnings.append(_("Warehouse Job Item has no destination location field ('location' or 'to_location')."))

    candidate_cache: Dict[str, List[Dict[str, Any]]] = {}

    for r in orders:
        qty = flt(r.get("quantity") or 0)
        if qty <= 0:
            continue

        item = r.get("item")
        dest_hu = (r.get("handling_unit") or "").strip() or None

        dest_loc = None
        if item:
            if item not in candidate_cache:
                candidate_cache[item] = _putaway_candidate_locations(item=item, company=company, branch=branch)
            cands = candidate_cache[item]
            if cands:
                dest_loc = cands[0]["location"]

        # Enforce scope for operator-provided HU and chosen destination Location  # NEW
        _assert_hu_in_job_scope(dest_hu, company, branch, ctx=_("Handling Unit"))
        if dest_loc:
            _assert_location_in_job_scope(dest_loc, company, branch, ctx=_("Destination Location"))

        payload: Dict[str, Any] = {
            "item": item,
            "quantity": qty,
            "serial_no": r.get("serial_no") or None,
            "batch_no": r.get("batch_no") or None,
            "handling_unit": dest_hu,
        }
        if dest_loc_field:
            payload[dest_loc_field] = dest_loc
        if has_uom and r.get("uom"):
            payload["uom"] = r.get("uom")
        if has_source_row:
            payload["source_row"] = r.get("name")
        if has_source_par:
            payload["source_parent"] = job.name

        job.append("items", payload)
        created_rows += 1
        created_qty  += qty

        if not dest_loc:
            warnings.append(
                _("Order Row {0}: no destination location selected in scope; operator must scan destination.")
                .format(r.get("name"))
            )
        if not dest_hu:
            warnings.append(
                _("Order Row {0}: no handling unit provided; operator must supply a handling unit.")
                .format(r.get("name"))
            )

        details.append({
            "order_row": r.get("name"),
            "item": item,
            "qty": qty,
            "dest_location": dest_loc,
            "dest_handling_unit": dest_hu,
        })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Prepared {0} units across {1} putaway rows (policy applied).").format(flt(created_qty), int(created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True,
        "message": msg,
        "created_rows": created_rows,
        "created_qty": created_qty,
        "lines": details,
        "warnings": warnings,
    }


# =============================================================================
# MOVE allocation from orders (scoped validations)
# =============================================================================

@frappe.whitelist()
def allocate_move(warehouse_job: str, clear_existing: int = 1):
    """
    Populate Warehouse Job -> items with paired move rows based on 'orders'.
    Validates that From/To locations & HUs match Job Company/Branch when provided.
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Move":
        frappe.throw(_("Warehouse Job must be of type 'Move' to allocate moves from Orders."))

    company, branch = _get_job_scope(job)

    if clear_existing:
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
            skipped.append(f"Row {r.idx}: missing From/To location")
            continue
        if qty <= 0:
            skipped.append(f"Row {r.idx}: quantity must be > 0")
            continue

        slc_f, slb_f = _get_location_scope(from_loc)
        slc_t, slb_t = _get_location_scope(to_loc)
        if not _same_scope(company, branch, slc_f, slb_f):
            skipped.append(_("Row {0}: From Location {1} out of scope.").format(r.idx, from_loc))
            continue
        if not _same_scope(company, branch, slc_t, slb_t):
            skipped.append(_("Row {0}: To Location {1} out of scope.").format(r.idx, to_loc))
            continue
        if hu_from:
            huc, hub = _get_handling_unit_scope(hu_from)
            if not _same_scope(company, branch, huc, hub):
                skipped.append(_("Row {0}: From Handling Unit {1} out of scope.").format(r.idx, hu_from))
                continue
        if hu_to:
            huc, hub = _get_handling_unit_scope(hu_to)
            if not _same_scope(company, branch, huc, hub):
                skipped.append(_("Row {0}: To Handling Unit {1} out of scope.").format(r.idx, hu_to))
                continue

        common = {
            "item": getattr(r, "item", None),
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }

        job.append("items", {**common, "location": from_loc, "handling_unit": hu_from or None, "quantity": -qty})
        job.append("items", {**common, "location": to_loc,   "handling_unit": hu_to   or None, "quantity":  qty})
        created_pairs += 1

    job.save(ignore_permissions=True)

    return {
        "message": _("Allocated {0} move pair(s).").format(created_pairs),
        "created_pairs": created_pairs,
        "skipped": skipped,
    }


# =============================================================================
# VAS actions (scoped)
# =============================================================================

@frappe.whitelist()
def initiate_vas_pick(warehouse_job: str, clear_existing: int = 1):
    """
    VAS → Build pick rows for BOM components using SAME policies as standard picks.
    - job.type must be 'VAS'
    - job.reference_order_type == 'VAS Order' and reference_order set
    - Quantities appended are NEGATIVE (outbound to VAS work area)
    - Scoped by Job Company/Branch
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)

    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Initiate VAS Pick can only run for Warehouse Job Type = VAS."))
    if (job.reference_order_type or "").strip() != "VAS Order" or not job.reference_order:
        frappe.throw(_("This VAS job must reference a VAS Order."))

    company, branch = _get_job_scope(job)

    if clear_existing:
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
        if vas_type:
            base["vas_order_type"] = vas_type
        if customer:
            r = frappe.get_all("Warehouse Item VAS BOM", filters={**base, "customer": customer}, fields=["name"], limit=1, ignore_permissions=True)
            if r: return r[0]["name"]
        r = frappe.get_all("Warehouse Item VAS BOM", filters=base, fields=["name"], limit=1, ignore_permissions=True)
        return r[0]["name"] if r else None

    for parent in jo_items:
        p_item = parent.get("item")
        p_qty  = flt(parent.get("quantity") or 0)
        if not p_item or p_qty <= 0:
            skipped.append(_("Job Order Row {0}: missing item or non-positive quantity").format(parent.get("name")))
            continue

        bom = _find_vas_bom(p_item)
        if not bom:
            skipped.append(_("No VAS BOM for {0} (type={1}, customer={2})").format(p_item, vas_type or "N/A", customer or "N/A"))
            continue

        inputs = frappe.get_all(
            "Customer VAS Item Input",
            filters={"parent": bom, "parenttype": "Warehouse Item VAS BOM"},
            fields=["name", "item", "quantity", "uom"],
            order_by="idx asc",
            ignore_permissions=True,
        )
        if not inputs:
            skipped.append(_("VAS BOM {0} has no inputs").format(bom))
            continue

        for comp in inputs:
            c_item = comp.get("item")
            per    = flt(comp.get("quantity") or 0)
            uom    = comp.get("uom")
            req    = per * p_qty
            if not c_item or req <= 0:
                skipped.append(_("BOM {0} component missing item/quantity (row {1})").format(bom, comp.get("name")))
                continue

            rules   = _get_item_rules(c_item)
            cand    = _query_available_candidates(item=c_item, company=company, branch=branch)
            ordered = _order_candidates(cand, rules, req)
            allocs  = _greedy_allocate(ordered, req, rules, force_exact=False)

            if not allocs:
                scope_note = []
                if company: scope_note.append(_("Company = {0}").format(company))
                if branch:  scope_note.append(_("Branch = {0}").format(branch))
                warnings.append(
                    _("No allocatable stock for VAS component {0} (Row {1}) within scope{2}.")
                    .format(c_item, comp.get("name"), f" [{', '.join(scope_note)}]" if scope_note else "")
                )

            # NEGATIVE for VAS pick
            allocs_neg = []
            for a in allocs:
                q = flt(a.get("qty") or 0)
                if q > 0:
                    b = dict(a)
                    b["qty"] = -q
                    allocs_neg.append(b)

            c_rows, c_qty = _append_job_items(
                job=job,
                source_parent=job.name,
                source_child=f"{parent.get('name')}::{bom}",
                item=c_item,
                uom=uom,
                allocations=allocs_neg,
            )
            created_rows += c_rows
            created_qty  += c_qty

            details.append({
                "parent_job_order_item": parent.get("name"),
                "parent_item": p_item,
                "component_item": c_item,
                "requested_qty": req,
                "allocated_qty": c_qty,  # negative
                "created_rows": c_rows,
                "short_qty": max(0.0, req + c_qty),  # c_qty is negative
            })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Initiated VAS Pick. Allocated {0} units in {1} row(s).").format(flt(created_qty), int(created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True,
        "message": msg,
        "created_rows": int(created_rows),
        "created_qty": flt(created_rows and created_qty or 0),  # negative sum (outbound)
        "lines": details,
        "skipped": skipped,
        "warnings": warnings,
    }


@frappe.whitelist()
def allocate_vas_putaway(warehouse_job: str):
    """
    VAS → Convert this job's *Orders* rows into *Items* rows (Putaway tasks) on the SAME job.
    - Runs only when job.type == "VAS"
    - Must be run BEFORE submission (docstatus == 0)
    - Applies the same destination policy as regular putaway (no staging)
    - handling_unit on Orders is the final HU
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Initiate VAS Putaway can only run for Warehouse Job Type = VAS."))
    if int(job.docstatus or 0) != 0:
        frappe.throw(_("Initiate VAS Putaway must be run before submission."))

    company, branch = _get_job_scope(job)

    jf = _safe_meta_fieldnames("Warehouse Job Item")
    has_uom        = "uom" in jf
    has_source_row = "source_row" in jf
    has_source_par = "source_parent" in jf
    has_location   = "location" in jf or "to_location" in jf
    dest_loc_field = "location" if "location" in jf else ("to_location" if "to_location" in jf else None)

    orders = _fetch_job_order_items(job.name)
    if not orders:
        return {"ok": True, "message": _("No items found on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    created_rows, created_qty = 0, 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if not has_location:
        warnings.append(_("Warehouse Job Item has no destination location field ('location' or 'to_location')."))

    candidate_cache: Dict[str, List[Dict[str, Any]]] = {}

    for r in orders:
        qty = abs(flt(r.get("quantity") or 0))
        if qty <= 0:
            continue

        item    = r.get("item")
        dest_hu = (r.get("handling_unit") or "").strip() or None

        # Choose destination location by policy
        dest_loc = None
        if item:
            if item not in candidate_cache:
                candidate_cache[item] = _putaway_candidate_locations(item=item, company=company, branch=branch)
            cands = candidate_cache[item]
            if cands:
                dest_loc = cands[0]["location"]

        # Enforce scope  # NEW
        _assert_hu_in_job_scope(dest_hu, company, branch, ctx=_("Handling Unit"))
        if dest_loc:
            _assert_location_in_job_scope(dest_loc, company, branch, ctx=_("Destination Location"))

        payload = {
            "item": item,
            "quantity": qty,  # putaway → positive
            "serial_no": r.get("serial_no") or None,
            "batch_no": r.get("batch_no") or None,
            "handling_unit": dest_hu,
        }
        if dest_loc_field:
            payload[dest_loc_field] = dest_loc
        if has_uom and r.get("uom"):
            payload["uom"] = r.get("uom")
        if has_source_row:
            payload["source_row"] = r.get("name")
        if has_source_par:
            payload["source_parent"] = job.name

        job.append("items", payload)
        created_rows += 1
        created_qty  += qty

        if not dest_loc:
            warnings.append(
                _("Order Row {0}: no destination location selected in scope; operator must scan destination.")
                .format(r.get("name"))
            )
        if not dest_hu:
            warnings.append(
                _("Order Row {0}: no handling unit provided; operator must supply a handling unit.")
                .format(r.get("name"))
            )

        details.append({"order_row": r.get("name"), "item": item, "qty": qty, "dest_location": dest_loc, "dest_handling_unit": dest_hu})

    job.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "ok": True,
        "message": _("Prepared {0} putaway item row(s) totaling {1}.").format(int(created_rows), flt(created_qty)),
        "created_rows": created_rows,
        "created_qty": created_qty,
        "lines": details,
        "warnings": warnings,
    }


# =============================================================================
# STOCKTAKE: Fetch Count Sheet (header + rows) for Warehouse Job
# =============================================================================

@frappe.whitelist()
def warehouse_job_fetch_count_sheet(warehouse_job: str, clear_existing: int = 1):
    """
    Build the Count Sheet (Warehouse Job -> counts) ONLY for items present on
    this Job's 'orders' table. Locations & Handling Units are filtered by the
    Job's Company/Branch scope. If blind_count is set on the Job, system_count
    is left blank (read-only field exists on the child).

    - Job.type must be 'Stocktake'
    - Optionally syncs header defaults from linked Stocktake Order
    - Creates rows from:
        (a) Ledger aggregates for in-scope items (location/hu/batch/serial)
        (b) Zero-stock placeholders for each in-scope Location and HU per item
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("Fetch Count Sheet is only available for Warehouse Job Type = Stocktake."))

    # ---- Items scope: ONLY items in Orders -------------------------------------------------
    order_items = frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job.name, "parenttype": "Warehouse Job"},
        fields=["distinct item AS item"],
        ignore_permissions=True,
    )
    item_list = [r["item"] for r in order_items if (r.get("item") or "").strip()]
    item_set = set(item_list)

    if not item_set:
        return {"ok": True, "message": _("No items found in Orders. Add items in the Orders table first."), "created_rows": 0}

    company, branch = _get_job_scope(job)

    # ---- Clear existing, if requested ------------------------------------------------------
    if int(clear_existing or 0):
        job.set("counts", [])

    # ---- Maybe sync header from Stocktake Order (safe fields only) -------------------------
    header = {
        "count_date": getattr(job, "count_date", None),
        "count_type": getattr(job, "count_type", None),
        "blind_count": int(getattr(job, "blind_count", 0) or 0),
        "qa_required": int(getattr(job, "qa_required", 0) or 0),
    }

    if (job.reference_order_type or "").strip() == "Stocktake Order" and getattr(job, "reference_order", None):
        so_meta = _safe_meta_fieldnames("Stocktake Order")
        desired = ["count_type", "blind_count", "qa_required", "count_date"]
        fields_to_fetch = [f for f in desired if f in so_meta]

        if fields_to_fetch:
            so = frappe.db.get_value(
                "Stocktake Order",
                job.reference_order,
                fields_to_fetch,
                as_dict=True,
            ) or {}
            for k in fields_to_fetch:
                v = so.get(k)
                if v not in (None, "") and not getattr(job, k, None):
                    setattr(job, k, v)
                    header[k] = v

    # ---- Meta: see which scope fields exist ------------------------------------------------
    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    conds = []
    params = []

    # Items IN (...)
    in_placeholders = ", ".join(["%s"] * len(item_set))
    params.extend(list(item_set))

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)):
        conds.append("COALESCE(hu.company, sl.company, l.company) = %s")
        params.append(company)
    if branch and (("branch" in slf) or ("branch" in huf) or ("branch" in llf)):
        conds.append("COALESCE(hu.branch, sl.branch, l.branch) = %s")
        params.append(branch)

    scope_sql = (" AND " + " AND ".join(conds)) if conds else ""

    # ---- (a) Ledger aggregates for these items in scope -----------------------------------
    sql = f"""
        SELECT
            l.item,
            l.storage_location,
            l.handling_unit,
            l.batch_no,
            l.serial_no,
            SUM(l.quantity) AS system_qty
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit
        WHERE l.item IN ({in_placeholders})
          {scope_sql}
        GROUP BY l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no
        HAVING SUM(l.quantity) > 0
    """
    aggregates = frappe.db.sql(sql, tuple(params), as_dict=True) or []

    # ---- (b) Zero-stock placeholders for each in-scope Location and HU --------------------
    loc_params = []
    loc_conds = []
    if company and ("company" in slf):
        loc_conds.append("sl.company = %s")
        loc_params.append(company)
    if branch and ("branch" in slf):
        loc_conds.append("sl.branch = %s")
        loc_params.append(branch)
    loc_where = ("WHERE " + " AND ".join(loc_conds)) if loc_conds else ""
    locations = frappe.db.sql(f"SELECT sl.name AS name FROM `tabStorage Location` sl {loc_where}", tuple(loc_params), as_dict=True) or []

    hu_params = []
    hu_conds = []
    if company and ("company" in huf):
        hu_conds.append("hu.company = %s")
        hu_params.append(company)
    if branch and ("branch" in huf):
        hu_conds.append("hu.branch = %s")
        hu_params.append(branch)
    hu_where = ("WHERE " + " AND ".join(hu_conds)) if hu_conds else ""
    hus = frappe.db.sql(f"SELECT hu.name AS name FROM `tabHandling Unit` hu {hu_where}", tuple(hu_params), as_dict=True) or []

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

    for a in aggregates:
        if a.get("item") not in item_set:
            continue
        _append_count_row(
            item=a.get("item"),
            location=a.get("storage_location"),
            handling_unit=a.get("handling_unit"),
            batch_no=a.get("batch_no"),
            serial_no=a.get("serial_no"),
            sys_qty=flt(a.get("system_qty") or 0),
        )

    for it in item_set:
        for loc in locations:
            _append_count_row(item=it, location=loc["name"], handling_unit=None, batch_no=None, serial_no=None, sys_qty=0)
        for hu in hus:
            _append_count_row(item=it, location=None, handling_unit=hu["name"], batch_no=None, serial_no=None, sys_qty=0)

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg_bits = [_("Created {0} count line(s).").format(created_rows)]
    if blind:
        msg_bits.append(_("Blind: system counts hidden"))
    if company:
        msg_bits.append(_("Company: {0}").format(company))
    if branch:
        msg_bits.append(_("Branch: {0}").format(branch))

    return {
        "ok": True,
        "message": " | ".join(msg_bits),
        "created_rows": created_rows,
        "header": {
            "count_date": getattr(job, "count_date", None),
            "count_type": getattr(job, "count_type", None),
            "blind_count": blind,
            "qa_required": int(getattr(job, "qa_required", 0) or 0),
        },
    }


# =============================================================================
# CREATE → JOB OPERATIONS from Warehouse Operation Item (used_in = job.type)
# =============================================================================

@frappe.whitelist()
def populate_job_operations(warehouse_job: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Fill the Warehouse Job's Operations table using Warehouse Operation Item,
    selecting rows where `used_in` equals the job's `type`. For VAS jobs, if
    `vas_order_type` is set on the job, prefer operations with the same VAS type
    while still including generic VAS operations (where vas_order_type is empty).

    Quantity defaults to the sum of quantities in this job's Orders table.
    Duplicate operations are skipped unless `clear_existing` is truthy.
    """
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))

    job = frappe.get_doc("Warehouse Job", warehouse_job)
    job_type = (job.type or "").strip()
    if not job_type:
        frappe.throw(_("Warehouse Job Type is required to create Job Operations."))

    # Find the actual child fieldname for "Warehouse Job Operations" (e.g. table_tncd)
    ops_field = _find_child_table_field("Warehouse Job", "Warehouse Job Operations")
    if not ops_field:
        frappe.throw(_("Warehouse Job has no Operations child table."))

    # Optionally clear existing rows
    if int(clear_existing or 0):
        job.set(ops_field, [])

    # Baseline quantity (sum of Orders)
    orders = _fetch_job_order_items(job.name)
    qty_baseline = sum([flt(o.get("quantity") or 0) for o in orders])

    # Build the operation list
    params: List[Any] = [job_type]
    sql = """
        SELECT
            name,
            operation_name,
            IFNULL(unit_std_hours, 0) AS unit_std_hours,
            handling_uom,
            notes
        FROM `tabWarehouse Operation Item`
        WHERE used_in = %s
    """
    if job_type == "VAS" and getattr(job, "vas_order_type", None):
        sql += " AND (vas_order_type = %s OR IFNULL(vas_order_type, '') = '')"
        params.append(job.vas_order_type)

    sql += " ORDER BY operation_name ASC"
    ops = frappe.db.sql(sql, tuple(params), as_dict=True) or []

    if not ops:
        return {
            "ok": True,
            "message": _("No Warehouse Operation Item found for type {0}.").format(job_type),
            "created_rows": 0,
            "qty_baseline": qty_baseline,
        }

    # Prepare dedupe set (if not cleared)
    existing_codes = set()
    for r in (getattr(job, ops_field) or []):
        code = getattr(r, "operation", None)
        if code:
            existing_codes.add(code)

    child_fields = _safe_meta_fieldnames("Warehouse Job Operations")
    has_desc   = "description" in child_fields
    has_notes  = "notes" in child_fields
    has_uom    = "handling_uom" in child_fields
    has_qty    = "quantity" in child_fields
    has_unitsh = "unit_std_hours" in child_fields
    has_totalh = "total_std_hours" in child_fields
    has_actual = "actual_hours" in child_fields

    created = 0
    for op in ops:
        code = op["name"]
        if code in existing_codes:
            continue

        unit_std = flt(op.get("unit_std_hours") or 0)
        qty = flt(qty_baseline or 0)

        payload: Dict[str, Any] = {"operation": code}
        if has_desc:
            payload["description"] = op.get("operation_name")
        if has_uom and op.get("handling_uom"):
            payload["handling_uom"] = op.get("handling_uom")
        if has_qty:
            payload["quantity"] = qty
        if has_unitsh:
            payload["unit_std_hours"] = unit_std
        if has_totalh:
            payload["total_std_hours"] = unit_std * qty
        if has_actual:
            payload["actual_hours"] = None
        if has_notes and op.get("notes"):
            payload["notes"] = op.get("notes")

        job.append(ops_field, payload)
        existing_codes.add(code)
        created += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "ok": True,
        "message": _("Added {0} operation(s).").format(created),
        "created_rows": created,
        "qty_baseline": qty_baseline,
        "ops_field": ops_field,
    }


# =============================================================================
# STOCKTAKE: Populate Adjustments (compare system_count vs actual_quantity)
# =============================================================================

@frappe.whitelist()
def populate_stocktake_adjustments(warehouse_job: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    For Warehouse Job (Type = Stocktake):
      For each row in 'counts', compute delta = actual_quantity - system_count.
      If delta != 0 and both values are present, append a row in 'items' with that quantity
      (positive = gain, negative = loss). Does not infer system quantities for blind rows.
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("This action is only available for Warehouse Job Type = Stocktake."))

    # Optionally clear existing 'items'
    if int(clear_existing or 0):
        job.set("items", [])

    item_fields = _safe_meta_fieldnames("Warehouse Job Item")
    has_uom        = "uom" in item_fields
    has_location   = "location" in item_fields
    has_handling   = "handling_unit" in item_fields
    has_source_row = "source_row" in item_fields
    has_source_par = "source_parent" in item_fields

    created = 0
    net_delta = 0.0

    for r in (job.counts or []):
        # both must be present to compute delta
        if (getattr(r, "actual_quantity", None) in (None, "")) or (getattr(r, "system_count", None) in (None, "")):
            continue

        actual = flt(getattr(r, "actual_quantity", 0))
        system = flt(getattr(r, "system_count", 0))
        delta = actual - system

        if delta == 0:
            continue

        payload: Dict[str, Any] = {
            "item": getattr(r, "item", None),
            "quantity": delta,
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        if has_location:
            payload["location"] = getattr(r, "location", None) or None
        if has_handling:
            payload["handling_unit"] = getattr(r, "handling_unit", None) or None
        if has_uom:
            payload["uom"] = _get_item_uom(payload["item"])
        if has_source_row:
            payload["source_row"] = f"COUNT:{getattr(r, 'name', '')}"
        if has_source_par:
            payload["source_parent"] = job.name

        job.append("items", payload)
        created += 1
        net_delta += delta

    job.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "ok": True,
        "message": _("Created {0} adjustment item(s). Net delta: {1}").format(int(created), flt(net_delta)),
        "created_rows": int(created),
        "net_delta": flt(net_delta),
    }


# =============================================================================
# Create Sales Invoice from Warehouse Job Charges
# =============================================================================

@frappe.whitelist()
def create_sales_invoice_from_job(
    warehouse_job: str,
    customer: Optional[str] = None,
    company: Optional[str] = None,
    posting_date: Optional[str] = None,
    cost_center: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a draft Sales Invoice from 'Warehouse Job Charges' on the Warehouse Job.

    Updates (Customer on Warehouse Job):
      - If `customer` param is not provided, use `job.customer`. If neither is present, raise.

    Rules:
      - Requires Customer and Company (passed-in or inferred from Job if fields exist).
      - All included charge rows must share the same currency (if a currency field exists on rows).
      - Maps fields:
          charge.item_code  -> si.items[].item_code
          charge.item_name  -> si.items[].item_name (if present)
          charge.uom        -> si.items[].uom (if present)
          charge.quantity   -> si.items[].qty (fallback to 1.0 if absent but total/rate > 0)
          charge.rate       -> si.items[].rate (if empty and qty>0, derive from total/qty)
          charge.total      -> only used to derive rate if needed
      - Links the SI back to the Job via a 'warehouse_job' field if present on SI,
        otherwise notes it in 'remarks'.
    """
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))

    job = frappe.get_doc("Warehouse Job", warehouse_job)

    # Child fieldname for charges
    charges_field = _find_child_table_field("Warehouse Job", "Warehouse Job Charges") or "charges"
    charges: List[Any] = list(getattr(job, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in {0}.").format(_("Warehouse Job Charges")))

    # Infer company / customer from job if available (customer newly added on Job)
    jf = _safe_meta_fieldnames("Warehouse Job")
    customer = customer or (getattr(job, "customer", None) if "customer" in jf else None)
    company  = company  or (getattr(job, "company",  None) if "company"  in jf else None)

    if not customer:
        frappe.throw(_("Customer is required (set Customer on Warehouse Job or pass it here)."))
    if not company:
        frappe.throw(_("Company is required."))

    # Ensure uniform currency across rows (when present)
    cf = _safe_meta_fieldnames("Warehouse Job Charges")
    row_has_currency = "currency" in cf
    row_has_rate     = "rate" in cf
    row_has_total    = "total" in cf
    row_has_uom      = "uom" in cf
    row_has_itemname = "item_name" in cf
    row_has_qty      = "quantity" in cf

    currencies = set()
    valid_rows: List[Dict[str, Any]] = []

    for ch in charges:
        item_code = getattr(ch, "item_code", None)
        if not item_code:
            continue

        qty   = flt(getattr(ch, "quantity", 0.0)) if row_has_qty else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if row_has_rate else 0.0
        total = flt(getattr(ch, "total", 0.0))    if row_has_total else 0.0
        uom   = (getattr(ch, "uom", None) or None) if row_has_uom else None
        item_name = (getattr(ch, "item_name", None) or None) if row_has_itemname else None
        curr  = (getattr(ch, "currency", None) or "").strip() if row_has_currency else ""

        if row_has_currency and curr:
            currencies.add(curr)

        # derive qty/rate sensibly
        if qty and not rate and total:
            rate = total / qty
        if (not qty or qty == 0) and total and not rate:
            qty, rate = 1.0, total  # one-liner charge

        # skip zero lines
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

    if row_has_currency:
        # Require a single currency across rows
        currencies = {c for c in currencies if c}
        if len(currencies) > 1:
            frappe.throw(_("All charge rows must have the same currency. Found: {0}").format(", ".join(sorted(currencies))))
        chosen_currency = (list(currencies)[0] if currencies else None)
    else:
        chosen_currency = None

    # Build Sales Invoice
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company = company
    if posting_date:
        si.posting_date = posting_date

    # Optional link back to Job
    sif = _safe_meta_fieldnames("Sales Invoice")
    if "warehouse_job" in sif:
        setattr(si, "warehouse_job", job.name)
    else:
        # fall back to remarks
        base_remarks = (getattr(si, "remarks", "") or "").strip()
        note = _("Auto-created from Warehouse Job {0}").format(job.name)
        si.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    # Currency if field exists and we detected one
    if chosen_currency and "currency" in sif:
        si.currency = chosen_currency  # ERPNext will handle conversions on validate

    # Append items
    sif_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    for r in valid_rows:
        row_payload = {
            "item_code": r["item_code"],
            "qty": r["qty"] or 0.0,
            "rate": r["rate"] or 0.0,
        }
        if "uom" in sif_item_fields and r.get("uom"):
            row_payload["uom"] = r["uom"]
        if "item_name" in sif_item_fields and r.get("item_name"):
            row_payload["item_name"] = r["item_name"]
        if cost_center and "cost_center" in sif_item_fields:
            row_payload["cost_center"] = cost_center

        si.append("items", row_payload)

    # Let standard validations compute taxes/totals
    si.flags.ignore_permissions = False
    si.insert()

    return {
        "ok": True,
        "message": _("Sales Invoice {0} created.").format(si.name),
        "sales_invoice": si.name,
    }

# --- Periodic Billing: Get Charges ----------------------------------------------------------
from datetime import date, timedelta
from frappe.utils import getdate

def _pb__charges_fieldname() -> Optional[str]:
    """Find the child table field on Periodic Billing that points to Periodic Billing Charges."""
    return _find_child_table_field("Periodic Billing", "Periodic Billing Charges")

def _pb__find_customer_contract(customer: Optional[str]) -> Optional[str]:
    """Pick a Warehouse Contract for the customer (docstatus 1 first, else draft)."""
    if not customer:
        return None
    wf = _safe_meta_fieldnames("Warehouse Contract")
    cond = {"docstatus": 1}
    if "customer" in wf:
        cond["customer"] = customer
    rows = frappe.get_all("Warehouse Contract", filters=cond, fields=["name"], limit=1, ignore_permissions=True)
    if rows:
        return rows[0]["name"]
    # fallback: any draft
    cond["docstatus"] = 0
    rows = frappe.get_all("Warehouse Contract", filters=cond, fields=["name"], limit=1, ignore_permissions=True)
    return rows[0]["name"] if rows else None

def _pb__get_storage_contract_item(contract: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return first storage charge line from Warehouse Contract Item."""
    if not contract:
        return None
    fields = ["item_charge AS item_code", "rate", "currency", "storage_uom", "time_uom"]
    rows = frappe.get_all(
        "Warehouse Contract Item",
        filters={"parent": contract, "parenttype": "Warehouse Contract", "storage_charge": 1},
        fields=fields,
        limit=1,
        ignore_permissions=True,
    )
    return rows[0] if rows else None

def _pb__distinct_hus_for_customer(customer: str, date_to: str) -> List[str]:
    """Return HUs used by this customer up to date_to, using schema-aware filters."""
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")
    wjf = _safe_meta_fieldnames("Warehouse Job")

    params: List[Any] = [date_to]
    joins: List[str] = []
    conds: List[str] = ["l.handling_unit IS NOT NULL", "l.posting_date <= %s"]

    if "customer" in llf:
        # Ledger itself carries customer -> easiest
        conds.append("l.customer = %s")
        params.append(customer)
    elif "customer" in huf:
        # Filter via HU master
        joins.append("LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit")
        conds.append("hu.customer = %s")
        params.append(customer)
    elif "customer" in wjf:
        # Fallback via job items -> jobs
        joins.append("LEFT JOIN `tabWarehouse Job Item` ji ON ji.handling_unit = l.handling_unit")
        joins.append("LEFT JOIN `tabWarehouse Job` j ON j.name = ji.parent")
        conds.append("j.customer = %s")
        params.append(customer)
    else:
        # Last resort: cannot filter by customer reliably; return all HUs seen before date_to
        pass

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
        (hu, date_from),
        as_dict=True,
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
        (hu, date_from, date_to),
        as_dict=True,
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

@frappe.whitelist()
def periodic_billing_get_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Populate Periodic Billing -> Periodic Billing Charges with:
      1) All Warehouse Job Charges for this customer, where job_open_date in [date_from .. date_to], docstatus=1
      2) Storage charges per Handling Unit (days used in period) priced from Warehouse Contract
    """
    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    customer = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to   = getattr(pb, "date_to", None)

    if not (customer and date_from and date_to):
        frappe.throw(_("Customer, Date From and Date To are required."))

    charges_field = _pb__charges_fieldname()
    if not charges_field:
        return {"ok": False, "message": _("Periodic Billing has no child table for 'Periodic Billing Charges'. Add one."), "created": 0}

    # Optionally clear existing rows
    if int(clear_existing or 0):
        pb.set(charges_field, [])

    warnings: List[str] = []
    created = 0
    grand_total = 0.0

    # ---- 1) Warehouse Job Charges in period ------------------------------------------------
    job_filters = {
        "docstatus": 1,
        "customer": customer,
        "job_open_date": ["between", [date_from, date_to]],
    }
    jobs = frappe.get_all(
        "Warehouse Job",
        filters=job_filters,
        fields=["name", "job_open_date"],
        order_by="job_open_date asc, name asc",
        ignore_permissions=True,
    ) or []

    if jobs:
        # Fetch child charges for all jobs in one go
        job_names = [j["name"] for j in jobs]
        placeholders = ", ".join(["%s"] * len(job_names))
        rows = frappe.db.sql(
            f"""
            SELECT c.parent AS warehouse_job, c.item_code, c.item_name, c.uom, c.quantity, c.rate, c.total, c.currency
            FROM `tabWarehouse Job Charges` c
            WHERE c.parent IN ({placeholders})
            ORDER BY FIELD(c.parent, {placeholders})
            """,
            tuple(job_names + job_names),
            as_dict=True,
        ) or []

        for r in rows:
            qty = flt(r.get("quantity") or 0.0)
            rate = flt(r.get("rate") or 0.0)
            total = flt(r.get("total") or (qty * rate))
            pb.append(charges_field, {
                "item": r.get("item_code"),
                "item_name": r.get("item_name"),
                "uom": r.get("uom"),
                "quantity": qty,
                "rate": rate,
                "total": total,
                "currency": r.get("currency"),
                "warehouse_job": r.get("warehouse_job"),
            })
            created += 1
            grand_total += total

    # ---- 2) Storage charges per HU ---------------------------------------------------------
    contract = _pb__find_customer_contract(customer)
    sci = _pb__get_storage_contract_item(contract)
    if not sci:
        warnings.append(_("No Warehouse Contract storage pricing found for this customer; storage charges skipped."))
    else:
        storage_item = sci.get("item_code")
        storage_rate = flt(sci.get("rate") or 0.0)
        storage_uom  = sci.get("storage_uom") or "Day"
        currency     = sci.get("currency")

        hu_list = _pb__distinct_hus_for_customer(customer, date_to)
        for hu in hu_list:
            days = _pb__count_used_days(hu, date_from, date_to)
            if days <= 0:
                continue
            total = flt(days) * storage_rate
            pb.append(charges_field, {
                "item": storage_item,
                "item_name": _("Storage Charge"),
                "uom": storage_uom,
                "quantity": days,
                "rate": storage_rate,
                "total": total,
                "currency": currency,
                "handling_unit": hu,
            })
            created += 1
            grand_total += total

    pb.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Added {0} charge line(s). Total: {1}").format(int(created), flt(grand_total))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True,
        "message": msg,
        "created": int(created),
        "grand_total": flt(grand_total),
        "warnings": warnings,
    }
    
@frappe.whitelist()
def create_sales_invoice_from_periodic_billing(
    periodic_billing: str,
    posting_date: Optional[str] = None,
    company: Optional[str] = None,
    cost_center: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Sales Invoice from Periodic Billing charges.

    - Uses Periodic Billing → Periodic Billing Charges as SI items.
    - Copies Customer from Periodic Billing.
    - Adds "Auto-created from Periodic Billing <name>" and "Period: <date_from> to <date_to>" to SI.remarks.
    - If `company` isn't passed, tries defaults; throws if still missing.
    """
    if not periodic_billing:
        frappe.throw(_("periodic_billing is required"))

    pb = frappe.get_doc("Periodic Billing", periodic_billing)

    # Required fields on PB
    customer  = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to   = getattr(pb, "date_to", None)
    if not customer:
        frappe.throw(_("Customer is required on Periodic Billing."))
    if not (date_from and date_to):
        frappe.throw(_("Date From and Date To are required on Periodic Billing."))

    # Find child table field that points to Periodic Billing Charges
    charges_field = _find_child_table_field("Periodic Billing", "Periodic Billing Charges")
    if not charges_field:
        frappe.throw(_("Periodic Billing has no child table for 'Periodic Billing Charges'."))

    charges = list(getattr(pb, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in Periodic Billing Charges."))

    # Resolve company if not provided
    company = company or frappe.defaults.get_default("company")
    if not company:
        frappe.throw(_("Company is required (pass it in, or set a Default Company)."))

    # Prepare SI
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company = company
    if posting_date:
        si.posting_date = posting_date

    # Optional link back (if SI has the field)
    sif = _safe_meta_fieldnames("Sales Invoice")
    if "periodic_billing" in sif:
        setattr(si, "periodic_billing", pb.name)

    # Remarks (append period)
    base_remarks = (getattr(si, "remarks", "") or "").strip()
    notes = [
        _("Auto-created from Periodic Billing {0}").format(pb.name),
        _("Period: {0} to {1}").format(date_from, date_to),
    ]
    si.remarks = (base_remarks + ("\n" if base_remarks else "") + "\n".join(notes)).strip()

    # Map child rows -> SI Items
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
            # skip lines without an item
            continue

        qty   = flt(getattr(ch, "quantity", 0.0)) if row_has_qty else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if row_has_rate else 0.0
        total = flt(getattr(ch, "total", 0.0))    if row_has_total else 0.0
        uom   = (getattr(ch, "uom", None) or None) if row_has_uom else None
        item_name = (getattr(ch, "item_name", None) or None) if row_has_itemname else None

        # derive qty/rate when needed
        if qty and not rate and total:
            rate = total / qty
        if (not qty or qty == 0) and total and not rate:
            qty, rate = 1.0, total  # one-liner charge

        # skip zero-value lines
        if not qty and not rate and not total:
            continue

        row_payload = {
            "item_code": item_code,
            "qty": qty or 0.0,
            "rate": rate or (total if (not qty and total) else 0.0),
        }
        if "uom" in sif_item_fields and uom:
            row_payload["uom"] = uom
        if "item_name" in sif_item_fields and item_name:
            row_payload["item_name"] = item_name
        if cost_center and "cost_center" in sif_item_fields:
            row_payload["cost_center"] = cost_center

        si.append("items", row_payload)
        created_rows += 1

    if created_rows == 0:
        frappe.throw(_("No valid Periodic Billing Charges to create Sales Invoice items."))

    # Standard validations will compute totals/taxes
    si.flags.ignore_permissions = False
    si.insert()

    return {
        "ok": True,
        "message": _("Sales Invoice {0} created.").format(si.name),
        "sales_invoice": si.name,
        "created_rows": created_rows,
    }


# =============================================================================
# Global validator (optional): ensure any manual entries stay in Job scope
# =============================================================================

def _validate_job_locations_in_scope(job: Any):
    """
    Optional: call from hooks.py on Warehouse Job validate to ensure any manually-entered
    Locations/Handling Units on Items/Orders/Counts are within the Job's Company/Branch.
    """
    company, branch = _get_job_scope(job)
    if not (company or branch):
        return

    # Items table
    for it in (job.items or []):
        loc = getattr(it, "location", None) or getattr(it, "to_location", None)
        hu  = getattr(it, "handling_unit", None)
        _assert_location_in_job_scope(loc, company, branch, ctx=_("Item Location"))
        _assert_hu_in_job_scope(hu, company, branch, ctx=_("Item Handling Unit"))

    # Orders table: From/To
    for orow in (job.orders or []):
        _assert_location_in_job_scope(getattr(orow, "storage_location_from", None), company, branch, ctx=_("From Location"))
        _assert_location_in_job_scope(getattr(orow, "storage_location_to", None),   company, branch, ctx=_("To Location"))
        _assert_hu_in_job_scope(getattr(orow, "handling_unit_from", None), company, branch, ctx=_("From Handling Unit"))
        _assert_hu_in_job_scope(getattr(orow, "handling_unit_to", None),   company, branch, ctx=_("To Handling Unit"))
