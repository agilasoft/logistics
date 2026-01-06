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
        # DEBUG: Log all validation calls
        try:
            frappe.log_error(
                f"Transport Job {self.name} validate() called - transport_job_type: {repr(self.get('transport_job_type'))}, "
                f"container_type: {repr(self.get('container_type'))}, container_no: {repr(self.get('container_no'))}",
                "Transport Job Validate Debug"
            )
        except:
            pass
        
        self.validate_required_fields()
        # Validate transport job type - only when it IS set (like Transport Order does)
        # This prevents "Job Type must be set first" errors by only validating when transport_job_type exists
        self._validate_transport_job_type()
        self._validate_load_type_compatibility()
        self.validate_legs()
        self.validate_accounts()
        self.validate_status_transition()
        
        # DEBUG: Log after validation
        try:
            frappe.log_error(
                f"Transport Job {self.name} validate() completed successfully",
                "Transport Job Validate Debug"
            )
        except:
            pass
    
    def before_save(self):
        """Calculate sustainability metrics and create job costing number before saving"""
        # Clear container fields if transport_job_type is not 'Container'
        transport_job_type = self.get('transport_job_type')
        if not transport_job_type or transport_job_type != 'Container':
            if self.get('container_type'):
                self.set('container_type', None)
            if self.get('container_no'):
                self.set('container_no', None)
        
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
        # Vehicle Type is mandatory only if Consolidate checkbox is not checked
        if not self.vehicle_type and not self.consolidate:
            frappe.throw(_("Vehicle Type is required when Consolidate is not checked"))
        if not self.company:
            frappe.throw(_("Company is required"))
        if not self.transport_job_type:
            frappe.throw(_("Transport Job Type is required"))
    
    def _validate_transport_job_type(self):
        """Validate transport job type specific business rules - only when transport_job_type IS set."""
        # IMPORTANT: Only validate when transport_job_type IS set (like Transport Order does)
        # This prevents "Job Type must be set first" errors by not requiring it to be set
        transport_job_type = self.get('transport_job_type')
        if not transport_job_type:
            return  # Early return - no validation if transport_job_type is not set
        
        # Container type validations - only when transport_job_type is 'Container'
        if transport_job_type == "Container":
            if not self.container_type:
                frappe.throw(_("Container Type is required for Container transport jobs."))
            if not self.container_no:
                frappe.throw(_("Container Number is required for Container transport jobs."))
    
    def _validate_load_type_compatibility(self):
        """Validate load type compatibility with transport job type using boolean flags."""
        if not self.load_type or not self.transport_job_type:
            return
        
        # Map transport_job_type to boolean field name
        field_map = {
            "Container": "container",
            "Non-Container": "non_container",
            "Special": "special",
            "Oversized": "oversized",
            "Multimodal": "multimodal",
            "Heavy Haul": "heavy_haul"
        }
        
        job_type_field = field_map.get(self.transport_job_type)
        if not job_type_field:
            return
        
        # Get load type boolean flag value
        load_type_flag = frappe.get_value("Load Type", self.load_type, job_type_field)
        
        if not load_type_flag:
            load_type_name = frappe.get_value("Load Type", self.load_type, "load_type_name")
            frappe.throw(_("Load Type '{0}' is not allowed for {1} transport jobs.").format(
                load_type_name or self.load_type, 
                self.transport_job_type
            ))
    
    def validate_legs(self):
        """Validate that submitted jobs have at least one leg and update missing data"""
        legs_field = _get_job_legs_fieldname(self)
        job_legs = self.get(legs_field) or []
        
        # Check that submitted jobs have at least one leg
        if self.docstatus == 1:  # Submitted
            if not job_legs:
                frappe.throw(_("Submitted Transport Job must have at least one leg"))
        
        # Update missing data from Transport Leg
        self._update_legs_missing_data(job_legs)
    
    def _update_legs_missing_data(self, job_legs):
        """Update missing data in legs by fetching from Transport Leg
        
        Args:
            job_legs: List of leg rows from the Transport Job
        """
        if not job_legs:
            return
        
        # Fields to fetch from Transport Leg
        fields_to_fetch = [
            "facility_type_from",
            "facility_from",
            "facility_type_to",
            "facility_to",
            "pick_mode",
            "drop_mode",
            "pick_address",
            "drop_address",
            "run_sheet",
            "date"
        ]
        
        for leg in job_legs:
            transport_leg_name = leg.get("transport_leg")
            if not transport_leg_name:
                # If transport_leg is not set, skip this row
                continue
            
            # Check if any required fields are missing
            has_missing = any(not leg.get(field) for field in fields_to_fetch[:-1])  # Exclude 'date' from required check (it's at the end)
            
            if has_missing:
                try:
                    # Fetch data from Transport Leg
                    transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
                    
                    # Update only missing fields
                    if not leg.get("facility_type_from") and transport_leg.get("facility_type_from"):
                        leg.facility_type_from = transport_leg.facility_type_from
                    
                    if not leg.get("facility_from") and transport_leg.get("facility_from"):
                        leg.facility_from = transport_leg.facility_from
                    
                    if not leg.get("facility_type_to") and transport_leg.get("facility_type_to"):
                        leg.facility_type_to = transport_leg.facility_type_to
                    
                    if not leg.get("facility_to") and transport_leg.get("facility_to"):
                        leg.facility_to = transport_leg.facility_to
                    
                    if not leg.get("pick_mode") and transport_leg.get("pick_mode"):
                        leg.pick_mode = transport_leg.pick_mode
                    
                    if not leg.get("drop_mode") and transport_leg.get("drop_mode"):
                        leg.drop_mode = transport_leg.drop_mode
                    
                    if not leg.get("pick_address") and transport_leg.get("pick_address"):
                        leg.pick_address = transport_leg.pick_address
                    
                    if not leg.get("drop_address") and transport_leg.get("drop_address"):
                        leg.drop_address = transport_leg.drop_address
                    
                    if not leg.get("run_sheet") and transport_leg.get("run_sheet"):
                        leg.run_sheet = transport_leg.run_sheet
                    
                    # Also update scheduled_date if missing
                    if not leg.get("scheduled_date") and transport_leg.get("date"):
                        leg.scheduled_date = transport_leg.date
                    
                except Exception as e:
                    frappe.log_error(
                        f"Error fetching data from Transport Leg {transport_leg_name}: {str(e)}",
                        "Transport Job Leg Data Fetch Error"
                    )
    
    def validate_accounts(self):
        """Validate that cost center and profit center belong to the company (when applicable)."""
        if not self.company:
            return

        if self.cost_center:
            cost_center_meta = frappe.get_meta("Cost Center")
            if cost_center_meta.has_field("company"):
                cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
                if cost_center_company and cost_center_company != self.company:
                    frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                        self.cost_center, self.company
                    ))

        if self.profit_center:
            profit_center_meta = frappe.get_meta("Profit Center")
            if profit_center_meta.has_field("company"):
                profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
                if profit_center_company and profit_center_company != self.company:
                    frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                        self.profit_center, self.company
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
            jcn.job_type = "Transport Job"  # Must be set before job_no (Dynamic Link)
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
    Create Run Sheet(s) for a submitted Transport Job, and pull its legs in.
    If `vehicle` is provided, ensure it isn't currently on an active run sheet.
    
    If group_legs_in_one_runsheet is checked, all legs are added to one Run Sheet.
    If unchecked, separate Run Sheets are created per leg.
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

    # Check if legs should be grouped in one run sheet
    group_legs = getattr(job, "group_legs_in_one_runsheet", False)

    if group_legs:
        # Create one Run Sheet with all legs (original behavior)
        rs = _create_single_run_sheet(job, vehicle, driver, transport_company)
        rs.insert(ignore_permissions=False)

        # Append legs from Transport Job -> to Run Sheet
        added = _append_runsheet_legs_from_job(job, rs)

        # Save RS after legs
        rs.save(ignore_permissions=True)

        return {"name": rs.name, "legs_added": added, "run_sheets_created": 1}
    else:
        # Create separate Run Sheets per leg
        job_legs_field = _get_job_legs_fieldname(job)
        job_rows = job.get(job_legs_field) or []
        
        if not job_rows:
            frappe.throw(_("This Transport Job has no legs."))

        run_sheets_created = []
        total_legs_added = 0

        for leg_row in job_rows:
            leg_dict = leg_row.as_dict()
            tl_name = leg_dict.get("transport_leg")
            
            # Skip if leg is already assigned to a Run Sheet
            if tl_name:
                current_rs = frappe.db.get_value("Transport Leg", tl_name, "run_sheet")
                if current_rs:
                    continue

            # Create a new Run Sheet for this leg
            rs = _create_single_run_sheet(job, vehicle, driver, transport_company)
            rs.insert(ignore_permissions=False)

            # Append only this leg to the Run Sheet
            added = _append_single_leg_to_runsheet(job, rs, leg_row)

            # Save RS after leg
            rs.save(ignore_permissions=True)

            run_sheets_created.append(rs.name)
            total_legs_added += added

        return {
            "name": run_sheets_created[0] if run_sheets_created else None,  # First one for backward compatibility
            "names": run_sheets_created,  # All created run sheets
            "legs_added": total_legs_added,
            "run_sheets_created": len(run_sheets_created)
        }


