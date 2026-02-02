# logistics/transport/doctype/transport_leg/transport_leg.py

import frappe
from frappe.model.document import Document


class TransportLeg(Document):
    def validate(self):
        """Validate Transport Leg data"""
        self.validate_required_fields()
        self.validate_time_windows()
        self.validate_route_compatibility()
        self.update_status()
    
    def update_status(self):
        """Update the status field based on start_date, end_date, run_sheet assignment, and sales_invoice"""
        if self.sales_invoice:
            # If sales_invoice is set, status should be "Billed" (highest priority)
            self.status = "Billed"
        elif self.end_date:
            # If end_date is set, status should be "Completed"
            self.status = "Completed"
        elif self.start_date:
            # If start_date is set but no end_date, status should be "Started"
            self.status = "Started"
        elif self.run_sheet:
            # If run_sheet is assigned but not started, status should be "Assigned"
            self.status = "Assigned"
        else:
            # If no run_sheet is assigned and no dates are set, status should be "Open"
            self.status = "Open"
    
    def before_save(self):
        """Ensure status is updated before saving"""
        self.update_status()
        self.track_run_sheet_change()
        self.auto_fill_addresses()
    
    def after_save(self):
        """Sync changes back to Run Sheet and trigger auto-vehicle assignment after Transport Leg is saved"""
        self.sync_to_run_sheet()
        self.sync_route_to_run_sheet()
        self.update_transport_job_status()
        self.update_run_sheet_status()
        self._trigger_auto_vehicle_assignment()
    
    def on_trash(self):
        """Remove this leg from Run Sheet when Transport Leg is deleted"""
        self.remove_from_run_sheet()
    
    def track_run_sheet_change(self):
        """Track if run_sheet field has changed"""
        if not self.is_new():
            old_run_sheet = frappe.db.get_value("Transport Leg", self.name, "run_sheet")
            self._old_run_sheet = old_run_sheet
        else:
            self._old_run_sheet = None
    
    def sync_to_run_sheet(self):
        """
        Sync Transport Leg changes to Run Sheet Leg child table.
        This ensures Run Sheet Leg reflects the latest Transport Leg data.
        """
        # Handle run_sheet field changes
        old_run_sheet = getattr(self, "_old_run_sheet", None)
        
        # If run_sheet changed from one sheet to another
        if old_run_sheet and old_run_sheet != self.run_sheet:
            # Remove from old Run Sheet
            self._remove_leg_from_run_sheet(old_run_sheet)
        
        # If assigned to a new Run Sheet
        if self.run_sheet:
            self._add_or_update_leg_in_run_sheet(self.run_sheet)
        
        # If run_sheet was cleared
        elif old_run_sheet and not self.run_sheet:
            self._remove_leg_from_run_sheet(old_run_sheet)
    
    def _add_or_update_leg_in_run_sheet(self, run_sheet_name):
        """Add or update this leg in the Run Sheet's legs table"""
        try:
            # Check if Run Sheet exists
            if not frappe.db.exists("Run Sheet", run_sheet_name):
                return
            
            # Get the Run Sheet
            rs = frappe.get_doc("Run Sheet", run_sheet_name)
            
            # Check if this leg already exists in the child table
            existing_row = None
            for row in rs.legs:
                if row.transport_leg == self.name:
                    existing_row = row
                    break
            
            if not existing_row:
                # Add new row
                rs.append("legs", {
                    "transport_leg": self.name,
                    # Other fields will be auto-fetched via fetch_from
                })
                rs.save(ignore_permissions=True)
            else:
                # Row exists - fields will auto-refresh via fetch_from on next load
                # But we can force a save to trigger fetch
                rs.save(ignore_permissions=True)
        
        except Exception as e:
            frappe.log_error(f"Error syncing Transport Leg {self.name} to Run Sheet {run_sheet_name}: {str(e)}")
    
    def _remove_leg_from_run_sheet(self, run_sheet_name):
        """Remove this leg from the specified Run Sheet's legs table"""
        try:
            if not frappe.db.exists("Run Sheet", run_sheet_name):
                return
            
            # Get the Run Sheet
            rs = frappe.get_doc("Run Sheet", run_sheet_name)
            
            # Find and remove the row
            for row in list(rs.legs):
                if row.transport_leg == self.name:
                    rs.remove(row)
            
            rs.save(ignore_permissions=True)
        
        except Exception as e:
            frappe.log_error(f"Error removing Transport Leg {self.name} from Run Sheet {run_sheet_name}: {str(e)}")
    
    def remove_from_run_sheet(self):
        """Remove this leg from its Run Sheet when Transport Leg is deleted"""
        if self.run_sheet:
            self._remove_leg_from_run_sheet(self.run_sheet)
    
    def auto_fill_addresses(self):
        """Auto-fill pick_address and drop_address based on facility primary addresses"""
        # Auto-fill pick_address if not already set
        if not self.pick_address and self.facility_type_from and self.facility_from:
            primary_address = self._get_primary_address(self.facility_type_from, self.facility_from)
            if primary_address:
                self.pick_address = primary_address
        
        # Auto-fill drop_address if not already set
        if not self.drop_address and self.facility_type_to and self.facility_to:
            primary_address = self._get_primary_address(self.facility_type_to, self.facility_to)
            if primary_address:
                self.drop_address = primary_address
    
    def sync_route_to_run_sheet(self):
        """Sync route changes from Transport Leg to Run Sheet - recalculate combined route"""
        if not self.run_sheet:
            return
        
        try:
            # When a leg's route changes, we need to recalculate the Run Sheet's combined route
            # This will be done by clearing the Run Sheet route so it gets recalculated on next load
            run_sheet = frappe.get_doc("Run Sheet", self.run_sheet)
            
            # Clear the saved route so it gets recalculated with updated leg routes
            if hasattr(run_sheet, "selected_route_polyline"):
                run_sheet.selected_route_polyline = None
            if hasattr(run_sheet, "selected_route_index"):
                run_sheet.selected_route_index = None
            
            run_sheet.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error syncing route from Transport Leg {self.name} to Run Sheet: {str(e)}")
    
    def _get_primary_address(self, facility_type, facility_name):
        """Get the primary address for a facility"""
        try:
            # Map facility types to their primary address field names
            primary_address_fields = {
                "Shipper": "shipper_primary_address",
                "Consignee": "consignee_primary_address", 
                "Container Yard": "containeryard_primary_address",
                "Container Depot": "containerdepot_primary_address",
                "Container Freight Station": "cfs_primary_address",
                "Transport Terminal": "transportterminal_primary_address"
            }
            
            # Get the primary address field name for this facility type
            primary_address_field = primary_address_fields.get(facility_type)
            
            if primary_address_field:
                # Get the facility document and its primary address
                facility_doc = frappe.get_doc(facility_type, facility_name)
                primary_address = getattr(facility_doc, primary_address_field, None)
                
                if primary_address:
                    return primary_address
            
            # Fallback: For facility types without primary address fields (Storage Facility, Truck Park)
            # or if primary address is not set, get addresses linked to this facility
            addresses = frappe.get_all("Address",
                filters={
                    "link_doctype": facility_type,
                    "link_name": facility_name
                },
                fields=["name", "is_primary_address", "is_shipping_address"],
                order_by="is_primary_address DESC, is_shipping_address DESC, creation ASC"
            )
            
            if addresses:
                # Return the primary address, or shipping address, or first address
                for address in addresses:
                    if address.is_primary_address or address.is_shipping_address:
                        return address.name
                return addresses[0].name
            
        except Exception as e:
            frappe.log_error(f"Error getting primary address for {facility_type} {facility_name}: {str(e)}")
        
        return None
    
    def validate_required_fields(self):
        """Validate required fields are present"""
        from frappe import _
        
        if not self.transport_job:
            frappe.throw(_("Transport Job is required"))
        if not self.vehicle_type:
            frappe.throw(_("Vehicle Type is required"))
        if not self.facility_from:
            frappe.throw(_("Pick Facility is required"))
        if not self.facility_to:
            frappe.throw(_("Drop Facility is required"))
    
    def validate_time_windows(self):
        """Validate time windows are logical"""
        from frappe import _
        from frappe.utils import get_time, getdate
        from datetime import datetime, date, time
        
        # Get the date to combine with time values
        leg_date = self.date or self.run_date or frappe.utils.today()
        if isinstance(leg_date, str):
            leg_date = getdate(leg_date)
        elif not isinstance(leg_date, date):
            leg_date = getdate(leg_date)
        
        if self.pick_window_start and self.pick_window_end:
            pick_start_time = get_time(self.pick_window_start)
            pick_end_time = get_time(self.pick_window_end)
            # Ensure we have time objects, not timedelta
            if isinstance(pick_start_time, time) and isinstance(pick_end_time, time):
                pick_start = datetime.combine(leg_date, pick_start_time)
                pick_end = datetime.combine(leg_date, pick_end_time)
                if pick_end <= pick_start:
                    frappe.throw(_("Pick Window End must be after Pick Window Start"))
        
        if self.drop_window_start and self.drop_window_end:
            drop_start_time = get_time(self.drop_window_start)
            drop_end_time = get_time(self.drop_window_end)
            # Ensure we have time objects, not timedelta
            if isinstance(drop_start_time, time) and isinstance(drop_end_time, time):
                drop_start = datetime.combine(leg_date, drop_start_time)
                drop_end = datetime.combine(leg_date, drop_end_time)
                if drop_end <= drop_start:
                    frappe.throw(_("Drop Window End must be after Drop Window Start"))
        
        # Note: Pick and Drop window settings are independent settings from their respective addresses
        # and should not be compared to each other. They are validated separately above.
    
    def validate_route_compatibility(self):
        """Validate route compatibility"""
        from frappe import _
        
        if self.facility_from == self.facility_to:
            frappe.throw(_("Pick Facility and Drop Facility cannot be the same"))
        
        # Warn if distance seems unreasonable (e.g., negative or extremely large)
        if hasattr(self, "distance_km") and self.distance_km:
            if self.distance_km < 0:
                frappe.throw(_("Distance cannot be negative"))
            if self.distance_km > 10000:  # 10,000 km seems like an upper bound for most transport
                frappe.msgprint(_("Warning: Distance ({0} km) seems unusually large. Please verify the route.").format(self.distance_km), indicator="orange")
    
    def update_transport_job_status(self):
        """Update the parent Transport Job status when this leg's status changes"""
        if not self.transport_job:
            return
        
        try:
            # Check database directly for current status
            db_status = frappe.db.get_value("Transport Job", self.transport_job, "status")
            db_docstatus = frappe.db.get_value("Transport Job", self.transport_job, "docstatus")
            
            # Only update if job is submitted
            if db_docstatus != 1:
                return
            
            # Fetch all legs for this job directly from database to ensure we have the latest data
            # This is more reliable than relying on the child table which might be cached
            # IMPORTANT: We need to use the current leg's in-memory status (self.status) instead of
            # the database value, because the database might not be updated yet when after_save() runs
            leg_statuses_data = frappe.db.get_all(
                "Transport Leg",
                filters={"transport_job": self.transport_job, "docstatus": ["<", 2]},
                fields=["name", "status"]
            )
            
            # Build leg_statuses list, replacing the current leg's status with in-memory value
            # This ensures we use the most up-to-date status for the current leg
            leg_statuses = []
            current_leg_found = False
            for leg in leg_statuses_data:
                if leg.name == self.name:
                    # Use the in-memory status for the current leg (most up-to-date)
                    if self.status:
                        leg_statuses.append(self.status)
                    current_leg_found = True
                else:
                    if leg.status:
                        leg_statuses.append(leg.status)
            
            # If current leg wasn't found in the query (shouldn't happen, but safety check)
            if not current_leg_found and self.status:
                leg_statuses.append(self.status)
            
            # Compute new_status using the same logic as TransportJob.update_status()
            # This ensures consistency across the codebase
            if not leg_statuses:
                # No legs found - default to Submitted
                new_status = "Submitted"
            else:
                # Determine job status based on leg statuses
                # Map Transport Leg statuses to Transport Job statuses:
                # - "Completed" or "Billed" → "Completed"
                # - "Started" or "Assigned" → "In Progress"
                # - "Open" → "Submitted"
                # This logic matches TransportJob.update_status() exactly
                if all(status in ["Completed", "Billed"] for status in leg_statuses):
                    new_status = "Completed"
                elif any(status in ["Started", "Assigned"] for status in leg_statuses):
                    new_status = "In Progress"
                elif all(status == "Open" for status in leg_statuses):
                    new_status = "Submitted"
                else:
                    # Mixed statuses - if any leg is in progress or completed, job is in progress
                    if any(status in ["Started", "Assigned", "Completed", "Billed"] for status in leg_statuses):
                        new_status = "In Progress"
                    else:
                        # Fallback to Submitted if we can't determine
                        new_status = "Submitted"
            
            # Ensure status is never "Draft" for submitted documents
            if not new_status or new_status == "Draft":
                new_status = "Submitted"
            
            # Only update if status actually changed
            # This prevents unnecessary database writes and realtime events
            if new_status != db_status:
                # Use frappe.db.set_value instead of raw SQL for better safety and consistency
                # update_modified=False to avoid changing the modified timestamp unnecessarily
                frappe.db.set_value(
                    "Transport Job",
                    self.transport_job,
                    "status",
                    new_status,
                    update_modified=False
                )
                frappe.db.commit()
                
                # Log if status changed significantly (for debugging)
                if db_status == "Submitted" and new_status in ["In Progress", "Completed"]:
                    frappe.log_error(
                        f"Transport Job {self.transport_job} status updated from '{db_status}' to '{new_status}' via leg {self.name} (status: {self.status}). "
                        f"All leg statuses: {leg_statuses}",
                        "Transport Job Status Update via Leg"
                    )
                
                # Only publish realtime event when status actually changed
                # This ensures clients only receive events for real status changes
                frappe.publish_realtime(
                    'transport_job_status_changed',
                    {
                        'job_name': self.transport_job,
                        'status': new_status,
                        'previous_status': db_status,
                        'docstatus': db_docstatus,
                        'triggered_by': 'transport_leg',
                        'leg_name': self.name,
                        'leg_status': self.status
                    },
                    user=frappe.session.user
                )
            else:
                # Log when status should change but doesn't (for debugging)
                if self.status in ["Started", "Assigned"] and new_status == "In Progress" and db_status != "In Progress":
                    frappe.log_error(
                        f"Transport Job {self.transport_job} status should be 'In Progress' but is '{db_status}'. "
                        f"Leg {self.name} status: {self.status}, All leg statuses: {leg_statuses}, Calculated new_status: {new_status}",
                        "Transport Job Status Update Issue"
                    )
        except Exception as e:
            frappe.log_error(f"Error updating Transport Job status for leg {self.name}: {str(e)}", "Transport Leg Status Update Error")
    
    def update_run_sheet_status(self):
        """Update the parent Run Sheet status when this leg's status changes"""
        if not self.run_sheet:
            return
        
        try:
            # Check database directly for current status
            db_status = frappe.db.get_value("Run Sheet", self.run_sheet, "status")
            db_docstatus = frappe.db.get_value("Run Sheet", self.run_sheet, "docstatus")
            
            # Only update if Run Sheet is submitted
            if db_docstatus != 1:
                return
            
            # Don't auto-update if status is manually set to "Hold"
            if db_status == "Hold":
                return
            
            # Get all legs for this Run Sheet directly from database to ensure we have the latest data
            # IMPORTANT: We need to use the current leg's in-memory status (self.status) instead of
            # the database value, because the database might not be updated yet when after_save() runs
            leg_statuses_data = frappe.db.get_all(
                "Transport Leg",
                filters={"run_sheet": self.run_sheet, "docstatus": ["<", 2]},
                fields=["name", "status"]
            )
            
            # Build leg_statuses list, replacing the current leg's status with in-memory value
            # This ensures we use the most up-to-date status for the current leg
            leg_statuses = []
            current_leg_found = False
            for leg in leg_statuses_data:
                if leg.name == self.name:
                    # Use the in-memory status for the current leg (most up-to-date)
                    if self.status:
                        leg_statuses.append(self.status)
                    current_leg_found = True
                else:
                    if leg.status:
                        leg_statuses.append(leg.status)
            
            # If current leg wasn't found in the query (shouldn't happen, but safety check)
            if not current_leg_found and self.status:
                leg_statuses.append(self.status)
            
            # Compute new_status using the same logic as RunSheet.update_status()
            if not leg_statuses:
                # No legs found - default to Dispatched
                new_status = "Dispatched"
            else:
                # Determine Run Sheet status based on leg statuses
                # Map Transport Leg statuses to Run Sheet statuses:
                # - "Completed" or "Billed" → "Completed" (if all legs are completed)
                # - "Started" → "In-Progress" (if any leg is started)
                # - "Assigned" → "Dispatched" (if any leg is assigned but not started)
                # - "Open" → "Dispatched" (if all legs are open)
                if all(status in ["Completed", "Billed"] for status in leg_statuses):
                    new_status = "Completed"
                elif any(status == "Started" for status in leg_statuses):
                    # If any leg is started, status is In-Progress
                    new_status = "In-Progress"
                elif any(status == "Assigned" for status in leg_statuses):
                    # If any leg is assigned (but not started), status is Dispatched
                    new_status = "Dispatched"
                elif all(status == "Open" for status in leg_statuses):
                    # If all legs are open, status is Dispatched
                    new_status = "Dispatched"
                else:
                    # Mixed statuses - prioritize Started > Assigned > Completed
                    if any(status == "Started" for status in leg_statuses):
                        new_status = "In-Progress"
                    elif any(status == "Assigned" for status in leg_statuses):
                        new_status = "Dispatched"
                    elif any(status in ["Completed", "Billed"] for status in leg_statuses):
                        # If some legs are completed but not all, status is In-Progress
                        new_status = "In-Progress"
                    else:
                        # Fallback to Dispatched if we can't determine
                        new_status = "Dispatched"
            
            # Only update if status actually changed
            # This prevents unnecessary database writes
            if new_status != db_status:
                # Use frappe.db.set_value instead of raw SQL for better safety and consistency
                # update_modified=False to avoid changing the modified timestamp unnecessarily
                frappe.db.set_value(
                    "Run Sheet",
                    self.run_sheet,
                    "status",
                    new_status,
                    update_modified=False
                )
                frappe.db.commit()
                
                # Log if status changed significantly (for debugging)
                if db_status == "Dispatched" and new_status in ["In-Progress", "Completed"]:
                    frappe.log_error(
                        f"Run Sheet {self.run_sheet} status updated from '{db_status}' to '{new_status}' via leg {self.name} (status: {self.status}). "
                        f"All leg statuses: {leg_statuses}",
                        "Run Sheet Status Update via Leg"
                    )
        except Exception as e:
            frappe.log_error(f"Error updating Run Sheet status for leg {self.name}: {str(e)}", "Transport Leg Run Sheet Status Update Error")
    
    def _trigger_auto_vehicle_assignment(self):
        """Trigger auto-vehicle assignment if enabled and leg doesn't have a run sheet"""
        if self.run_sheet:
            return
        
        try:
            from logistics.transport.automation_helpers import auto_assign_vehicle_to_leg
            auto_assign_vehicle_to_leg(self)
        except Exception as e:
            frappe.log_error(f"Error triggering auto-vehicle assignment for leg {self.name}: {str(e)}", "Auto Vehicle Assignment Error")


