# -*- coding: utf-8 -*-
# Copyright (c) 2021, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from typing import Dict, Any, List, Optional
from frappe.utils import nowdate, flt, getdate, get_datetime, add_days, cint

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
        except Exception:
            pass
        
        # Reset status and docstatus for new/duplicated documents
        # When duplicating, both status and docstatus are copied from the original, so we need to reset them
        if self.is_new():
            # Always reset docstatus to 0 for new documents (duplicates may have docstatus = 1)
            self.docstatus = 0
            # Always reset status to Draft for new documents (duplicates may have status = Submitted/In Progress/Completed)
            self.status = "Draft"
        
        self.validate_required_fields()
        # Validate transport job type - only when it IS set (like Transport Order does)
        # This prevents "Job Type must be set first" errors by only validating when transport_job_type exists
        self._validate_transport_job_type()
        self._validate_load_type_compatibility()
        self.validate_legs()
        self.validate_accounts()
        self.validate_status_transition()
        
        # Prevent duplicate Transport Jobs for the same transport_order
        self._validate_no_duplicate_transport_order()
        
        # Copy service level from Transport Order when transport_order is set
        self._copy_service_level_from_order()
        
        # Capacity validation
        self.validate_vehicle_type_capacity()
        self.validate_capacity()

        # Convert package measurements when UOM was changed (e.g. after import)
        try:
            from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
            apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
        except Exception:
            pass

        self._update_packing_summary()
        
        # DEBUG: Log after validation
        try:
            frappe.log_error(
                f"Transport Job {self.name} validate() completed successfully",
                "Transport Job Validate Debug"
            )
        except Exception:
            pass
    
    def before_save(self):
        """Calculate sustainability metrics and create job costing number before saving"""
        from logistics.utils.module_integration import run_propagate_on_link
        run_propagate_on_link(self)
        # Clear container fields if transport_job_type is not 'Container'
        transport_job_type = self.get('transport_job_type')
        if not transport_job_type or transport_job_type != 'Container':
            if self.get('container_type'):
                self.set('container_type', None)
            if self.get('container_no'):
                self.set('container_no', None)
        
        self.calculate_sustainability_metrics()
        self.create_job_costing_number_if_needed()
        
        # Derive SLA target date from Logistics Service Level when applicable
        self._derive_sla_target_from_service_level()
        
        # Update status - but be careful during submission
        # Check database directly to see if document is actually submitted (more reliable than self.docstatus)
        if not self.is_new():
            db_docstatus = frappe.db.get_value(self.doctype, self.name, "docstatus")
            db_status = frappe.db.get_value(self.doctype, self.name, "status")
            
            # If document is submitted in database but status is Draft, fix it immediately using SQL
            # This bypasses any hooks that might interfere
            if db_docstatus == 1 and db_status == "Draft":
                frappe.db.sql(
                    f"UPDATE `tab{self.doctype}` SET `status` = 'Submitted' WHERE `name` = %s",
                    (self.name,)
                )
                frappe.db.commit()
                # Reload to get updated status
                self.reload()
                return  # Don't call update_status, status is already fixed
            
            # If document is submitted, ensure docstatus is set correctly in object
            if db_docstatus == 1:
                self.docstatus = 1
                # Also ensure status is not Draft (safeguard)
                if db_status == "Draft":
                    frappe.db.sql(
                        f"UPDATE `tab{self.doctype}` SET `status` = 'Submitted' WHERE `name` = %s",
                        (self.name,)
                    )
                    frappe.db.commit()
                    self.reload()
                    return
        
        # Skip status update if document is being submitted (flagged with _submitting)
        if not getattr(self, '_submitting', False):
            old_status = self.status
            self.update_status()
            new_status = self.status
            
            # For submitted documents, update status if it changed (but never to Draft)
            if self.docstatus == 1:
                if new_status and new_status != "Draft" and old_status != new_status:
                    self.db_set("status", new_status, update_modified=False)
                elif new_status == "Draft":
                    # This should never happen, but force to Submitted as safeguard
                    self.db_set("status", "Submitted", update_modified=False)
    
    def after_insert(self):
        """Create job costing number for new documents"""
        self.create_job_costing_number_if_needed()
    
    def before_submit(self):
        """Mark document as submitting and set status to Submitted"""
        # Set flag to prevent before_save from calling update_status during submission
        self._submitting = True
        
        # CRITICAL: Set status to "Submitted" BEFORE submission completes
        # This ensures status is set even if after_submit doesn't run
        # Use direct SQL to bypass any hooks
        if not self.is_new():
            frappe.db.sql(
                f"UPDATE `tab{self.doctype}` SET `status` = 'Submitted' WHERE `name` = %s",
                (self.name,)
            )
            frappe.db.commit()
            # Also set in the object
            self.status = "Submitted"
    
    def after_submit(self):
        """Record sustainability metrics and update status after job submission"""
        # IMPORTANT: Ensure docstatus is 1 (sometimes it's not set in the object yet)
        # Reload from database to get the actual docstatus
        current_docstatus = frappe.db.get_value(self.doctype, self.name, "docstatus")
        if current_docstatus != 1:
            # If not submitted, something went wrong - log and return
            frappe.log_error(
                f"Transport Job {self.name} after_submit called but docstatus is {current_docstatus}, not 1",
                "Transport Job After Submit Error"
            )
            return
        
        # Ensure docstatus is set in the object for update_status to work
        self.docstatus = 1
        
        # Clear submitting flag
        if hasattr(self, '_submitting'):
            delattr(self, '_submitting')
        
        # CRITICAL: Set status to "Submitted" IMMEDIATELY using direct SQL to bypass any hooks
        # This ensures status is set even if something tries to reset it
        frappe.db.sql(
            f"UPDATE `tab{self.doctype}` SET `status` = 'Submitted' WHERE `name` = %s",
            (self.name,)
        )
        frappe.db.commit()
        
        # Verify status was saved correctly
        db_status = frappe.db.get_value(self.doctype, self.name, "status")
        if db_status != "Submitted":
            # If status wasn't saved correctly, try again with db_set
            frappe.log_error(
                f"Transport Job {self.name} status not set to Submitted after SQL update. Current status: {db_status}. Retrying with db_set.",
                "Transport Job Status Update Error"
            )
            self.db_set("status", "Submitted", update_modified=False)
            frappe.db.commit()
        
        # Reload the document to get the latest state
        self.reload()
        
        # Update status based on leg statuses (this may change status to "In Progress" or "Completed" if legs are already in those states)
        # This allows status to be updated based on current leg statuses after initial submission
        self.update_status()
        new_status = self.status
        
        # Ensure status is never "Draft" for a submitted document
        if not new_status or new_status == "Draft":
            new_status = "Submitted"
        
        # Update status in database if it changed from "Submitted"
        # Always ensure it's set correctly (never Draft for submitted documents)
        if new_status != "Draft" and new_status != db_status:
            frappe.db.sql(
                f"UPDATE `tab{self.doctype}` SET `status` = %s WHERE `name` = %s",
                (new_status, self.name)
            )
            frappe.db.commit()
            # Publish realtime event for status change
            frappe.publish_realtime(
                'transport_job_status_changed',
                {
                    'job_name': self.name,
                    'status': new_status,
                    'previous_status': db_status,
                    'docstatus': 1
                },
                user=frappe.session.user
            )
        
        # Final verification - ensure status is never Draft for submitted documents
        final_status = frappe.db.get_value(self.doctype, self.name, "status")
        if final_status == "Draft":
            frappe.log_error(
                f"Transport Job {self.name} status is still Draft after after_submit. Forcing to Submitted via SQL.",
                "Transport Job Status Update Error"
            )
            frappe.db.sql(
                f"UPDATE `tab{self.doctype}` SET `status` = 'Submitted' WHERE `name` = %s",
                (self.name,)
            )
            frappe.db.commit()
        
        self.record_sustainability_metrics()
        
        # Reserve capacity if vehicle is assigned
        self.reserve_capacity()
    
    def after_save(self):
        """Ensure status is correct after save, especially for submitted documents"""
        # This hook runs after every save, including after submission
        # Check database directly to see if document is actually submitted
        if not self.is_new():
            db_docstatus = frappe.db.get_value(self.doctype, self.name, "docstatus")
            db_status = frappe.db.get_value(self.doctype, self.name, "status")
            
            # CRITICAL: If document is submitted but status is Draft, fix it immediately
            # This catches cases where after_submit didn't run or status was reset
            if db_docstatus == 1 and db_status == "Draft":
                # Use direct SQL to bypass any hooks and ensure it's saved
                frappe.db.sql(
                    f"UPDATE `tab{self.doctype}` SET `status` = 'Submitted' WHERE `name` = %s",
                    (self.name,)
                )
                frappe.db.commit()
                frappe.log_error(
                    f"Transport Job {self.name} status was Draft after save for submitted document (docstatus=1). Fixed to Submitted in after_save hook.",
                    "Transport Job Status Fix in after_save"
                )
                # Reload to reflect the change
                self.reload()
                # After fixing, update based on leg statuses
                self.docstatus = 1
                self.update_status()
                new_status = self.status
                if new_status and new_status != "Draft" and new_status != "Submitted":
                    frappe.db.sql(
                        f"UPDATE `tab{self.doctype}` SET `status` = %s WHERE `name` = %s",
                        (new_status, self.name)
                    )
                    frappe.db.commit()
                return
            
            # For submitted documents, ensure status is correct based on leg statuses
            if db_docstatus == 1:
                # Ensure docstatus is set in object
                self.docstatus = 1
                
                # Reload to get latest leg data
                self.reload()
                
                # Update status based on leg statuses (may change to "In Progress" or "Completed")
                self.update_status()
                new_status = self.status
                
                # Ensure status is never "Draft" for a submitted document
                if not new_status or new_status == "Draft":
                    new_status = "Submitted"
                
                # Update if status needs to change (always update to ensure it's current)
                if new_status != "Draft" and new_status != db_status:
                    frappe.db.sql(
                        f"UPDATE `tab{self.doctype}` SET `status` = %s WHERE `name` = %s",
                        (new_status, self.name)
                    )
                    frappe.db.commit()
                    # Log the update for debugging
                    if new_status != "Submitted":
                        frappe.log_error(
                            f"Transport Job {self.name} status updated from '{db_status}' to '{new_status}' in after_save hook based on leg statuses.",
                            "Transport Job Status Update in after_save"
                        )
                    # Publish realtime event for status change
                    frappe.publish_realtime(
                        'transport_job_status_changed',
                        {
                            'job_name': self.name,
                            'status': new_status,
                            'previous_status': db_status,
                            'docstatus': db_docstatus
                        },
                        user=frappe.session.user
                    )
    
    def on_cancel(self):
        """Handle cancellation - set status to Cancelled and release capacity"""
        # Get previous status before cancellation
        previous_status = frappe.db.get_value(self.doctype, self.name, "status") or "Draft"
        
        # Set status to Cancelled when document is cancelled
        # Use db_set to update directly in database (bypasses validation)
        self.db_set("status", "Cancelled", update_modified=False)
        frappe.db.commit()
        
        # Publish realtime event for status change
        frappe.publish_realtime(
            'transport_job_status_changed',
            {
                'job_name': self.name,
                'status': 'Cancelled',
                'previous_status': previous_status,
                'docstatus': 2
            },
            user=frappe.session.user
        )
        
        # Release capacity if vehicle was assigned
        self.release_capacity()
    
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
    
    def _validate_no_duplicate_transport_order(self):
        """Validate that no duplicate Transport Job exists for the same transport_order and that Transport Order is submitted"""
        if not self.transport_order:
            return  # No transport_order set, skip validation
        
        # Check if Transport Order exists and is submitted
        order_docstatus = frappe.db.get_value("Transport Order", self.transport_order, "docstatus")
        if order_docstatus is None:
            frappe.throw(
                _("Transport Order {0} does not exist.").format(self.transport_order)
            )
        
        if order_docstatus != 1:
            frappe.throw(
                _("Transport Order {0} must be submitted before creating a Transport Job. Please submit the Transport Order first.").format(
                    self.transport_order
                )
            )
        
        # Check for existing Transport Job with the same transport_order
        existing = frappe.db.exists(
            "Transport Job",
            {
                "transport_order": self.transport_order,
                "name": ["!=", self.name]
            }
        )
        
        if existing:
            frappe.throw(
                _("A Transport Job ({0}) already exists for Transport Order {1}. Duplicate Transport Jobs are not allowed.").format(
                    existing,
                    self.transport_order
                )
            )

    def _copy_service_level_from_order(self):
        """Copy logistics_service_level from Transport Order when transport_order is set."""
        if not self.transport_order:
            return
        order_service_level = frappe.db.get_value("Transport Order", self.transport_order, "service_level")
        if order_service_level and not self.get("logistics_service_level"):
            self.logistics_service_level = order_service_level

    def _derive_sla_target_from_service_level(self):
        """Derive sla_target_date from Logistics Service Level module row (Transport)."""
        if not self.get("logistics_service_level"):
            return
        from logistics.logistics.doctype.logistics_service_level.logistics_service_level import get_sla_settings_for_module
        settings = get_sla_settings_for_module(self.logistics_service_level, "Transport")
        if not settings:
            return
        base_opt = (settings.get("sla_target_base_date") or "").strip()
        if base_opt == "Manual on Job":
            return
        base_field_map = {
            "Booking Date": "booking_date",
            "Scheduled Date": "scheduled_date",
            "Job Open Date": "creation",
            "Invoice Date": None,
        }
        base_field = base_field_map.get(base_opt)
        base_value = None
        if base_field == "creation":
            base_value = self.creation if self.get("creation") else None
        elif base_field and self.get(base_field):
            base_value = self.get(base_field)
        elif base_opt == "Invoice Date" and self.get("sales_invoice"):
            base_value = frappe.db.get_value("Sales Invoice", self.sales_invoice, "posting_date")
        if not base_value:
            return
        base_date = getdate(base_value) if base_value else None
        if not base_date:
            return
        days = cint(settings.get("sla_transit_days")) or 0
        end_hour = cint(settings.get("sla_business_day_end_hour"))
        if end_hour is None:
            end_hour = 17
        target_date = add_days(base_date, days)
        target_dt = get_datetime(f"{target_date} {end_hour:02d}:00:00")
        self.sla_target_date = target_dt
        self.sla_target_source = "From Service Level"
    
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
        
        # Check for duplicate transport_leg values
        transport_leg_counts = {}
        for leg in job_legs:
            transport_leg_name = leg.get("transport_leg")
            if transport_leg_name:
                transport_leg_counts[transport_leg_name] = transport_leg_counts.get(transport_leg_name, 0) + 1
        
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
            
            # Check if this transport_leg is a duplicate
            is_duplicate = transport_leg_counts.get(transport_leg_name, 0) > 1
            
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
                    
                    # Don't update run_sheet if there are duplicate transport_leg values
                    # Check for run_sheet from Transport Leg first
                    if not leg.get("run_sheet") and transport_leg.get("run_sheet") and not is_duplicate:
                        leg.run_sheet = transport_leg.run_sheet
                    
                    # If run_sheet is still missing, check if Transport Leg belongs to a consolidation with a run_sheet
                    if not leg.get("run_sheet") and transport_leg.get("transport_consolidation") and not is_duplicate:
                        try:
                            consolidation_name = transport_leg.get("transport_consolidation")
                            consolidation_run_sheet = frappe.db.get_value(
                                "Transport Consolidation",
                                consolidation_name,
                                "run_sheet"
                            )
                            if consolidation_run_sheet:
                                leg.run_sheet = consolidation_run_sheet
                        except Exception as e:
                            frappe.log_error(
                                f"Error fetching run_sheet from Transport Consolidation for leg {transport_leg_name}: {str(e)}",
                                "Transport Job Consolidation Run Sheet Fetch Error"
                            )
                    
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
        """Update status based on job submission and leg statuses
        
        This method automatically determines the correct status based on:
        - Document state (docstatus 0 = Draft, docstatus 1 = Submitted/In Progress/Completed, docstatus 2 = Cancelled)
        - Leg statuses for submitted documents
        - Ensures status always follows docstatus
        """
        if self.is_new():
            # New documents are always Draft
            self.status = "Draft"
            return
        
        # If cancelled (docstatus = 2), status must be Cancelled
        if self.docstatus == 2:
            self.status = "Cancelled"
            return
        
        # If draft (docstatus = 0), status must be Draft
        if self.docstatus == 0:
            self.status = "Draft"
            return
        
        # If submitted (docstatus = 1), check leg statuses to determine job status
        # Default to "Submitted" unless legs indicate "In Progress" or "Completed"
        if self.docstatus == 1:
            legs_field = _get_job_legs_fieldname(self)
            job_legs = self.get(legs_field) or []
            
            if not job_legs:
                # No legs - status should be Submitted
                self.status = "Submitted"
                return
            
            # Get all leg statuses directly from database to ensure we have the latest
            # This is important because leg statuses may have changed since the job was loaded
            leg_statuses = []
            for leg_row in job_legs:
                transport_leg_name = leg_row.get("transport_leg")
                if transport_leg_name:
                    # Always fetch fresh status from database
                    leg_status = frappe.db.get_value("Transport Leg", transport_leg_name, "status")
                    if leg_status:
                        leg_statuses.append(leg_status)
            
            if not leg_statuses:
                # No leg statuses found - default to Submitted
                self.status = "Submitted"
                return
            
            # Determine job status based on leg statuses
            # Map Transport Leg statuses to Transport Job statuses:
            # - "Completed" or "Billed" → "Completed"
            # - "Started" or "Assigned" → "In Progress"
            # - "Open" → "Submitted"
            
            old_status = self.status
            
            if all(status in ["Completed", "Billed"] for status in leg_statuses):
                self.status = "Completed"
                # Trigger auto-billing if status changed to Completed
                if old_status != "Completed":
                    self._trigger_auto_billing()
            elif any(status in ["Started", "Assigned"] for status in leg_statuses):
                self.status = "In Progress"
            elif all(status == "Open" for status in leg_statuses):
                self.status = "Submitted"
            else:
                # Mixed statuses - if any leg is in progress or completed, job is in progress
                if any(status in ["Started", "Assigned", "Completed", "Billed"] for status in leg_statuses):
                    self.status = "In Progress"
                else:
                    # Fallback to Submitted if we can't determine
                    self.status = "Submitted"
    
    @frappe.whitelist()
    def get_milestone_html(self):
        """Generate HTML for milestone visualization in Milestones tab."""
        try:
            from logistics.document_management.milestone_html import build_milestone_html

            legs = self.get("legs") or []
            origin_name = "Pickup"
            destination_name = "Delivery"
            if legs:
                first = legs[0]
                last = legs[-1]
                origin_name = first.get("facility_from") or first.get("pick_address") or "Pickup"
                destination_name = last.get("facility_to") or last.get("drop_address") or "Delivery"

            milestones = frappe.get_all(
                "Job Milestone",
                filters={"job_type": "Transport Job", "job_number": self.name},
                fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
                order_by="planned_start",
            )

            customer_name = self.customer or ""
            detail_items = [
                ("Customer", customer_name),
                ("Status", self.status),
                ("Scheduled", str(self.scheduled_date) if self.scheduled_date else ""),
            ]

            def format_dt(dt):
                return frappe.utils.format_datetime(dt) if dt else None

            return build_milestone_html(
                doctype="Transport Job",
                docname=self.name or "new",
                origin_name=origin_name,
                destination_name=destination_name,
                detail_items=detail_items,
                milestones=milestones,
                format_datetime_fn=format_dt,
                origin_party_name=customer_name,
                destination_party_name="",
            )
        except Exception as e:
            frappe.log_error(f"Error in get_milestone_html: {str(e)}", "Transport Job - Milestone HTML")
            return "<div class='alert alert-danger'>Error loading milestone view. Please check the error log.</div>"

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
    
    # ==================== Capacity Management ====================
    
    def calculate_capacity_requirements(self) -> Dict[str, Any]:
        """
        Calculate total capacity requirements from packages with UOM conversion.
        
        Returns:
            Dictionary with 'weight', 'weight_uom', 'volume', 'volume_uom', 'pallets'
        """
        try:
            from logistics.utils.measurements import (
                convert_weight, convert_volume, calculate_volume_from_dimensions,
                get_default_uoms, get_aggregation_volume_uom,
            )
            default_uoms = get_default_uoms(self.company)
            weight_uom = default_uoms['weight']
            volume_uom = get_aggregation_volume_uom(self.company) or default_uoms['volume']

            total_weight = 0
            total_volume = 0
            total_pallets = 0

            packages = getattr(self, 'packages', []) or []

            for pkg in packages:
                # Weight
                pkg_weight = flt(getattr(pkg, 'weight', 0))
                if pkg_weight > 0:
                    pkg_weight_uom = getattr(pkg, 'weight_uom', None) or weight_uom
                    total_weight += convert_weight(
                        pkg_weight, from_uom=pkg_weight_uom, to_uom=weight_uom, company=self.company
                    )

                # Volume - prefer direct volume, calculate from dimensions if not available
                pkg_volume = flt(getattr(pkg, 'volume', 0))
                if pkg_volume > 0:
                    pkg_volume_uom = getattr(pkg, 'volume_uom', None) or default_uoms['volume']
                    total_volume += convert_volume(
                        pkg_volume, from_uom=pkg_volume_uom, to_uom=volume_uom, company=self.company
                    )
                elif hasattr(pkg, 'length') and hasattr(pkg, 'width') and hasattr(pkg, 'height'):
                    # Calculate from dimensions
                    length = flt(getattr(pkg, 'length', 0))
                    width = flt(getattr(pkg, 'width', 0))
                    height = flt(getattr(pkg, 'height', 0))
                    if length > 0 and width > 0 and height > 0:
                        dim_uom = getattr(pkg, 'dimension_uom', None) or default_uoms['dimension']
                        pkg_volume = calculate_volume_from_dimensions(
                            length, width, height,
                            dimension_uom=dim_uom,
                            volume_uom=volume_uom,
                            company=self.company
                        )
                        total_volume += pkg_volume

                # Pallets
                total_pallets += flt(getattr(pkg, 'no_of_packs', 0))

            return {
                'weight': total_weight,
                'weight_uom': weight_uom,
                'volume': total_volume,
                'volume_uom': volume_uom,
                'pallets': total_pallets
            }
        except Exception:
            raise

    def _update_packing_summary(self):
        """Update total_packages, total_volume, total_weight from packages."""
        packages = getattr(self, "packages", []) or []
        self.total_packages = sum(flt(getattr(p, "no_of_packs", 0) or getattr(p, "quantity", 0) or 1) for p in packages)
        try:
            if self.company:
                req = self.calculate_capacity_requirements()
                self.total_volume = flt(req.get("volume", 0))
                self.total_weight = flt(req.get("weight", 0))
            else:
                self.total_volume = sum(flt(getattr(p, "volume", 0)) for p in packages)
                self.total_weight = sum(flt(getattr(p, "weight", 0)) for p in packages)
        except Exception:
            self.total_volume = sum(flt(getattr(p, "volume", 0)) for p in packages)
            self.total_weight = sum(flt(getattr(p, "weight", 0)) for p in packages)
    
    def validate_vehicle_type_capacity(self):
        """Validate vehicle type capacity when vehicle_type is assigned"""
        if not getattr(self, 'vehicle_type', None):
            return
        
        try:
            from logistics.transport.capacity.capacity_manager import CapacityManager
            from logistics.transport.capacity.vehicle_type_capacity import get_vehicle_type_capacity_info
            
            # Calculate capacity requirements
            requirements = self.calculate_capacity_requirements()
            
            if requirements['weight'] == 0 and requirements['volume'] == 0 and requirements['pallets'] == 0:
                return  # No requirements to validate
            
            # Get vehicle type capacity information
            capacity_info = get_vehicle_type_capacity_info(self.vehicle_type)
            
            # Check capacity with buffer
            buffer = 10.0 / 100.0  # 10% buffer
            
            if requirements['weight'] > 0:
                max_weight = capacity_info.get('max_weight', 0) * (1 - buffer)
                if requirements['weight'] > max_weight:
                    frappe.msgprint(_("Warning: Required weight ({0} {1}) may exceed capacity for vehicle type {2}").format(
                        requirements['weight'], requirements['weight_uom'], self.vehicle_type
                    ), indicator='orange')
            
            if requirements['volume'] > 0:
                max_volume = capacity_info.get('max_volume', 0) * (1 - buffer)
                if requirements['volume'] > max_volume:
                    frappe.msgprint(_("Warning: Required volume ({0} {1}) may exceed capacity for vehicle type {2}").format(
                        requirements['volume'], requirements['volume_uom'], self.vehicle_type
                    ), indicator='orange')
            
            if requirements['pallets'] > 0:
                max_pallets = capacity_info.get('max_pallets', 0) * (1 - buffer)
                if requirements['pallets'] > max_pallets:
                    frappe.msgprint(_("Warning: Required pallets ({0}) may exceed capacity for vehicle type {1}").format(
                        requirements['pallets'], self.vehicle_type
                    ), indicator='orange')
        except ImportError:
            # Capacity management not fully implemented yet
            pass
        except Exception as e:
            frappe.log_error(f"Error validating vehicle type capacity: {str(e)}", "Capacity Validation Error")
    
    def validate_capacity(self):
        """Validate capacity if vehicle is assigned"""
        if not getattr(self, 'vehicle', None):
            return
        
        try:
            from logistics.transport.capacity.capacity_manager import CapacityManager
            
            requirements = self.calculate_capacity_requirements()
            
            if requirements['weight'] == 0 and requirements['volume'] == 0 and requirements['pallets'] == 0:
                return  # No requirements to validate
            
            manager = CapacityManager(self.company)
            check_result = manager.check_capacity_sufficient(
                self.vehicle,
                {
                    'weight': requirements['weight'],
                    'volume': requirements['volume'],
                    'pallets': requirements['pallets']
                }
            )
            
            if not check_result['sufficient']:
                if manager.settings.get('strict_validation', True):
                    frappe.throw(_("Insufficient vehicle capacity:\n{0}").format(
                        "\n".join(check_result['warnings'])
                    ))
                else:
                    for warning in check_result['warnings']:
                        frappe.msgprint(warning, indicator='orange')
            elif check_result['warnings']:
                for warning in check_result['warnings']:
                    frappe.msgprint(warning, indicator='yellow')
        except ImportError:
            # Capacity management not fully implemented yet
            pass
        except Exception as e:
            frappe.log_error(f"Error validating capacity: {str(e)}", "Capacity Validation Error")
    
    def reserve_capacity(self):
        """Reserve capacity when job is assigned to vehicle"""
        if not getattr(self, 'vehicle', None) or self.docstatus != 1:  # Only for submitted jobs
            return
        
        try:
            from logistics.transport.capacity.capacity_reserver import reserve_job_capacity
            reserve_job_capacity(self)
        except ImportError:
            # Capacity reserver not implemented yet
            pass
        except Exception as e:
            frappe.log_error(f"Error reserving capacity: {str(e)}", "Capacity Reservation Error")
    
    def release_capacity(self):
        """Release capacity when job is completed/cancelled"""
        if not getattr(self, 'vehicle', None):
            return
        
        try:
            from logistics.transport.capacity.capacity_reserver import release_job_capacity
            release_job_capacity(self)
        except ImportError:
            # Capacity reserver not implemented yet
            pass
        except Exception as e:
            frappe.log_error(f"Error releasing capacity: {str(e)}", "Capacity Release Error")

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
    
    # Validate Transport Job status is "Completed"
    if getattr(job, "status", None) != "Completed":
        frappe.throw(_("Sales Invoice can only be created when Transport Job status is 'Completed'. Current status: {0}").format(job.status or "Draft"))
    
    # Validate required fields
    if not job.customer:
        frappe.throw(_("Customer is required to create Sales Invoice. Please set a customer on the Transport Job."))
    
    if not job.company:
        frappe.throw(_("Company is required to create Sales Invoice. Please set a company on the Transport Job."))
    
    # Validate all legs are completed
    _validate_all_legs_completed(job)
    
    # Check if Sales Invoice already exists for this job
    existing_sales_invoice = getattr(job, "sales_invoice", None)
    if existing_sales_invoice:
        # Check if the Sales Invoice actually exists (it might have been deleted)
        if frappe.db.exists("Sales Invoice", existing_sales_invoice):
            frappe.throw(_("Sales Invoice {0} already exists for this Transport Job.").format(existing_sales_invoice))
        else:
            # Sales Invoice was deleted, clear the stale reference
            frappe.db.set_value("Transport Job", job.name, "sales_invoice", None, update_modified=False)
            frappe.db.commit()
            # Reload the job document to get the updated value
            job.reload()
            frappe.msgprint(
                _("Cleared stale reference to deleted Sales Invoice {0}. You can now create a new Sales Invoice.").format(existing_sales_invoice),
                indicator="blue"
            )
    
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
    
    # Check if there are any charges with item_code
    valid_charges_count = 0
    if charges:
        valid_charges = [ch for ch in charges if getattr(ch, "item_code", None)]
        valid_charges_count = len(valid_charges)
        if not valid_charges:
            frappe.throw(_("Transport Job has charges but none have an Item Code. Please set Item Code on the charges before creating Sales Invoice."))
    
    items_created = 0
    if charges:
        # Create items from charges
        for charge in charges:
            item_code = getattr(charge, "item_code", None)
            if not item_code:
                # Skip charges without item_code
                continue
            
            item_name = getattr(charge, "item_name", None) or "Transport Service"
            qty = flt(getattr(charge, "quantity", 1))
            
            # Transport Job Charges uses 'unit_rate' and 'estimated_revenue'
            # Use estimated_revenue if available, otherwise use unit_rate
            unit_rate = flt(getattr(charge, "unit_rate", 0))
            estimated_revenue = flt(getattr(charge, "estimated_revenue", 0))
            
            # Calculate rate: prefer estimated_revenue, fallback to unit_rate
            # If estimated_revenue exists, calculate rate from it
            if estimated_revenue > 0:
                rate = estimated_revenue / qty if qty > 0 else estimated_revenue
            elif unit_rate > 0:
                rate = unit_rate
            else:
                rate = 0
            
            item_payload = {
                "item_code": item_code,
                "item_name": item_name,
                "qty": qty,
                "rate": rate
            }
            
            # Add UOM if available
            uom = getattr(charge, "uom", None)
            if uom and "uom" in si_item_fields:
                item_payload["uom"] = uom
            
            # Add description if available (use item_name or revenue_calc_notes)
            description = getattr(charge, "revenue_calc_notes", None)
            if description and "description" in si_item_fields:
                item_payload["description"] = description
            elif item_name and "description" in si_item_fields:
                item_payload["description"] = item_name
            
            # Add accounting fields to Sales Invoice Item
            if getattr(job, "cost_center", None) and "cost_center" in si_item_fields:
                item_payload["cost_center"] = job.cost_center
            if getattr(job, "profit_center", None) and "profit_center" in si_item_fields:
                item_payload["profit_center"] = job.profit_center
            # Link to job for Recognition Engine and lifecycle tracking
            if "reference_doctype" in si_item_fields and "reference_name" in si_item_fields:
                item_payload["reference_doctype"] = job.doctype
                item_payload["reference_name"] = job.name
            
            si.append("items", item_payload)
            items_created += 1
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
        if "reference_doctype" in si_item_fields and "reference_name" in si_item_fields:
            item_payload["reference_doctype"] = job.doctype
            item_payload["reference_name"] = job.name
        
        si.append("items", item_payload)
        items_created += 1
    
    # Validate that at least one item was created
    if items_created == 0:
        frappe.throw(_("Cannot create Sales Invoice. No valid items could be created from the charges. Please ensure charges have Item Code and valid amounts."))
    
    # Set missing values and insert
    si.set_missing_values()
    si.insert(ignore_permissions=True)
    
    # Update Transport Job with Sales Invoice reference and lifecycle
    from frappe.utils import today
    updates = {"sales_invoice": si.name, "date_sales_invoice_requested": today()}
    for k, v in updates.items():
        frappe.db.set_value("Transport Job", job.name, k, v, update_modified=False)
    
    return {
        "ok": True,
        "message": _("Sales Invoice {0} created successfully.").format(si.name),
        "sales_invoice": si.name,
        "charges_used": valid_charges_count,
        "items_created": items_created
    }


