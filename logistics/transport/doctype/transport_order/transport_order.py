# apps/logistics/logistics/transport/doctype/transport_order/transport_order.py

import frappe
from frappe import _
from frappe.model.document import Document
from typing import List, Dict, Any, Optional

# make these two lines exactly this:
ORDER_LEGS_FIELDNAME_FALLBACKS = ["legs"]
JOB_LEGS_FIELDNAME_FALLBACKS   = ["legs"]



class TransportOrder(Document):
    def validate(self):
        """If the Transport Template changes, clear the Leg Plan table."""
        try:
            if self.has_value_changed("transport_template"):
                legs_field = _find_child_table_fieldname("Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS)
                self.set(legs_field, [])
        except Exception:
            old = getattr(self, "_doc_before_save", None) or self.get_doc_before_save()
            if old and getattr(old, "transport_template", None) != getattr(self, "transport_template", None):
                legs_field = _find_child_table_fieldname("Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS)
                self.set(legs_field, [])


# -------------------------
# Internal helpers (server)
# -------------------------

def _find_child_table_fieldname(parent_dt: str, child_dt: str, fallbacks: Optional[List[str]] = None) -> str:
    """
    Find the fieldname on `parent_dt` that is a Table pointing to `child_dt`.
    Falls back to common guesses. Throws a helpful error if not found.
    """
    meta = frappe.get_meta(parent_dt)
    for df in meta.fields:
        if df.fieldtype == "Table" and (df.options or "").strip() == child_dt:
            return df.fieldname

    # Try fallbacks
    for guess in (fallbacks or []):
        if meta.has_field(guess):
            df = meta.get_field(guess)
            if getattr(df, "fieldtype", None) == "Table":
                return guess

    # Build a useful message
    table_fields = [f"{df.fieldname} -> {df.options}" for df in meta.fields if df.fieldtype == "Table"]
    frappe.throw(
        _(
            "Could not find a child Table field on {parent} that points to {child}. "
            "Table fields found: {found}"
        ).format(parent=parent_dt, child=child_dt, found=", ".join(table_fields))
    )


def _fetch_template_legs(template_name: str) -> List[Dict[str, Any]]:
    """
    Pull ordered legs from Transport Template's child table: Transport Template Leg.
    Includes fields only if they exist (so you can evolve the template safely).
    """
    if not template_name:
        frappe.throw("Please select a Transport Template first.")

    meta = frappe.get_meta("Transport Template Leg")

    candidate_fields = [
        "facility_type_from",
        "facility_from",
        "pick_mode",
        "facility_type_to",
        "facility_to",
        "drop_mode",
    ]

    fields = ["name", "idx"]
    for f in candidate_fields:
        if meta.has_field(f):
            fields.append(f)

    rows = frappe.get_all(
        "Transport Template Leg",
        filters={"parent": template_name, "parenttype": "Transport Template"},
        fields=fields,
        order_by="idx asc",
    )
    return rows or []


def _apply_legs_to_order(doc: "TransportOrder", template_rows: List[Dict[str, Any]], replace: bool = True) -> int:
    """
    Write rows into the Transport Order's child table.
    Copies any of the known leg fields present in the template rows.
    """
    order_legs_field = _find_child_table_fieldname("Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS)

    if replace:
        doc.set(order_legs_field, [])

    for r in template_rows:
        child = doc.append(order_legs_field, {})
        for f in (
            "facility_type_from",
            "facility_from",
            "pick_mode",
            "facility_type_to",
            "facility_to",
            "drop_mode",
        ):
            if f in r:
                setattr(child, f, r.get(f))

    return len(template_rows)


# ---------------------------------
# Whitelisted server-side “actions”
# ---------------------------------

@frappe.whitelist()
def action_get_leg_plan(docname: str, replace: int = 1, save: int = 1) -> Dict[str, Any]:
    """
    Populate Transport Order's Leg Plan from its Transport Template.
    """
    if not docname:
        frappe.throw("Missing Transport Order name.")

    doc = frappe.get_doc("Transport Order", docname)
    template = getattr(doc, "transport_template", None)
    if not template:
        frappe.throw("Please select a Transport Template in the Transport Order first.")

    rows = _fetch_template_legs(template)
    order_legs_field = _find_child_table_fieldname("Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS)
    cleared = len(getattr(doc, order_legs_field, []) or []) if int(replace) else 0
    added = _apply_legs_to_order(doc, rows, replace=bool(int(replace)))

    if int(save):
        doc.save(ignore_permissions=True)

    return {
        "template": template,
        "added": int(added),
        "cleared": int(cleared if int(replace) else 0),
        "docname": docname,
    }


# -------------------------------------------------------------------
# ACTION: Create Transport Job from a submitted Transport Order
# -------------------------------------------------------------------

@frappe.whitelist()
def action_create_transport_job(docname: str):
    """Create (or reuse) a Transport Job from a submitted Transport Order."""
    try:
        doc = frappe.get_doc('Transport Order', docname)

        if doc.docstatus != 1:
            frappe.throw(_('Please submit the Transport Order before creating a Transport Job.'))

        # Reuse if already created
        existing = frappe.db.get_value('Transport Job', {'transport_order': doc.name}, 'name')
        if existing:
            return {'name': existing, 'created': False, 'already_exists': True}

        job = frappe.new_doc('Transport Job')
        job_meta = frappe.get_meta(job.doctype)

        # ---- Header field mapping (TO -> TJ)
        header_map = {
            'transport_order': doc.name,
            'transport_template': getattr(doc, 'transport_template', None),
            'customer': getattr(doc, 'customer', None),
            'booking_date': getattr(doc, 'booking_date', None),
            'customer_ref_no': getattr(doc, 'customer_ref_no', None),
            'hazardous': getattr(doc, 'hazardous', None),
            'refrigeration': getattr(doc, 'refrigeration', None),
            'vehicle_type': getattr(doc, 'vehicle_type', None),
        }
        for k, v in header_map.items():
            if v is not None and job_meta.has_field(k):
                job.set(k, v)

        # ---- Packages (TO -> TJ) by common fields
        _copy_child_rows_by_common_fields(
            src_doc=doc, src_table_field='packages',
            dst_doc=job, dst_table_field='packages'
        )

        # ---- Charges (TO -> TJ) by common fields
        _copy_child_rows_by_common_fields(
            src_doc=doc, src_table_field='charges',
            dst_doc=job, dst_table_field='charges'
        )

        # Insert now to get a real job name for back-references from Transport Leg
        job.insert(ignore_permissions=False)

        # ---- Legs: create top-level Transport Leg for each TO leg, then link into TJ legs
        order_legs_field = _find_child_table_fieldname("Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS)
        job_legs_field   = _find_child_table_fieldname("Transport Job",   "Transport Job Legs",   JOB_LEGS_FIELDNAME_FALLBACKS)

        _create_and_attach_job_legs_from_order_legs(
            order_doc=doc,
            job_doc=job,
            order_legs_field=order_legs_field,
            job_legs_field=job_legs_field
        )

        # Save added legs to job
        job.save(ignore_permissions=False)
        frappe.db.commit()
        return {'name': job.name, 'created': True, 'already_exists': False}

    except Exception:
        frappe.log_error(title='Create Transport Job failed', message=frappe.get_traceback())
        raise


# =========================
# Helpers
# =========================

def _copy_child_rows_by_common_fields(src_doc: Document, src_table_field: str,
                                      dst_doc: Document, dst_table_field: str):
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

    excluded_types = {'Section Break', 'Column Break', 'Tab Break', 'Table', 'Table MultiSelect'}
    excluded_names = {
        'name', 'owner', 'modified_by', 'creation', 'modified',
        'parent', 'parentfield', 'parenttype', 'idx', 'docstatus'
    }
    dst_fields = {
        df.fieldname for df in dst_child_meta.fields
        if df.fieldtype not in excluded_types and df.fieldname not in excluded_names
    }

    for s in src_rows:
        s_dict = s.as_dict()
        new_row = {fn: s_dict.get(fn) for fn in dst_fields if fn in s_dict}
        dst_doc.append(dst_table_field, new_row)


def _create_and_attach_job_legs_from_order_legs(order_doc: Document, job_doc: Document,
                                                order_legs_field: str, job_legs_field: str):
    """
    Create Transport Leg docs from Transport Order Legs and attach them to Transport Job Legs.

    Copies these fields when available on the order leg:
      facility_type_from, facility_from, pick_mode,
      facility_type_to,   facility_to,   drop_mode

    Also sets Transport Job reference on each created Transport Leg.
    """
    order_legs = order_doc.get(order_legs_field) or []
    if not order_legs:
        return

    for ol in order_legs:
        # Create top-level Transport Leg
        leg = frappe.new_doc('Transport Leg')
        _safe_set(leg, 'transport_job',     job_doc.name)  # back-reference to the Job

        _safe_set(leg, 'facility_type_from', getattr(ol, 'facility_type_from', None))
        _safe_set(leg, 'facility_from',       getattr(ol, 'facility_from', None))
        _safe_set(leg, 'pick_mode',           getattr(ol, 'pick_mode', None))

        _safe_set(leg, 'facility_type_to',    getattr(ol, 'facility_type_to', None))
        _safe_set(leg, 'facility_to',         getattr(ol, 'facility_to', None))
        _safe_set(leg, 'drop_mode',           getattr(ol, 'drop_mode', None))

        leg.insert(ignore_permissions=False)

        # Link into Transport Job Legs child table (denormalized snapshot for quick view/filter)
        job_doc.append(job_legs_field, {
            'transport_leg':       leg.name,
            'facility_type_from':  getattr(ol, 'facility_type_from', None),
            'facility_from':       getattr(ol, 'facility_from', None),
            'pick_mode':           getattr(ol, 'pick_mode', None),
            'facility_type_to':    getattr(ol, 'facility_type_to', None),
            'facility_to':         getattr(ol, 'facility_to', None),
            'drop_mode':           getattr(ol, 'drop_mode', None),
        })


def _safe_set(doc: Document, fieldname: str, value):
    """Set a value only if the field exists on the document."""
    if value is None:
        return
    meta = frappe.get_meta(doc.doctype)
    if meta.has_field(fieldname):
        doc.set(fieldname, value)
