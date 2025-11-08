# -*- coding: utf-8 -*-
# Copyright (c) 2021, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from typing import Dict, Any, List, Optional
from frappe.utils import nowdate, flt

class TransportJob(Document):
    def validate(self):
        """Validate Transport Job data"""
        self.validate_required_fields()
        self.validate_legs()
        self.validate_accounts()
        self.validate_status_transition()
    
    def before_save(self):
        """Calculate sustainability metrics and create job costing number before saving"""
        self.calculate_sustainability_metrics()
        self.create_job_costing_number_if_needed()
        self.update_status()
    
    def after_insert(self):
        """Create job costing number for new documents"""
        self.create_job_costing_number_if_needed()
    
    def after_submit(self):
        """Record sustainability metrics and update status after job submission"""
        if self.status == "Draft":
            self.status = "Submitted"
        self.record_sustainability_metrics()
    
    def calculate_sustainability_metrics(self):
        """Calculate sustainability metrics for this transport job"""
        try:
            from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
            
            # Calculate total distance from legs
            total_distance = 0
            if hasattr(self, 'legs') and self.legs:
                for leg in self.legs:
                    if hasattr(leg, 'distance') and leg.distance:
                        total_distance += flt(leg.distance)
            
            # Store calculated metrics for display
            self.total_distance = total_distance
            
            # Calculate estimated fuel consumption based on vehicle type and distance
            if hasattr(self, 'vehicle_type') and self.vehicle_type and total_distance > 0:
                fuel_consumption = self._calculate_fuel_consumption(self.vehicle_type, total_distance)
                self.fuel_consumption = fuel_consumption
                
                # Calculate estimated carbon footprint
                carbon_footprint = self._calculate_carbon_footprint(self.vehicle_type, fuel_consumption)
                self.estimated_carbon_footprint = carbon_footprint
                
        except Exception as e:
            frappe.log_error(f"Error calculating sustainability metrics for Transport Job {self.name}: {e}", "Transport Job Sustainability Error")
    
    def record_sustainability_metrics(self):
        """Record sustainability metrics in the centralized system"""
        try:
            from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
            
            result = integrate_sustainability(
                doctype=self.doctype,
                docname=self.name,
                module="Transport",
                doc=self
            )
            
            if result.get("status") == "success":
                frappe.msgprint(_("Sustainability metrics recorded successfully"))
            elif result.get("status") == "skipped":
                # Don't show message if sustainability is not enabled
                pass
            else:
                frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Transport Job Sustainability Error")
                
        except Exception as e:
            frappe.log_error(f"Error recording sustainability metrics for Transport Job {self.name}: {e}", "Transport Job Sustainability Error")
    
    def _calculate_fuel_consumption(self, vehicle_type: str, distance: float) -> float:
        """Calculate estimated fuel consumption based on vehicle type and distance"""
        # Fuel consumption rates (liters per 100 km) by vehicle type
        fuel_rates = {
            "Truck": 25.0,  # 25 L/100km
            "Van": 12.0,    # 12 L/100km
            "Car": 8.0,     # 8 L/100km
            "Motorcycle": 4.0,  # 4 L/100km
        }
        
        rate = fuel_rates.get(vehicle_type, 15.0)  # Default 15 L/100km
        return (rate * distance) / 100.0
    
    def _calculate_carbon_footprint(self, vehicle_type: str, fuel_consumption: float) -> float:
        """Calculate estimated carbon footprint based on fuel consumption"""
        # Carbon emission factors (kg CO2e per liter) by fuel type
        # Assuming diesel for trucks/vans, petrol for cars/motorcycles
        carbon_factors = {
            "Truck": 2.68,  # Diesel
            "Van": 2.68,    # Diesel
            "Car": 2.31,    # Petrol
            "Motorcycle": 2.31,  # Petrol
        }
        
        factor = carbon_factors.get(vehicle_type, 2.5)  # Default factor
        return factor * fuel_consumption
    
    def validate_required_fields(self):
        """Validate required fields are present"""
        if not self.customer:
            frappe.throw(_("Customer is required"))
        if not self.vehicle_type:
            frappe.throw(_("Vehicle Type is required"))
        if not self.company:
            frappe.throw(_("Company is required"))
    
    def validate_legs(self):
        """Validate that submitted jobs have at least one leg"""
        if self.docstatus == 1:  # Submitted
            legs_field = _get_job_legs_fieldname(self)
            job_legs = self.get(legs_field) or []
            if not job_legs:
                frappe.throw(_("Submitted Transport Job must have at least one leg"))
    
    def validate_accounts(self):
        """Validate that cost center, profit center, and branch belong to the company"""
        if self.company:
            if self.cost_center:
                cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
                if cost_center_company != self.company:
                    frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                        self.cost_center, self.company
                    ))
            if self.profit_center:
                profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
                if profit_center_company != self.company:
                    frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                        self.profit_center, self.company
                    ))
            if self.branch:
                branch_company = frappe.db.get_value("Branch", self.branch, "company")
                if branch_company != self.company:
                    frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                        self.branch, self.company
                    ))
    
    def validate_status_transition(self):
        """Validate status transitions are allowed"""
        if self.is_new():
            return
        
        old_status = frappe.db.get_value(self.doctype, self.name, "status")
        new_status = self.status
        
        if old_status == new_status:
            return
        
        # Define allowed transitions
        allowed_transitions = {
            "Draft": ["Submitted", "Cancelled"],
            "Submitted": ["In Progress", "Cancelled"],
            "In Progress": ["Completed", "Cancelled"],
            "Completed": [],  # Cannot change from Completed
            "Cancelled": []  # Cannot change from Cancelled
        }
        
        if old_status and new_status not in allowed_transitions.get(old_status, []):
            frappe.throw(_("Cannot change status from {0} to {1}").format(old_status, new_status))
        
        # Prevent cancellation if Sales Invoice exists
        if new_status == "Cancelled" and self.sales_invoice:
            frappe.throw(_("Cannot cancel Transport Job with Sales Invoice {0}").format(self.sales_invoice))
    
    def update_status(self):
        """Update status based on job submission and leg statuses"""
        if self.is_new():
            if not self.status:
                self.status = "Draft"
            return
        
        # If submitted, check leg statuses to determine job status
        if self.docstatus == 1:  # Submitted
            legs_field = _get_job_legs_fieldname(self)
            job_legs = self.get(legs_field) or []
            
            if not job_legs:
                if self.status != "Submitted":
                    self.status = "Submitted"
                return
            
            # Get all leg statuses
            leg_statuses = []
            for leg_row in job_legs:
                transport_leg_name = leg_row.get("transport_leg")
                if transport_leg_name:
                    leg_status = frappe.db.get_value("Transport Leg", transport_leg_name, "status")
                    if leg_status:
                        leg_statuses.append(leg_status)
            
            if not leg_statuses:
                if self.status != "Submitted":
                    self.status = "Submitted"
                return
            
            # Determine job status based on leg statuses
            if all(status == "Completed" for status in leg_statuses):
                old_status = self.status
                self.status = "Completed"
                # Trigger auto-billing if status changed to Completed
                if old_status != "Completed":
                    self._trigger_auto_billing()
            elif any(status in ["In Progress", "Dispatched"] for status in leg_statuses):
                if self.status not in ["In Progress", "Completed"]:
                    self.status = "In Progress"
            elif all(status in ["Draft", "Pending"] for status in leg_statuses):
                if self.status != "Submitted":
                    self.status = "Submitted"
    
    def _trigger_auto_billing(self):
        """Trigger auto-billing if enabled"""
        try:
            from logistics.transport.automation_helpers import auto_bill_transport_job
            auto_bill_transport_job(self)
        except Exception as e:
            frappe.log_error(f"Error triggering auto-billing for Transport Job {self.name}: {str(e)}", "Auto Billing Error")
    
    def create_job_costing_number_if_needed(self):
        """Create Job Costing Number if it doesn't exist"""
        if self.job_costing_number:
            return
        
        if not self.name:
            # For new documents, this will be called in after_insert
            return
        
        try:
            # Check if Job Costing Number already exists for this job
            existing_jcn = frappe.db.exists("Job Costing Number", {"job_no": self.name})
            if existing_jcn:
                self.job_costing_number = existing_jcn
                return
            
            # Create new Job Costing Number
            jcn = frappe.new_doc("Job Costing Number")
            jcn.job_no = self.name
            jcn.job_name = self.name
            jcn.company = self.company
            jcn.customer = self.customer
            jcn.insert(ignore_permissions=True)
            
            self.job_costing_number = jcn.name
        except Exception as e:
            frappe.log_error(f"Error creating Job Costing Number for Transport Job {self.name}: {str(e)}", "Job Costing Number Creation Error")