# ------------------------
# Helper functions for Run Sheet creation
# ------------------------

def _create_single_run_sheet(job: Document, vehicle: Optional[str] = None, 
                             driver: Optional[str] = None,
                             transport_company: Optional[str] = None) -> Document:
    """
    Create a single Run Sheet document with common fields from the Transport Job.
    Does not insert the document - caller must call insert() and save().
    """
    rs = frappe.new_doc("Run Sheet")
    _safe_set(rs, "run_date", nowdate())
    _safe_set(rs, "vehicle_type", getattr(job, "vehicle_type", None))
    _safe_set(rs, "vehicle", vehicle or getattr(job, "vehicle", None))
    _safe_set(rs, "driver", driver or getattr(job, "driver", None))
    _safe_set(rs, "transport_company", transport_company or getattr(job, "transport_company", None))
    _safe_set(rs, "customer", getattr(job, "customer", None))  # optional, if field exists
    _safe_set(rs, "transport_job", job.name)  # only if RS has such a field
    _safe_set(rs, "status", "Draft")  # if status exists
    return rs


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


def _append_single_leg_to_runsheet(job: Document, rs: Document, leg_row: Document) -> int:
    """
    Append a single leg from Transport Job to a Run Sheet.
    Similar to _append_runsheet_legs_from_job but for a single leg.
    """
    rs_legs_field = _get_runsheet_legs_fieldname(rs)
    rs_child_dt = _get_runsheet_child_dt(rs)
    rs_child_meta = frappe.get_meta(rs_child_dt)

    # Build a copy map by common fieldnames between TJ Legs and RS Legs child doctypes
    excluded = {'name','owner','creation','modified','modified_by','parent','parenttype','parentfield','idx','docstatus'}
    allowed_rs_fields = {df.fieldname for df in rs_child_meta.fields if df.fieldname and df.fieldname not in excluded}

    s = leg_row.as_dict()

    # If the TL is already on a Run Sheet, skip
    tl_name = s.get("transport_leg")
    if tl_name:
        current_rs = frappe.db.get_value("Transport Leg", tl_name, "run_sheet")
        if current_rs:
            # Skip to avoid double assignment
            return 0

    payload = {k: v for k, v in s.items() if k in allowed_rs_fields}

    # Add a sensible sequence if RS has it
    if "sequence" in allowed_rs_fields and "sequence" not in payload:
        payload["sequence"] = 1

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

    return 1


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
        
        # Add accounting fields to Sales Invoice Item
        if getattr(job, "cost_center", None):
            item_payload["cost_center"] = job.cost_center
        if getattr(job, "profit_center", None):
            item_payload["profit_center"] = job.profit_center
        
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