def _validate_all_legs_completed(job: Document) -> None:
    """Validate that all legs in the Transport Job are completed or billed"""
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
        # Accept both "Completed" and "Billed" statuses as valid for billing
        if leg_doc.status not in ["Completed", "Billed"]:
            incomplete_legs.append(leg_doc)
    
    if incomplete_legs:
        incomplete_names = [leg.name for leg in incomplete_legs]
        incomplete_statuses = [f"{leg.name} ({leg.status})" for leg in incomplete_legs]
        frappe.throw(_("Cannot create Sales Invoice. The following legs are not completed: {0}").format(", ".join(incomplete_statuses)))


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
    
    # Check for duplicate transport_leg values
    transport_leg_counts = {}
    for leg in job_legs:
        transport_leg_name = leg.get("transport_leg")
        if transport_leg_name:
            transport_leg_counts[transport_leg_name] = transport_leg_counts.get(transport_leg_name, 0) + 1
    
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
        
        # Check if this transport_leg is a duplicate
        is_duplicate = transport_leg_counts.get(transport_leg_name, 0) > 1
        
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
                
                # Don't update run_sheet if there are duplicate transport_leg values
                # Check for run_sheet from Transport Leg first
                if not leg.get("run_sheet") and transport_leg.get("run_sheet") and not is_duplicate:
                    frappe.db.set_value("Transport Job Legs", leg.name, "run_sheet", 
                                       transport_leg.run_sheet, update_modified=False)
                    updated_this_leg = True
                
                # If run_sheet is still missing, check if Transport Leg belongs to a consolidation with a run_sheet
                if not leg.get("run_sheet") and transport_leg.get("transport_consolidation") and not is_duplicate:
                    try:
                        consolidation_name = transport_leg.get("transport_consolidation")
                        consolidation_run_sheet = frappe.db.get_value(
                            "Transport Consolidation",
                            consolidation_name,
                            "run_sheet"
                        )
                        if consolidation_run_sheet:
                            frappe.db.set_value("Transport Job Legs", leg.name, "run_sheet", 
                                               consolidation_run_sheet, update_modified=False)
                            updated_this_leg = True
                    except Exception as e:
                        frappe.log_error(
                            f"Error fetching run_sheet from Transport Consolidation for leg {transport_leg_name}: {str(e)}",
                            "Fetch Missing Leg Data Error"
                        )
                
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
        
        # Always check for consolidation run_sheet, even if other fields are not missing
        # But skip if this transport_leg is a duplicate
        is_duplicate = transport_leg_counts.get(transport_leg_name, 0) > 1
        if not leg.get("run_sheet") and not is_duplicate:
            try:
                transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
                if transport_leg.get("transport_consolidation"):
                    consolidation_name = transport_leg.get("transport_consolidation")
                    consolidation_run_sheet = frappe.db.get_value(
                        "Transport Consolidation",
                        consolidation_name,
                        "run_sheet"
                    )
                    if consolidation_run_sheet:
                        frappe.db.set_value("Transport Job Legs", leg.name, "run_sheet", 
                                           consolidation_run_sheet, update_modified=False)
                        updated_count += 1
            except Exception as e:
                frappe.log_error(
                    f"Error fetching run_sheet from Transport Consolidation for leg {transport_leg_name}: {str(e)}",
                    "Fetch Missing Leg Data Error"
                )
    
    # Commit the changes
    frappe.db.commit()
    
    return {
        "ok": True,
        "updated_count": updated_count,
        "message": _("Updated {0} leg(s) with missing data").format(updated_count)
    }