@frappe.whitelist()
def force_status_update(name: str):
    """Force a status update on a Transport Leg by triggering save hooks"""
    try:
        leg_doc = frappe.get_doc("Transport Leg", name)
        leg_doc.save(ignore_permissions=True)
        return {"ok": True, "status": leg_doc.status}
    except Exception as e:
        frappe.log_error(f"Error forcing status update for Transport Leg {name}: {str(e)}")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def test_status_update(name: str, test_start_date: str = None, test_end_date: str = None):
    """Test status update by setting dates and checking if status updates correctly"""
    try:
        leg_doc = frappe.get_doc("Transport Leg", name)
        
        # Store original values
        original_start = leg_doc.start_date
        original_end = leg_doc.end_date
        original_status = leg_doc.status
        
        # Set test dates if provided
        if test_start_date:
            leg_doc.start_date = test_start_date
        if test_end_date:
            leg_doc.end_date = test_end_date
            
        # Save and check status
        leg_doc.save(ignore_permissions=True)
        new_status = leg_doc.status
        
        return {
            "ok": True, 
            "name": name,
            "original_start": original_start,
            "original_end": original_end, 
            "original_status": original_status,
            "new_start": leg_doc.start_date,
            "new_end": leg_doc.end_date,
            "new_status": new_status,
            "status_changed": original_status != new_status
        }
    except Exception as e:
        frappe.log_error(f"Error testing status update for Transport Leg {name}: {str(e)}")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def set_dates_and_update_status(name: str, start_date: str = None, end_date: str = None):
    """Set dates on Transport Leg and ensure status is properly updated"""
    try:
        leg_doc = frappe.get_doc("Transport Leg", name)
        
        # Set dates if provided
        if start_date:
            leg_doc.start_date = start_date
        if end_date:
            leg_doc.end_date = end_date
            
        # Explicitly call update_status to ensure it's updated
        leg_doc.update_status()
        
        # Save the document
        leg_doc.save(ignore_permissions=True)
        
        return {
            "ok": True,
            "name": name,
            "start_date": leg_doc.start_date,
            "end_date": leg_doc.end_date,
            "status": leg_doc.status
        }
    except Exception as e:
        frappe.log_error(f"Error setting dates and updating status for Transport Leg {name}: {str(e)}")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def fix_status_for_submitted_legs():
    """Fix status for all submitted Transport Legs that have incorrect status"""
    try:
        # Get all submitted Transport Legs
        legs = frappe.get_all("Transport Leg", 
                             filters={"docstatus": 1}, 
                             fields=["name", "status", "start_date", "end_date", "run_sheet", "sales_invoice"])
        
        fixed_count = 0
        results = []
        
        for leg_data in legs:
            leg_name = leg_data.name
            current_status = leg_data.status
            
            # Calculate expected status
            if leg_data.sales_invoice:
                expected_status = "Billed"
            elif leg_data.end_date:
                expected_status = "Completed"
            elif leg_data.start_date:
                expected_status = "Started"
            elif leg_data.run_sheet:
                expected_status = "Assigned"
            else:
                expected_status = "Open"
            
            # If status is incorrect, fix it
            if current_status != expected_status:
                try:
                    # Use db_set to update submitted document
                    leg_doc = frappe.get_doc("Transport Leg", leg_name)
                    leg_doc.db_set("status", expected_status, update_modified=False)
                    
                    results.append({
                        "leg_name": leg_name,
                        "old_status": current_status,
                        "new_status": expected_status,
                        "fixed": True
                    })
                    fixed_count += 1
                except Exception as e:
                    results.append({
                        "leg_name": leg_name,
                        "old_status": current_status,
                        "new_status": expected_status,
                        "fixed": False,
                        "error": str(e)
                    })
        
        return {
            "ok": True,
            "total_legs": len(legs),
            "fixed_count": fixed_count,
            "results": results[:10]  # Return first 10 results to avoid too much data
        }
    except Exception as e:
        frappe.log_error(f"Error fixing status for submitted legs: {str(e)}")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def regenerate_routing(leg_name: str):
    """Regenerate routing for a Transport Leg"""
    from logistics.transport.routing import compute_leg_distance_time
    
    result = compute_leg_distance_time(leg_name)
    if result.get("ok", False):
        return {
            "distance_km": result.get("distance_km", 0),
            "duration_min": result.get("duration_min", 0),
            "provider": result.get("provider", "")
        }
    else:
        frappe.throw(result.get("msg", "Routing computation failed"))


