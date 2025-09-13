# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime
from frappe import _

# ---------------------------------------------------------------------------
# Meta helpers
# ---------------------------------------------------------------------------

def _safe_meta_fieldnames(doctype: str) -> set:
    meta = frappe.get_meta(doctype)
    out = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None)
        if not fn and isinstance(df, dict):
            fn = df.get("fieldname")
        if fn:
            out.add(fn)
    return out

# ---------------------------------------------------------------------------
# Scope helpers (Company / Branch)
# ---------------------------------------------------------------------------

def _get_job_scope(job) -> tuple[str | None, str | None]:
    jf = _safe_meta_fieldnames("Warehouse Job")
    company = getattr(job, "company", None) if "company" in jf else None
    branch  = getattr(job, "branch",  None) if "branch"  in jf else None
    return company or None, branch or None

def _get_location_scope(location: str | None) -> tuple[str | None, str | None]:
    if not location:
        return None, None
    lf = _safe_meta_fieldnames("Storage Location")
    fields = []
    if "company" in lf: fields.append("company")
    if "branch"  in lf: fields.append("branch")
    if not fields:
        return None, None
    row = frappe.db.get_value("Storage Location", location, fields, as_dict=True) or {}
    return row.get("company"), row.get("branch")

def _get_handling_unit_scope(hu: str | None) -> tuple[str | None, str | None]:
    if not hu:
        return None, None
    hf = _safe_meta_fieldnames("Handling Unit")
    fields = []
    if "company" in hf: fields.append("company")
    if "branch"  in hf: fields.append("branch")
    if not fields:
        return None, None
    row = frappe.db.get_value("Handling Unit", hu, fields, as_dict=True) or {}
    return row.get("company"), row.get("branch")

def _resolve_row_scope(job, ji) -> tuple[str | None, str | None]:
    """
    Resolve (company, branch) for the ledger row:
      1) From Warehouse Job (if present)
      2) Else from Storage Location
      3) Else from Handling Unit
    """
    comp, br = _get_job_scope(job)
    if comp or br:
        return comp, br
    comp, br = _get_location_scope(getattr(ji, "location", None))
    if comp or br:
        return comp, br
    return _get_handling_unit_scope(getattr(ji, "handling_unit", None))

# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def _get_last_qty(
    item: str,
    location: str,
    handling_unit: str | None = None,
    serial_no: str | None = None,
    batch_no: str | None = None,
    company: str | None = None,
    branch: str | None = None,
) -> float:
    """
    Return the last end_qty snapshot for this item+location(+HU/serial/batch),
    filtered by Company/Branch if those columns exist on the Ledger.
    """
    ledger_fields = _safe_meta_fieldnames("Warehouse Stock Ledger")

    conds = [
        "item = %(item)s",
        "storage_location = %(location)s",
        "IFNULL(handling_unit,'') = %(handling_unit)s",
        "IFNULL(serial_no,'') = %(serial_no)s",
        "IFNULL(batch_no,'') = %(batch_no)s",
    ]
    if "company" in ledger_fields and company:
        conds.append("company = %(company)s")
    if "branch" in ledger_fields and branch:
        conds.append("branch = %(branch)s")

    where_sql = " AND ".join(conds)
    params = {
        "item": item,
        "location": location,
        "handling_unit": handling_unit or "",
        "serial_no": serial_no or "",
        "batch_no": batch_no or "",
        "company": company,
        "branch": branch,
    }

    row = frappe.db.sql(
        f"""
        SELECT end_qty
        FROM `tabWarehouse Stock Ledger`
        WHERE {where_sql}
        ORDER BY posting_date DESC, creation DESC
        LIMIT 1
        """,
        params,
        as_dict=True,
    )
    return flt(row[0].end_qty) if row else 0.0

# ---------------------------------------------------------------------------
# Write helper
# ---------------------------------------------------------------------------

def _make_ledger_row(job, ji, delta_qty, beg_qty, end_qty, posting_dt):
    """Insert a Warehouse Stock Ledger movement row with Company/Branch when available."""
    ledger_fields = _safe_meta_fieldnames("Warehouse Stock Ledger")

    # Resolve row scope (job -> location -> HU)
    row_company, row_branch = _resolve_row_scope(job, ji)

    led = frappe.new_doc("Warehouse Stock Ledger")

    # Posting context
    led.posting_date  = posting_dt
    led.warehouse_job = job.name

    # Keys
    led.item             = ji.item
    led.storage_location = ji.location
    led.handling_unit    = getattr(ji, "handling_unit", None)
    led.serial_no        = getattr(ji, "serial_no", None)
    led.batch_no         = getattr(ji, "batch_no", None)

    # Scope (only set if fields exist on the Ledger)
    if "company" in ledger_fields:
        led.company = row_company
    if "branch" in ledger_fields:
        led.branch = row_branch

    # Quantities
    led.quantity     = delta_qty
    led.beg_quantity = beg_qty
    led.end_qty      = end_qty

    led.insert(ignore_permissions=True)

# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class WarehouseJob(Document):
    def on_submit(self):
        job_type = (getattr(self, "type", "") or "").strip()

        if not getattr(self, "items", None):
            frappe.throw(_("No items to post to the Warehouse Stock Ledger."))

        posting_dt = now_datetime()

        for ji in self.items:
            if not getattr(ji, "location", None):
                frappe.throw(_("Row #{0}: Location is required.").format(ji.idx))
            if not getattr(ji, "item", None):
                frappe.throw(_("Row #{0}: Item is required.").format(ji.idx))

            qty = flt(getattr(ji, "quantity", 0))

            if job_type in ("Putaway", "Pick"):
                if qty <= 0:
                    frappe.throw(_("Row #{0}: Quantity must be greater than zero for {1}.").format(ji.idx, job_type))
                sign  = 1 if job_type == "Putaway" else -1
                delta = sign * qty
            else:
                # Move / Others: accept signed quantities (negative for source, positive for destination)
                if qty == 0:
                    frappe.throw(_("Row #{0}: Quantity cannot be zero.").format(ji.idx))
                delta = qty

            # Scope for snapshot (company/branch)
            row_company, row_branch = _resolve_row_scope(self, ji)

            beg = _get_last_qty(
                item=ji.item,
                location=ji.location,
                handling_unit=getattr(ji, "handling_unit", None),
                serial_no=getattr(ji, "serial_no", None),
                batch_no=getattr(ji, "batch_no", None),
                company=row_company,
                branch=row_branch,
            )
            end = beg + delta

            # Prevent negative ending balances when outbound
            if end < 0:
                frappe.throw(
                    _(
                        "Row #{idx}: Insufficient stock to move/pick {qty}. "
                        "Beginning qty: {beg}, would end at {end}."
                    ).format(idx=ji.idx, qty=abs(delta), beg=beg, end=end)
                )

            _make_ledger_row(self, ji, delta, beg, end, posting_dt)