@frappe.whitelist()
def fix_submitted_job_status(job_name: str) -> Dict[str, Any]:
    """
    Fix status for a submitted Transport Job that is still showing as Draft.
    This can happen if after_submit hook didn't run properly.
    
    Args:
        job_name: Name of the Transport Job
        
    Returns:
        Dict with status and updated status value
    """
    if not job_name:
        frappe.throw(_("Transport Job name is required"))
    
    # Get current status from database directly
    current_status = frappe.db.get_value("Transport Job", job_name, "status")
    current_docstatus = frappe.db.get_value("Transport Job", job_name, "docstatus")
    
    # Only fix if document is submitted but status is Draft or None
    if current_docstatus == 1 and (not current_status or current_status == "Draft"):
        job = frappe.get_doc("Transport Job", job_name)
        job.docstatus = 1  # Ensure docstatus is set for update_status
        
        # First, always set to "Submitted" for submitted documents
        frappe.db.set_value("Transport Job", job_name, "status", "Submitted", update_modified=False)
        frappe.db.commit()
        
        # Then call update_status to determine correct status based on leg statuses
        job.reload()
        job.update_status()
        new_status = job.status
        
        # If update_status determined a different status (In Progress or Completed), update it
        # But ensure it's never "Draft" for a submitted document
        if new_status and new_status != "Draft" and new_status != "Submitted":
            frappe.db.set_value("Transport Job", job_name, "status", new_status, update_modified=False)
            frappe.db.commit()
        elif not new_status or new_status == "Draft":
            # Fallback: ensure status is always "Submitted" for submitted documents
            frappe.db.set_value("Transport Job", job_name, "status", "Submitted", update_modified=False)
            frappe.db.commit()
            new_status = "Submitted"
        
        return {
            "ok": True,
            "message": _("Status updated from {0} to {1}").format(current_status or "Draft", new_status),
            "old_status": current_status or "Draft",
            "new_status": new_status
        }
    else:
        return {
            "ok": False,
            "message": _("Document is not submitted or status is already correct"),
            "current_status": current_status,
            "docstatus": current_docstatus
        }