@frappe.whitelist()
def fetch_missing_leg_data(job_name: str) -> Dict[str, Any]:
    """
    Fetch and update missing data from Transport Leg for all legs in a Transport Job.
    This method works even for submitted documents by using db_set.
    
    Args:
        job_name: Name of the Transport Job
        
    Returns:
        Dict with status and count of updated legs
    """
    if not job_name:
        frappe.throw(_("Transport Job name is required"))
    
    job = frappe.get_doc("Transport Job", job_name)
    legs_field = _get_job_legs_fieldname(job)
    job_legs = job.get(legs_field) or []
    
    if not job_legs:
        return {"ok": True, "updated_count": 0, "message": _("No legs found in this Transport Job")}
    
    # Fields to fetch from Transport Leg
    fields_to_fetch = [
        "facility_type_from",
        "facility_from",
        "facility_type_to",
        "facility_to",
        "pick_mode",
        "drop_mode",
        "pick_address",
        "drop_address",
        "run_sheet",
        "date"
    ]
    
    updated_count = 0
    
    for leg in job_legs:
        transport_leg_name = leg.get("transport_leg")
        if not transport_leg_name:
            continue
        
        # Check if any required fields are missing (excluding 'date' which is last)
        has_missing = any(not leg.get(field) for field in fields_to_fetch[:-1])
        
        if has_missing:
            try:
                # Fetch data from Transport Leg
                transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
                
                # Track if we updated anything
                updated_this_leg = False
                
                # Update missing fields using db_set to work with submitted documents
                if not leg.get("facility_type_from") and transport_leg.get("facility_type_from"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "facility_type_from", 
                                       transport_leg.facility_type_from, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("facility_from") and transport_leg.get("facility_from"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "facility_from", 
                                       transport_leg.facility_from, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("facility_type_to") and transport_leg.get("facility_type_to"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "facility_type_to", 
                                       transport_leg.facility_type_to, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("facility_to") and transport_leg.get("facility_to"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "facility_to", 
                                       transport_leg.facility_to, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("pick_mode") and transport_leg.get("pick_mode"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "pick_mode", 
                                       transport_leg.pick_mode, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("drop_mode") and transport_leg.get("drop_mode"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "drop_mode", 
                                       transport_leg.drop_mode, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("pick_address") and transport_leg.get("pick_address"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "pick_address", 
                                       transport_leg.pick_address, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("drop_address") and transport_leg.get("drop_address"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "drop_address", 
                                       transport_leg.drop_address, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("run_sheet") and transport_leg.get("run_sheet"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "run_sheet", 
                                       transport_leg.run_sheet, update_modified=False)
                    updated_this_leg = True
                
                if not leg.get("scheduled_date") and transport_leg.get("date"):
                    frappe.db.set_value("Transport Job Legs", leg.name, "scheduled_date", 
                                       transport_leg.date, update_modified=False)
                    updated_this_leg = True
                
                if updated_this_leg:
                    updated_count += 1
                    
            except Exception as e:
                frappe.log_error(
                    f"Error fetching data from Transport Leg {transport_leg_name}: {str(e)}",
                    "Fetch Missing Leg Data Error"
                )
    
    # Commit the changes
    frappe.db.commit()
    
    return {
        "ok": True,
        "updated_count": updated_count,
        "message": _("Updated {0} leg(s) with missing data").format(updated_count)
    }
