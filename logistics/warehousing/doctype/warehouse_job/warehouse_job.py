# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from typing import Optional, List, Dict, Any
from frappe.model.document import Document
from frappe.utils import flt, now_datetime
from frappe import _
from logistics.warehousing.api_parts.common import _get_default_currency

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
    def before_save(self):
        # Calculate totals before saving the job
        self.calculate_totals()
        
        # Calculate sustainability metrics
        self.calculate_sustainability_metrics()
        
        # Auto-fill basic charge pricing from Warehouse Contract (rates only)
        try:
            if getattr(self, 'charges', None):
                contract = getattr(self, 'warehouse_contract', None) or _find_customer_contract(getattr(self, 'customer', None))
                for ch in self.charges:
                    item_code = getattr(ch, 'item_code', None) or getattr(ch, 'item', None)
                    
                    # Only auto-fill rates, currency, and uom, not quantities
                    if item_code and (getattr(ch, 'rate', None) in (None, '') or flt(ch.rate) == 0):
                        rate, cur, uom = _get_charge_price_from_contract(contract, item_code)
                        if rate is not None:
                            ch.rate = rate
                        if cur and hasattr(ch, 'currency'):
                            ch.currency = cur
                        if uom and hasattr(ch, 'uom'):
                            ch.uom = uom
                    
                    # (re)compute total if quantity and rate are available
                    if hasattr(ch, 'total') and getattr(ch, 'quantity', 0) and getattr(ch, 'rate', 0):
                        ch.total = flt(getattr(ch, 'quantity', 0)) * flt(getattr(ch, 'rate', 0))
                    
        except Exception as e:
            frappe.logger().warning(f"[WarehouseJob.before_save] charges autofill warning: {e}")
        
        # Job Costing Number will be created in after_insert method

    def after_insert(self):
        """Create Job Costing Number after document is inserted"""
        self.create_job_costing_number_if_needed()
        # Save the document to persist the job_costing_number field
        if self.job_costing_number:
            self.save(ignore_permissions=True)
    
    def after_submit(self):
        """Record sustainability metrics after job submission"""
        self.record_sustainability_metrics()
    
    def calculate_sustainability_metrics(self):
        """Calculate sustainability metrics for this warehouse job"""
        try:
            # Calculate energy consumption from operations
            total_energy_consumption = 0
            if hasattr(self, 'operations') and self.operations:
                for operation in self.operations:
                    if hasattr(operation, 'energy_consumption') and operation.energy_consumption:
                        total_energy_consumption += flt(operation.energy_consumption)
            
            # Store calculated metrics for display
            self.total_energy_consumption = total_energy_consumption
            
            # Calculate estimated carbon footprint from energy consumption
            if total_energy_consumption > 0:
                carbon_footprint = self._calculate_carbon_footprint_from_energy(total_energy_consumption)
                self.estimated_carbon_footprint = carbon_footprint
            
            # Calculate waste generation if available
            total_waste = 0
            if hasattr(self, 'waste_generated') and self.waste_generated:
                total_waste = flt(self.waste_generated)
            self.total_waste_generated = total_waste
                
        except Exception as e:
            frappe.log_error(f"Error calculating sustainability metrics for Warehouse Job {self.name}: {e}", "Warehouse Job Sustainability Error")
    
    def record_sustainability_metrics(self):
        """Record sustainability metrics in the centralized system"""
        try:
            from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
            
            result = integrate_sustainability(
                doctype=self.doctype,
                docname=self.name,
                module="Warehousing",
                doc=self
            )
            
            if result.get("status") == "success":
                frappe.msgprint(_("Sustainability metrics recorded successfully"))
            elif result.get("status") == "skipped":
                # Don't show message if sustainability is not enabled
                pass
            else:
                frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Warehouse Job Sustainability Error")
                
        except Exception as e:
            frappe.log_error(f"Error recording sustainability metrics for Warehouse Job {self.name}: {e}", "Warehouse Job Sustainability Error")
    
    def _calculate_carbon_footprint_from_energy(self, energy_consumption: float) -> float:
        """Calculate carbon footprint from energy consumption"""
        # Default electricity emission factor (kg CO2e per kWh)
        electricity_factor = 0.4
        return electricity_factor * energy_consumption

    @frappe.whitelist()
    def get_warehouse_dashboard_html(self, job_name=None):
        """Generate HTML for warehouse dashboard visualization"""
        try:
            # If job_name is provided, get the job document
            if job_name:
                job = frappe.get_doc("Warehouse Job", job_name)
            else:
                job = self
            
            # Get company and branch
            company = getattr(job, 'company', None) or ""
            branch = getattr(job, 'branch', None) or ""
            
            frappe.logger().info(f"Loading warehouse dashboard for company: {company}, branch: {branch}")
            
            # Get dashboard data directly
            dashboard_data = job._get_dashboard_data(company, branch)
            
            # Render complete HTML with data
            dashboard_html = job._render_dashboard_html(dashboard_data, company, branch)
            
            frappe.logger().info(f"Dashboard HTML generated successfully, final size: {len(dashboard_html)} characters")
            return dashboard_html
            
        except Exception as e:
            frappe.logger().error(f"Error loading warehouse dashboard: {e}")
            return f"""
                <div style="padding: 20px; text-align: center; color: #666;">
                    <h3>Warehouse Dashboard</h3>
                    <p>Error loading dashboard: {str(e)}</p>
                    <p>Please refresh the page or contact support.</p>
                </div>
            """
    def _get_dashboard_data(self, company, branch):
        """Get dashboard data from database"""
        try:
            # Get handling units data
            handling_units = self._get_handling_units_data(company, branch)
            
            # Get storage locations data
            storage_locations = self._get_storage_locations_data(company, branch)
            
            # Get warehouse map data
            warehouse_map = self._get_warehouse_map_data(company, branch)
            
            # Get gate passes for this warehouse job
            gate_passes = self._get_gate_passes_data(company, branch)
            
            return {
                "handling_units": handling_units,
                "storage_locations": storage_locations,
                "warehouse_map": warehouse_map,
                "gate_passes": gate_passes
            }
        except Exception as e:
            frappe.logger().error(f"Error getting dashboard data: {e}")
            return {
                "handling_units": [],
                "storage_locations": [],
                "warehouse_map": {},
                "gate_passes": []
            }
    def _render_dashboard_html(self, data, company, branch):
        """Render complete dashboard HTML with data"""
    def _get_handling_units_data(self, company, branch):
        """Get handling units data from job allocations (items)"""
        try:
            handling_units = []
            
            # Check if there are any items in the job
            if not self.items or len(self.items) == 0:
                frappe.logger().info(f"No items found in warehouse job {self.name}")
                return []
            
            # Group items by handling unit
            hu_items = {}
            for item in self.items:
                if item.handling_unit:
                    hu_name = item.handling_unit
                    if hu_name not in hu_items:
                        hu_items[hu_name] = []
                    
                    # Get item details - try Warehouse Item first, then Item
                    item_name = item.item  # Default to item code
                    if item.item:
                        try:
                            # Try Warehouse Item first
                            warehouse_item_doc = frappe.get_doc("Warehouse Item", item.item)
                            item_name = warehouse_item_doc.item_name if warehouse_item_doc else item.item
                        except:
                            try:
                                # Fallback to Item doctype
                                item_doc = frappe.get_doc("Item", item.item)
                                item_name = item_doc.item_name if item_doc else item.item
                            except:
                                # If both fail, use the item code as name
                                item_name = item.item
                    
                    # Get volume and weight from item
                    item_volume = flt(item.volume or 0)
                    item_weight = flt(item.weight or 0)
                    item_length = flt(item.length or 0)
                    item_width = flt(item.width or 0)
                    item_height = flt(item.height or 0)
                    
                    # Calculate volume from dimensions if not provided
                    if item_volume == 0 and item_length > 0 and item_width > 0 and item_height > 0:
                        item_volume = item_length * item_width * item_height
                    
                    hu_items[hu_name].append({
                        "item": item.item,
                        "item_name": item_name,
                        "qty": flt(item.quantity or 0),
                        "location": item.location or "N/A",
                        "volume": item_volume,
                        "weight": item_weight,
                        "length": item_length,
                        "width": item_width,
                        "height": item_height
                    })
            
            # If no handling units found, return empty list
            if not hu_items:
                frappe.logger().info(f"No handling units found in warehouse job {self.name}")
                return []
            
            # Create handling unit records
            for hu_name, items in hu_items.items():
                # Get handling unit details
                try:
                    hu_doc = frappe.get_doc("Handling Unit", hu_name)
                    hu_type = hu_doc.handling_unit_type if hasattr(hu_doc, 'handling_unit_type') else "Pallet"
                    hu_brand = hu_doc.brand if hasattr(hu_doc, 'brand') else "Unknown"
                except:
                    hu_type = "Pallet"
                    hu_brand = "Unknown"
                
                # Calculate totals
                total_qty = sum(flt(item["qty"]) for item in items)
                
                # Calculate volume based on volume_qty_type setting
                if getattr(self, 'volume_qty_type', 'Total') == 'Total':
                    # Volume is total for entire quantity, not per unit
                    total_volume = sum(flt(item["volume"]) for item in items)
                else:
                    # Volume is per unit, so multiply by quantity
                    total_volume = sum(flt(item["volume"]) * flt(item["qty"]) for item in items)
                
                # Calculate weight based on weight_qty_type setting
                if getattr(self, 'weight_qty_type', 'Per Unit') == 'Per Unit':
                    # Weight is per unit, so multiply by quantity
                    total_weight = sum(flt(item["weight"]) * flt(item["qty"]) for item in items)
                else:
                    # Weight is total for entire quantity, not per unit
                    total_weight = sum(flt(item["weight"]) for item in items)
                
                # Get handling unit capacity limits
                capacity_info = self._get_handling_unit_capacity(hu_name)
                
                # Check if totals exceed capacity
                volume_exceeded = total_volume > capacity_info.get('max_volume', 0) if capacity_info.get('max_volume', 0) > 0 else False
                weight_exceeded = total_weight > capacity_info.get('max_weight', 0) if capacity_info.get('max_weight', 0) > 0 else False
                capacity_warning = volume_exceeded or weight_exceeded
                
                handling_units.append({
                    "name": hu_name,
                    "type": hu_type,
                    "brand": hu_brand,
                    "status": "Available",
                    "company": company,
                    "branch": branch,
                    "items": items,
                    "total_qty": total_qty,
                    "total_volume": total_volume,
                    "total_weight": total_weight,
                    "capacity_info": capacity_info,
                    "volume_exceeded": volume_exceeded,
                    "weight_exceeded": weight_exceeded,
                    "capacity_warning": capacity_warning
                })
            
            return handling_units
            
        except Exception as e:
            frappe.logger().error(f"Error getting handling units data: {e}")
            return []
    
    def _get_handling_unit_capacity(self, hu_name):
        """Get handling unit capacity limits"""
        try:
            # Get handling unit document
            hu_doc = frappe.get_doc("Handling Unit", hu_name)
            
            # Get warehouse settings for defaults
            from logistics.warehousing.doctype.warehouse_settings.warehouse_settings import get_warehouse_settings
            company = getattr(hu_doc, 'company', None) or frappe.defaults.get_user_default("Company")
            warehouse_settings = get_warehouse_settings(company)
            
            # Get capacity from handling unit type if available
            capacity_info = {
                'max_volume': 0,
                'max_weight': 0,
                'current_volume': 0,
                'current_weight': 0,
                'volume_utilization': 0,
                'weight_utilization': 0,
                'volume_uom': warehouse_settings['default_volume_uom'],
                'weight_uom': warehouse_settings['default_weight_uom']
            }
            
            # Get UOMs from handling unit
            if hasattr(hu_doc, 'volume_uom') and hu_doc.volume_uom:
                capacity_info['volume_uom'] = hu_doc.volume_uom
            if hasattr(hu_doc, 'weight_uom') and hu_doc.weight_uom:
                capacity_info['weight_uom'] = hu_doc.weight_uom
            
            # Try to get capacity from handling unit type
            if hasattr(hu_doc, 'handling_unit_type') and hu_doc.handling_unit_type:
                try:
                    hu_type_doc = frappe.get_doc("Handling Unit Type", hu_doc.handling_unit_type)
                    capacity_info['max_volume'] = flt(hu_type_doc.max_volume or 0)
                    capacity_info['max_weight'] = flt(hu_type_doc.max_weight or 0)
                    
                    # Get UOMs from handling unit type if not set in handling unit
                    if not capacity_info['volume_uom'] and hasattr(hu_type_doc, 'volume_uom') and hu_type_doc.volume_uom:
                        capacity_info['volume_uom'] = hu_type_doc.volume_uom
                    if not capacity_info['weight_uom'] and hasattr(hu_type_doc, 'weight_uom') and hu_type_doc.weight_uom:
                        capacity_info['weight_uom'] = hu_type_doc.weight_uom
                except:
                    pass
            
            # If no capacity defined in type, try to get from handling unit itself
            if capacity_info['max_volume'] == 0 and hasattr(hu_doc, 'max_volume'):
                capacity_info['max_volume'] = flt(hu_doc.max_volume or 0)
            if capacity_info['max_weight'] == 0 and hasattr(hu_doc, 'max_weight'):
                capacity_info['max_weight'] = flt(hu_doc.max_weight or 0)
            
            # If still no capacity defined, use warehouse settings defaults based on type
            if capacity_info['max_volume'] == 0 and capacity_info['max_weight'] == 0:
                hu_type = getattr(hu_doc, 'type', '').lower()
                if 'pallet' in hu_type:
                    capacity_info['max_volume'] = warehouse_settings['default_pallet_volume']
                    capacity_info['max_weight'] = warehouse_settings['default_pallet_weight']
                elif 'box' in hu_type:
                    capacity_info['max_volume'] = warehouse_settings['default_box_volume']
                    capacity_info['max_weight'] = warehouse_settings['default_box_weight']
                else:
                    capacity_info['max_volume'] = 1.0  # Default fallback
                    capacity_info['max_weight'] = 500.0  # Default fallback
            
            return capacity_info
            
        except Exception as e:
            frappe.logger().error(f"Error getting handling unit capacity for {hu_name}: {e}")
            return {
                'max_volume': 0,
                'max_weight': 0,
                'current_volume': 0,
                'current_weight': 0,
                'volume_utilization': 0,
                'weight_utilization': 0
            }
    
    def _render_capacity_info(self, hu):
        """Render capacity information and warnings"""
        capacity_info = hu.get('capacity_info', {})
        total_volume = hu.get('total_volume', 0)
        total_weight = hu.get('total_weight', 0)
        volume_exceeded = hu.get('volume_exceeded', False)
        weight_exceeded = hu.get('weight_exceeded', False)
        
        max_volume = capacity_info.get('max_volume', 0)
        max_weight = capacity_info.get('max_weight', 0)
        volume_uom = capacity_info.get('volume_uom', 'm³')
        weight_uom = capacity_info.get('weight_uom', 'kg')
        
        if max_volume == 0 and max_weight == 0:
            return ""  # No capacity limits defined
        
        # Calculate utilization percentages
        volume_util = (total_volume / max_volume * 100) if max_volume > 0 else 0
        weight_util = (total_weight / max_weight * 100) if max_weight > 0 else 0
        
        # Get warehouse settings for thresholds
        from logistics.warehousing.doctype.warehouse_settings.warehouse_settings import get_warehouse_settings
        company = hu.get('company') or frappe.defaults.get_user_default("Company")
        warehouse_settings = get_warehouse_settings(company)
        
        warning_threshold = warehouse_settings['capacity_warning_threshold']
        critical_threshold = warehouse_settings['capacity_critical_threshold']
        
        # Determine warning level
        volume_warning = volume_util > critical_threshold
        weight_warning = weight_util > critical_threshold
        volume_caution = volume_util > warning_threshold
        weight_caution = weight_util > warning_threshold
        
        warning_color = "#dc3545" if (volume_warning or weight_warning) else "#ffc107" if (volume_caution or weight_caution) else "#28a745"
        warning_text = "EXCEEDED" if (volume_warning or weight_warning) else "WARNING" if (volume_caution or weight_caution) else "OK"
        
        capacity_html = f"""
            <div style="margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid {warning_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <strong style="font-size: 11px; color: #495057;">Capacity Planning</strong>
                    <span style="background: {warning_color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: 600;">{warning_text}</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 10px;">
                    <div>
                        <strong>Volume:</strong> {total_volume:.2f} / {max_volume:.2f} {volume_uom} ({volume_util:.1f}%)
                        <div style="background: #e9ecef; height: 4px; border-radius: 2px; margin-top: 2px;">
                            <div style="background: {'#dc3545' if volume_warning else '#ffc107' if volume_caution else '#28a745'}; height: 100%; width: {min(volume_util, 100):.1f}%; border-radius: 2px;"></div>
                        </div>
                    </div>
                    <div>
                        <strong>Weight:</strong> {total_weight:.2f} / {max_weight:.2f} {weight_uom} ({weight_util:.1f}%)
                        <div style="background: #e9ecef; height: 4px; border-radius: 2px; margin-top: 2px;">
                            <div style="background: {'#dc3545' if weight_warning else '#ffc107' if weight_caution else '#28a745'}; height: 100%; width: {min(weight_util, 100):.1f}%; border-radius: 2px;"></div>
                        </div>
                    </div>
                </div>
        """
        
        if volume_warning or weight_warning:
            capacity_html += f"""
                <div style="margin-top: 6px; padding: 4px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 3px; font-size: 9px; color: #721c24;">
                    <i class="fa fa-exclamation-triangle"></i> <strong>Capacity Exceeded!</strong> 
                    {'Volume limit exceeded!' if volume_warning else ''} 
                    {'Weight limit exceeded!' if weight_warning else ''}
                </div>
            """
        elif volume_caution or weight_caution:
            capacity_html += f"""
                <div style="margin-top: 6px; padding: 4px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 3px; font-size: 9px; color: #856404;">
                    <i class="fa fa-exclamation-circle"></i> <strong>Approaching Capacity</strong> 
                    {'Volume > 80%' if volume_caution else ''} 
                    {'Weight > 80%' if weight_caution else ''}
                </div>
            """
        
        capacity_html += "</div>"
        return capacity_html
    
    def _get_storage_locations_data(self, company, branch):
        """Get storage locations data"""
        try:
            # Get storage locations from job items
            if not hasattr(self, 'items') or not self.items:
                return []
            
            locations = []
            for item in self.items:
                location = getattr(item, 'location', None)
                if location:
                    locations.append({
                        "name": location,
                        "status": "Available",
                        "company": company,
                        "branch": branch
                    })
            
            return locations
            
        except Exception as e:
            frappe.logger().error(f"Error getting storage locations data: {e}")
            return []
    
    def _get_warehouse_map_data(self, company, branch):
        """Get warehouse map data"""
        try:
            # Get warehouse map data
            return {
                "company": company,
                "branch": branch,
                "locations": []
            }
            
        except Exception as e:
            frappe.logger().error(f"Error getting warehouse map data: {e}")
            return {}
    
    def _get_gate_passes_data(self, company, branch):
        """Get gate passes data for this warehouse job"""
        try:
            if not self.name:
                return []
            
            # Get gate passes for this warehouse job
            gate_passes = frappe.get_all(
                "Gate Pass",
                filters={"warehouse_job": self.name},
                fields=[
                    "name", "status", "job_type", "dock_door", "eta", "plate_no", 
                    "transport_company", "vehicle_type", "driver_name", "driver_contact",
                    "gate_pass_date", "gate_pass_time", "actual_in_time", "actual_out_time",
                    "company", "branch"
                ]
            )
            
            return gate_passes
            
        except Exception as e:
            frappe.logger().error(f"Error getting gate passes data: {e}")
            return []
        handling_units = data.get("handling_units", [])
        storage_locations = data.get("storage_locations", [])
        warehouse_map = data.get("warehouse_map", {})
        
        # Get job details for header
        job_name = self.name or "New Job"
        job_type = getattr(self, 'type', '') or 'Draft'
        customer = getattr(self, 'customer', '') or ''
        customer_name = getattr(self, 'customer_name', '') or ''
        
        # Calculate stats
        total_hus = len(handling_units)
        available_hus = len([hu for hu in handling_units if hu.get("status") == "Available"])
        total_locations = len(storage_locations)
        available_locations = len([loc for loc in storage_locations if loc.get("status") == "Available"])
        
        # Render operations HTML
        operations_html = self._render_operations()
        
        # Render handling units HTML
        handling_units_html = self._render_handling_units(handling_units)
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Warehouse Dashboard</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: \#f5f5f5;
                    color: #333;
                }}

                /* Job Header - Run Sheet Style */
                .job-header {{
                    background: \#ffffff;
                    border: 1px solid \#e0e0e0;
                    border-radius: 6px;
                    margin-bottom: 20px;
                    padding: 12px 16px;
                }}
                
                .header-main {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 20px;
                }}
                
                .header-job-section {{
                    display: flex;
                    flex-direction: column;
                    gap: 0px;
                }}
                
                .section-label {{
                    font-size: 10px;
                    color: #6c757d;
                    text-transform: uppercase;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                    margin-bottom: -2px;
                }}
                
                .job-name {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #007bff;
                    margin-top: -2px;
                }}
                
                .job-customer {{
                    font-size: 16px;
                    color: #6c757d;
                    font-weight: 500;
                    margin-top: 4px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}
                
                .job-customer i {{
                    font-size: 14px;
                    color: #6c757d;
                }}
                
                .header-details {{
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                    align-items: flex-start;
                }}
                
                .header-item {{
                    font-size: 11px;
                    color: #6c757d;
                    font-weight: 500;
                    line-height: 1.4;
                }}
                
                .header-item b {{
                    color: #2c3e50;
                    font-weight: 600;
                }}

                .dashboard-container {{
                    display: grid;
                    grid-template-columns: 1fr 2fr;
                    gap: 20px;
                    min-height: 100vh;
                }}

                .left-panel {{
                    min-width: 0;
                }}

                .right-panel {{
                    min-width: 0;
                }}

                .section {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 20px;
                }}

                .section h3 {{
                    margin-bottom: 15px;
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 8px;
                }}

                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}

                .stat-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}

                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}

                .stat-label {{
                    font-size: 14px;
                    opacity: 0.9;
                }}

                /* Minimalist Run Sheet Style HU Cards */
                .handling-units-grid {{
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    max-height: 400px;
                    overflow-y: auto;
                }}

                .handling-unit-card {{
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    transition: all 0.3s ease;
                    border-left: 4px solid #667eea;
                    cursor: pointer;
                    margin-bottom: 32px;
                }}

                .handling-unit-card:hover {{
                    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                    transform: translateY(-2px);
                }}

                .hu-card-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 12px;
                }}

                .hu-card-header h5 {{
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                    line-height: 1.2;
                }}

                .hu-number {{
                    background: #667eea;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 600;
                }}

                .hu-details {{
                    font-size: 11px;
                    color: #6c757d;
                    line-height: 1.4;
                    margin-bottom: 8px;
                }}

                .hu-actions {{
                    display: flex;
                    gap: 6px;
                    margin-top: 8px;
                }}

                .action-icon {{
                    font-size: 14px;
                    cursor: pointer;
                    transition: opacity 0.2s ease;
                }}

                .action-icon:hover {{
                    opacity: 0.7;
                }}

                .status-badge {{
                    padding: 2px 6px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 500;
                    text-transform: uppercase;
                    background: #f8f9fa;
                    color: #6c757d;
                    border: 1px solid #e9ecef;
                }}

                .handling-unit-card.available {{
                    border-left-color: #28a745;
                }}

                .handling-unit-card.in-use {{
                    border-left-color: #007bff;
                }}

                .handling-unit-card.under-maintenance {{
                    border-left-color: #ffc107;
                }}

            </style>
        """
    def _render_dashboard_html(self, data, company, branch):
        """Render complete dashboard HTML with data"""
        handling_units = data.get("handling_units", [])
        storage_locations = data.get("storage_locations", [])
        warehouse_map = data.get("warehouse_map", {})
        
        # Get job details for header
        job_name = self.name or "New Job"
        job_type = getattr(self, 'type', '') or 'Draft'
        customer = getattr(self, 'customer', '') or ''
        customer_name = getattr(self, 'customer_name', '') or ''
        
        # Calculate stats
        total_hus = len(handling_units)
        available_hus = len([hu for hu in handling_units if hu.get("status") == "Available"])
        total_locations = len(storage_locations)
        available_locations = len([loc for loc in storage_locations if loc.get("status") == "Available"])
        
        # Render operations HTML
        operations_html = self._render_operations()
        
        # Render handling units HTML
        handling_units_html = self._render_handling_units(handling_units)
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Warehouse Dashboard</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: \#f5f5f5;
                    color: #333;
                }}

                /* Job Header - Run Sheet Style */
                .job-header {{
                    background: \#ffffff;
                    border: 1px solid \#e0e0e0;
                    border-radius: 6px;
                    margin-bottom: 20px;
                    padding: 12px 16px;
                }}
                
                .header-main {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 20px;
                }}
                
                .header-job-section {{
                    display: flex;
                    flex-direction: column;
                    gap: 0px;
                }}
                
                .section-label {{
                    font-size: 10px;
                    color: #6c757d;
                    text-transform: uppercase;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                    margin-bottom: -2px;
                }}
                
                .job-name {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #007bff;
                    margin-top: -2px;
                }}
                
                .job-customer {{
                    font-size: 16px;
                    color: #6c757d;
                    font-weight: 500;
                    margin-top: 4px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}
                
                .job-customer i {{
                    font-size: 14px;
                    color: #6c757d;
                }}
                
                .header-details {{
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                    align-items: flex-start;
                }}
                
                .header-item {{
                    font-size: 11px;
                    color: #6c757d;
                    font-weight: 500;
                    line-height: 1.4;
                }}
                
                .header-item b {{
                    color: #2c3e50;
                    font-weight: 600;
                }}

                .dashboard-container {{
                    display: grid;
                    grid-template-columns: 1fr 2fr;
                    gap: 20px;
                    min-height: 100vh;
                }}

                .left-panel {{
                    min-width: 0;
                }}

                .right-panel {{
                    min-width: 0;
                }}

                .section {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 20px;
                }}

                .section h3 {{
                    margin-bottom: 15px;
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 8px;
                }}

                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}

                .stat-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}

                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}

                .stat-label {{
                    font-size: 14px;
                    opacity: 0.9;
                }}

                /* Minimalist Run Sheet Style HU Cards */
                .handling-units-grid {{
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    max-height: 400px;
                    overflow-y: auto;
                }}

                .handling-unit-card {{
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    transition: all 0.3s ease;
                    border-left: 4px solid #667eea;
                    cursor: pointer;
                    margin-bottom: 32px;
                }}

                .handling-unit-card:hover {{
                    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                    transform: translateY(-2px);
                }}

                .hu-card-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 12px;
                }}

                .hu-card-header h5 {{
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                    line-height: 1.2;
                }}

                .hu-number {{
                    background: #667eea;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 600;
                }}

                .hu-details {{
                    font-size: 11px;
                    color: #6c757d;
                    line-height: 1.4;
                    margin-bottom: 8px;
                }}

                .hu-actions {{
                    display: flex;
                    gap: 6px;
                    margin-top: 8px;
                }}

                .action-icon {{
                    font-size: 14px;
                    cursor: pointer;
                    transition: opacity 0.2s ease;
                }}

                .action-icon:hover {{
                    opacity: 0.7;
                }}

                .status-badge {{
                    padding: 2px 6px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 500;
                    text-transform: uppercase;
                    background: #f8f9fa;
                    color: #6c757d;
                    border: 1px solid #e9ecef;
                }}

                .handling-unit-card.available {{
                    border-left-color: #28a745;
                }}

                .handling-unit-card.in-use {{
                    border-left-color: #007bff;
                }}

                .handling-unit-card.under-maintenance {{
                    border-left-color: #ffc107;
                }}

                /* Milestone Flow */
                .milestone-flow {{
                    display: flex;
                    align-items: flex-start;
                    margin-top: 12px;
                    padding: 8px 0;
                    width: 100%;
                }}

                .milestone-step {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    position: relative;
                    flex: 1;
                    min-width: 0;
                    justify-content: flex-start;
                }}

                .milestone-step:not(:last-child)::after {{
                    content: '';
                    position: absolute;
                    top: 8px;
                    left: 50%;
                    width: calc(100% - 8px);
                    height: 2px;
                    background: #e3f2fd;
                    z-index: 1;
                }}

                .milestone-step.completed:not(:last-child)::after {{
                    background: #1976d2;
                }}

                .milestone-dot {{
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: #e3f2fd;
                    border: 2px solid #e3f2fd;
                    position: relative;
                    z-index: 2;
                    transition: all 0.3s ease;
                    margin-bottom: 8px;
                    margin-left: auto;
                    margin-right: auto;
                }}

                .milestone-dot.completed {{
                    background: #1976d2;
                    border-color: #1976d2;
                }}

                .milestone-label {{
                    font-size: 10px;
                    color: #1976d2;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    text-align: center;
                    margin-bottom: 4px;
                }}

                .milestone-label.completed {{
                    color: #1976d2;
                }}

                .milestone-details {{
                    font-size: 9px;
                    color: #666;
                    text-align: center;
                    line-height: 1.2;
                    max-width: 80px;
                    word-wrap: break-word;
                }}

                .milestone-location {{
                    font-weight: 500;
                    color: #1976d2;
                }}

                .milestone-date {{
                    color: #666;
                    font-style: italic;
                }}

                /* Location List */
                .location-list-container {{
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    height: 500px;
                    overflow: auto;
                }}
                
                .location-item {{
                    display: flex;
                    align-items: center;
                    padding: 12px 16px;
                    margin-bottom: 8px;
                    border-radius: 6px;
                    border: 1px solid #e9ecef;
                    background: \#ffffff;
                    transition: all 0.2s ease;
                }}
                
                .location-item:hover {{
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    transform: translateY(-1px);
                }}
                
                .location-item.allocated {{
                    background: #1976d2;
                    color: white;
                    border-color: #0d47a1;
                }}
                
                .location-item.available {{
                    background: #e3f2fd;
                    color: #1976d2;
                    border-color: #bbdefb;
                }}
                
                .location-code {{
                    font-weight: 600;
                    font-size: 14px;
                    margin-right: 12px;
                    min-width: 80px;
                }}
                
                .location-details {{
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }}
                
                .location-path {{
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 4px;
                }}
                
                .location-item.allocated .location-path {{
                    color: #e3f2fd;
                }}
                
                .location-info {{
                    display: flex;
                    gap: 16px;
                    font-size: 11px;
                }}
                
                .location-info span {{
                    background: rgba(0,0,0,0.1);
                    padding: 2px 6px;
                    border-radius: 3px;
                }}
                
                .location-item.allocated .location-info span {{
                    background: rgba(255,255,255,0.2);
                }}
                
                .location-status {{
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-weight: 500;
                }}
                
                .status-allocated {{
                    background: #0d47a1;
                    color: white;
                }}
                
                .status-available {{
                    background: #bbdefb;
                    color: #1976d2;
                }}

                /* Operations List - Modern Minimalist Style */
                .operations-container {{
                    margin: 0 0 32px 0;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }}
                
                .operations-list {{
                    display: flex;
                    flex-direction: column;
                    gap: 0px;
                }}
                
                .operation-card {{
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    transition: all 0.3s ease;
                }}
                
                .operation-card:hover {{
                    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                    transform: translateY(-2px);
                }}
                
                .operation-card.completed {{
                    border-left: 4px solid #28a745;
                }}
                
                .operation-card.in-progress {{
                    border-left: 4px solid #007bff;
                }}
                
                .operation-card.pending {{
                    border-left: 4px solid #6c757d;
                }}
                
                .operation-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                }}
                
                .operation-title-section {{
                    flex: 1;
                }}
                
                .operation-header h5 {{
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                    line-height: 1.2;
                }}
                
                .operation-description {{
                    font-size: 11px;
                    color: #6c757d;
                    margin-top: 2px;
                    line-height: 1.3;
                }}
                
                .operation-status-badge {{
                    background: #6c757d;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 600;
                    text-transform: uppercase;
                    margin-right: 8px;
                }}
                
                .operation-actions {{
                    display: flex;
                    gap: 6px;
                }}
                
                .action-icon {{
                    font-size: 14px;
                    cursor: pointer;
                    transition: opacity 0.2s ease;
                }}
                
                .action-icon:hover {{
                    opacity: 0.7;
                }}
                
                .operation-dates {{
                    display: flex;
                    flex-direction: row;
                    justify-content: space-between;
                    gap: 8px;
                }}
                
                .date-row {{
                    display: flex;
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 0px;
                }}
                
                .date-row label {{
                    font-size: 10px;
                    color: #6c757d;
                    font-weight: 500;
                    margin-bottom: -2px;
                }}
                
                .date-row span {{
                    font-size: 10px;
                    color: #333;
                    margin-top: -2px;
                }}

                .warehouse-legend {{
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-bottom: 15px;
                    font-size: 10px;
                }}

                .legend-item {{
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }}

                .legend-color {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                }}

                .site-group {{
                    margin-bottom: 30px;
                    border: 2px solid #e9ecef;
                    border-radius: 8px;
                    padding: 15px;
                    background: \#ffffff;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                }}

                .site-group:hover {{
                    border-color: #3498db;
                    box-shadow: 0 2px 8px rgba(52, 152, 219, 0.2);
                }}

                .site-title {{
                    display: none;
                }}

                .building-group {{
                    margin-bottom: 25px;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 12px;
                    background: #f8f9fa;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                }}

                .building-group:hover {{
                    border-color: #3498db;
                    box-shadow: 0 2px 6px rgba(52, 152, 219, 0.15);
                }}

                .building-title {{
                    display: none;
                }}

                .zone-group {{
                    margin-bottom: 20px;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                    padding: 10px;
                    background: \#ffffff;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                    display: inline-block;
                    width: 22%;
                    margin-right: 2%;
                    vertical-align: top;
                }}

                .zone-group:nth-child(4) {{
                    margin-right: 0;
                }}

                .zone-group:nth-child(5) {{
                    width: 22%;
                    margin-right: 0;
                    clear: left;
                }}

                .zone-group:hover {{
                    border-color: #3498db;
                    box-shadow: 0 1px 4px rgba(52, 152, 219, 0.1);
                }}

                .zone-title {{
                    display: none;
                }}

                .aisle-group {{
                    margin-bottom: 15px;
                    border: 1px solid #f1f3f4;
                    border-radius: 3px;
                    padding: 8px;
                    background: #fafbfc;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                }}

                .aisle-group:hover {{
                    border-color: #3498db;
                    box-shadow: 0 1px 3px rgba(52, 152, 219, 0.1);
                }}

                .aisle-title {{
                    display: none;
                }}

                .bay-group {{
                    margin-bottom: 10px;
                    border: 1px solid #f8f9fa;
                    border-radius: 2px;
                    padding: 6px;
                    background: \#ffffff;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                }}

                .bay-group:hover {{
                    border-color: #3498db;
                    box-shadow: 0 1px 2px rgba(52, 152, 219, 0.1);
                }}

                .bay-title {{
                    display: none;
                }}

                .level-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(12px, 1fr));
                    gap: 3px;
                    justify-items: start;
                    max-width: 100%;
                }}

                .warehouse-square {{
                    width: 12px;
                    height: 12px;
                    border: none;
                    background: #f8f9fa;
                    border-radius: 2px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                }}

                .warehouse-square.available {{
                    background: #e3f2fd;
                }}

                .warehouse-square.occupied {{
                    background: #1976d2;
                }}

                .warehouse-square.partial {{
                    background: #64b5f6;
                }}

                .warehouse-square.allocated {{
                    background: #0d47a1;
                    box-shadow: 0 2px 4px rgba(13, 71, 161, 0.3);
                }}

                .warehouse-square:hover {{
                    transform: scale(1.3);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                    z-index: 10;
                }}

                .square-tooltip {{
                    position: absolute;
                    background: #333;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    white-space: nowrap;
                    z-index: 1000;
                    pointer-events: none;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }}

                .warehouse-square:hover .square-tooltip {{
                    opacity: 1;
                }}

                @media (max-width: 768px) {{
                    .dashboard-container {{
                        grid-template-columns: 1fr;
                        height: auto;
                    }}
                    
                    .header-main {{
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 12px;
                    }}
                    
                    .header-details {{
                        gap: 12px;
                        flex-wrap: wrap;
                        width: 100%;
                    }}
                    
                    .job-name {{
                        font-size: 20px;
                    }}
                    
                    .cinema-seat {{
                        width: 20px;
                        height: 20px;
                        font-size: 9px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="job-header">
                <div class="header-main">
                    <div class="header-job-section">
                        <label class="section-label">{job_type.upper()}</label>
                        <div class="job-name">{job_name}</div>
                        <div class="job-customer">
                            <i class="fa fa-user"></i> {customer_name or customer or 'Not specified'}
                        </div>
                    </div>
                    <div class="header-details">
                        <div class="header-item">
                            Open Date: <b>{self.get('job_open_date', 'Not specified')}</b>
                        </div>
                        <div class="header-item">
                            Reference Order: <b>{self.get('reference_order', 'Not specified')}</b>
                        </div>
                        <div class="header-item">
                            Warehouse Contract: <b>{self.get('warehouse_contract', 'Not specified')}</b>
                        </div>
                        <div class="header-item">
                            Company: <b>{company or 'Not specified'}</b>
                        </div>
                        <div class="header-item">
                            Branch: <b>{branch or 'Not specified'}</b>
                        </div>
                    </div>
                </div>
            </div>

            <div class="dashboard-container">
            <div class="left-panel">
                <div class="operations-container">
                    {operations_html}
                </div>
            </div>

                <div class="right-panel">
                    {handling_units_html}
                </div>
            </div>
            
            <script>
            // Define functions in global scope
            window.toggleHuItems = function(huId) {{
                const itemsDiv = document.getElementById(huId + '-items');
                const link = event.target;
                
                if (itemsDiv.style.display === 'none') {{
                    itemsDiv.style.display = 'block';
                    link.innerHTML = '<i class="fa fa-chevron-up"></i> Hide Items';
                }} else {{
                    itemsDiv.style.display = 'none';
                    // Restore original text with cube icon
                    const originalText = link.getAttribute('data-original-text') || 'items';
                    link.innerHTML = '<i class="fa fa-cube"></i> ' + originalText;
                }}
            }};
            
            window.filterByBuilding = function(building) {{
                const buildingGroups = document.querySelectorAll('.building-group');
                
                buildingGroups.forEach(group => {{
                    if (building === '' || group.getAttribute('data-building') === building) {{
                        group.style.display = 'block';
                    }} else {{
                        group.style.display = 'none';
                    }}
                }});
            }};
            
            window.startOperation = function(operationId) {{
                const operationCard = document.querySelectorAll('.operation-card')[operationId];
                const startDateElement = operationCard.querySelector('.date-row:first-child span');
                
                // Update start date
                const now = new Date();
                const formattedDate = now.toLocaleDateString() + ' ' + now.toLocaleTimeString();
                startDateElement.textContent = formattedDate;
                
                // Update card status
                operationCard.className = 'operation-card in-progress';
                
                // Save to backend using custom API method
                frappe.call({{
                    method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.update_operation_start',
                    args: {{
                        job_name: '{self.name}',
                        operation_id: operationId,
                        start_date: frappe.datetime.now_datetime()
                    }},
                    callback: function(r) {{
                        if (!r.exc) {{
                            frappe.show_alert({{message: __('Operation started successfully'), indicator: 'green'}});
                            // Refresh the page to show updated data
                            setTimeout(() => {{
                                window.location.reload();
                            }}, 1000);
                        }} else {{
                            frappe.show_alert({{message: __('Error starting operation'), indicator: 'red'}});
                        }}
                    }}
                }});
            }};
            
            window.endOperation = function(operationId) {{
                const operationCard = document.querySelectorAll('.operation-card')[operationId];
                const endDateElement = operationCard.querySelectorAll('.date-row')[1].querySelector('span');
                
                // Update end date
                const now = new Date();
                const formattedDate = now.toLocaleDateString() + ' ' + now.toLocaleTimeString();
                endDateElement.textContent = formattedDate;
                
                // Update card status
                operationCard.className = 'operation-card completed';
                
                // Save to backend using custom API method
                frappe.call({{
                    method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.update_operation_end',
                    args: {{
                        job_name: '{self.name}',
                        operation_id: operationId,
                        end_date: frappe.datetime.now_datetime()
                    }},
                    callback: function(r) {{
                        if (!r.exc) {{
                            frappe.show_alert({{message: __('Operation ended successfully'), indicator: 'green'}});
                            // Refresh the page to show updated data
                            setTimeout(() => {{
                                window.location.reload();
                            }}, 1000);
                        }} else {{
                            frappe.show_alert({{message: __('Error ending operation'), indicator: 'red'}});
                        }}
                    }}
                }});
            }};
            
            // Also define as global functions for backward compatibility
            function toggleHuItems(huId) {{ return window.toggleHuItems(huId); }}
            function filterByBuilding(building) {{ return window.filterByBuilding(building); }}
            function startOperation(operationId) {{ return window.startOperation(operationId); }}
            function endOperation(operationId) {{ return window.endOperation(operationId); }}
            </script>
        </body>
        </html>
        """
    
    def _render_handling_units(self, handling_units):
        """Render handling units HTML with run sheet styling and expandable items"""
        if not handling_units:
            # Check if there are items but no handling units
            has_items = hasattr(self, 'items') and self.items and len(self.items) > 0
            has_orders = hasattr(self, 'orders') and self.orders and len(self.orders) > 0
            
            if has_items:
                # Items exist but no handling units assigned
                return f"""
                    <div style="padding: 24px; text-align: center; color: #64748b; background: #f0f9ff; border-radius: 8px; border: 1px solid #bae6fd;">
                        <h3 style="color: #0369a1; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Items Ready for Assignment</h3>
                        <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.5;">This job has {len(self.items)} item(s) but no handling units are assigned yet.</p>
                        <div style="background: #dbeafe; padding: 12px; border-radius: 6px; border-left: 3px solid #3b82f6;">
                            <p style="margin: 0; font-size: 13px; color: #1e40af; font-weight: 500;">Add handling units to items in the Items table or use the "Allocate" button to automatically assign them.</p>
                        </div>
                    </div>
                """
            elif has_orders:
                # Orders exist but no items allocated
                return f"""
                    <div style="padding: 24px; text-align: center; color: #64748b; background: #fffbeb; border-radius: 8px; border: 1px solid #fed7aa;">
                        <h3 style="color: #d97706; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Orders Ready for Allocation</h3>
                        <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.5;">This job has {len(self.orders)} order(s) but no items have been allocated yet.</p>
                        <div style="background: #fef3c7; padding: 12px; border-radius: 6px; border-left: 3px solid #f59e0b;">
                            <p style="margin: 0; font-size: 13px; color: #92400e; font-weight: 500;">Click the "Allocate" button to allocate items from orders or manually add items to the Items table.</p>
                        </div>
                    </div>
                """
            else:
                # No items or orders
                return f"""
                    <div style="padding: 24px; text-align: center; color: #64748b; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
                        <h3 style="color: #16a34a; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Ready to Get Started</h3>
                        <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.5;">This warehouse job doesn't have any items allocated yet.</p>
                        <div style="background: #dcfce7; padding: 12px; border-radius: 6px; border-left: 3px solid #22c55e;">
                            <p style="margin: 0; font-size: 13px; color: #166534; font-weight: 500;">Add orders to this job first, then use the "Allocate" button to allocate items or manually add items to the Items table.</p>
                        </div>
                    </div>
                """
        
        html_parts = []
        for i, hu in enumerate(handling_units):
            status_class = (hu.get("status") or "").lower().replace(" ", "-")
            status_display = hu.get("status", "N/A")
            
            # Get milestone status for this handling unit based on job type
            job_type = getattr(self, 'type', 'Putaway') or 'Putaway'
            
            # Create milestone flow HTML based on job type
            milestone_flow = ""
            try:
                milestones = self._get_milestone_status(hu.get('name', ''), job_type)
                
                if job_type.lower() == 'putaway':
                    # Get milestone details for location and date
                    milestone_details = self._get_milestone_details(hu.get('name', ''), job_type)
                    
                    milestone_flow = f"""
                    <div class="milestone-flow">
                        <div class="milestone-step {'completed' if milestones['start'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['start'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['start'] else ''}">Start</span>
                            <div class="milestone-details">
                                <div class="milestone-location">Job Created</div>
                                <div class="milestone-date">Ready</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['received'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['received'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['received'] else ''}">Received</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('received', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('received', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['putaway'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['putaway'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['putaway'] else ''}">Putaway</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('putaway', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('putaway', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['end'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['end'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['end'] else ''}">End</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('end', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('end', {}).get('date', '')}</div>
                            </div>
                        </div>
                    </div>
                """
                elif job_type.lower() == 'pick':
                    # Get milestone details for location and date
                    milestone_details = self._get_milestone_details(hu.get('name', ''), job_type)
                    
                    milestone_flow = f"""
                    <div class="milestone-flow">
                        <div class="milestone-step {'completed' if milestones['start'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['start'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['start'] else ''}">Start</span>
                            <div class="milestone-details">
                                <div class="milestone-location">Job Created</div>
                                <div class="milestone-date">Ready</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['pick'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['pick'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['pick'] else ''}">Pick</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('pick', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('pick', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['release'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['release'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['release'] else ''}">Release</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('release', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('release', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['end'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['end'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['end'] else ''}">End</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('end', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('end', {}).get('date', '')}</div>
                            </div>
                        </div>
                    </div>
                """
                elif job_type.lower() == 'vas':
                    # Get milestone details for location and date
                    milestone_details = self._get_milestone_details(hu.get('name', ''), job_type)
                    
                    milestone_flow = f"""
                    <div class="milestone-flow">
                        <div class="milestone-step {'completed' if milestones['start'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['start'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['start'] else ''}">Start</span>
                            <div class="milestone-details">
                                <div class="milestone-location">Job Created</div>
                                <div class="milestone-date">Ready</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['pick'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['pick'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['pick'] else ''}">Pick</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('pick', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('pick', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['working'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['working'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['working'] else ''}">Working</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('working', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('working', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['putaway'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['putaway'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['putaway'] else ''}">Putaway</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('putaway', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('putaway', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['end'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['end'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['end'] else ''}">End</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('end', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('end', {}).get('date', '')}</div>
                            </div>
                        </div>
                    </div>
                """
                else:
                    # Default to putaway flow
                    # Get milestone details for location and date
                    milestone_details = self._get_milestone_details(hu.get('name', ''), job_type)
                    
                    milestone_flow = f"""
                    <div class="milestone-flow">
                        <div class="milestone-step {'completed' if milestones['start'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['start'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['start'] else ''}">Start</span>
                            <div class="milestone-details">
                                <div class="milestone-location">Job Created</div>
                                <div class="milestone-date">Ready</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['received'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['received'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['received'] else ''}">Received</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('received', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('received', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['putaway'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['putaway'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['putaway'] else ''}">Putaway</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('putaway', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('putaway', {}).get('date', '')}</div>
                            </div>
                        </div>
                        <div class="milestone-step {'completed' if milestones['end'] else ''}">
                            <div class="milestone-dot {'completed' if milestones['end'] else ''}"></div>
                            <span class="milestone-label {'completed' if milestones['end'] else ''}">End</span>
                            <div class="milestone-details">
                                <div class="milestone-location">{milestone_details.get('end', {}).get('location', 'Pending')}</div>
                                <div class="milestone-date">{milestone_details.get('end', {}).get('date', '')}</div>
                            </div>
                        </div>
                    </div>
                """
            except Exception as e:
                frappe.logger().error(f"Error generating milestone flow for {hu.get('name', '')} (job_type: {job_type}): {str(e)}")
                milestone_flow = ""  # Empty milestone flow on error
            
            # Items HTML with expandable functionality
            items_html = ""
            if hu.get("items") and len(hu.get("items", [])) > 0:
                items_list = ""
                for item in hu.get("items", []):
                    # Show item details with location info
                    location_info = f" → {item.get('location', 'N/A')}" if item.get('location') else ""
                    serial_info = f" (SN: {item.get('serial_no')})" if item.get('serial_no') else ""
                    batch_info = f" (Batch: {item.get('batch_no')})" if item.get('batch_no') else ""
                    
                    # Calculate volume and weight for this item based on settings
                    item_volume_base = flt(item.get('volume', 0))
                    item_weight_base = flt(item.get('weight', 0))
                    item_qty = flt(item.get('qty', 0))
                    
                    # Calculate volume based on volume_qty_type setting
                    if getattr(self, 'volume_qty_type', 'Total') == 'Total':
                        # Volume is total for the entire quantity, not per unit
                        item_volume = item_volume_base
                    else:
                        # Volume is per unit, so multiply by quantity
                        item_volume = item_volume_base * item_qty
                    
                    # Calculate weight based on weight_qty_type setting
                    if getattr(self, 'weight_qty_type', 'Per Unit') == 'Per Unit':
                        # Weight is per unit, so multiply by quantity
                        item_weight = item_weight_base * item_qty
                    else:
                        # Weight is total for the entire quantity, not per unit
                        item_weight = item_weight_base
                    
                    # Get UOMs from handling unit capacity info
                    hu_capacity = hu.get('capacity_info', {})
                    volume_uom = hu_capacity.get('volume_uom', 'm³')
                    weight_uom = hu_capacity.get('weight_uom', 'kg')
                    
                    items_list += f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid #eee;">
                            <div style="font-weight: 500; font-size: 11px;">
                                {item.get('item', 'N/A')}{location_info}{serial_info}{batch_info}
                            </div>
                            <div style="display: flex; gap: 4px; align-items: center;">
                                <div style="background: #667eea; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{item.get('qty', 0)}</div>
                                <div style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{item_volume:.2f} {volume_uom}</div>
                                <div style="background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{item_weight:.2f} {weight_uom}</div>
                            </div>
                        </div>
                    """
                
            
            html_parts.append(f"""
                <div class="handling-unit-card {status_class}">
                    <div class="hu-card-header">
                        <h5>{hu.get('name', 'N/A')}</h5>
                        <span class="status-badge {status_class}">{status_display}</span>
                    </div>
                    <div class="hu-details">
                        <strong>Type:</strong> {hu.get('type', 'N/A')} | 
                        <strong>Brand:</strong> {hu.get('brand', 'N/A')} | 
                        <strong>Items:</strong> {len(hu.get('items', []))} | 
                        <strong>Total Qty:</strong> {hu.get('total_qty', 0)} | 
                        <strong>Total Vol:</strong> {hu.get('total_volume', 0):.2f} {hu.get('capacity_info', {}).get('volume_uom', 'm³')} | 
                        <strong>Total Wt:</strong> {hu.get('total_weight', 0):.2f} {hu.get('capacity_info', {}).get('weight_uom', 'kg')}
                    </div>
                    {self._render_capacity_info(hu)}
                    {milestone_flow}
                    <div style="margin-top: 12px; text-align: center;">
                        <a href="#" onclick="toggleHuItems('hu-{i}'); return false;" data-original-text="{len(hu.get('items', []))} items" style="color: #667eea; text-decoration: none; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                            <i class="fa fa-cube"></i> {len(hu.get('items', []))} items
                        </a>
                    </div>
                    <div id="hu-{i}-items" style="display: none; margin-top: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px; font-size: 11px;">
                        {items_list}
                    </div>
                </div>
            """)
        
        return "".join(html_parts)
    
    def _render_operations(self):
        """Render operations list with start/end actions and dates"""
        try:
            # Get operations from the warehouse job operations child table
            operations = []
            
            if hasattr(self, 'operations') and self.operations:
                for op in self.operations:
                    start_date = getattr(op, 'start_date', None)
                    end_date = getattr(op, 'end_date', None)
                    
                    # Determine status based on dates
                    if end_date:
                        status = "completed"
                    elif start_date:
                        status = "in-progress"
                    else:
                        status = "pending"
                    
                    operations.append({
                        "title": getattr(op, 'operation', 'N/A'),
                        "description": getattr(op, 'description', ''),
                        "status": status,
                        "start_date": start_date,
                        "end_date": end_date,
                        "actual_hours": getattr(op, 'actual_hours', 0),
                        "quantity": getattr(op, 'quantity', 0)
                    })
            
            # If no operations, add a default one
            if not operations:
                operations.append({
                    "title": "No Operations Available",
                    "status": "pending",
                    "start_date": None,
                    "end_date": None,
                    "description": "No operations have been defined for this job"
                })
            
            html_parts = []
            
            # Render operation cards
            for i, op in enumerate(operations):
                status_class = f"status-{op['status']}"
                status_text = op['status'].replace('-', ' ').title()
                
                # Format dates properly
                if op['start_date']:
                    try:
                        start_date = op['start_date'].strftime('%Y-%m-%d %H:%M')
                    except:
                        start_date = str(op['start_date'])
                else:
                    start_date = 'Not Started'
                    
                if op['end_date']:
                    try:
                        end_date = op['end_date'].strftime('%Y-%m-%d %H:%M')
                    except:
                        end_date = str(op['end_date'])
                else:
                    end_date = 'Not Ended'
                
                # Determine status badge text and color
                if op['status'] == 'completed':
                    status_badge = 'Completed'
                    status_color = '#28a745'
                elif op['status'] == 'in-progress':
                    status_badge = 'Started'
                    status_color = '#007bff'
                else:
                    status_badge = 'Not Started'
                    status_color = '#6c757d'
                
                # Determine which action buttons to show
                show_start_button = not op['start_date']
                show_end_button = op['start_date'] and not op['end_date']
                
                html_parts.append(f"""
                    <div class="operation-card {op['status']}">
                        <div class="operation-header">
                            <div class="operation-title-section">
                                <h5>{op['title']}</h5>
                                {f'<div class="operation-description">{op["description"]}</div>' if op.get("description") else ''}
                            </div>
                            <div class="operation-status-badge" style="background: {status_color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-right: 8px;">
                                {status_badge}
                            </div>
                            <div class="operation-actions">
                                {f'<i class="fa fa-play-circle action-icon start-icon" title="Start Operation" onclick="startOperation({i})" style="color: #28a745; cursor: pointer;"></i>' if show_start_button else ''}
                                {f'<i class="fa fa-stop-circle action-icon end-icon" title="End Operation" onclick="endOperation({i})" style="color: #dc3545; cursor: pointer;"></i>' if show_end_button else ''}
                            </div>
                        </div>
                        
                        <div class="operation-dates">
                            <div class="date-row">
                                <label>Start:</label>
                                <span>{start_date}</span>
                            </div>
                            <div class="date-row">
                                <label>End:</label>
                                <span>{end_date}</span>
                            </div>
                            {f'<div class="date-row"><label>Qty:</label><span>{op["quantity"]}</span></div>' if op.get('quantity', 0) > 0 else ''}
                            {f'<div class="date-row"><label>Hours:</label><span>{op["actual_hours"]}</span></div>' if op.get('actual_hours') is not None and op.get('actual_hours') != "" else ''}
                        </div>
                    </div>
                """)
            
            return "".join(html_parts)
            
        except Exception as e:
            frappe.logger().error(f"Error rendering operations: {e}")
            return """
                <div style="text-align: center; padding: 40px; color: #dc3545;">
                    <p>Error loading operations.</p>
                    <small>Please try again later.</small>
                </div>
            """
    
    def _render_cinema_style_map(self, warehouse_map):
        """Render hierarchical warehouse floor grouped by site → building → zone → aisle → level"""
        html_parts = []
        
        # Add building filter (even when no data)
        html_parts.append("""
            <div class="building-filter" style="margin-bottom: 15px; text-align: center;">
                <label for="building-select" style="font-size: 12px; color: #666; margin-right: 8px;">Filter by Building:</label>
                <select id="building-select" onchange="filterByBuilding(this.value)" style="padding: 4px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px;">
                    <option value="">All Buildings</option>
        """)
        
        if warehouse_map:
            # Get unique buildings for filter
            buildings = set()
            for site_data in warehouse_map.values():
                for building in site_data.keys():
                    buildings.add(building)
            
            for building in sorted(buildings):
                html_parts.append(f'<option value="{building}">{building}</option>')
        
        html_parts.append("""
                </select>
            </div>
        """)
        
        # Add legend at the top
        html_parts.append("""
            <div class="warehouse-legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #e3f2fd;"></div>
                    <span>Available</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #1976d2;"></div>
                    <span>Occupied</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #64b5f6;"></div>
                    <span>Partial</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #0d47a1;"></div>
                    <span>Allocated</span>
                </div>
            </div>
        """)
        
        if not warehouse_map:
            html_parts.append("""
                <div style="text-align: center; padding: 40px; color: #6c757d;">
                    <p>No warehouse data available.</p>
                    <small>Create storage locations to see the warehouse floor.</small>
                </div>
            """)
            return "".join(html_parts)
        
        # Get allocated locations from job items
        allocated_locations = set()
        if hasattr(self, 'items') and self.items:
            for item in self.items:
                location = getattr(item, 'location', None)
                if location:
                    # Normalize location format to match our structure
                    allocated_locations.add(location)
                    # Also add with forward slashes for compatibility
                    normalized_location = location.replace('/', '/')
                    allocated_locations.add(normalized_location)
        
        html_parts = []
        
        # Render hierarchical structure: Site → Building → Zone → Aisle → Bay → Level
        for site, buildings in warehouse_map.items():
            html_parts.append(f'<div class="site-group" title="Site: {site}">')
            html_parts.append(f'<div class="site-title">🏢 {site}</div>')
            
            for building, zones in buildings.items():
                html_parts.append(f'<div class="building-group" data-building="{building}" title="Building: {building}">')
                html_parts.append(f'<div class="building-title">🏗️ {building}</div>')
                
                for zone, aisles in zones.items():
                    html_parts.append(f'<div class="zone-group" title="Zone: {zone}">')
                    html_parts.append(f'<div class="zone-title">📍 {zone}</div>')
                    
                    for aisle, bays in aisles.items():
                        html_parts.append(f'<div class="aisle-group" title="Aisle: {aisle}">')
                        html_parts.append(f'<div class="aisle-title">🚚 {aisle}</div>')
                        
                        for bay, levels in bays.items():
                            html_parts.append(f'<div class="bay-group" title="Bay: {bay}">')
                            html_parts.append(f'<div class="bay-title">📦 {bay}</div>')
                            
                            html_parts.append(f'<div class="level-grid">')
                            
                            for level, data in levels.items():
                                available_count = data.get("available_count", 0)
                                total_count = data.get("location_count", 0)
                                
                                # Determine square status
                                if total_count == 0:
                                    status_class = "partial"
                                elif available_count == 0:
                                    status_class = "occupied"
                                elif available_count == total_count:
                                    status_class = "available"
                                else:
                                    status_class = "partial"
                                
                                # Check if this location is allocated (try multiple formats)
                                location_name = f"{site}/{building}/{zone}/{aisle}/{bay}/{level}"
                                location_name_alt = f"{site}/{building}/{zone}/{aisle}/{bay}/{level}"
                                
                                is_allocated = (
                                    location_name in allocated_locations or 
                                    location_name_alt in allocated_locations or
                                    any(loc in location_name for loc in allocated_locations)
                                )
                                
                                if is_allocated:
                                    status_class = "allocated"
                                
                                # Create simple tooltip with just location code
                                location_code = f"{bay}-{level}"
                                
                                html_parts.append(f"""
                                    <div class="warehouse-square {status_class}" title="{location_code}">
                                        <div class="square-tooltip">
                                            {location_code}
                                        </div>
                                    </div>
                                """)
                            
                            html_parts.append('</div>')
                            html_parts.append('</div>')  # Close bay-group
                        
                        html_parts.append('</div>')  # Close aisle-group
                    html_parts.append('</div>')  # Close zone-group
                html_parts.append('</div>')  # Close building-group
            html_parts.append('</div>')  # Close site-group
        
        return "".join(html_parts)
    
    def _render_location_list(self, company, branch):
        """Render list of applicable locations with storage type and details"""
        try:
            # Get storage locations filtered by company and site
            filters = {}
            if company:
                filters["company"] = company
            if hasattr(self, 'site') and self.site:
                filters["site"] = self.site
            
            locations = frappe.get_all("Storage Location", 
                fields=["name", "site", "building", "zone", "aisle", "bay", "level", "status", "storage_type"],
                filters=filters,
                order_by="site, building, zone, aisle, bay, level"
            )
            
            if not locations:
                return """
                    <div style="text-align: center; padding: 40px; color: #6c757d;">
                        <p>No storage locations available.</p>
                        <small>Create storage locations to see the location list.</small>
                    </div>
                """
            
            # Get allocated locations from job items
            allocated_locations = set()
            if hasattr(self, 'items') and self.items:
                for item in self.items:
                    location = getattr(item, 'location', None)
                    if location:
                        allocated_locations.add(location)
                        # Also add with forward slashes for compatibility
                        normalized_location = location.replace('/', '/')
                        allocated_locations.add(normalized_location)
            
            html_parts = []
            
            # Add header
            html_parts.append("""
                <div style="margin-bottom: 20px; text-align: center;">
                    <h3 style="margin: 0; color: #333; font-size: 16px;">Applicable Storage Locations</h3>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 12px;">
                        Filtered by Company: {company} | Branch: {branch}
                    </p>
                </div>
            """.format(company=company or "All", branch=branch or "All"))
            
            # Render location items
            for loc in locations:
                location_name = f"{loc.get('bay', 'N/A')}-{loc.get('level', 'N/A')}"
                location_path = f"{loc.get('site', 'N/A')} / {loc.get('building', 'N/A')} / {loc.get('zone', 'N/A')} / {loc.get('aisle', 'N/A')}"
                
                # Check if location is allocated
                is_allocated = location_name in allocated_locations or any(
                    location_name in allocated_loc for allocated_loc in allocated_locations
                )
                
                status_class = "allocated" if is_allocated else "available"
                status_text = "Allocated" if is_allocated else "Available"
                status_badge_class = "status-allocated" if is_allocated else "status-available"
                
                html_parts.append(f"""
                    <div class="location-item {status_class}">
                        <div class="location-code">{location_name}</div>
                        <div class="location-details">
                            <div class="location-path">{location_path}</div>
                            <div class="location-info">
                                <span>Type: {loc.get('storage_type', 'N/A')}</span>
                                <span>Status: {loc.get('status', 'N/A')}</span>
                                <span>Site: {loc.get('site', 'N/A')}</span>
                                <span>Building: {loc.get('building', 'N/A')}</span>
                            </div>
                        </div>
                        <div class="location-status {status_badge_class}">{status_text}</div>
                    </div>
                """)
            
            return "".join(html_parts)
            
        except Exception as e:
            frappe.logger().error(f"Error rendering location list: {e}")
            return """
                <div style="text-align: center; padding: 40px; color: #dc3545;">
                    <p>Error loading locations.</p>
                    <small>Please try again later.</small>
                </div>
            """
    
    def _render_warehouse_map(self, warehouse_map):
        """Render warehouse map HTML (legacy method for backward compatibility)"""
        return self._render_cinema_style_map(warehouse_map)

    def calculate_totals(self):
        """Calculate total volume, weight, and handling units for the job."""
        if not self.items:
            self.total_volume = 0
            self.total_weight = 0
            self.total_handling_units = 0
            return
        
        total_volume = 0
        total_weight = 0
        unique_handling_units = set()
        
        for item in self.items:
            # Calculate volume if dimensions are available
            if item.length and item.width and item.height:
                item_volume = flt(item.length) * flt(item.width) * flt(item.height)
            elif item.volume:
                item_volume = flt(item.volume)
            else:
                item_volume = 0
            
            # Add volume based on volume_qty_type setting
            if getattr(self, 'volume_qty_type', 'Total') == 'Total':
                # Volume is total for the entire quantity, not per unit
                total_volume += item_volume
            else:
                # Volume is per unit, so multiply by quantity
                total_volume += item_volume * flt(item.quantity or 0)
            
            # Add weight based on weight_qty_type setting
            if item.weight:
                if getattr(self, 'weight_qty_type', 'Per Unit') == 'Per Unit':
                    # Weight is per unit, so multiply by quantity
                    total_weight += flt(item.weight) * flt(item.quantity or 0)
                else:
                    # Weight is total for the entire quantity, not per unit
                    total_weight += flt(item.weight)
            
            # Count unique handling units
            if item.handling_unit:
                unique_handling_units.add(item.handling_unit)
        
        self.total_volume = total_volume
        self.total_weight = total_weight
        self.total_handling_units = len(unique_handling_units)

    def create_job_costing_number_if_needed(self):
        """Create Job Costing Number when document is first saved"""
        # Only create if job_costing_number is not set
        if not self.job_costing_number:
            # Check if this is the first save (no existing Job Costing Number)
            existing_job_ref = frappe.db.get_value("Job Costing Number", {
                "job_type": "Warehouse Job",
                "job_no": self.name
            })
            
            if not existing_job_ref:
                # Create Job Costing Number
                job_ref = frappe.new_doc("Job Costing Number")
                job_ref.job_type = "Warehouse Job"
                job_ref.job_no = self.name
                job_ref.company = self.company
                job_ref.branch = self.branch
                job_ref.cost_center = self.cost_center
                job_ref.profit_center = self.profit_center
                # Leave recognition_date blank - will be filled in separate function
                # Use warehouse job's job_open_date instead
                job_ref.job_open_date = self.job_open_date
                job_ref.insert(ignore_permissions=True)
                
                # Set the job_costing_number field
                self.job_costing_number = job_ref.name
                
                frappe.msgprint(_("Job Costing Number {0} created successfully").format(job_ref.name))

    def on_submit(self):
        # Validate capacity limits before submitting
        from logistics.warehousing.api_parts.capacity_management import validate_warehouse_job_capacity
        validate_warehouse_job_capacity(self)
        
        job_type = (getattr(self, "type", "") or "").strip()

        if not getattr(self, "items", None):
            # For Stocktake jobs, allow empty items if populate adjustment has been triggered
            if job_type == "Stocktake":
                populate_triggered = getattr(self, "populate_adjustment_triggered", False)
                if not populate_triggered:
                    frappe.throw(_("No items to post to the Warehouse Stock Ledger. Either add items manually or use 'Populate Adjustments' button."))
            else:
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
                if qty == 0 and job_type != "Stocktake":
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
                        "Row #{0}: Insufficient stock to move/pick {1}. "
                        "Beginning qty: {2}, would end at {3}."
                    ).format(ji.idx, abs(delta), beg, end)
                )

            _make_ledger_row(self, ji, delta, beg, end, posting_dt)

        # Update storage location statuses after all ledger entries are created
        from logistics.warehousing.api import _set_sl_status_by_balance
        affected_locations = set()
        for ji in self.items:
            if getattr(ji, "location", None):
                affected_locations.add(ji.location)
        
        for location in affected_locations:
            _set_sl_status_by_balance(location)

    def _get_milestone_status(self, handling_unit_name, job_type):
        """Get milestone status for a handling unit"""
        try:
            # Default milestone status - all incomplete
            milestones = {
                'start': False,
                'received': False,
                'putaway': False,
                'picked': False,
                'released': False
            }
            
            # For now, return default status
            # TODO: Implement actual milestone tracking based on operations
            return milestones
            
        except Exception as e:
            frappe.logger().error(f"Error getting milestone status for {handling_unit_name} (job_type: {job_type}): {str(e)}")
            return {
                'start': False,
                'received': False,
                'putaway': False,
                'picked': False,
                'released': False
            }
    
    def _get_milestone_details(self, handling_unit_name, job_type):
        """Get milestone details for a handling unit"""
        try:
            # Default milestone details
            details = {
                'received': {'location': 'Pending', 'date': ''},
                'putaway': {'location': 'Pending', 'date': ''},
                'picked': {'location': 'Pending', 'date': ''},
                'released': {'location': 'Pending', 'date': ''}
            }
            
            # For now, return default details
            # TODO: Implement actual milestone details based on operations
            return details
            
        except Exception as e:
            frappe.logger().error(f"Error getting milestone details for {handling_unit_name} (job_type: {job_type}): {str(e)}")
            return {
                'received': {'location': 'Pending', 'date': ''},
                'putaway': {'location': 'Pending', 'date': ''},
                'picked': {'location': 'Pending', 'date': ''},
                'released': {'location': 'Pending', 'date': ''}
            }

# ---------------------------------------------------------------------------
# Charges pricing helpers
# ---------------------------------------------------------------------------

def _find_customer_contract(customer: str | None) -> str | None:
    """Find an active Warehouse Contract for a given customer (prefers submitted)."""
    if not customer:
        return None
    cond = {"customer": customer}
    rows = frappe.get_all("Warehouse Contract", filters={**cond, "docstatus": 1}, fields=["name"], limit=1)
    if rows:
        return rows[0]["name"]
    rows = frappe.get_all("Warehouse Contract", filters={**cond, "docstatus": 0}, fields=["name"], limit=1)
    return rows[0]["name"] if rows else None


def _get_charge_price_from_contract(contract: str | None, item_code: str | None):
    """Return (rate, currency, uom) for a charge item from Warehouse Contract Item; None if not found."""
    if not contract or not item_code:
        return None, None, None
    row = frappe.get_all(
        "Warehouse Contract Item",
        filters={"parent": contract, "parenttype": "Warehouse Contract", "item_charge": item_code},
        fields=["rate", "currency", "uom"],
        limit=1,
        ignore_permissions=True,
    )
    if row:
        return flt(row[0].get("rate") or 0.0), row[0].get("currency"), row[0].get("uom")
    return None, None, None


@frappe.whitelist()
def warehouse_job_fetch_charge_price(warehouse_job: str, item_code: str) -> dict:
    """Client helper: fetch rate/currency/uom for charge item based on the Job's contract (or customer's)."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    contract = getattr(job, "warehouse_contract", None) or _find_customer_contract(getattr(job, "customer", None))
    rate, currency, uom = _get_charge_price_from_contract(contract, item_code)
    return {"rate": flt(rate or 0.0), "currency": currency, "uom": uom}