@frappe.whitelist()
def update_run_sheet_from_consolidation(job_name: str):
    """
    Update run_sheet in Transport Job Legs from Transport Consolidation if available.
    This works even for submitted documents.
    
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
    
    updated_count = 0
    
    for leg in job_legs:
        transport_leg_name = leg.get("transport_leg")
        if not transport_leg_name:
            continue
        
        # Only update if run_sheet is missing
        if not leg.get("run_sheet"):
            try:
                transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
                if transport_leg.get("transport_consolidation"):
                    consolidation_name = transport_leg.get("transport_consolidation")
                    consolidation_run_sheet = frappe.db.get_value(
                        "Transport Consolidation",
                        consolidation_name,
                        "run_sheet"
                    )
                    if consolidation_run_sheet:
                        frappe.db.set_value("Transport Job Legs", leg.name, "run_sheet", 
                                           consolidation_run_sheet, update_modified=False)
                        updated_count += 1
            except Exception as e:
                frappe.log_error(
                    f"Error fetching run_sheet from Transport Consolidation for leg {transport_leg_name}: {str(e)}",
                    "Update Run Sheet From Consolidation Error"
                )
    
    # Commit the changes
    if updated_count > 0:
        frappe.db.commit()
    
    return {
        "ok": True,
        "updated_count": updated_count,
        "message": _("Updated {0} leg(s) with run_sheet from consolidation").format(updated_count) if updated_count > 0 else _("No updates needed")
    }


@frappe.whitelist()
def update_run_sheet_from_transport_leg(job_name: str):
    """
    Update run_sheet in Transport Job Legs from Transport Leg if available.
    This works even for submitted documents.
    This ensures that when a Run Sheet is created from a Transport Job,
    the run_sheet field in the legs child table is populated dynamically.
    
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
    
    updated_count = 0
    
    for leg in job_legs:
        transport_leg_name = leg.get("transport_leg")
        if not transport_leg_name:
            continue
        
        # Get run_sheet from Transport Leg
        try:
            transport_leg_run_sheet = frappe.db.get_value("Transport Leg", transport_leg_name, "run_sheet")
            
            # Update if Transport Leg has a run_sheet and it's different from the child table value
            if transport_leg_run_sheet and transport_leg_run_sheet != leg.get("run_sheet"):
                frappe.db.set_value("Transport Job Legs", leg.name, "run_sheet", 
                                   transport_leg_run_sheet, update_modified=False)
                updated_count += 1
        except Exception as e:
            frappe.log_error(
                f"Error fetching run_sheet from Transport Leg {transport_leg_name} for Transport Job {job_name}: {str(e)}",
                "Update Run Sheet From Transport Leg Error"
            )
    
    # Commit the changes
    if updated_count > 0:
        frappe.db.commit()
    
    return {
        "ok": True,
        "updated_count": updated_count,
        "message": _("Updated {0} leg(s) with run_sheet from Transport Leg").format(updated_count) if updated_count > 0 else _("No updates needed")
    }
