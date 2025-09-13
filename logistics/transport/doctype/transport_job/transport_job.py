# -*- coding: utf-8 -*-
# Copyright (c) 2021, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from typing import Dict, Any, List, Optional
from frappe.utils import nowdate

class TransportJob(Document):
    pass

ACTIVE_RUNSHEET_STATUSES = ("Planned", "Dispatched", "In Progress")  # consider these “active”


# --------------------------------------------------------------------
# Helpers to discover child-table fieldnames dynamically & safe-setting
# --------------------------------------------------------------------

def _get_table_field_for(parent_dt: str, child_dt: str) -> Optional[str]:
    """Find the fieldname of a Table field on parent_dt that points to child_dt."""
    meta = frappe.get_meta(parent_dt)
    for df in meta.fields:
        if df.fieldtype == "Table" and df.options == child_dt:
            return df.fieldname
    return None

def _has_field(dt: str, fieldname: str) -> bool:
    return frappe.get_meta(dt).has_field(fieldname)

def _safe_set(doc: Document, fieldname: str, value):
    if value is None:
        return
    if _has_field(doc.doctype, fieldname):
        doc.set(fieldname, value)

def _pluck_names(rows: List[Dict[str, Any]]) -> List[str]:
    return [r.get("name") for r in rows if r.get("name")]

def _get_job_legs_fieldname(job: Document) -> str:
    """
    Prefer 'legs' if present; else find the table pointing to 'Transport Job Legs'.
    """
    meta = frappe.get_meta(job.doctype)
    if meta.has_field("legs"):
        df = meta.get_field("legs")
        if getattr(df, "fieldtype", None) == "Table":
            return "legs"
    # Fallback by options
    fieldname = _get_table_field_for(job.doctype, "Transport Job Legs")
    if fieldname:
        return fieldname
    frappe.throw("Cannot locate the Transport Job legs table on this document.")
    return "legs"  # not reached

def _get_runsheet_legs_fieldname(rs: Document) -> str:
    meta = frappe.get_meta(rs.doctype)
    if meta.has_field("legs"):
        df = meta.get_field("legs")
        if getattr(df, "fieldtype", None) == "Table":
            return "legs"
    # fallback by options name if your child dt is named 'Run Sheet Leg'
    fieldname = _get_table_field_for(rs.doctype, "Run Sheet Leg")
    if fieldname:
        return fieldname
    frappe.throw("Cannot locate the Run Sheet legs table on this document.")
    return "legs"

def _get_runsheet_child_dt(rs: Document) -> str:
    fld = _get_runsheet_legs_fieldname(rs)
    df = frappe.get_meta(rs.doctype).get_field(fld)
    return df.options


# ------------------------------------------------
# Public: vehicles lookup & run sheet creation API
# ------------------------------------------------

@frappe.whitelist()
def get_available_vehicles(jobname: Optional[str] = None) -> Dict[str, Any]:
    """
    Return vehicles not assigned to an active Run Sheet.
    If the Vehicle doctype has a 'vehicle_type' field and the job has one, filter by it.
    """
    vt_filter = None
    if jobname:
        try:
            job = frappe.get_doc("Transport Job", jobname)
            vt = getattr(job, "vehicle_type", None)
            if vt and _has_field("Vehicle", "vehicle_type"):
                vt_filter = vt
        except Exception:
            pass

    # vehicles used in active run sheets
    active_vehicles = frappe.get_all(
        "Run Sheet",
        filters={"status": ["in", list(ACTIVE_RUNSHEET_STATUSES)], "vehicle": ["is", "set"]},
        pluck="vehicle",
        distinct=True,
        limit=500,
    )
    active_vehicles = set(active_vehicles or [])

    v_filters: Dict[str, Any] = {}
    if vt_filter:
        v_filters["vehicle_type"] = vt_filter

    vehicles = frappe.get_all("Vehicle", filters=v_filters, fields=["name", "license_plate", "vehicle_type"], limit=200)
    free = [v for v in vehicles if v["name"] not in active_vehicles]

    return {"vehicles": free}


