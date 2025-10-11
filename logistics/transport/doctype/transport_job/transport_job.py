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

def _safe_meta_fieldnames(doctype: str) -> set:
    """Get fieldnames that exist on a doctype as a set."""
    try:
        meta = frappe.get_meta(doctype)
        return {df.fieldname for df in meta.fields if df.fieldname}
    except Exception:
        return set()

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
        # Use proper document update to trigger status update hooks
        if tl_name and _has_field("Transport Leg", "run_sheet"):
            try:
                leg_doc = frappe.get_doc("Transport Leg", tl_name)
                if leg_doc.run_sheet != rs.name:
                    leg_doc.run_sheet = rs.name
                    leg_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error updating Transport Leg {tl_name} run_sheet assignment in transport_job: {str(e)}")
                # Fallback to db.set_value if document update fails
                frappe.db.set_value("Transport Leg", tl_name, "run_sheet", rs.name, update_modified=False)

        added += 1

    return added


@frappe.whitelist()
def create_sales_invoice(job_name: str) -> Dict[str, Any]:
    """
    Create a Sales Invoice from a Transport Job when all legs are completed.
    """
    if not job_name:
        frappe.throw(_("Transport Job name is required."))
    
    job = frappe.get_doc("Transport Job", job_name)
    if job.docstatus != 1:
        frappe.throw(_("Transport Job must be submitted to create Sales Invoice."))
    
    # Get all legs for this job
    legs_field = _get_job_legs_fieldname(job)
    job_legs = job.get(legs_field) or []
    
    if not job_legs:
        frappe.throw(_("No legs found in this Transport Job."))
    
    # Check if all legs are completed
    completed_legs = []
    incomplete_legs = []
    
    for leg_row in job_legs:
        transport_leg_name = leg_row.get("transport_leg")
        if not transport_leg_name:
            continue
            
        leg_doc = frappe.get_doc("Transport Leg", transport_leg_name)
        if leg_doc.status == "Completed":
            completed_legs.append(leg_doc)
        else:
            incomplete_legs.append(leg_doc)
    
    if incomplete_legs:
        incomplete_names = [leg.name for leg in incomplete_legs]
        frappe.throw(_("Cannot create Sales Invoice. The following legs are not completed: {0}").format(", ".join(incomplete_names)))
    
    if not completed_legs:
        frappe.throw(_("No completed legs found to create Sales Invoice."))
    
    # Check if Sales Invoice already exists for this job
    if job.sales_invoice:
        frappe.throw(_("Sales Invoice {0} already exists for this Transport Job.").format(job.sales_invoice))
    
    # Create Sales Invoice
    si = frappe.new_doc("Sales Invoice")
    si.customer = job.customer
    si.company = job.company
    si.posting_date = frappe.utils.today()
    
    # Add reference in remarks since transport_job field doesn't exist
    base_remarks = si.remarks or ""
    note = _("Auto-created from Transport Job {0}").format(job.name)
    si.remarks = f"{base_remarks}\n{note}" if base_remarks else note
    
    # Create items for each completed leg
    si_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    for leg in completed_legs:
        # Try to find a suitable item or create a service item
        item_code = None
        item_name = f"Transport from {leg.facility_from or 'Origin'} to {leg.facility_to or 'Destination'}"
        
        # Try to find existing transport service items
        existing_items = frappe.get_all("Item", 
            filters={"item_group": "Services", "disabled": 0}, 
            fields=["name"], 
            limit=1
        )
        
        if existing_items:
            item_code = existing_items[0].name
        else:
            # Try to find any service item
            service_items = frappe.get_all("Item", 
                filters={"disabled": 0}, 
                fields=["name"], 
                limit=1
            )
            if service_items:
                item_code = service_items[0].name
            else:
                # Use a generic approach - create item without item_code
                item_code = None
        
        # Try to get rate from leg charges or use default
        rate = 0.0
        if hasattr(leg, 'rate') and leg.rate:
            rate = leg.rate
        elif hasattr(leg, 'amount') and leg.amount:
            rate = leg.amount
        
        item_payload = {
            "item_name": item_name,
            "description": f"Transport Leg: {leg.name}",
            "qty": 1,
            "rate": rate
        }
        
        # Only add item_code if we found one
        if item_code:
            item_payload["item_code"] = item_code
        
        # Add transport_leg field if it exists in Sales Invoice Item
        if "transport_leg" in si_item_fields:
            item_payload["transport_leg"] = leg.name
        else:
            # Add transport leg reference in description if field doesn't exist
            item_payload["description"] = f"Transport Leg: {leg.name} - {item_payload.get('description', '')}"
        
        si.append("items", item_payload)
    
    # Set missing values and insert
    si.set_missing_values()
    si.insert(ignore_permissions=True)
    
    # Update Transport Legs with Sales Invoice reference
    for leg in completed_legs:
        frappe.db.set_value("Transport Leg", leg.name, "sales_invoice", si.name, update_modified=False)
    
    # Update Transport Job with Sales Invoice reference
    frappe.db.set_value("Transport Job", job.name, "sales_invoice", si.name, update_modified=False)
    
    return {
        "ok": True,
        "message": _("Sales Invoice {0} created successfully.").format(si.name),
        "sales_invoice": si.name,
        "legs_updated": len(completed_legs)
    }
