# logistics/transport/doctype/transport_leg/transport_leg.py

import frappe
from frappe.model.document import Document


class TransportLeg(Document):
    def validate(self):
        """Update status based on start_date and end_date fields"""
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
        """Sync changes back to Run Sheet after Transport Leg is saved"""
        self.sync_to_run_sheet()
    
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
    
    def _get_primary_address(self, facility_type, facility_name):
        """Get the primary address for a facility"""
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