@frappe.whitelist()
def regenerate_carbon(leg_name: str):
    """Regenerate carbon calculation for a Transport Leg"""
    from logistics.transport.carbon import compute_leg_carbon
    
    result = compute_leg_carbon(leg_name)
    if result.get("ok", False):
        return {
            "co2e_kg": result.get("co2e_kg", 0),
            "method": result.get("method", ""),
            "scope": result.get("scope", ""),
            "provider": result.get("provider", ""),
            "factor": result.get("factor", 0)
        }
    else:
        frappe.throw(result.get("msg", "Carbon computation failed"))


@frappe.whitelist()
def get_addresses_for_facility(facility_type: str, facility_name: str):
    """Get all addresses linked to a facility - used for frontend query filters"""
    if not facility_type or not facility_name:
        return []
    
    try:
        # Get addresses linked to this facility
        # This runs server-side with proper permissions, avoiding permission errors
        addresses = frappe.get_all("Address",
            filters={
                "link_doctype": facility_type,
                "link_name": facility_name
            },
            fields=["name"],
            order_by="is_primary_address DESC, is_shipping_address DESC, creation ASC"
        )
        
        return [addr.name for addr in addresses]
        
    except Exception as e:
        frappe.log_error(f"Error getting addresses for {facility_type} {facility_name}: {str(e)}")
    
    return []