@frappe.whitelist()
def calculate_charges_from_contract(warehouse_job: str) -> dict:
    """Recalculate existing charges for a warehouse job based on its contract."""
    try:
        job = frappe.get_doc("Warehouse Job", warehouse_job)
        
        # Check if charges exist
        if not getattr(job, "charges", None) or len(job.charges) == 0:
            return {"ok": False, "message": "No charges found. Please add charges first."}
        
        # Get contract
        contract = getattr(job, "warehouse_contract", None) or _find_customer_contract(getattr(job, "customer", None))
        if not contract:
            return {"ok": False, "message": "No warehouse contract found for this job."}
        
        # Get contract items for job charges
        contract_items = frappe.db.sql("""
            SELECT 
                item_charge AS item_code, 
                rate, 
                currency, 
                uom, 
                handling_unit_type, 
                storage_type, 
                unit_type,
                inbound_charge,
                outbound_charge,
                transfer_charge,
                vas_charge,
                stocktake_charge,
                billing_time_unit,
                billing_time_multiplier,
                minimum_billing_time
            FROM `tabWarehouse Contract Item`
            WHERE parent = %s AND parenttype = 'Warehouse Contract'
            AND (inbound_charge = 1 OR outbound_charge = 1 OR transfer_charge = 1 OR vas_charge = 1 OR stocktake_charge = 1)
            ORDER BY handling_unit_type, storage_type
        """, (contract,), as_dict=True)
        
        if not contract_items:
            return {"ok": False, "message": "No job charge items found in contract."}
        
        # Recalculate existing charges
        charges_updated = 0
        job_type = getattr(job, "type", "Generic")
        standard_cost_warnings = []
        
        for charge in job.charges:
            item_code = getattr(charge, "item_code", None)
            if not item_code:
                continue
                
            # Find matching contract item
            contract_item = None
            for ci in contract_items:
                if ci.get("item_code") == item_code:
                    contract_item = ci
                    break
            
            if contract_item and _contract_item_applies_to_job_type(contract_item, job_type):
                # Recalculate quantity and rate based on contract
                billing_qty, billing_method = _calculate_contract_based_quantity_for_job(job, contract_item)
                
                # Update charge with contract values
                charge.rate = flt(contract_item.get("rate", 0))
                charge.currency = contract_item.get("currency", _get_default_currency(job.company))
                charge.uom = contract_item.get("uom", "Day")
                charge.quantity = billing_qty
                charge.total = billing_qty * flt(contract_item.get("rate", 0))
                
                # Update calculation notes
                charge.calculation_notes = _generate_comprehensive_calculation_notes_for_contract_charge(
                    job, contract_item, billing_method, billing_qty
                )
                
                # Calculate and set standard cost if enabled
                warnings = _calculate_standard_cost_for_charge(charge, job)
                if warnings:
                    standard_cost_warnings.extend(warnings)
                
                charges_updated += 1
        
        # Save the job
        job.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Prepare response message
        message = f"Recalculated {charges_updated} charge(s) based on contract."
        if standard_cost_warnings:
            message += f"\n\nStandard Cost Warnings:\n" + "\n".join([f"• {warning}" for warning in standard_cost_warnings])
        
        return {
            "ok": True, 
            "message": message,
            "charges_updated": charges_updated,
            "warnings": standard_cost_warnings
        }
        
    except Exception as e:
        frappe.log_error(f"Error calculating charges from contract: {str(e)}")
        return {"ok": False, "message": f"Error: {str(e)}"}


