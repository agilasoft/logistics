# apps/logistics/logistics/transport/doctype/transport_order/transport_order.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate

# keep these exactly as requested
ORDER_LEGS_FIELDNAME_FALLBACKS = ["legs"]
JOB_LEGS_FIELDNAME_FALLBACKS = ["legs"]


class TransportOrder(Document):
    def validate(self):
        """If the Transport Template changes, clear the Leg Plan table."""
        try:
            if self.has_value_changed("transport_template"):
                legs_field = _find_child_table_fieldname(
                    "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                )
                self.set(legs_field, [])
        except Exception:
            old = getattr(self, "_doc_before_save", None) or self.get_doc_before_save()
            if old and getattr(old, "transport_template", None) != getattr(self, "transport_template", None):
                legs_field = _find_child_table_fieldname(
                    "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                )
                self.set(legs_field, [])


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------
def _find_child_table_fieldname(parent_dt: str, child_dt: str, fallbacks: Optional[List[str]] = None) -> str:
    """Find the Table field on parent_dt that points to child_dt, else try fallbacks."""
    meta = frappe.get_meta(parent_dt)
    for df in meta.fields:
        if df.fieldtype == "Table" and (df.options or "").strip() == child_dt:
            return df.fieldname

    for guess in (fallbacks or []):
        if meta.has_field(guess):
            df = meta.get_field(guess)
            if getattr(df, "fieldtype", None) == "Table":
                return guess

    table_fields = [f"{df.fieldname} -> {df.options}" for df in meta.fields if df.fieldtype == "Table"]
    frappe.throw(
        _(
            "Could not find a child Table field on {parent} that points to {child}. "
            "Table fields found: {found}"
        ).format(parent=parent_dt, child=child_dt, found=", ".join(table_fields))
    )


def _get_template_child_dt() -> Tuple[str, str]:
    """Return (child_doctype, fieldname_on_template) for Transport Template."""
    meta = frappe.get_meta("Transport Template")
    for df in meta.fields:
        if df.fieldtype == "Table" and df.options:
            return df.options, df.fieldname
    # sensible default
    return "Transport Template Leg", "legs"


def _has_field(doctype: str, fieldname: str) -> bool:
    try:
        return frappe.get_meta(doctype).has_field(fieldname)
    except Exception:
        return False


def _coalesce(obj: Any, names: List[str], default=None):
    """Return first non-None attribute/key from names on obj."""
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v is not None:
                return v
        if isinstance(obj, dict) and n in obj:
            v = obj.get(n)
            if v is not None:
                return v
    return default


def _fetch_template_legs(template_name: str) -> List[Dict[str, Any]]:
    """
    Pull ordered legs from Transport Template's child table.
    Only includes fields that exist on the child doctype to keep it schema-safe.
    """
    if not template_name:
        frappe.throw("Please select a Transport Template first.")

    child_dt, _child_field = _get_template_child_dt()
    child_meta = frappe.get_meta(child_dt)

    # fields we commonly expect on a template leg
    candidates = [
        "facility_type_from",
        "facility_from",
        "pick_mode",
        "pick_address",
        "facility_type_to",
        "facility_to",
        "drop_mode",
        "drop_address",
        "vehicle_type",
        "transport_job_type",
        # for scheduling:
        "day_offset",
        "offset_days",
        "days_offset",
    ]

    fields = ["name", "idx"]
    for f in candidates:
        if child_meta.has_field(f):
            fields.append(f)

    rows = frappe.get_all(
        child_dt,
        filters={"parent": template_name, "parenttype": "Transport Template"},
        fields=fields,
        order_by="idx asc",
    )
    return rows or []


def _map_template_row_to_order_row(order_child_dt: str, tmpl_row: Dict[str, Any], base_date) -> Dict[str, Any]:
    """
    Map template leg fields onto Transport Order Legs row (only for fields that exist on the child doctype).
    Computes scheduled_date using day_offset when possible.
    """
    out: Dict[str, Any] = {}

    def set_if(field: str, value):
        if _has_field(order_child_dt, field):
            out[field] = value

    # copy common fields
    set_if("facility_type_from", _coalesce(tmpl_row, ["facility_type_from", "from_type"]))
    set_if("facility_from", _coalesce(tmpl_row, ["facility_from", "from_name"]))
    set_if("pick_mode", _coalesce(tmpl_row, ["pick_mode"]))
    set_if("pick_address", _coalesce(tmpl_row, ["pick_address"]))

    set_if("facility_type_to", _coalesce(tmpl_row, ["facility_type_to", "to_type"]))
    set_if("facility_to", _coalesce(tmpl_row, ["facility_to", "to_name"]))
    set_if("drop_mode", _coalesce(tmpl_row, ["drop_mode"]))
    set_if("drop_address", _coalesce(tmpl_row, ["drop_address"]))

    set_if("vehicle_type", _coalesce(tmpl_row, ["vehicle_type", "vt"]))
    set_if("transport_job_type", _coalesce(tmpl_row, ["transport_job_type", "job_type"]))
    set_if("priority", _coalesce(tmpl_row, ["priority"]))

    # day offset → scheduled_date
    raw_off = _coalesce(tmpl_row, ["day_offset", "offset_days", "days_offset"], 0)
    try:
        offset = cint(raw_off or 0)
    except Exception:
        offset = 0
    if base_date and _has_field(order_child_dt, "scheduled_date"):
        try:
            set_if("scheduled_date", add_days(base_date, offset))
        except Exception:
            set_if("scheduled_date", base_date)

    # keep the offset if child table has a field for it
    set_if("day_offset", offset)

    return out


# -------------------------------------------------------------------
# Whitelisted actions
# -------------------------------------------------------------------
@frappe.whitelist()
def action_get_leg_plan(docname: str, replace: int = 1, save: int = 1):
    """Populate Transport Order legs from the selected Transport Template."""
    if not docname:
        frappe.throw("Missing Transport Order name.")

    doc = frappe.get_doc("Transport Order", docname)

    # discover order child table dt/field
    order_child_dt = "Transport Order Legs"
    order_child_field = _find_child_table_fieldname(
        "Transport Order", order_child_dt, ORDER_LEGS_FIELDNAME_FALLBACKS
    )

    template_name = _coalesce(doc, ["transport_template", "template", "template_name"])
    if not template_name:
        frappe.throw("Please choose a Transport Template on this order first.")

    template_rows = _fetch_template_legs(template_name)
    if not template_rows:
        frappe.throw(f"No legs found in template: {frappe.bold(template_name)}")

    base_date = None
    if getattr(doc, "scheduled_date", None):
        try:
            base_date = getdate(doc.scheduled_date)
        except Exception:
            base_date = None

    if cint(replace):
        doc.set(order_child_field, [])

    created = 0
    for tr in template_rows:
        row_data = _map_template_row_to_order_row(order_child_dt, tr, base_date)
        if not row_data:
            continue
        doc.append(order_child_field, row_data)
        created += 1

    if cint(save):
        doc.flags.ignore_permissions = True
        doc.save()

    # --- build UI message safely ---
    base_label = frappe.utils.formatdate(base_date) if base_date else "—"
    mode_label = "Replace" if cint(replace) else "Append"

    html = f"""
        <div>
            <div style="font-weight:600;margin-bottom:6px;">
                {_('Template')}: {frappe.utils.escape_html(template_name)}
            </div>
            <ul style="margin:0 0 8px 16px;padding:0;">
                <li>{_('Base date')}: {base_label}</li>
                <li>{_('Legs added')}: <b>{created}</b></li>
                <li>{_('Mode')}: {mode_label}</li>
            </ul>
        </div>
    """
    frappe.msgprint(html, title=_("Leg plan created"), indicator="green")

    return {
        "ok": True,
        "order": docname,
        "template": template_name,
        "base_date": str(base_date) if base_date else None,
        "legs_added": created,
        "replaced": bool(cint(replace)),
        "saved": bool(cint(save)),
    }

# -------------------------------------------------------------------
# ACTION: Create Transport Job from a submitted Transport Order
# -------------------------------------------------------------------
@frappe.whitelist()
def action_create_transport_job(docname: str):
    """Create (or reuse) a Transport Job from a submitted Transport Order."""
    try:
        doc = frappe.get_doc("Transport Order", docname)

        if doc.docstatus != 1:
            frappe.throw(_("Please submit the Transport Order before creating a Transport Job."))

        # Reuse if already created
        existing = frappe.db.get_value("Transport Job", {"transport_order": doc.name}, "name")
        if existing:
            return {"name": existing, "created": False, "already_exists": True}

        job = frappe.new_doc("Transport Job")
        job_meta = frappe.get_meta(job.doctype)

        # ---- Header field mapping (TO -> TJ)
        header_map = {
            "transport_order": doc.name,
            "transport_template": getattr(doc, "transport_template", None),
            "customer": getattr(doc, "customer", None),
            "booking_date": getattr(doc, "booking_date", None),
            "customer_ref_no": getattr(doc, "customer_ref_no", None),
            "hazardous": getattr(doc, "hazardous", None),
            "refrigeration": getattr(doc, "refrigeration", None),
            "vehicle_type": getattr(doc, "vehicle_type", None),
            "load_type": getattr(doc, "load_type", None),
            "pick_address": getattr(doc, "pick_address", None),
            "drop_address": getattr(doc, "drop_address", None),
            "company": getattr(doc, "company", None),
            "branch": getattr(doc, "branch", None),
        }
        for k, v in header_map.items():
            if v is not None and job_meta.has_field(k):
                job.set(k, v)

        # ---- Packages (TO -> TJ) by common fields
        _copy_child_rows_by_common_fields(
            src_doc=doc, src_table_field="packages", dst_doc=job, dst_table_field="packages"
        )

        # ---- Charges (TO -> TJ) by common fields
        _copy_child_rows_by_common_fields(
            src_doc=doc, src_table_field="charges", dst_doc=job, dst_table_field="charges"
        )

        # Insert now to get a real job name for back-references from Transport Leg
        job.insert(ignore_permissions=False)

        # ---- Legs: create top-level Transport Leg for each TO leg, then link into TJ legs
        order_legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        job_legs_field = _find_child_table_fieldname(
            "Transport Job", "Transport Job Legs", JOB_LEGS_FIELDNAME_FALLBACKS
        )

        _create_and_attach_job_legs_from_order_legs(
            order_doc=doc,
            job_doc=job,
            order_legs_field=order_legs_field,
            job_legs_field=job_legs_field,
        )

        # Save added legs to job
        job.save(ignore_permissions=False)
        frappe.db.commit()
        return {"name": job.name, "created": True, "already_exists": False}

    except Exception:
        frappe.log_error(title="Create Transport Job failed", message=frappe.get_traceback())
        raise


# =========================
# Copy/link helpers
# =========================
def _copy_child_rows_by_common_fields(src_doc: Document, src_table_field: str, dst_doc: Document, dst_table_field: str):
    """Copy child rows from src to dst, matching by common fieldnames only."""
    src_rows = src_doc.get(src_table_field) or []
    if not src_rows:
        return

    dst_parent_meta = frappe.get_meta(dst_doc.doctype)
    dst_tbl_df = dst_parent_meta.get_field(dst_table_field)
    if not dst_tbl_df or not dst_tbl_df.options:
        return

    dst_child_dt = dst_tbl_df.options
    dst_child_meta = frappe.get_meta(dst_child_dt)

    excluded_types = {"Section Break", "Column Break", "Tab Break", "Table", "Table MultiSelect"}
    excluded_names = {
        "name",
        "owner",
        "modified_by",
        "creation",
        "modified",
        "parent",
        "parentfield",
        "parenttype",
        "idx",
        "docstatus",
    }
    dst_fields = {
        df.fieldname
        for df in dst_child_meta.fields
        if df.fieldtype not in excluded_types and df.fieldname not in excluded_names
    }

    for s in src_rows:
        s_dict = s.as_dict()
        new_row = {fn: s_dict.get(fn) for fn in dst_fields if fn in s_dict}
        dst_doc.append(dst_table_field, new_row)


def _create_and_attach_job_legs_from_order_legs(
    order_doc: Document, job_doc: Document, order_legs_field: str, job_legs_field: str
):
    """
    Create Transport Leg docs from Transport Order Legs and attach them to Transport Job Legs.

    Copies these fields when available on the order leg:
      facility_type_from, facility_from, pick_mode, pick_address,
      facility_type_to,   facility_to,   drop_mode, drop_address

    Also sets Transport Job reference on each created Transport Leg.
    """
    order_legs = order_doc.get(order_legs_field) or []
    if not order_legs:
        return

    for ol in order_legs:
        # Create top-level Transport Leg
        leg = frappe.new_doc("Transport Leg")
        _safe_set(leg, "transport_job", job_doc.name)  # back-reference to the Job
        _safe_set(leg, "date", order_doc.scheduled_date)  # back-reference to the Job

        _safe_set(leg, "facility_type_from", getattr(ol, "facility_type_from", None))
        _safe_set(leg, "facility_from", getattr(ol, "facility_from", None))
        _safe_set(leg, "pick_mode", getattr(ol, "pick_mode", None))
        _safe_set(leg, "pick_address", getattr(ol, "pick_address", None))

        _safe_set(leg, "facility_type_to", getattr(ol, "facility_type_to", None))
        _safe_set(leg, "facility_to", getattr(ol, "facility_to", None))
        _safe_set(leg, "drop_mode", getattr(ol, "drop_mode", None))
        _safe_set(leg, "drop_address", getattr(ol, "drop_address", None))

        leg.insert(ignore_permissions=False)

        # Link into Transport Job Legs child table (denormalized snapshot for quick view/filter)
        job_doc.append(
            job_legs_field,
            {
                "transport_leg": leg.name,
                "facility_type_from": getattr(ol, "facility_type_from", None),
                "facility_from": getattr(ol, "facility_from", None),
                "pick_mode": getattr(ol, "pick_mode", None),
                "pick_address": getattr(ol, "pick_address", None),
                "facility_type_to": getattr(ol, "facility_type_to", None),
                "facility_to": getattr(ol, "facility_to", None),
                "drop_mode": getattr(ol, "drop_mode", None),
                "drop_address": getattr(ol, "drop_address", None),
            },
        )


def _safe_set(doc: Document, fieldname: str, value):
    """Set a value only if the field exists on the document."""
    if value is None:
        return
    meta = frappe.get_meta(doc.doctype)
    if meta.has_field(fieldname):
        doc.set(fieldname, value)