@frappe.whitelist()
def get_primary_address(facility_type: str, facility_name: str):
    """Get the primary address for a facility"""
    if not facility_type or not facility_name:
        return None
    
    try:
        # Map facility types to their primary address field names
        primary_address_fields = {
            "Shipper": "shipper_primary_address",
            "Consignee": "consignee_primary_address", 
            "Container Yard": "containeryard_primary_address",
            "Container Depot": "containerdepot_primary_address",
            "Container Freight Station": "cfs_primary_address"
        }
        
        # Get the primary address field name for this facility type
        primary_address_field = primary_address_fields.get(facility_type)
        
        if primary_address_field:
            # Get the facility document and its primary address
            facility_doc = frappe.get_doc(facility_type, facility_name)
            primary_address = getattr(facility_doc, primary_address_field, None)
            
            if primary_address:
                return primary_address
        
        # Fallback: For facility types without primary address fields (Storage Facility, Truck Park)
        # or if primary address is not set, get addresses linked to this facility
        addresses = frappe.get_all("Address",
            filters={
                "link_doctype": facility_type,
                "link_name": facility_name
            },
            fields=["name", "is_primary_address", "is_shipping_address"],
            order_by="is_primary_address DESC, is_shipping_address DESC, creation ASC"
        )
        
        if addresses:
            # Return the primary address, or shipping address, or first address
            for address in addresses:
                if address.is_primary_address or address.is_shipping_address:
                    return address.name
            return addresses[0].name
        
    except Exception as e:
        frappe.log_error(f"Error getting primary address for {facility_type} {facility_name}: {str(e)}")
    
    return None