def _calculate_standard_cost_for_charge(charge, job):
    """Calculate and set standard cost for a charge if standard costing is enabled."""
    warnings = []
    
    try:
        # Check if standard costing is enabled in warehouse settings
        # Warehouse Settings is keyed by company, not a singleton
        company = getattr(job, 'company', None)
        
        if not company:
            frappe.logger().info("No company found for job, skipping standard cost calculation")
            warnings.append("No company found for job, skipping standard cost calculation")
            return warnings
        
        enable_standard_costing = frappe.db.get_value("Warehouse Settings", company, "enable_standard_costing")
        frappe.logger().info(f"Standard costing enabled for company {company}: {enable_standard_costing}")
        
        if not enable_standard_costing:
            frappe.logger().info(f"Standard costing not enabled for company {company}")
            warnings.append(f"Standard costing is not enabled for company {company}. Please enable it in Warehouse Settings.")
            return warnings
        
        # Get item code
        item_code = getattr(charge, 'item_code', None) or getattr(charge, 'item', None)
        frappe.logger().info(f"Processing standard cost for item: {item_code}")
        
        if not item_code:
            frappe.logger().info("No item code found for charge, skipping standard cost calculation")
            warnings.append("No item code found for charge, skipping standard cost calculation")
            return warnings
        
        # Get standard unit cost from item
        item_doc = frappe.get_doc("Item", item_code)
        standard_unit_cost = flt(getattr(item_doc, 'custom_standard_unit_cost', 0))
        frappe.logger().info(f"Standard unit cost for item {item_code}: {standard_unit_cost}")
        
        if standard_unit_cost > 0:
            # Calculate standard cost (quantity × standard unit cost)
            quantity = flt(getattr(charge, 'quantity', 0))
            standard_cost = quantity * standard_unit_cost
            frappe.logger().info(f"Calculated standard cost: {quantity} × {standard_unit_cost} = {standard_cost}")
            
            # Set standard unit cost and total standard cost
            charge.standard_unit_cost = standard_unit_cost
            charge.total_standard_cost = standard_cost
            
            # Add standard cost to calculation notes if it exists
            if hasattr(charge, 'calculation_notes') and charge.calculation_notes:
                # Add standard cost information to existing notes
                notes = charge.calculation_notes
                if "Standard Cost:" not in notes:
                    notes += f"\n  • Standard Cost: {quantity} × {standard_unit_cost} = {standard_cost}"
                    charge.calculation_notes = notes
            else:
                # Create new calculation notes with standard cost
                charge.calculation_notes = f"""Standard Cost Calculation:
  • Item: {item_code}
  • Quantity: {quantity}
  • Standard Unit Cost: {standard_unit_cost}
  • Standard Cost: {quantity} × {standard_unit_cost} = {standard_cost}"""
        else:
            frappe.logger().info(f"No standard unit cost found for item {item_code} (value: {standard_unit_cost})")
            warnings.append(f"No standard unit cost found for item {item_code}. Please set the 'Standard Unit Cost' field in the Item master.")
            
    except Exception as e:
        frappe.log_error(f"Error calculating standard cost for charge: {str(e)}")
        warnings.append(f"Error calculating standard cost: {str(e)}")
    
    return warnings