ACTIVE_RUNSHEET_STATUSES = ("Planned", "Dispatched", "In Progress")  # consider these "active"


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
    Uses charges from Transport Job level.
    """
    if not job_name:
        frappe.throw(_("Transport Job name is required."))
    
    job = frappe.get_doc("Transport Job", job_name)
    if job.docstatus != 1:
        frappe.throw(_("Transport Job must be submitted to create Sales Invoice."))
    
    # Validate all legs are completed
    _validate_all_legs_completed(job)
    
    # Check if Sales Invoice already exists for this job
    if getattr(job, "sales_invoice", None):
        frappe.throw(_("Sales Invoice {0} already exists for this Transport Job.").format(job.sales_invoice))
    
    # Create Sales Invoice
    si = frappe.new_doc("Sales Invoice")
    si.customer = job.customer
    si.company = job.company
    si.posting_date = frappe.utils.today()
    
    # Add accounting fields from Transport Job
    if getattr(job, "branch", None):
        si.branch = job.branch
    if getattr(job, "cost_center", None):
        si.cost_center = job.cost_center
    if getattr(job, "profit_center", None):
        si.profit_center = job.profit_center
    
    # Add reference to Job Costing Number if it exists
    if getattr(job, "job_costing_number", None):
        si.job_costing_number = job.job_costing_number
    
    # Add reference to Sales Quote if it exists
    if hasattr(job, "sales_quote") and job.sales_quote:
        si.quotation_no = job.sales_quote
    
    # Add reference in remarks
    base_remarks = si.remarks or ""
    note = _("Auto-created from Transport Job {0}").format(job.name)
    si.remarks = f"{base_remarks}\n{note}" if base_remarks else note
    
    # Use charges from Transport Job
    charges = job.get("charges") or []
    si_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    
    if charges:
        # Create items from charges
        for charge in charges:
            item_code = getattr(charge, "item_code", None)
            item_name = getattr(charge, "item_name", None) or getattr(charge, "charge_type", "Transport Service")
            description = getattr(charge, "description", None) or item_name
            qty = flt(getattr(charge, "quantity", 1))
            rate = flt(getattr(charge, "rate", 0))
            amount = flt(getattr(charge, "amount", 0))
            
            # Use amount if provided, otherwise calculate from rate * qty
            if amount > 0:
                rate = amount / qty if qty > 0 else amount
            
            item_payload = {
                "item_name": item_name,
                "description": description,
                "qty": qty,
                "rate": rate
            }
            
            if item_code:
                item_payload["item_code"] = item_code
            
            # Add accounting fields to Sales Invoice Item
            if getattr(job, "cost_center", None):
                item_payload["cost_center"] = job.cost_center
            if getattr(job, "profit_center", None):
                item_payload["profit_center"] = job.profit_center
            
            si.append("items", item_payload)
    else:
        # Fallback: Create a single item if no charges
        item_name = f"Transport Job: {job.name}"
        description = _("Transport services for {0}").format(job.name)
        
        # Try to find a service item
        service_items = frappe.get_all("Item", 
            filters={"item_group": "Services", "disabled": 0}, 
            fields=["name"], 
            limit=1
        )
        
        item_code = service_items[0].name if service_items else None
        
        item_payload = {
            "item_name": item_name,
            "description": description,
            "qty": 1,
            "rate": 0
        }
        
        if item_code:
            item_payload["item_code"] = item_code
        
        si.append("items", item_payload)
    
    # Set missing values and insert
    si.set_missing_values()
    si.insert(ignore_permissions=True)
    
    # Update Transport Job with Sales Invoice reference
    frappe.db.set_value("Transport Job", job.name, "sales_invoice", si.name, update_modified=False)
    
    return {
        "ok": True,
        "message": _("Sales Invoice {0} created successfully.").format(si.name),
        "sales_invoice": si.name,
        "charges_used": len(charges)
    }


def _validate_all_legs_completed(job: Document) -> None:
    """Validate that all legs in the Transport Job are completed"""
    legs_field = _get_job_legs_fieldname(job)
    job_legs = job.get(legs_field) or []
    
    if not job_legs:
        frappe.throw(_("No legs found in this Transport Job."))
    
    incomplete_legs = []
    
    for leg_row in job_legs:
        transport_leg_name = leg_row.get("transport_leg")
        if not transport_leg_name:
            continue
            
        leg_doc = frappe.get_doc("Transport Leg", transport_leg_name)
        if leg_doc.status != "Completed":
            incomplete_legs.append(leg_doc)
    
    if incomplete_legs:
        incomplete_names = [leg.name for leg in incomplete_legs]
        frappe.throw(_("Cannot create Sales Invoice. The following legs are not completed: {0}").format(", ".join(incomplete_names)))