@frappe.whitelist()
def action_create_run_sheet(jobname: str, vehicle: Optional[str] = None, driver: Optional[str] = None,
                            transport_company: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a Run Sheet for a submitted Transport Job, and pull its legs in.
    If `vehicle` is provided, ensure it isn't currently on an active run sheet.
    """
    if not jobname:
        frappe.throw(_("Missing Transport Job name."))

    job = frappe.get_doc("Transport Job", jobname)
    if job.docstatus != 1:
        frappe.throw(_("Please submit the Transport Job first."))

    # Validate chosen vehicle availability (if provided)
    if vehicle:
        exists = frappe.db.exists("Run Sheet", {
            "vehicle": vehicle,
            "status": ["in", list(ACTIVE_RUNSHEET_STATUSES)]
        })
        if exists:
            frappe.throw(_("Selected vehicle is already assigned to an active Run Sheet ({0}).").format(exists))

    # Create Run Sheet (Draft)
    rs = frappe.new_doc("Run Sheet")
    _safe_set(rs, "run_date", nowdate())
    _safe_set(rs, "vehicle_type", getattr(job, "vehicle_type", None))
    _safe_set(rs, "vehicle", vehicle or getattr(job, "vehicle", None))
    _safe_set(rs, "driver", driver or getattr(job, "driver", None))
    _safe_set(rs, "transport_company", transport_company or getattr(job, "transport_company", None))
    _safe_set(rs, "customer", getattr(job, "customer", None))  # optional, if field exists
    _safe_set(rs, "transport_job", job.name)  # only if RS has such a field
    _safe_set(rs, "status", "Draft")  # if status exists

    rs.insert(ignore_permissions=False)

    # Append legs from Transport Job -> to Run Sheet
    added = _append_runsheet_legs_from_job(job, rs)

    # Save RS after legs
    rs.save(ignore_permissions=True)

    return {"name": rs.name, "legs_added": added}


# ------------------------
# Core append-legs routine
# ------------------------

def _append_runsheet_legs_from_job(job: Document, rs: Document) -> int:
    job_legs_field = _get_job_legs_fieldname(job)
    rs_legs_field = _get_runsheet_legs_fieldname(rs)
    rs_child_dt = _get_runsheet_child_dt(rs)

    job_rows = job.get(job_legs_field) or []
    if not job_rows:
        frappe.throw(_("This Transport Job has no legs."))

    rs_child_meta = frappe.get_meta(rs_child_dt)

    # Build a copy map by common fieldnames between TJ Legs and RS Legs child doctypes
    # Always make sure we bring 'transport_leg'
    excluded = {'name','owner','creation','modified','modified_by','parent','parenttype','parentfield','idx','docstatus'}
    allowed_rs_fields = {df.fieldname for df in rs_child_meta.fields if df.fieldname and df.fieldname not in excluded}

    added = 0
    for i, jrow in enumerate(job_rows, start=1):
        s = jrow.as_dict()

        # If the TL is already on a Run Sheet, skip (or you may choose to error)
        tl_name = s.get("transport_leg")
        if tl_name:
            current_rs = frappe.db.get_value("Transport Leg", tl_name, "run_sheet")
            if current_rs:
                # Skip to avoid double assignment
                continue

        payload = {k: v for k, v in s.items() if k in allowed_rs_fields}

        # Add a sensible sequence if RS has it
        if "sequence" in allowed_rs_fields and "sequence" not in payload:
            payload["sequence"] = i

        # Ensure the key link exists if RS child has the field
        if "transport_leg" in allowed_rs_fields:
            payload["transport_leg"] = tl_name

        # Set defaults for status fields if present
        if "leg_status" in allowed_rs_fields and not payload.get("leg_status"):
            payload["leg_status"] = "Pending"

        rs.append(rs_legs_field, payload)

        # Immediately lock association on TL (optional but prevents races)
        if tl_name and _has_field("Transport Leg", "run_sheet"):
            frappe.db.set_value("Transport Leg", tl_name, "run_sheet", rs.name, update_modified=False)

        added += 1

    return added