@frappe.whitelist()
def update_operation_start(job_name, operation_id, start_date):
    """Update operation start date"""
    try:
        frappe.logger().info(f"update_operation_start called with: job_name={job_name}, operation_id={operation_id}, start_date={start_date}")
        
        # Convert operation_id to integer
        operation_id = int(operation_id)
        
        # Get the warehouse job
        job = frappe.get_doc('Warehouse Job', job_name)
        frappe.logger().info(f"Job loaded: {job.name}, operations count: {len(job.operations) if hasattr(job, 'operations') else 0}")
        
        # Check if operation exists
        if hasattr(job, 'operations') and len(job.operations) > operation_id:
            operation = job.operations[operation_id]
            frappe.logger().info(f"Operation found: {operation.operation}, current start_date: {operation.start_date}")
            
            # Update the start date
            operation.start_date = start_date
            frappe.logger().info(f"Set start_date to: {operation.start_date}")
            
            # Compute actual_hours if both start and end dates are present
            if operation.start_date and operation.end_date:
                from frappe.utils import get_datetime
                start_dt = get_datetime(operation.start_date)
                end_dt = get_datetime(operation.end_date)
                frappe.logger().info(f"update_operation_start: start_dt={start_dt} (type: {type(start_dt)})")
                frappe.logger().info(f"update_operation_start: end_dt={end_dt} (type: {type(end_dt)})")
                if start_dt and end_dt:
                    # Handle timezone-aware datetimes by converting to naive datetimes
                    if hasattr(start_dt, 'replace'):
                        start_dt = start_dt.replace(tzinfo=None)
                    if hasattr(end_dt, 'replace'):
                        end_dt = end_dt.replace(tzinfo=None)
                    
                    sec = max(0.0, (end_dt - start_dt).total_seconds())
                    operation.actual_hours = round(sec / 3600.0, 4)
                    frappe.logger().info(f"Computed actual_hours: {operation.actual_hours} from {sec} seconds")
            
            # Save the job
            job.save()
            frappe.db.commit()
            
            # Verify the save
            job.reload()
            updated_operation = job.operations[operation_id]
            frappe.logger().info(f"After save - start_date: {updated_operation.start_date}")
            
            return {"message": "Operation start date updated successfully"}
        else:
            return {"error": f"Operation not found. Available operations: {len(job.operations) if hasattr(job, 'operations') else 0}"}
            
    except Exception as e:
        frappe.logger().error(f"Error updating operation start: {e}")
        import traceback
        frappe.logger().error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}


@frappe.whitelist()
def update_operation_end(job_name, operation_id, end_date):
    """Update operation end date"""
    try:
        frappe.logger().info(f"update_operation_end called with: job_name={job_name}, operation_id={operation_id}, end_date={end_date}")
        
        # Convert operation_id to integer
        operation_id = int(operation_id)
        
        # Get the warehouse job
        job = frappe.get_doc('Warehouse Job', job_name)
        frappe.logger().info(f"Job loaded: {job.name}, operations count: {len(job.operations) if hasattr(job, 'operations') else 0}")
        
        # Check if operation exists
        if hasattr(job, 'operations') and len(job.operations) > operation_id:
            operation = job.operations[operation_id]
            frappe.logger().info(f"Operation found: {operation.operation}, current end_date: {operation.end_date}")
            
            # Update the end date
            operation.end_date = end_date
            frappe.logger().info(f"Set end_date to: {operation.end_date}")
            
            # Compute actual_hours if both start and end dates are present
            if operation.start_date and operation.end_date:
                from frappe.utils import get_datetime
                start_dt = get_datetime(operation.start_date)
                end_dt = get_datetime(operation.end_date)
                if start_dt and end_dt:
                    # Handle timezone-aware datetimes by converting to naive datetimes
                    if hasattr(start_dt, 'replace'):
                        start_dt = start_dt.replace(tzinfo=None)
                    if hasattr(end_dt, 'replace'):
                        end_dt = end_dt.replace(tzinfo=None)
                    
                    sec = max(0.0, (end_dt - start_dt).total_seconds())
                    operation.actual_hours = round(sec / 3600.0, 4)
                    frappe.logger().info(f"Computed actual_hours: {operation.actual_hours} from {sec} seconds")
            
            # Save the job
            job.save()
            frappe.db.commit()
            
            # Verify the save
            job.reload()
            updated_operation = job.operations[operation_id]
            frappe.logger().info(f"After save - end_date: {updated_operation.end_date}")
            
            return {"message": "Operation end date updated successfully"}
        else:
            return {"error": f"Operation not found. Available operations: {len(job.operations) if hasattr(job, 'operations') else 0}"}
            
    except Exception as e:
        frappe.logger().error(f"Error updating operation end: {e}")
        import traceback
        frappe.logger().error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}



@frappe.whitelist()
def allocate_items(job_name: str) -> Dict[str, Any]:
    """
    Allocate items in a warehouse job following proper allocation policies.
    Supports different allocation types based on job type: Pick, Putaway, Move, VAS.
    
    Args:
        job_name: Name of the Warehouse Job
    
    Returns:
        Dict with success status and details
    """
    try:
        job = frappe.get_doc("Warehouse Job", job_name)
        
        if not job.staging_area:
            return {
                "success": False,
                "error": "Staging area is required for allocation"
            }
        
        # Check if there are orders to allocate from
        if not job.orders or len(job.orders) == 0:
            return {
                "success": False,
                "error": "No orders found in the job. Please add orders before allocating."
            }
        
        # Determine allocation method based on job type
        job_type = (job.type or "").strip()
        result = None
        
        if job_type == "Pick":
            result = frappe.call(
                "logistics.warehousing.api.allocate_pick",
                warehouse_job=job_name
            )
        elif job_type == "Putaway":
            result = frappe.call(
                "logistics.warehousing.api.allocate_putaway",
                warehouse_job=job_name
            )
        elif job_type == "Move":
            result = frappe.call(
                "logistics.warehousing.api.allocate_move",
                warehouse_job=job_name,
                clear_existing=1
            )
        elif job_type == "VAS":
            result = frappe.call(
                "logistics.warehousing.api_parts.vas.allocate_vas",
                warehouse_job=job_name
            )
        else:
            return {
                "success": False,
                "error": f"Unsupported job type '{job_type}'. Supported types: Pick, Putaway, Move, VAS"
            }
        
        if result and result.get("ok"):
            # Handle Move allocation which returns created_pairs instead of created_rows
            if job_type == "Move":
                created_pairs = result.get("created_pairs", 0)
                skipped = result.get("skipped", [])
                if created_pairs == 0 and skipped:
                    return {
                        "success": False,
                        "error": f"Allocation failed: No move pairs created. {len(skipped)} order(s) skipped. Reasons: {', '.join(skipped[:3])}",
                        "warnings": skipped
                    }
                return {
                    "success": True,
                    "allocated_count": created_pairs * 2,  # Each pair creates 2 items (from and to)
                    "allocated_qty": 0,  # Move doesn't track qty separately
                    "message": result.get("message", f"Allocated {created_pairs} move pair(s)"),
                    "warnings": skipped if skipped else [],
                    "details": []
                }
            return {
                "success": True,
                "allocated_count": result.get("created_rows", 0),
                "allocated_qty": result.get("created_qty", 0),
                "message": result.get("message", f"Allocated {result.get('created_rows', 0)} items"),
                "warnings": result.get("warnings", []),
                "details": result.get("lines", [])
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Allocation failed") if result else "Allocation failed",
                "warnings": result.get("warnings", []) if result else []
            }
        
    except Exception as e:
        frappe.log_error(f"Error allocating items: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def clear_allocations(job_name: str) -> Dict[str, Any]:
    """
    Clear all allocations in a warehouse job.
    
    Args:
        job_name: Name of the Warehouse Job
    
    Returns:
        Dict with success status and details
    """
    try:
        job = frappe.get_doc("Warehouse Job", job_name)
        
        if not job.items:
            return {
                "success": False,
                "error": "No items found in the job"
            }
        
        cleared_count = 0
        
        for item in job.items:
            if item.location or item.handling_unit:
                item.location = None
                item.handling_unit = None
                cleared_count += 1
        
        job.save()
        
        return {
            "success": True,
            "cleared_count": cleared_count,
            "message": f"Cleared allocations for {cleared_count} items"
        }
        
    except Exception as e:
        frappe.log_error(f"Error clearing allocations: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def create_operations(job_name: str) -> Dict[str, Any]:
    """
    Create operations from operation templates based on job type.
    Fills Warehouse Job Operations with Unit Std Hours, Handling Basis, Handling UOM,
    and Quantity based on handling_basis from Warehouse Operation Item.
    
    Args:
        job_name: Name of the Warehouse Job
    
    Returns:
        Dict with success status and details
    """
    try:
        job = frappe.get_doc("Warehouse Job", job_name)
        
        if not job.type:
            return {
                "success": False,
                "error": "Job type is required to create operations from templates."
            }
        
        created_count = 0
        
        # Clear existing operations first
        job.set("operations", [])
        
        # Get operation templates for this job type with handling_basis, ordered by order field
        templates = frappe.get_all(
            "Warehouse Operation Item",
            filters={
                "used_in": job.type
            },
            fields=["name", "code", "operation_name", "unit_std_hours", "handling_basis", "handling_uom", "notes", "order"],
            order_by="`order` asc, operation_name asc"
        )
        
        if not templates:
            return {
                "success": False,
                "error": f"No operation templates found for job type '{job.type}'. Please create operation templates first."
            }
        
        # Calculate quantities based on handling_basis from job items
        job_quantities = _calculate_job_quantities(job)
        
        # Log calculated quantities for debugging
        frappe.logger().info(f"Calculated job quantities for {job.name}: {job_quantities}")
        
        # Create operations from templates (already ordered by order field)
        for template in templates:
            operation = job.append("operations", {})
            operation.operation = template.name  # Link to Warehouse Operation Item
            operation.description = template.notes or template.operation_name
            operation.unit_std_hours = template.unit_std_hours or 0
            operation.handling_basis = template.handling_basis or "Item Unit"
            
            # Set handling_uom if field exists - use from template first, fallback to first job item
            if hasattr(operation, 'handling_uom'):
                handling_uom = template.handling_uom
                
                # If template doesn't have handling_uom, get from first job item as fallback
                if not handling_uom and job.items:
                    first_item = job.items[0].get("item")
                    if first_item:
                        handling_uom = frappe.db.get_value("Warehouse Item", first_item, "uom")
                
                if handling_uom:
                    operation.handling_uom = handling_uom
            
            operation.order = template.order or 0
            
            # Calculate quantity based on handling_basis
            handling_basis = template.handling_basis or "Item Unit"
            if handling_basis == "Task":
                operation.quantity = 1
            else:
                operation.quantity = job_quantities.get(handling_basis, 0)
            
            # Calculate total_std_hours
            operation.total_std_hours = operation.unit_std_hours * operation.quantity
            
            operation.actual_hours = 0
            operation.start_date = None
            operation.end_date = None
            created_count += 1
        
        job.save()
        
        return {
            "success": True,
            "created_count": created_count,
            "message": f"Created {created_count} operations from templates for {job.type} job type"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating operations: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def _calculate_job_quantities(job) -> Dict[str, float]:
    """
    Calculate quantities for different handling_basis types from warehouse job items.
    
    Args:
        job: Warehouse Job document
        
    Returns:
        Dict with quantities for each handling_basis type
    """
    quantities = {
        "Item Unit": 0,
        "Volume": 0,
        "Weight": 0,
        "Handling Unit": 0,
        "Task": 0
    }
    
    if not job.items:
        return quantities
    
    unique_handling_units = set()
    
    for item in job.items:
        qty = flt(item.quantity or 0)
        
        # Item Unit: sum of all item quantities
        quantities["Item Unit"] += qty
        
        # Volume: calculate based on volume_qty_type setting
        item_volume = 0
        if item.volume and item.volume > 0:
            # Use direct volume if available
            item_volume = flt(item.volume)
        elif item.length and item.width and item.height:
            # Calculate volume from dimensions if volume not provided
            item_volume = flt(item.length) * flt(item.width) * flt(item.height)
        else:
            # Try to get volume from Warehouse Item if available
            try:
                if item.item:
                    warehouse_item = frappe.get_doc("Warehouse Item", item.item)
                    if warehouse_item.volume and warehouse_item.volume > 0:
                        item_volume = flt(warehouse_item.volume)
                    elif warehouse_item.length and warehouse_item.width and warehouse_item.height:
                        item_volume = flt(warehouse_item.length) * flt(warehouse_item.width) * flt(warehouse_item.height)
            except:
                pass  # If Warehouse Item not found or no volume data, use 0
        
        # Add volume based on volume_qty_type setting
        if getattr(job, 'volume_qty_type', 'Total') == 'Total':
            # Volume is total for the entire quantity, not per unit
            quantities["Volume"] += item_volume
        else:
            # Volume is per unit, so multiply by quantity
            quantities["Volume"] += item_volume * qty
        
        # Weight: calculate based on weight_qty_type setting
        item_weight = 0
        if item.weight and item.weight > 0:
            # Use direct weight if available
            item_weight = flt(item.weight)
        else:
            # Try to get weight from Warehouse Item if available
            try:
                if item.item:
                    warehouse_item = frappe.get_doc("Warehouse Item", item.item)
                    if warehouse_item.weight and warehouse_item.weight > 0:
                        item_weight = flt(warehouse_item.weight)
            except:
                pass  # If Warehouse Item not found or no weight data, use 0
        
        # Add weight based on weight_qty_type setting
        if getattr(job, 'weight_qty_type', 'Per Unit') == 'Per Unit':
            # Weight is per unit, so multiply by quantity
            quantities["Weight"] += item_weight * qty
        else:
            # Weight is total for the entire quantity, not per unit
            quantities["Weight"] += item_weight
        
        # Handling Unit: count unique handling units
        if item.handling_unit:
            unique_handling_units.add(item.handling_unit)
    
    quantities["Handling Unit"] = len(unique_handling_units)
    
    return quantities


@frappe.whitelist()
def get_warehouse_dashboard_html(job_name):
    """Standalone function to get warehouse dashboard HTML"""
    try:
        # Validate job_name
        if not job_name or job_name == 'new-warehouse-job':
            return f"""
                <div style="padding: 24px; text-align: center; color: #64748b; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <h3 style="color: #334155; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Dashboard Ready</h3>
                    <p style="margin: 0; font-size: 14px; line-height: 1.5;">Save the warehouse job to view the dashboard and start tracking your operations.</p>
                </div>
            """
        
        # Check if job exists
        if not frappe.db.exists("Warehouse Job", job_name):
            # Check if this looks like an unsaved job (temporary name pattern)
            if job_name and (job_name.startswith('new-warehouse-job-') or job_name.startswith('WRO') and len(job_name) > 10):
                return f"""
                    <div style="padding: 24px; text-align: center; color: #64748b; background: #fef3c7; border-radius: 8px; border: 1px solid #fbbf24;">
                        <h3 style="color: #d97706; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Save Required</h3>
                        <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.5;">This warehouse job has not been saved yet. Please save the job first to load the dashboard.</p>
                        <div style="background: #fef3c7; padding: 12px; border-radius: 6px; border-left: 3px solid #f59e0b;">
                            <p style="margin: 0; font-size: 13px; color: #92400e; font-weight: 500;">Click the "Save" button to save your changes and then refresh the dashboard.</p>
                        </div>
                    </div>
                """
            else:
                return f"""
                    <div style="padding: 24px; text-align: center; color: #64748b; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;">
                        <h3 style="color: #dc2626; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Job Not Available</h3>
                        <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.5;">The warehouse job <strong>{job_name}</strong> could not be found. It may have been deleted or moved.</p>
                        <div style="background: #fef3c7; padding: 12px; border-radius: 6px; border-left: 3px solid #f59e0b;">
                            <p style="margin: 0; font-size: 13px; color: #92400e; font-weight: 500;">Try refreshing the page or creating a new warehouse job to get started.</p>
                        </div>
                    </div>
                """
        
        job = frappe.get_doc("Warehouse Job", job_name)
        return job.get_warehouse_dashboard_html(job_name)
        
    except frappe.DoesNotExistError:
        frappe.logger().error(f"Warehouse Job {job_name} does not exist")
        return f"""
            <div style="padding: 24px; text-align: center; color: #64748b; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;">
                <h3 style="color: #dc2626; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Job Not Available</h3>
                <p style="margin: 0; font-size: 14px; line-height: 1.5;">Warehouse Job {job_name} could not be found.</p>
            </div>
        """
    except Exception as e:
        frappe.logger().error(f"Error loading warehouse dashboard for {job_name}: {e}")
        return f"""
            <div style="padding: 24px; text-align: center; color: #64748b; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;">
                <h3 style="color: #dc2626; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Dashboard Error</h3>
                <p style="margin: 0; font-size: 14px; line-height: 1.5;">Unable to load the dashboard. Please refresh the page or contact support if the issue persists.</p>
            </div>
        """


# ---------------------------------------------------------------------------
# Warehouse Job Charges - Contract Billing Alignment
# ---------------------------------------------------------------------------

def _get_contract_item_details(contract: str | None, item_code: str | None) -> dict | None:
    """Get contract item details for billing method alignment."""
    if not contract or not item_code:
        return None
    
    try:
        row = frappe.get_all(
            "Warehouse Contract Item",
            filters={"parent": contract, "parenttype": "Warehouse Contract", "item_charge": item_code},
            fields=["unit_type", "uom", "rate", "currency", "billing_time_unit", "billing_time_multiplier", "minimum_billing_time"],
            limit=1,
            ignore_permissions=True,
        )
        return row[0] if row else None
    except Exception as e:
        frappe.logger().warning(f"Error getting contract item details: {e}")
        return None


def _calculate_contract_based_quantity(charge, job, contract_item) -> tuple[float, str]:
    """Calculate billing quantity based on contract billing method."""
    try:
        if not contract_item:
            # No contract, use simple quantity
            return flt(getattr(charge, 'quantity', 1)), "Manual Entry"
        
        unit_type = contract_item.get('unit_type', 'Day')
        billing_method = _map_unit_type_to_billing_method(unit_type)
        
        if billing_method == 'Per Day':
            qty = _calculate_per_day_quantity_for_job(job)
        elif billing_method == 'Per Volume':
            qty = _calculate_per_volume_quantity_for_job(charge, job)
        elif billing_method == 'Per Weight':
            qty = _calculate_per_weight_quantity_for_job(charge, job)
        elif billing_method == 'Per Piece':
            qty = _calculate_per_piece_quantity_for_job(charge, job)
        elif billing_method == 'Per Container':
            qty = _calculate_per_container_quantity_for_job(charge, job)
        elif billing_method == 'Per Hour':
            qty = _calculate_per_hour_quantity_for_job(charge, job)
        elif billing_method == 'Per Handling Unit':
            qty = _calculate_per_handling_unit_quantity_for_job(charge, job)
        elif billing_method == 'High Water Mark':
            qty = _calculate_high_water_mark_quantity_for_job(charge, job)
        else:
            qty = flt(getattr(charge, 'quantity', 1))
            
        return qty, billing_method
            
    except Exception as e:
        frappe.logger().warning(f"Error calculating contract-based quantity: {e}")
        return flt(getattr(charge, 'quantity', 1)), "Error"


def _map_unit_type_to_billing_method(unit_type: str) -> str:
    """Map contract unit_type to billing method."""
    mapping = {
        'Day': 'Per Day',
        'Volume': 'Per Volume', 
        'Weight': 'Per Weight',
        'Package': 'Per Container',
        'Piece': 'Per Piece',
        'Operation Time': 'Per Hour',
        'Handling Unit': 'Per Handling Unit',
        'High Water Mark': 'High Water Mark'
    }
    return mapping.get(unit_type, 'Per Day')


def _calculate_per_day_quantity_for_job(job) -> float:
    """Calculate days for job billing."""
    try:
        job_open_date = getattr(job, 'job_open_date', None)
        job_close_date = getattr(job, 'job_close_date', None)
        
        if not job_open_date:
            return 1.0
            
        if job_close_date:
            # Job is completed
            start_date = frappe.utils.getdate(job_open_date)
            end_date = frappe.utils.getdate(job_close_date)
            days = (end_date - start_date).days + 1
        else:
            # Job is ongoing, calculate from open date to today
            start_date = frappe.utils.getdate(job_open_date)
            end_date = frappe.utils.getdate()
            days = (end_date - start_date).days + 1
        
        return float(max(1, days))
    except Exception as e:
        frappe.logger().warning(f"Error calculating per day quantity: {e}")
        return 1.0


def _calculate_per_volume_quantity_for_job(charge, job) -> float:
    """Calculate volume quantity for job billing."""
    try:
        # Get volume from charge or calculate from job items
        volume_qty = getattr(charge, 'volume_quantity', 0)
        if volume_qty > 0:
            return flt(volume_qty)
        
        # Calculate from job items
        total_volume = 0.0
        for item in getattr(job, 'items', []) or []:
            volume = flt(getattr(item, 'volume', 0))
            quantity = flt(getattr(item, 'quantity', 0))
            
            # Calculate volume based on volume_qty_type setting
            if getattr(job, 'volume_qty_type', 'Total') == 'Total':
                # Volume is total for the entire quantity, not per unit
                total_volume += volume
            else:
                # Volume is per unit, so multiply by quantity
                total_volume += volume * quantity
        
        return total_volume
    except Exception as e:
        frappe.logger().warning(f"Error calculating per volume quantity: {e}")
        return 0.0


def _calculate_per_weight_quantity_for_job(charge, job) -> float:
    """Calculate weight quantity for job billing."""
    try:
        # Get weight from charge or calculate from job items
        weight_qty = getattr(charge, 'weight_quantity', 0)
        if weight_qty > 0:
            return flt(weight_qty)
        
        # Calculate from job items
        total_weight = 0.0
        for item in getattr(job, 'items', []) or []:
            weight = flt(getattr(item, 'weight', 0))
            quantity = flt(getattr(item, 'quantity', 0))
            total_weight += weight * quantity
        
        return total_weight
    except Exception as e:
        frappe.logger().warning(f"Error calculating per weight quantity: {e}")
        return 0.0


def _calculate_per_piece_quantity_for_job(charge, job) -> float:
    """Calculate piece quantity for job billing."""
    try:
        # Get piece quantity from charge or calculate from job items
        piece_qty = getattr(charge, 'piece_quantity', 0)
        if piece_qty > 0:
            return flt(piece_qty)
        
        # Calculate from job items
        total_pieces = 0.0
        for item in getattr(job, 'items', []) or []:
            quantity = flt(getattr(item, 'quantity', 0))
            total_pieces += quantity
        
        return total_pieces
    except Exception as e:
        frappe.logger().warning(f"Error calculating per piece quantity: {e}")
        return 1.0


def _calculate_per_container_quantity_for_job(charge, job) -> float:
    """Calculate container quantity for job billing."""
    try:
        # Get container quantity from charge or calculate from job items
        container_qty = getattr(charge, 'container_quantity', 0)
        if container_qty > 0:
            return flt(container_qty)
        
        # Calculate from job items
        containers = set()
        for item in getattr(job, 'items', []) or []:
            container = getattr(item, 'container', None)
            if container:
                containers.add(container)
        
        return float(len(containers)) if containers else float(len(getattr(job, 'items', [])))
    except Exception as e:
        frappe.logger().warning(f"Error calculating per container quantity: {e}")
        return 1.0


def _calculate_per_hour_quantity_for_job(charge, job) -> float:
    """Calculate hour quantity for job billing."""
    try:
        # Get hour quantity from charge or calculate from job timing
        hour_qty = getattr(charge, 'hour_quantity', 0)
        if hour_qty > 0:
            return flt(hour_qty)
        
        # Calculate from job start/end times
        job_open_date = getattr(job, 'job_open_date', None)
        job_close_date = getattr(job, 'job_close_date', None)
        
        if job_open_date and job_close_date:
            start_time = frappe.utils.get_datetime(f"{job_open_date} {getattr(job, 'job_open_time', '00:00:00')}")
            end_time = frappe.utils.get_datetime(f"{job_close_date} {getattr(job, 'job_close_time', '23:59:59')}")
            hours = (end_time - start_time).total_seconds() / 3600
            return max(1.0, hours)
        else:
            # Estimate based on job type
            job_type = getattr(job, 'job_type', 'Generic')
            estimated_hours = {
                'Inbound': 2.0,
                'Outbound': 1.5,
                'Transfer': 1.0,
                'VAS': 3.0,
                'Stocktake': 4.0
            }.get(job_type, 2.0)
            return estimated_hours
            
    except Exception as e:
        frappe.logger().warning(f"Error calculating per hour quantity: {e}")
        return 2.0


def _calculate_per_handling_unit_quantity_for_job(charge, job) -> float:
    """Calculate handling unit quantity for job billing."""
    try:
        # Get handling unit quantity from charge or calculate from job items
        hu_qty = getattr(charge, 'handling_unit_quantity', 0)
        if hu_qty > 0:
            return flt(hu_qty)
        
        # Calculate from job items
        handling_units = set()
        for item in getattr(job, 'items', []) or []:
            hu = getattr(item, 'handling_unit', None)
            if hu:
                handling_units.add(hu)
        
        return float(len(handling_units)) if handling_units else 1.0
    except Exception as e:
        frappe.logger().warning(f"Error calculating per handling unit quantity: {e}")
        return 1.0


def _calculate_high_water_mark_quantity_for_job(charge, job) -> float:
    """Calculate high water mark quantity for job billing."""
    try:
        # Get peak quantity from charge
        peak_qty = getattr(charge, 'peak_quantity', 0)
        if peak_qty > 0:
            return flt(peak_qty)
        
        # Calculate peak from job items (highest quantity at any point)
        max_quantity = 0.0
        for item in getattr(job, 'items', []) or []:
            quantity = flt(getattr(item, 'quantity', 0))
            max_quantity = max(max_quantity, quantity)
        
        return max_quantity if max_quantity > 0 else 1.0
    except Exception as e:
        frappe.logger().warning(f"Error calculating high water mark quantity: {e}")
        return 1.0


def _generate_comprehensive_calculation_notes(charge, job, contract_item, billing_method: str, billing_qty: float) -> str:
    """Generate comprehensive calculation notes for warehouse job charges."""
    try:
        quantity = flt(getattr(charge, 'quantity', 0))
        rate = flt(getattr(charge, 'rate', 0))
        total = flt(getattr(charge, 'total', 0))
        uom = getattr(charge, 'uom', 'N/A')
        currency = getattr(charge, 'currency', _get_default_currency(job.company))
        
        job_name = getattr(job, 'name', 'N/A')
        job_type = getattr(job, 'job_type', 'N/A')
        job_open_date = getattr(job, 'job_open_date', 'N/A')
        job_close_date = getattr(job, 'job_close_date', 'Ongoing')
        
        notes = f"""Warehouse Job Charge Calculation:
  • Warehouse Job: {job_name}
  • Job Type: {job_type}
  • Period: {job_open_date} to {job_close_date}
  • Billing Method: {billing_method}
  • UOM: {uom}
  • Rate per {uom}: {rate}
  • Billing Quantity: {billing_qty}
  • Calculation: {billing_qty} × {rate} = {total}
  • Currency: {currency}"""
        
        # Add method-specific calculation details
        if billing_method == 'Per Day':
            notes += f"""
  • Per Day Calculation:
    - Job Open Date: {job_open_date}
    - Job Close Date: {job_close_date}
    - Days Calculated: {billing_qty}"""
        elif billing_method == 'Per Volume':
            total_volume = _calculate_per_volume_quantity_for_job(charge, job)
            notes += f"""
  • Per Volume Calculation:
    - Total Volume from Job Items: {total_volume}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Weight':
            total_weight = _calculate_per_weight_quantity_for_job(charge, job)
            notes += f"""
  • Per Weight Calculation:
    - Total Weight from Job Items: {total_weight}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Piece':
            total_pieces = _calculate_per_piece_quantity_for_job(charge, job)
            notes += f"""
  • Per Piece Calculation:
    - Total Pieces from Job Items: {total_pieces}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Container':
            container_count = _calculate_per_container_quantity_for_job(charge, job)
            notes += f"""
  • Per Container Calculation:
    - Container Count from Job Items: {container_count}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Hour':
            hours = _calculate_per_hour_quantity_for_job(charge, job)
            notes += f"""
  • Per Hour Calculation:
    - Hours Calculated: {hours}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Handling Unit':
            hu_count = _calculate_per_handling_unit_quantity_for_job(charge, job)
            notes += f"""
  • Per Handling Unit Calculation:
    - Handling Units Count: {hu_count}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'High Water Mark':
            peak_qty = _calculate_high_water_mark_quantity_for_job(charge, job)
            notes += f"""
  • High Water Mark Calculation:
    - Peak Quantity: {peak_qty}
    - Billing Quantity: {billing_qty}"""
        
        # Add contract details
        if contract_item:
            notes += f"""
  • Contract Setup Applied:
    - Rate sourced from Warehouse Contract Item
    - Contract Unit Type: {contract_item.get('unit_type', 'N/A')}
    - Time billing settings: {contract_item.get('billing_time_unit', 'N/A')} unit, {contract_item.get('billing_time_multiplier', 1)} multiplier, {contract_item.get('minimum_billing_time', 1)} minimum
    - Contract UOM: {contract_item.get('uom', 'N/A')}
    - Contract Currency: {contract_item.get('currency', _get_default_currency(job.company))}"""
        else:
            notes += f"""
  • Contract Setup Applied:
    - Rate sourced from Warehouse Job Charges table
    - Applied based on job execution and contract terms
    - Charge type: {billing_method} billing method"""
        
        return notes
        
    except Exception as e:
        frappe.logger().warning(f"Error generating comprehensive calculation notes: {e}")
        return f"Calculation notes generation error: {str(e)}"


def _contract_item_applies_to_job_type(contract_item: dict, job_type: str) -> bool:
    """Check if a contract item applies to a specific job type."""
    job_type_mapping = {
        "Inbound": "inbound_charge",
        "Outbound": "outbound_charge",
        "Pick": "outbound_charge",  # Pick operations are outbound
        "Putaway": "inbound_charge",  # Putaway operations are inbound
        "Transfer": "transfer_charge",
        "VAS": "vas_charge",
        "Stocktake": "stocktake_charge"
    }
    
    charge_type = job_type_mapping.get(job_type, "inbound_charge")  # Default to inbound
    return bool(contract_item.get(charge_type, 0))


def _create_charge_from_contract_item(job, contract_item: dict) -> dict:
    """Create a charge from a contract item."""
    try:
        # Calculate billing quantity based on contract method
        billing_qty, billing_method = _calculate_contract_based_quantity_for_job(job, contract_item)
        
        if billing_qty <= 0:
            return None
        
        rate = flt(contract_item.get("rate", 0))
        total = billing_qty * rate
        
        # Create charge
        charge = {
            "item_code": contract_item.get("item_code"),
            "item_name": f"Job Charge ({job.get('job_type', 'Generic')})",
            "uom": contract_item.get("uom", "Day"),
            "quantity": billing_qty,
            "rate": rate,
            "total": total,
            "currency": contract_item.get("currency", _get_default_currency(job.company)),
            "calculation_notes": _generate_comprehensive_calculation_notes_for_contract_charge(
                job, contract_item, billing_method, billing_qty
            )
        }
        
        return charge
        
    except Exception as e:
        frappe.logger().warning(f"Error creating charge from contract item: {e}")
        return None


def _calculate_contract_based_quantity_for_job(job, contract_item: dict) -> tuple[float, str]:
    """Calculate billing quantity for a job based on contract item."""
    try:
        unit_type = contract_item.get('unit_type', 'Day')
        billing_method = _map_unit_type_to_billing_method(unit_type)
        
        
        if billing_method == 'Per Day':
            qty = _calculate_per_day_quantity_for_job(job)
        elif billing_method == 'Per Volume':
            qty = _calculate_per_volume_quantity_for_job_contract(job)
        elif billing_method == 'Per Weight':
            qty = _calculate_per_weight_quantity_for_job_contract(job)
        elif billing_method == 'Per Piece':
            qty = _calculate_per_piece_quantity_for_job_contract(job)
        elif billing_method == 'Per Container':
            qty = _calculate_per_container_quantity_for_job_contract(job)
        elif billing_method == 'Per Hour':
            qty = _calculate_per_hour_quantity_for_job_contract(job, contract_item)
        elif billing_method == 'Per Handling Unit':
            qty = _calculate_per_handling_unit_quantity_for_job_contract(job)
        elif billing_method == 'High Water Mark':
            qty = _calculate_high_water_mark_quantity_for_job_contract(job)
        else:
            qty = 1.0
        
            
        return qty, billing_method
            
    except Exception as e:
        frappe.logger().warning(f"Error calculating contract-based quantity: {e}")
        return 1.0, "Error"


def _calculate_per_volume_quantity_for_job_contract(job) -> float:
    """Calculate volume quantity for job billing from contract."""
    try:
        total_volume = 0.0
        for item in getattr(job, 'items', []) or []:
            volume = flt(getattr(item, 'volume', 0))
            quantity = flt(getattr(item, 'quantity', 0))
            
            # Calculate volume based on volume_qty_type setting
            if getattr(job, 'volume_qty_type', 'Total') == 'Total':
                # Volume is total for the entire quantity, not per unit
                total_volume += volume
            else:
                # Volume is per unit, so multiply by quantity
                total_volume += volume * quantity
        
        return total_volume
    except Exception as e:
        frappe.logger().warning(f"Error calculating per volume quantity: {e}")
        return 0.0


def _calculate_per_weight_quantity_for_job_contract(job) -> float:
    """Calculate weight quantity for job billing from contract."""
    try:
        total_weight = 0.0
        for item in getattr(job, 'items', []) or []:
            weight = flt(getattr(item, 'weight', 0))
            quantity = flt(getattr(item, 'quantity', 0))
            total_weight += weight * quantity
        
        return total_weight
    except Exception as e:
        frappe.logger().warning(f"Error calculating per weight quantity: {e}")
        return 0.0


def _calculate_per_piece_quantity_for_job_contract(job) -> float:
    """Calculate piece quantity for job billing from contract."""
    try:
        total_pieces = 0.0
        items = getattr(job, 'items', []) or []
        
        for item in items:
            quantity = flt(getattr(item, 'quantity', 0))
            item_code = getattr(item, 'item', 'Unknown')
            total_pieces += quantity
        return total_pieces
    except Exception as e:
        frappe.logger().warning(f"Error calculating per piece quantity: {e}")
        return 1.0


def _calculate_per_container_quantity_for_job_contract(job) -> float:
    """Calculate container quantity for job billing from contract."""
    try:
        containers = set()
        for item in getattr(job, 'items', []) or []:
            container = getattr(item, 'container', None)
            if container:
                containers.add(container)
        
        return float(len(containers)) if containers else float(len(getattr(job, 'items', [])))
    except Exception as e:
        frappe.logger().warning(f"Error calculating per container quantity: {e}")
        return 1.0


def _calculate_per_hour_quantity_for_job_contract(job, contract_item: dict) -> float:
    """Calculate hour quantity for job billing from contract."""
    try:
        # Get time billing settings from contract
        billing_unit = contract_item.get("billing_time_unit", "Hour")
        multiplier = flt(contract_item.get("billing_time_multiplier", 1))
        minimum_time = flt(contract_item.get("minimum_billing_time", 1))
        
        # Calculate actual time
        job_open_date = getattr(job, 'job_open_date', None)
        job_close_date = getattr(job, 'job_close_date', None)
        
        if job_open_date and job_close_date:
            start_time = frappe.utils.get_datetime(f"{job_open_date} {getattr(job, 'job_open_time', '00:00:00')}")
            end_time = frappe.utils.get_datetime(f"{job_close_date} {getattr(job, 'job_close_time', '23:59:59')}")
            hours = (end_time - start_time).total_seconds() / 3600
            actual_time = max(minimum_time, hours)
        else:
            # Estimate based on job type
            job_type = getattr(job, 'job_type', 'Generic')
            estimated_hours = {
                'Inbound': 2.0,
                'Outbound': 1.5,
                'Transfer': 1.0,
                'VAS': 3.0,
                'Stocktake': 4.0
            }.get(job_type, 2.0)
            actual_time = estimated_hours
        
        # Apply multiplier and minimum time
        calculated_time = max(minimum_time, actual_time * multiplier)
        
        return calculated_time
        
    except Exception as e:
        frappe.logger().warning(f"Error calculating per hour quantity: {e}")
        return 2.0


def _calculate_per_handling_unit_quantity_for_job_contract(job) -> float:
    """Calculate handling unit quantity for job billing from contract."""
    try:
        handling_units = set()
        job_type = getattr(job, 'type', 'Generic')
        
        if job_type == 'Stocktake':
            # For stocktake jobs, use counts table
            counts = getattr(job, 'counts', []) or []
            
            for count in counts:
                hu = getattr(count, 'handling_unit', None)
                if hu:
                    handling_units.add(hu)
        else:
            # For other job types, use items table
            items = getattr(job, 'items', []) or []
            
            for item in items:
                hu = getattr(item, 'handling_unit', None)
                if hu:
                    handling_units.add(hu)
        
        result = float(len(handling_units)) if handling_units else 1.0
        return result
    except Exception as e:
        frappe.logger().warning(f"Error calculating per handling unit quantity: {e}")
        return 1.0


def _calculate_high_water_mark_quantity_for_job_contract(job) -> float:
    """Calculate high water mark quantity for job billing from contract."""
    try:
        max_quantity = 0.0
        for item in getattr(job, 'items', []) or []:
            quantity = flt(getattr(item, 'quantity', 0))
            max_quantity = max(max_quantity, quantity)
        
        return max_quantity if max_quantity > 0 else 1.0
    except Exception as e:
        frappe.logger().warning(f"Error calculating high water mark quantity: {e}")
        return 1.0


def _generate_comprehensive_calculation_notes_for_contract_charge(job, contract_item: dict, billing_method: str, billing_qty: float) -> str:
    """Generate comprehensive calculation notes for contract-generated charges."""
    try:
        rate = flt(contract_item.get("rate", 0))
        total = billing_qty * rate
        uom = contract_item.get("uom", "N/A")
        currency = contract_item.get("currency", _get_default_currency(job.company))
        
        job_name = getattr(job, 'name', 'N/A')
        job_type = getattr(job, 'type', 'N/A')
        job_open_date = getattr(job, 'job_open_date', 'N/A')
        job_close_date = getattr(job, 'job_close_date', 'Ongoing')
        
        notes = f"""Warehouse Job Charge Calculation (Contract Generated):
  • Warehouse Job: {job_name}
  • Job Type: {job_type}
  • Period: {job_open_date} to {job_close_date}
  • Billing Method: {billing_method}
  • UOM: {uom}
  • Rate per {uom}: {rate}
  • Billing Quantity: {billing_qty}
  • Calculation: {billing_qty} × {rate} = {total}
  • Currency: {currency}"""
        
        # Add method-specific calculation details
        if billing_method == 'Per Day':
            notes += f"""
  • Per Day Calculation:
    - Job Open Date: {job_open_date}
    - Job Close Date: {job_close_date}
    - Days Calculated: {billing_qty}"""
        elif billing_method == 'Per Volume':
            total_volume = _calculate_per_volume_quantity_for_job_contract(job)
            notes += f"""
  • Per Volume Calculation:
    - Total Volume from Job Items: {total_volume}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Weight':
            total_weight = _calculate_per_weight_quantity_for_job_contract(job)
            notes += f"""
  • Per Weight Calculation:
    - Total Weight from Job Items: {total_weight}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Piece':
            total_pieces = _calculate_per_piece_quantity_for_job_contract(job)
            notes += f"""
  • Per Piece Calculation:
    - Total Pieces from Job Items: {total_pieces}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Container':
            container_count = _calculate_per_container_quantity_for_job_contract(job)
            notes += f"""
  • Per Container Calculation:
    - Container Count from Job Items: {container_count}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Hour':
            hours = _calculate_per_hour_quantity_for_job_contract(job, contract_item)
            notes += f"""
  • Per Hour Calculation:
    - Hours Calculated: {hours}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'Per Handling Unit':
            hu_count = _calculate_per_handling_unit_quantity_for_job_contract(job)
            notes += f"""
  • Per Handling Unit Calculation:
    - Handling Units Count: {hu_count}
    - Billing Quantity: {billing_qty}"""
        elif billing_method == 'High Water Mark':
            peak_qty = _calculate_high_water_mark_quantity_for_job_contract(job)
            notes += f"""
  • High Water Mark Calculation:
    - Peak Quantity: {peak_qty}
    - Billing Quantity: {billing_qty}"""
        
        # Add contract details
        notes += f"""
  • Contract Setup Applied:
    - Rate sourced from Warehouse Contract Item
    - Contract Unit Type: {contract_item.get('unit_type', 'N/A')}
    - Time billing settings: {contract_item.get('billing_time_unit', 'N/A')} unit, {contract_item.get('billing_time_multiplier', 1)} multiplier, {contract_item.get('minimum_billing_time', 1)} minimum
    - Contract UOM: {contract_item.get('uom', 'N/A')}
    - Contract Currency: {contract_item.get('currency', _get_default_currency(job.company))}
    - Contract Item: {contract_item.get('item_code', 'N/A')}"""
        
        return notes
        
    except Exception as e:
        frappe.logger().warning(f"Error generating contract charge calculation notes: {e}")
        return f"Calculation notes generation error: {str(e)}"


@frappe.whitelist()
def post_standard_costs(warehouse_job: str) -> dict:
    """
    Create Journal Entry for standard costs from warehouse job charges.
    
    Args:
        warehouse_job: Name of the warehouse job
        
    Returns:
        dict: Result with success status, message, journal_entry, and total_amount
    """
    try:
        # Get the warehouse job document
        job = frappe.get_doc("Warehouse Job", warehouse_job)
        
        if not job.charges:
            return {"ok": False, "message": "No charges found in warehouse job"}
        
        # Filter charges that have standard costs and are not already posted
        charges_with_standard_cost = []
        already_posted_charges = []
        
        for charge in job.charges:
            if charge.total_standard_cost and flt(charge.total_standard_cost) > 0:
                if getattr(charge, 'standard_cost_posted', False):
                    already_posted_charges.append(charge.item_code or charge.item or 'Unknown')
                else:
                    charges_with_standard_cost.append(charge)
        
        if not charges_with_standard_cost:
            if already_posted_charges:
                return {"ok": False, "message": f"All charges with standard costs have already been posted. Posted charges: {', '.join(already_posted_charges)}"}
            else:
                return {"ok": False, "message": "No charges with standard costs found"}
        
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = frappe.utils.today()
        je.company = job.company
        je.branch = job.branch
        je.cost_center = job.cost_center
        je.profit_center = job.profit_center
        je.job_costing_number = job.job_costing_number
        
        # Set reference to warehouse job
        je.user_remark = f"Standard Costs for Warehouse Job: {job.name}"
        
        total_amount = 0
        je_entries = []
        
        for charge in charges_with_standard_cost:
            if not charge.item_code:
                continue
                
            # Get item details to fetch standard cost accounts
            item_doc = frappe.get_doc("Item", charge.item_code)
            
            # Get standard cost accounts from item
            standard_cost_account = item_doc.get("custom_standard_cost_account")
            applied_standard_cost_account = item_doc.get("custom_applied_standard_cost_account")
            
            if not standard_cost_account or not applied_standard_cost_account:
                frappe.logger().warning(f"Standard cost accounts not configured for item: {charge.item_code}")
                continue
            
            amount = flt(charge.total_standard_cost)
            if amount <= 0:
                continue
                
            total_amount += amount
            
            # Debit: Standard Cost Account
            je_entries.append({
                "account": standard_cost_account,
                "debit_in_account_currency": amount,
                "credit_in_account_currency": 0,
                "cost_center": job.cost_center,
                "profit_center": job.profit_center,
                "job_costing_number": job.job_costing_number,
                "item": charge.item_code,
                "reference_type": "",
                "reference_name": "",
                "party_type": None,
                "party": None,
                "against_account": applied_standard_cost_account,
                "user_remark": f"Standard cost for {charge.item_code} - {charge.item_name or charge.item_code} (Warehouse Job: {job.name})"
            })
            
            # Credit: Applied Standard Cost Account
            je_entries.append({
                "account": applied_standard_cost_account,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": amount,
                "cost_center": job.cost_center,
                "profit_center": job.profit_center,
                "job_costing_number": job.job_costing_number,
                "item": charge.item_code,
                "reference_type": "",
                "reference_name": "",
                "party_type": None,
                "party": None,
                "against_account": standard_cost_account,
                "user_remark": f"Applied standard cost for {charge.item_code} - {charge.item_name or charge.item_code} (Warehouse Job: {job.name})"
            })
        
        if not je_entries:
            return {"ok": False, "message": "No valid journal entries could be created"}
        
        # Add entries to journal entry
        for entry in je_entries:
            je.append("accounts", entry)
        
        # Save and submit the journal entry
        je.insert(ignore_permissions=True)
        je.submit()
        
        # Update charges to mark them as posted
        for charge in charges_with_standard_cost:
            charge.standard_cost_posted = 1
            charge.standard_cost_posted_at = frappe.utils.now()
            charge.journal_entry_reference = je.name
        
        # Save the job with updated charge information
        job.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "ok": True,
            "message": f"Journal Entry {je.name} created successfully for standard costs",
            "journal_entry": je.name,
            "total_amount": total_amount,
            "charges_posted": len(charges_with_standard_cost)
        }
        
    except Exception as e:
        frappe.logger().error(f"Error posting standard costs for warehouse job {warehouse_job}: {str(e)}")
        return {
            "ok": False,
            "message": f"Error creating journal entry: {str(e)}"
        }


@frappe.whitelist()
def get_contract_charge_items(warehouse_contract: str, context: str = None) -> dict:
    """Get all allowed charge items from a warehouse contract for a specific context."""
    try:
        if not warehouse_contract:
            return {"ok": False, "message": "Warehouse contract is required"}
        
        # Build filters based on context
        filters = {
            "parent": warehouse_contract,
            "parenttype": "Warehouse Contract"
        }
        
        # Add context-specific filters
        if context:
            context = context.lower().strip()
            if context == "inbound":
                filters["inbound_charge"] = 1
            elif context == "outbound":
                filters["outbound_charge"] = 1
            elif context == "transfer":
                filters["transfer_charge"] = 1
            elif context == "vas":
                filters["vas_charge"] = 1
            elif context == "storage":
                filters["storage_charge"] = 1
            elif context == "stocktake":
                filters["stocktake_charge"] = 1
        
        # Get contract items
        contract_items = frappe.get_all(
            "Warehouse Contract Item",
            filters=filters,
            fields=[
                "item_charge",
                "item_name",
                "rate",
                "currency",
                "uom",
                "inbound_charge",
                "outbound_charge", 
                "transfer_charge",
                "vas_charge",
                "storage_charge",
                "stocktake_charge"
            ],
            order_by="item_charge"
        )
        
        return {
            "ok": True,
            "items": contract_items,
            "count": len(contract_items)
        }
        
    except Exception as e:
        frappe.logger().error(f"Error getting contract charge items: {str(e)}")
        return {
            "ok": False,
            "message": f"Error retrieving contract items: {str(e)}"
        }
