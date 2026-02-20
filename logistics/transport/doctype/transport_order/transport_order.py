    # apps/logistics/logistics/transport/doctype/transport_order/transport_order.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import time

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate
from pymysql.err import ProgrammingError

# keep these exactly as requested
ORDER_LEGS_FIELDNAME_FALLBACKS = ["legs"]
JOB_LEGS_FIELDNAME_FALLBACKS = ["legs"]

# Fields we want to copy over from Sales Quote Transport rows into Transport Order Charges
SALES_QUOTE_CHARGE_FIELDS = [
    "item_code",
    "item_name",
    "calculation_method",
    "quantity",
    "uom",
    "currency",
    "unit_rate",
    "unit_type",
    "minimum_quantity",
    "minimum_charge",
    "maximum_charge",
    "base_amount",
    "estimated_revenue",
    "use_tariff_in_revenue",
    "use_tariff_in_cost",
    "tariff",
    "cost_calculation_method",
    "cost_quantity",
    "cost_uom",
    "cost_currency",
    "unit_cost",
    "cost_unit_type",
    "cost_minimum_quantity",
    "cost_minimum_charge",
    "cost_maximum_charge",
    "cost_base_amount",
    "estimated_cost",
    "revenue_calc_notes",
    "cost_calc_notes",
]


def _sync_quote_and_sales_quote(doc):
    """Sync quote_type/quote with sales_quote for backward compatibility."""
    if getattr(doc, "quote_type", None) == "Sales Quote" and getattr(doc, "quote", None):
        doc.sales_quote = doc.quote
    elif getattr(doc, "quote_type", None) == "One-Off Quote":
        doc.sales_quote = None
    elif not getattr(doc, "quote_type", None) and getattr(doc, "sales_quote", None):
        doc.quote_type = "Sales Quote"
        doc.quote = doc.sales_quote


class TransportOrder(Document):
    def validate(self):
        # Preserve quote field value before syncing (to prevent it from being cleared)
        # Get original values from database if document exists
        original_quote = None
        original_quote_type = None
        original_sales_quote = None
        
        if not self.is_new():
            try:
                original_quote = frappe.db.get_value(self.doctype, self.name, 'quote')
                original_quote_type = frappe.db.get_value(self.doctype, self.name, 'quote_type')
                original_sales_quote = frappe.db.get_value(self.doctype, self.name, 'sales_quote')
            except Exception:
                pass
        
        # Use current values if not in database yet
        if not original_quote:
            original_quote = getattr(self, 'quote', None)
        if not original_quote_type:
            original_quote_type = getattr(self, 'quote_type', None)
        if not original_sales_quote:
            original_sales_quote = getattr(self, 'sales_quote', None)
        
        _sync_quote_and_sales_quote(self)
        
        # Ensure quote field is preserved - restore original values if they were cleared
        # This ensures the quote field remains after submission
        if original_quote and not getattr(self, 'quote', None):
            self.quote = original_quote
        if original_quote_type and not getattr(self, 'quote_type', None):
            self.quote_type = original_quote_type
        # Only preserve sales_quote if quote_type is Sales Quote (One-Off Quote clears sales_quote)
        if original_sales_quote and getattr(self, 'quote_type', None) == 'Sales Quote' and not getattr(self, 'sales_quote', None):
            self.sales_quote = original_sales_quote
        # If the Transport Template changes, clear the Leg Plan table.
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
        
        # Validate sales_quote duplication rules for one-off quotes
        self._validate_sales_quote_duplication()
        
        # Validate that pick and drop facilities are different in each leg
        self._validate_leg_facilities()
        
        # Validate transport job type specific rules
        self._validate_transport_job_type()
        
        # Note: vehicle_type validation moved to before_submit() to allow save without vehicle_type
        # Users can save draft documents and fill vehicle_type later before submitting
        
        # Validate load type is allowed for job type
        self.validate_load_type_allowed_for_job()
        
        # Validate consolidation eligibility
        self.validate_consolidation_eligibility()
        
        # Validate vehicle type compatibility with load type
        self.validate_vehicle_type_load_type_compatibility()
        
        # Capacity validation
        self.validate_vehicle_type_capacity()

        # Convert package measurements when UOM was changed (e.g. after import)
        try:
            from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
            apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
        except Exception:
            pass
        
        # Aggregate package volumes and weights (with UOM conversion)
        self.aggregate_volume_from_packages()
        self.aggregate_weight_from_packages()
        self._update_packing_summary()

    def before_save(self):
        from logistics.utils.module_integration import run_propagate_on_link
        run_propagate_on_link(self)

    def aggregate_volume_from_packages(self):
        """Set header volume from sum of package volumes, converted to base/default volume UOM."""
        packages = getattr(self, "packages", []) or []
        if not packages:
            return
        try:
            from logistics.utils.measurements import convert_volume, get_aggregation_volume_uom, get_default_uoms
            target_volume_uom = get_aggregation_volume_uom(company=getattr(self, "company", None))
            if not target_volume_uom:
                return
            defaults = get_default_uoms(company=getattr(self, "company", None))
            target_normalized = str(target_volume_uom).strip().upper()
            total = 0
            for pkg in packages:
                pkg_vol = flt(getattr(pkg, "volume", 0) or 0)
                if pkg_vol <= 0:
                    continue
                pkg_volume_uom = getattr(pkg, "volume_uom", None) or defaults.get("volume")
                if not pkg_volume_uom:
                    continue
                if str(pkg_volume_uom).strip().upper() == target_normalized:
                    total += pkg_vol
                else:
                    total += convert_volume(
                        pkg_vol,
                        from_uom=pkg_volume_uom,
                        to_uom=target_volume_uom,
                        company=getattr(self, "company", None),
                    )
            # Note: Transport Order doesn't have header volume field, but method is available for future use
            # or for API calls
        except Exception:
            pass
    
    def aggregate_weight_from_packages(self):
        """Set header weight from sum of package weights, converted to base/default weight UOM."""
        packages = getattr(self, "packages", []) or []
        if not packages:
            return
        try:
            from logistics.utils.measurements import convert_weight, get_default_uoms
            defaults = get_default_uoms(company=getattr(self, "company", None))
            target_weight_uom = defaults.get("weight")  # Typically "Kg"
            if not target_weight_uom:
                return
            target_normalized = str(target_weight_uom).strip().upper()
            total = 0
            for pkg in packages:
                pkg_weight = flt(getattr(pkg, "weight", 0) or 0)
                if pkg_weight <= 0:
                    continue
                pkg_weight_uom = getattr(pkg, "weight_uom", None) or defaults.get("weight")
                if not pkg_weight_uom:
                    continue
                if str(pkg_weight_uom).strip().upper() == target_normalized:
                    total += pkg_weight
                else:
                    total += convert_weight(
                        pkg_weight,
                        from_uom=pkg_weight_uom,
                        to_uom=target_weight_uom,
                        company=getattr(self, "company", None),
                    )
            # Note: Transport Order doesn't have header weight field, but method is available for future use
            # or for API calls
        except Exception:
            pass

    def _update_packing_summary(self):
        """Update total_packages, total_volume, total_weight from packages."""
        packages = getattr(self, "packages", []) or []
        self.total_packages = sum(flt(getattr(p, "no_of_packs", 0) or getattr(p, "quantity", 0) or 1) for p in packages)
        self.total_volume = self.get_total_volume()
        self.total_weight = self.get_total_weight()

    @frappe.whitelist()
    def aggregate_volume_from_packages_api(self):
        """Whitelisted API method to aggregate volume and weight from packages for client-side calls."""
        self.aggregate_volume_from_packages()
        self.aggregate_weight_from_packages()
        return {
            "volume": getattr(self, "volume", 0),
            "weight": getattr(self, "weight", 0)
        }

    def before_submit(self):
        """Validate transport legs before submitting the Transport Order."""
        # Ensure quote field values are preserved - sync quote and sales_quote before submission
        _sync_quote_and_sales_quote(self)
        
        # Validate quote reference: either sales_quote (for Sales Quote) or quote (for One-Off Quote) must be set
        quote_type = getattr(self, "quote_type", None)
        if quote_type == "Sales Quote":
            if not self.sales_quote:
                frappe.throw(_("Sales Quote is required. Please select a Sales Quote before submitting the Transport Order."))
        elif quote_type == "One-Off Quote":
            if not getattr(self, "quote", None):
                frappe.throw(_("One-Off Quote is required. Please select a One-Off Quote before submitting the Transport Order."))
        else:
            # If quote_type is not set, check if sales_quote is set (backward compatibility)
            if not self.sales_quote:
                frappe.throw(_("Sales Quote is required. Please select a Sales Quote before submitting the Transport Order."))
        
        # Validate packages is not empty
        packages = getattr(self, 'packages', []) or []
        if not packages:
            frappe.throw(_("Packages are required. Please add at least one package before submitting the Transport Order."))
        
        # Validate vehicle_type is required only if consolidate is not checked
        # This validation is in before_submit (not validate) to allow saving drafts without vehicle_type
        self._validate_vehicle_type_required()
        
        self._validate_transport_legs()
    
    def after_submit(self):
        """Ensure quote field values remain after submission."""
        # Preserve quote field value after submission - ensure it's not cleared
        # Get the quote value from the database to ensure it's preserved
        current_quote = frappe.db.get_value(self.doctype, self.name, 'quote')
        current_quote_type = frappe.db.get_value(self.doctype, self.name, 'quote_type')
        current_sales_quote = frappe.db.get_value(self.doctype, self.name, 'sales_quote')
        
        # If quote was set before submission, ensure it remains set
        # This prevents any code from clearing the quote field after submission
        if current_quote and not getattr(self, 'quote', None):
            self.db_set('quote', current_quote, update_modified=False)
        if current_quote_type and not getattr(self, 'quote_type', None):
            self.db_set('quote_type', current_quote_type, update_modified=False)
        if current_sales_quote and not getattr(self, 'sales_quote', None):
            self.db_set('sales_quote', current_sales_quote, update_modified=False)

    def _validate_transport_legs(self):
        """Validate that transport legs have complete details and scheduled_date if filled."""
        legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        legs = self.get(legs_field) or []
        
        if not legs:
            frappe.throw(_("Transport Order must have at least one leg. Please add transport legs before submitting."))
        
        for i, leg in enumerate(legs, 1):
            # Check for required fields
            missing_fields = []
            
            # Check facility details
            if not leg.get("facility_type_from"):
                missing_fields.append("Facility Type From")
            if not leg.get("facility_from"):
                missing_fields.append("Facility From")
            if not leg.get("facility_type_to"):
                missing_fields.append("Facility Type To")
            if not leg.get("facility_to"):
                missing_fields.append("Facility To")
            
            # Check transport details
            if not leg.get("vehicle_type"):
                missing_fields.append("Vehicle Type")
            if not leg.get("transport_job_type"):
                missing_fields.append("Transport Job Type")
            
            # Check pick and drop modes
            if not leg.get("pick_mode"):
                missing_fields.append("Pick Mode")
            if not leg.get("drop_mode"):
                missing_fields.append("Drop Mode")
            
            # Check scheduled_date if it's filled
            if leg.get("scheduled_date"):
                try:
                    from frappe.utils import getdate
                    getdate(leg.scheduled_date)  # Validate date format
                except Exception:
                    frappe.throw(_("Row {0}: Invalid scheduled date format. Please use a valid date format.").format(i))
            
            # Note: day_offset is not a field in Transport Order Legs table
            # It's only used during template mapping
            
            # Report missing fields
            if missing_fields:
                frappe.throw(_("Row {0}: Missing required fields: {1}").format(i, ", ".join(missing_fields)))
            
            # Validate address details if addresses are set (they should be valid Address links)
            # Note: pick_mode and drop_mode are Link fields to Pick and Drop Mode records, not literal strings
            if leg.get("pick_address") and not frappe.db.exists("Address", leg.get("pick_address")):
                frappe.throw(_("Row {0}: Pick address '{1}' does not exist.").format(i, leg.get("pick_address")))
            
            if leg.get("drop_address") and not frappe.db.exists("Address", leg.get("drop_address")):
                frappe.throw(_("Row {0}: Drop address '{1}' does not exist.").format(i, leg.get("drop_address")))
            
            # Validate PEZA/non-PEZA address classification
            self._validate_peza_addresses(leg, i)
            
            # Auto-fill addresses from facilities if not set
            self._auto_fill_leg_addresses(leg, i)

    def _validate_peza_addresses(self, leg, leg_index):
        """Validate that addresses have PEZA/non-PEZA classification set."""
        pick_address = leg.get("pick_address")
        drop_address = leg.get("drop_address")
        
        if pick_address:
            try:
                address_doc = frappe.get_doc("Address", pick_address)
                # Check if custom_peza_classification field exists and is set
                if address_doc.meta.has_field("custom_peza_classification"):
                    peza_classification = getattr(address_doc, "custom_peza_classification", None)
                    if not peza_classification:
                        frappe.throw(_("Row {0}: Pick address '{1}' must have PEZA classification set (PEZA or Non-PEZA).").format(leg_index, pick_address))
            except Exception as e:
                frappe.log_error(f"Error validating PEZA classification for pick address {pick_address}: {str(e)}", "PEZA Validation Error")
        
        if drop_address:
            try:
                address_doc = frappe.get_doc("Address", drop_address)
                # Check if custom_peza_classification field exists and is set
                if address_doc.meta.has_field("custom_peza_classification"):
                    peza_classification = getattr(address_doc, "custom_peza_classification", None)
                    if not peza_classification:
                        frappe.throw(_("Row {0}: Drop address '{1}' must have PEZA classification set (PEZA or Non-PEZA).").format(leg_index, drop_address))
            except Exception as e:
                frappe.log_error(f"Error validating PEZA classification for drop address {drop_address}: {str(e)}", "PEZA Validation Error")

    def _auto_fill_leg_addresses(self, leg, leg_index):
        """Auto-fill addresses from facilities if not already set.
        
        Preserves existing pick_mode and drop_mode values - only sets pick_address and drop_address.
        pick_mode and drop_mode are Link fields to Pick and Drop Mode records and should not be
        set to literal strings like "Address".
        """
        try:
            # Auto-fill pick address from facility
            # Only set address if not already set, and preserve existing pick_mode value
            if not leg.get("pick_address") and leg.get("facility_type_from") and leg.get("facility_from"):
                facility_doc = frappe.get_doc(leg.facility_type_from, leg.facility_from)
                if hasattr(facility_doc, 'address') and facility_doc.address:
                    leg.pick_address = facility_doc.address
                    # Update the leg in the document - only set pick_address, preserve pick_mode
                    legs_field = _find_child_table_fieldname(
                        "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                    )
                    self.set_value(legs_field, leg_index - 1, "pick_address", facility_doc.address)
                    # Do not modify pick_mode - preserve existing value or leave it unset
            
            # Auto-fill drop address from facility
            # Only set address if not already set, and preserve existing drop_mode value
            if not leg.get("drop_address") and leg.get("facility_type_to") and leg.get("facility_to"):
                facility_doc = frappe.get_doc(leg.facility_type_to, leg.facility_to)
                if hasattr(facility_doc, 'address') and facility_doc.address:
                    leg.drop_address = facility_doc.address
                    # Update the leg in the document - only set drop_address, preserve drop_mode
                    legs_field = _find_child_table_fieldname(
                        "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                    )
                    self.set_value(legs_field, leg_index - 1, "drop_address", facility_doc.address)
                    # Do not modify drop_mode - preserve existing value or leave it unset
                    
        except Exception as e:
            # Log error but don't fail validation
            frappe.log_error(f"Error auto-filling addresses for leg {leg_index}: {str(e)}", "Transport Order Address Auto-fill")

    def _validate_sales_quote_duplication(self):
        """When quote is One-Off Quote, at most one Transport Order per One-Off Quote.
        On duplicate (new doc with same One-Off Quote), clear quote reference.
        """
        if not self.is_new() or getattr(self, "quote_type", None) != "One-Off Quote" or not getattr(self, "quote", None):
            return
        try:
            existing = frappe.db.exists(
                "Transport Order",
                {"quote_type": "One-Off Quote", "quote": self.quote, "name": ["!=", self.name or ""]}
            )
            if existing:
                original_quote = self.quote
                self.quote_type = None
                self.quote = None
                self.sales_quote = None
                if hasattr(self, "charges") and self.charges:
                    self.set("charges", [])
                frappe.msgprint(
                    _("One-Off Quote '{0}' is already linked to another Transport Order. Quote reference cleared.").format(original_quote),
                    title=_("Quote Cleared"),
                    indicator="orange"
                )
        except Exception as e:
            frappe.log_error(
                f"Error validating quote duplication for Transport Order: {str(e)}",
                "Transport Order Quote Validation Error"
            )

    def _validate_leg_facilities(self):
        """Validate that pick and drop facilities are different in each leg, or if same facility, addresses must be different."""
        legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        legs = self.get(legs_field) or []
        
        for i, leg in enumerate(legs, 1):
            facility_from = leg.get("facility_from")
            facility_to = leg.get("facility_to")
            pick_address = leg.get("pick_address")
            drop_address = leg.get("drop_address")
            
            # If facilities are the same, check that addresses are different
            if facility_from and facility_to and facility_from == facility_to:
                # If addresses are the same (or both missing), throw error
                if pick_address == drop_address:
                    frappe.throw(_("Row {0}: Pick facility and drop facility cannot be the same.").format(i))
                # If addresses are different, allow it (no error)

    def _validate_transport_job_type(self):
        """Validate transport job type specific business rules."""
        if not self.transport_job_type:
            return
        
        # Container type validations
        if self.transport_job_type == "Container":
            self._validate_container_requirements()
        elif self.transport_job_type == "Heavy Haul":
            self._validate_heavy_haul_requirements()
        elif self.transport_job_type == "Oversized":
            self._validate_oversized_requirements()
        elif self.transport_job_type == "Special":
            self._validate_special_requirements()
        elif self.transport_job_type == "Multimodal":
            self._validate_multimodal_requirements()
        
        # Vehicle type compatibility validation
        self._validate_vehicle_type_compatibility()
        
        # Load type compatibility validation
        self.validate_load_type_allowed_for_job()

    def _validate_container_requirements(self):
        """Validate container-specific requirements."""
        # Skip container_type validation when creating from One-Off Quote
        if not getattr(self.flags, 'skip_container_type_validation', False):
            if not self.container_type:
                frappe.throw(_("Container Type is required for Container transport jobs."))
        
        # Skip container_no validation when creating from Sales Quote
        if not getattr(self.flags, 'skip_container_no_validation', False):
            if not self.container_no:
                frappe.throw(_("Container Number is required for Container transport jobs."))
        
        # Validate container number format if needed
        if self.container_no and len(self.container_no) < 4:
            frappe.throw(_("Container Number must be at least 4 characters long."))

    def _validate_heavy_haul_requirements(self):
        """Validate heavy haul specific requirements."""
        # Check if vehicle type is suitable for heavy haul
        if self.vehicle_type:
            vehicle_type_doc = frappe.get_doc("Vehicle Type", self.vehicle_type)
            if hasattr(vehicle_type_doc, 'max_weight') and vehicle_type_doc.max_weight:
                if self.get_total_weight() > vehicle_type_doc.max_weight:
                    frappe.throw(_("Total weight exceeds maximum capacity for selected vehicle type."))
        
        # Check for special permits or documentation
        if not self.internal_notes:
            frappe.msgprint(_("Heavy Haul transport may require special permits. Please add relevant information in Internal Notes."))

    def _validate_oversized_requirements(self):
        """Validate oversized cargo requirements."""
        # Check dimensions if available
        if hasattr(self, 'packages') and self.packages:
            for package in self.packages:
                if hasattr(package, 'length') and hasattr(package, 'width') and hasattr(package, 'height'):
                    if (package.length > 12 or package.width > 2.5 or package.height > 4):
                        frappe.msgprint(_("Oversized cargo detected. Special routing and permits may be required."))
                        break
        
        # Check for special handling notes
        if not self.internal_notes:
            frappe.msgprint(_("Oversized transport may require special handling. Please add relevant information in Internal Notes."))

    def _validate_special_requirements(self):
        """Validate special transport requirements."""
        # Skip validation when creating from Sales Quote
        if getattr(self.flags, 'skip_special_requirements_validation', False):
            return
        
        # Check for hazardous materials
        if self.hazardous:
            frappe.msgprint(_("Hazardous materials require special handling and documentation."))

    def _validate_multimodal_requirements(self):
        """Validate multimodal transport requirements."""
        # Check if multiple transport modes are specified
        if not self.internal_notes:
            frappe.msgprint(_("Multimodal transport requires coordination details in Internal Notes."))
        
        # Validate that legs have different transport modes if applicable
        legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        legs = self.get(legs_field) or []
        if len(legs) < 2:
            frappe.msgprint(_("Multimodal transport typically requires multiple legs."))

    def _validate_vehicle_type_compatibility(self):
        """Validate vehicle type compatibility with transport job type."""
        if not self.vehicle_type or not self.transport_job_type:
            return
        
        # Get vehicle type restrictions
        vehicle_type_doc = frappe.get_doc("Vehicle Type", self.vehicle_type)
        
        # Check if vehicle type is suitable for the job type
        if hasattr(vehicle_type_doc, 'suitable_for'):
            suitable_for = vehicle_type_doc.suitable_for or []
            if self.transport_job_type not in suitable_for:
                frappe.msgprint(_("Selected vehicle type may not be suitable for {0} transport.").format(self.transport_job_type))

    def validate_load_type_allowed_for_job(self):
        """Validate that the selected Load Type is allowed for the chosen Transport Job Type."""
        if not self.load_type or not self.transport_job_type:
            return

        field_map = {
            "Container": "container",
            "Non-Container": "non_container",
            "Special": "special",
            "Oversized": "oversized",
            "Multimodal": "multimodal",
            "Heavy Haul": "heavy_haul"
        }

        allowed_field = field_map.get(self.transport_job_type)
        if not allowed_field:
            return

        allowed = frappe.db.get_value(
            "Load Type",
            self.load_type,
            allowed_field
        )

        if not allowed:
            frappe.throw(
                _(f"Load Type {self.load_type} is not allowed for {self.transport_job_type} jobs.")
            )

    def validate_vehicle_type_capacity(self):
        """Validate vehicle type capacity when vehicle_type is assigned"""
        if not getattr(self, 'vehicle_type', None):
            return
        
        try:
            from logistics.transport.capacity.vehicle_type_capacity import get_vehicle_type_capacity_info

            # Calculate capacity requirements from packages (uses Logistics Settings UOMs)
            requirements = self.calculate_capacity_requirements()
            
            if requirements['weight'] == 0 and requirements['volume'] == 0 and requirements['pallets'] == 0:
                return  # No requirements to validate
            
            # Get vehicle type capacity information
            capacity_info = get_vehicle_type_capacity_info(self.vehicle_type, self.company)
            
            # Validate capacity
            if requirements['weight'] > 0 and capacity_info.get('max_weight', 0) < requirements['weight']:
                frappe.throw(_("Total weight ({0} {1}) exceeds typical capacity for vehicle type {2}").format(
                    requirements['weight'], requirements['weight_uom'], self.vehicle_type
                ))
            
            if requirements['volume'] > 0 and capacity_info.get('max_volume', 0) < requirements['volume']:
                frappe.throw(_("Total volume ({0} {1}) exceeds typical capacity for vehicle type {2}").format(
                    requirements['volume'], requirements['volume_uom'], self.vehicle_type
                ))
            
            if requirements['pallets'] > 0 and capacity_info.get('max_pallets', 0) < requirements['pallets']:
                frappe.throw(_("Total pallets ({0}) exceeds typical capacity for vehicle type {1}").format(
                    requirements['pallets'], self.vehicle_type
                ))
        except ImportError:
            # Capacity management not fully implemented yet
            pass
        except Exception as e:
            frappe.log_error(f"Error validating vehicle type capacity in Transport Order: {str(e)}", "Capacity Validation Error")
    
    def calculate_capacity_requirements(self):
        """Calculate total capacity requirements from packages using Logistics Settings UOMs."""
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
    
    def _validate_vehicle_type_required(self):
        """Validate that vehicle_type is required only if consolidate is not checked."""
        # Skip vehicle_type validation when creating from Sales Quote
        if getattr(self.flags, 'skip_vehicle_type_validation', False):
            return
        
        # Vehicle Type is mandatory only if Consolidate checkbox is not checked
        if not self.vehicle_type and not self.consolidate:
            frappe.throw(_("Vehicle Type is required when Consolidate is not checked"))

    def get_total_weight(self):
        """Calculate total weight from packages."""
        total_weight = 0
        if hasattr(self, 'packages') and self.packages:
            for package in self.packages:
                if hasattr(package, 'weight') and package.weight:
                    total_weight += float(package.weight or 0)
        return total_weight

    def get_total_volume(self):
        """Calculate total volume from packages."""
        total_volume = 0
        if hasattr(self, 'packages') and self.packages:
            for package in self.packages:
                if hasattr(package, 'volume') and package.volume:
                    total_volume += float(package.volume or 0)
        return total_volume

    def get_required_permits(self):
        """Get list of required permits based on transport job type."""
        permits = []
        
        if self.transport_job_type == "Heavy Haul":
            permits.extend(["Heavy Vehicle Permit", "Oversize Load Permit"])
        elif self.transport_job_type == "Oversized":
            permits.extend(["Oversize Load Permit", "Route Clearance"])
        elif self.transport_job_type == "Special":
            permits.extend(["Special Transport Permit"])
        elif self.transport_job_type == "Hazardous":
            permits.extend(["Hazardous Materials Permit", "Environmental Clearance"])
        
        if self.hazardous:
            permits.extend(["Hazardous Materials Permit", "Environmental Clearance"])
        
        return list(set(permits))  # Remove duplicates

    def get_estimated_cost_factors(self):
        """Get cost factors based on transport job type."""
        factors = {
            "base_rate": 1.0,
            "surcharge": 0.0,
            "special_handling": False
        }
        
        if self.transport_job_type == "Heavy Haul":
            factors["surcharge"] = 0.5  # 50% surcharge
            factors["special_handling"] = True
        elif self.transport_job_type == "Oversized":
            factors["surcharge"] = 0.3  # 30% surcharge
            factors["special_handling"] = True
        elif self.transport_job_type == "Special":
            factors["surcharge"] = 0.4  # 40% surcharge
            factors["special_handling"] = True
        elif self.transport_job_type == "Multimodal":
            factors["surcharge"] = 0.2  # 20% surcharge
        
        if self.hazardous:
            factors["surcharge"] += 0.3  # Additional 30% for hazardous
            factors["special_handling"] = True
        
        if self.reefer:
            factors["surcharge"] += 0.2  # Additional 20% for reefer
        
        return factors

    def get_vehicle_requirements(self):
        """Get vehicle requirements based on transport job type."""
        requirements = {
            "min_capacity_weight": 0,
            "min_capacity_volume": 0,
            "special_equipment": [],
            "driver_qualifications": []
        }
        
        if self.transport_job_type == "Heavy Haul":
            requirements["min_capacity_weight"] = 50000  # 50 tons
            requirements["special_equipment"].extend(["Heavy Duty Trailer", "Crane"])
            requirements["driver_qualifications"].extend(["Heavy Vehicle License", "Crane Operator License"])
        elif self.transport_job_type == "Oversized":
            requirements["min_capacity_volume"] = 100  # 100 m³
            requirements["special_equipment"].extend(["Oversize Trailer", "Escort Vehicle"])
            requirements["driver_qualifications"].extend(["Oversize Load License"])
        elif self.transport_job_type == "Special":
            requirements["special_equipment"].extend(["Specialized Equipment"])
            requirements["driver_qualifications"].extend(["Special Transport License"])
        
        if self.hazardous:
            requirements["special_equipment"].extend(["Hazmat Equipment"])
            requirements["driver_qualifications"].extend(["Hazmat License"])
        
        if self.reefer:
            requirements["special_equipment"].extend(["Refrigerated Unit"])
            requirements["driver_qualifications"].extend(["Temperature Control Training"])
        
        return requirements

    def get_consolidation_eligibility(self):
        """Check if this transport order can be consolidated with others."""
        if not self.transport_job_type or not self.load_type:
            return False
        
        # Get load type document
        try:
            load_type_doc = frappe.get_doc("Load Type", self.load_type)
            if not getattr(load_type_doc, 'can_be_consolidated', False):
                return False
            
            # Check if job type is suitable for consolidation
            if self.transport_job_type in ["Heavy Haul", "Oversized", "Special"]:
                return False  # These typically cannot be consolidated
            
            return True
        except Exception:
            return False
    
    def validate_consolidation_eligibility(self):
        """Validate consolidation eligibility and provide user feedback."""
        if not self.load_type:
            return
        
        try:
            load_type_doc = frappe.get_doc("Load Type", self.load_type)
            # Check if load type allows consolidation (use can_handle_consolidation field)
            can_handle_consolidation = getattr(load_type_doc, "can_handle_consolidation", 0)
            if not (can_handle_consolidation == 1 or can_handle_consolidation == True):
                if self.consolidate:
                    frappe.msgprint(
                        _("Load Type {0} does not allow consolidation. The Consolidate checkbox may not be effective.").format(
                            self.load_type
                        ),
                        indicator="orange"
                    )
        except Exception:
            pass  # Load type validation already handled elsewhere
    
    def validate_vehicle_type_load_type_compatibility(self):
        """Ensure selected Vehicle Type is compatible with Load Type."""
        if not self.vehicle_type or not self.load_type:
            return
        
        try:
            # Check if Vehicle Type has load_type restrictions
            vehicle_type_doc = frappe.get_doc("Vehicle Type", self.vehicle_type)
            
            # If Vehicle Type has a load_type field, validate it matches
            if hasattr(vehicle_type_doc, 'load_type') and vehicle_type_doc.load_type:
                if vehicle_type_doc.load_type != self.load_type:
                    frappe.msgprint(
                        _("Warning: Vehicle Type {0} has Load Type {1} which differs from selected Load Type {2}").format(
                            self.vehicle_type, vehicle_type_doc.load_type, self.load_type
                        ),
                        indicator="orange"
                    )
            
            # Check Vehicle Type Load Types child table if it exists
            if hasattr(vehicle_type_doc, 'allowed_load_types') and vehicle_type_doc.allowed_load_types:
                allowed_load_types = [lt.load_type for lt in vehicle_type_doc.allowed_load_types if lt.load_type]
                if allowed_load_types and self.load_type not in allowed_load_types:
                    frappe.msgprint(
                        _("Warning: Vehicle Type {0} may not be compatible with Load Type {1}").format(
                            self.vehicle_type, self.load_type
                        ),
                        indicator="orange"
                    )
        except Exception:
            pass  # Vehicle type validation already handled elsewhere

    def get_estimated_duration(self):
        """Get estimated duration based on transport job type."""
        base_duration = 2  # hours
        
        if self.transport_job_type == "Heavy Haul":
            return base_duration * 3  # 6 hours
        elif self.transport_job_type == "Oversized":
            return base_duration * 2.5  # 5 hours
        elif self.transport_job_type == "Special":
            return base_duration * 2  # 4 hours
        elif self.transport_job_type == "Multimodal":
            return base_duration * 4  # 8 hours
        else:
            return base_duration  # 2 hours

    def get_priority_score(self):
        """Calculate priority score based on transport job type and other factors."""
        score = 0
        
        # Base score by job type
        if self.transport_job_type == "Heavy Haul":
            score += 10
        elif self.transport_job_type == "Oversized":
            score += 8
        elif self.transport_job_type == "Special":
            score += 6
        elif self.transport_job_type == "Multimodal":
            score += 4
        else:
            score += 2
        
        # Additional factors
        if self.hazardous:
            score += 5
        if self.reefer:
            score += 3
        
        return score

    def get_route_restrictions(self):
        """Get route restrictions based on transport job type."""
        restrictions = []
        
        if self.transport_job_type == "Heavy Haul":
            restrictions.extend(["No Low Bridges", "Heavy Vehicle Routes Only"])
        elif self.transport_job_type == "Oversized":
            restrictions.extend(["Oversize Load Routes", "Escort Required"])
        elif self.transport_job_type == "Hazardous":
            restrictions.extend(["Hazmat Routes", "No Residential Areas"])
        
        return restrictions

    def on_change(self):
        """Handle changes to the document."""
        # Skip if flag is set (e.g., when creating from Sales Quote)
        if getattr(self.flags, 'skip_sales_quote_on_change', False):
            return
        
        # Skip if document name is still temporary (starts with "new-")
        # This prevents errors when the document is being saved for the first time
        if self.name and self.name.startswith("new-"):
            return
            
        if self.has_value_changed("sales_quote"):
            if self.sales_quote:
                self._populate_charges_from_sales_quote()
            else:
                # Clear charges if sales_quote is removed
                self.set("charges", [])
                frappe.msgprint(
                    "Charges cleared as Sales Quote was removed",
                    title="Charges Updated",
                    indicator="blue"
                )
        
        # Handle One-Off Quote changes
        if self.has_value_changed("quote") or self.has_value_changed("quote_type"):
            if getattr(self, "quote_type", None) == "One-Off Quote" and self.quote:
                self._populate_charges_from_one_off_quote()
            elif getattr(self, "quote_type", None) == "One-Off Quote" and not self.quote:
                # Clear charges if One-Off Quote is removed
                self.set("charges", [])
                frappe.msgprint(
                    "Charges cleared as One-Off Quote was removed",
                    title="Charges Updated",
                    indicator="blue"
                )

    def _populate_charges_from_sales_quote(self):
        """Populate charges based on sales_quote_transport of the filled sales_quote."""
        if not self.sales_quote:
            return

        try:
            # Verify that the sales_quote exists
            if not frappe.db.exists("Sales Quote", self.sales_quote):
                frappe.msgprint(
                    f"Sales Quote {self.sales_quote} does not exist",
                    title="Error",
                    indicator="red"
                )
                return

            # Clear existing charges
            self.set("charges", [])

            # Fetch sales_quote_transport records from the selected sales_quote
            fields_to_fetch = ["name"] + SALES_QUOTE_CHARGE_FIELDS
            sales_quote_transport_records = frappe.get_all(
                "Sales Quote Transport",
                filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
                fields=fields_to_fetch,
                order_by="idx"
            )

            if not sales_quote_transport_records:
                frappe.msgprint(
                    f"No transport charges found in Sales Quote: {self.sales_quote}",
                    title="No Charges Found",
                    indicator="orange"
                )
                return

            # Map and populate charges
            charges_added = 0
            for sqt_record in sales_quote_transport_records:
                charge_row = self._map_sales_quote_transport_to_charge(sqt_record)
                if charge_row:
                    self.append("charges", charge_row)
                    charges_added += 1

            if charges_added > 0:
                frappe.msgprint(
                    f"Successfully populated {charges_added} charges from Sales Quote: {self.sales_quote}",
                    title="Charges Updated",
                    indicator="green"
                )
            else:
                frappe.msgprint(
                    f"No valid charges could be mapped from Sales Quote: {self.sales_quote}",
                    title="No Valid Charges",
                    indicator="orange"
                )

        except Exception as e:
            frappe.log_error(
                f"Error populating charges from sales quote {self.sales_quote}: {str(e)}",
                "Transport Order Charges Population Error"
            )
            frappe.msgprint(
                f"Error populating charges: {str(e)}",
                title="Error",
                indicator="red"
            )

    def _populate_charges_from_one_off_quote(self):
        """Populate charges based on one_off_quote_transport of the filled one_off_quote."""
        if not self.quote or getattr(self, "quote_type", None) != "One-Off Quote":
            return

        try:
            # Verify that the one_off_quote exists
            if not frappe.db.exists("One-Off Quote", self.quote):
                frappe.msgprint(
                    f"One-Off Quote {self.quote} does not exist",
                    title="Error",
                    indicator="red"
                )
                return

            # Clear existing charges
            self.set("charges", [])

            # Fetch one_off_quote_transport records from the selected one_off_quote
            fields_to_fetch = ["name"] + SALES_QUOTE_CHARGE_FIELDS
            one_off_quote_transport_records = frappe.get_all(
                "One-Off Quote Transport",
                filters={"parent": self.quote, "parenttype": "One-Off Quote"},
                fields=fields_to_fetch,
                order_by="idx"
            )

            if not one_off_quote_transport_records:
                frappe.msgprint(
                    f"No transport charges found in One-Off Quote: {self.quote}",
                    title="No Charges Found",
                    indicator="orange"
                )
                return

            # Map and populate charges (One-Off Quote Transport has same structure as Sales Quote Transport)
            charges_added = 0
            for oqt_record in one_off_quote_transport_records:
                charge_row = self._map_sales_quote_transport_to_charge(oqt_record)
                if charge_row:
                    self.append("charges", charge_row)
                    charges_added += 1

            if charges_added > 0:
                frappe.msgprint(
                    f"Successfully populated {charges_added} charges from One-Off Quote: {self.quote}",
                    title="Charges Updated",
                    indicator="green"
                )
            else:
                frappe.msgprint(
                    f"No valid charges could be mapped from One-Off Quote: {self.quote}",
                    title="No Valid Charges",
                    indicator="orange"
                )

        except Exception as e:
            frappe.log_error(
                f"Error populating charges from one-off quote {self.quote}: {str(e)}",
                "Transport Order Charges Population Error"
            )
            frappe.msgprint(
                f"Error populating charges: {str(e)}",
                title="Error",
                indicator="red"
            )

    def _map_sales_quote_transport_to_charge(self, sqt_record):
        """Map sales_quote_transport record to transport_order_charges format."""
        try:
            # Map overlapping fields directly
            charge_data = {}
            for field in SALES_QUOTE_CHARGE_FIELDS:
                if field in sqt_record:
                    charge_data[field] = sqt_record.get(field)

            # Fallbacks for essential fields
            if not charge_data.get("item_name") and sqt_record.get("item_code"):
                item_doc = frappe.get_doc("Item", sqt_record.item_code)
                charge_data["item_name"] = item_doc.item_name

            if not charge_data.get("uom") and sqt_record.get("item_code"):
                item_doc = item_doc if "item_doc" in locals() else frappe.get_doc("Item", sqt_record.item_code)
                charge_data["uom"] = item_doc.stock_uom

            if charge_data.get("unit_rate") is None:
                charge_data["unit_rate"] = 0

            if not charge_data.get("quantity"):
                charge_data["quantity"] = 1

            return charge_data

        except Exception as e:
            frappe.log_error(
                f"Error mapping sales quote transport record: {str(e)}",
                "Transport Order Charge Mapping Error"
            )
            return None


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
def populate_charges_from_sales_quote(docname: str = None, sales_quote: str = None):
    """Populate charges from sales_quote. Called from frontend when sales_quote field changes.
    
    Returns charge data that can be populated in the frontend.
    """
    if not sales_quote:
        return {"charges": []}
    
    try:
        # Verify that the sales_quote exists
        if not frappe.db.exists("Sales Quote", sales_quote):
            return {
                "error": f"Sales Quote {sales_quote} does not exist",
                "charges": []
            }
        
        # Fetch sales_quote_transport records from the selected sales_quote
        fields_to_fetch = ["name"] + SALES_QUOTE_CHARGE_FIELDS
        sales_quote_transport_records = frappe.get_all(
            "Sales Quote Transport",
            filters={"parent": sales_quote, "parenttype": "Sales Quote"},
            fields=fields_to_fetch,
            order_by="idx"
        )
        
        if not sales_quote_transport_records:
            return {
                "charges": [],
                "message": f"No transport charges found in Sales Quote: {sales_quote}"
            }
        
        # Map and populate charges
        charges = []
        for sqt_record in sales_quote_transport_records:
            charge_row = _map_sales_quote_transport_to_charge_dict(sqt_record)
            if charge_row:
                charges.append(charge_row)
        
        # Note: We do NOT save the document here to avoid "document has been modified" errors.
        # The client-side JavaScript will handle updating the form with the charges data.
        # For saved documents, the client will update the form and the user can save normally.
        
        return {
            "charges": charges,
            "charges_count": len(charges)
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error populating charges from sales quote {sales_quote}: {str(e)}",
            "Transport Order Charges Population Error"
        )
        return {
            "error": str(e),
            "charges": []
        }


def _map_sales_quote_transport_to_charge_dict(sqt_record):
    """Map sales_quote_transport record to transport_order_charges format (returns dict)."""
    try:
        # Map overlapping fields directly
        charge_data = {}
        for field in SALES_QUOTE_CHARGE_FIELDS:
            if field in sqt_record:
                charge_data[field] = sqt_record.get(field)
        
        # Fallbacks for essential fields
        item_doc = None
        if sqt_record.get("item_code"):
            if not charge_data.get("item_name") or not charge_data.get("uom"):
                item_doc = frappe.get_doc("Item", sqt_record.item_code)
                if not charge_data.get("item_name"):
                    charge_data["item_name"] = item_doc.item_name
                if not charge_data.get("uom"):
                    charge_data["uom"] = item_doc.stock_uom
        
        if charge_data.get("unit_rate") is None:
            charge_data["unit_rate"] = 0
        
        if not charge_data.get("quantity"):
            charge_data["quantity"] = 1
        
        return charge_data
        
    except Exception as e:
        frappe.log_error(
            f"Error mapping sales quote transport record: {str(e)}",
            "Transport Order Charge Mapping Error"
        )
        return None


@frappe.whitelist()
def populate_charges_from_one_off_quote(docname: str = None, one_off_quote: str = None):
    """Populate charges from one_off_quote. Called from frontend when one_off_quote field changes.
    
    Returns charge data that can be populated in the frontend.
    """
    if not one_off_quote:
        return {"charges": []}
    
    try:
        # Verify that the one_off_quote exists
        if not frappe.db.exists("One-Off Quote", one_off_quote):
            return {
                "error": f"One-Off Quote {one_off_quote} does not exist",
                "charges": []
            }
        
        # Fetch one_off_quote_transport records from the selected one_off_quote
        fields_to_fetch = ["name"] + SALES_QUOTE_CHARGE_FIELDS
        one_off_quote_transport_records = frappe.get_all(
            "One-Off Quote Transport",
            filters={"parent": one_off_quote, "parenttype": "One-Off Quote"},
            fields=fields_to_fetch,
            order_by="idx"
        )
        
        if not one_off_quote_transport_records:
            return {
                "charges": [],
                "message": f"No transport charges found in One-Off Quote: {one_off_quote}"
            }
        
        # Map and populate charges (One-Off Quote Transport has same structure as Sales Quote Transport)
        charges = []
        for oqt_record in one_off_quote_transport_records:
            charge_row = _map_sales_quote_transport_to_charge_dict(oqt_record)
            if charge_row:
                charges.append(charge_row)
        
        # Note: We do NOT save the document here to avoid "document has been modified" errors.
        # The client-side JavaScript will handle updating the form with the charges data.
        # For saved documents, the client will update the form and the user can save normally.
        
        return {
            "charges": charges,
            "charges_count": len(charges)
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error populating charges from one-off quote {one_off_quote}: {str(e)}",
            "Transport Order Charges Population Error"
        )
        return {
            "error": str(e),
            "charges": []
        }


@frappe.whitelist()
def action_get_leg_plan(docname: str, replace: int = 1, save: int = 1):
    """Populate Transport Order legs from the selected Transport Template."""
    if not docname:
        frappe.throw("Missing Transport Order name.")

    # Check if docname is a temporary name (starts with "new-")
    # This can happen if the function is called before the document is fully saved
    if docname.startswith("new-"):
        frappe.throw(_("Cannot create leg plan for unsaved document. Please save the Transport Order first."))

    # Guard: Check if we're in a save transaction and handle accordingly
    if getattr(frappe.flags, 'in_save', False):
        frappe.db.commit()
        time.sleep(0.3)  # Wait for transaction to complete

    # Get the document directly, handling DoesNotExistError
    try:
        doc = frappe.get_doc("Transport Order", docname)
    except frappe.DoesNotExistError:
        # Retry once after delay if document not found (may have been in save transaction)
        time.sleep(0.3)
        try:
            # Use get_cached_doc to avoid false not-found during post-save calls
            doc = frappe.get_cached_doc("Transport Order", docname)
        except frappe.DoesNotExistError:
            # Return graceful error response for post-save fetch failures
            return {"error": "doc_not_ready"}

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
        
        # Auto-fill transport_job_type from parent Transport Order (default to parent value)
        if getattr(doc, "transport_job_type", None):
            row_data["transport_job_type"] = doc.transport_job_type
        
        # Auto-fill scheduled_date from parent Transport Order (default to parent value)
        # This ensures scheduled_date defaults to Transport Order's scheduled_date
        # The _map_template_row_to_order_row function already calculates scheduled_date from
        # base_date + day_offset, but we ensure it defaults to base_date if not set
        if base_date and _has_field(order_child_dt, "scheduled_date"):
            # If scheduled_date was not set by template mapping, use base_date directly
            if not row_data.get("scheduled_date"):
                row_data["scheduled_date"] = base_date
            # Otherwise, scheduled_date is already set from base_date + day_offset in
            # _map_template_row_to_order_row, which is correct (defaults to base_date when offset=0)
        
        if not row_data.get("vehicle_type") and getattr(doc, "vehicle_type", None):
            row_data["vehicle_type"] = doc.vehicle_type
        
        doc.append(order_child_field, row_data)
        created += 1

    # Save the document if requested
    saved = False
    if cint(save):
        try:
            doc.flags.ignore_permissions = True
            doc.save()
            saved = True
        except Exception as e:
            frappe.log_error(f"Error saving Transport Order {docname} after leg plan creation: {str(e)}", "Leg Plan Save Error")
            # Continue even if save fails - document is still modified in memory

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
        "saved": saved,
    }

# -------------------------------------------------------------------
# ACTION: Create Transport Job from a submitted Transport Order
# -------------------------------------------------------------------
@frappe.whitelist()
def action_create_transport_job(docname: str):
    """Create (or reuse) a Transport Job from a submitted Transport Order."""
    try:
        # Check if docname is a temporary name (starts with "new-")
        if docname and docname.startswith("new-"):
            frappe.throw(_("Cannot create Transport Job for unsaved document. Please save the Transport Order first."))
        
        # Guard: Check if we're in a save transaction and handle accordingly
        if getattr(frappe.flags, 'in_save', False):
            frappe.db.commit()
            time.sleep(0.3)  # Wait for transaction to complete
        
        # Get the document directly, handling DoesNotExistError
        try:
            doc = frappe.get_doc("Transport Order", docname)
        except frappe.DoesNotExistError:
            # Retry once after delay if document not found (may have been in save transaction)
            time.sleep(0.3)
            try:
                # Use get_cached_doc to avoid false not-found during post-save calls
                doc = frappe.get_cached_doc("Transport Order", docname)
            except frappe.DoesNotExistError:
                # Return graceful error response for post-save fetch failures
                return {"error": "doc_not_ready"}

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
            "transport_job_type": getattr(doc, "transport_job_type", None),
            "customer": getattr(doc, "customer", None),
            "booking_date": getattr(doc, "booking_date", None),
            "customer_ref_no": getattr(doc, "customer_ref_no", None),
            "hazardous": getattr(doc, "hazardous", None),
            "refrigeration": getattr(doc, "reefer", None),
            "vehicle_type": getattr(doc, "vehicle_type", None),
            "load_type": getattr(doc, "load_type", None),
            "container_type": getattr(doc, "container_type", None),
            "container_no": getattr(doc, "container_no", None),
            "consolidate": getattr(doc, "consolidate", None),
            "pick_address": getattr(doc, "pick_address", None),
            "drop_address": getattr(doc, "drop_address", None),
            "company": getattr(doc, "company", None),
            "branch": getattr(doc, "branch", None),
            "cost_center": getattr(doc, "cost_center", None),
            "profit_center": getattr(doc, "profit_center", None),
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
        # Temporarily ignore mandatory and validation checks to prevent "Job Type must be set first" popups
        # The transport_job_type is set, but conditional field validation may trigger prematurely
        job.flags.ignore_mandatory = True
        job.flags.ignore_validate = True
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
        
    except frappe.DuplicateEntryError:
        # Handle race condition: another process may have created the job
        frappe.db.rollback()
        # Check again if job was created by another process
        existing = frappe.db.get_value("Transport Job", {"transport_order": docname}, "name")
        if existing:
            return {"name": existing, "created": False, "already_exists": True}
        # If we still can't find it, log and re-raise
        frappe.log_error(
            f"Duplicate Transport Job error for Transport Order {docname}, but could not find existing record",
            "Transport Job Duplicate Error"
        )
        frappe.throw(_("Failed to create Transport Job due to a duplicate entry. This may occur if multiple requests are processed simultaneously. Please try again or check if a Transport Job already exists for this Transport Order."))
    except Exception as e:
        frappe.log_error(f"Error creating transport job: {str(e)}")
        frappe.throw(_("Failed to create Transport Job: {0}").format(str(e)))


# -------------------------------------------------------------------
# API Endpoints for Transport Job Type functionality
# -------------------------------------------------------------------

@frappe.whitelist()
def get_transport_job_type_info(transport_job_type: str) -> Dict[str, Any]:
    """Get information about a specific transport job type."""
    if not transport_job_type:
        return {}
    
    info = {
        "name": transport_job_type,
        "description": "",
        "requirements": [],
        "restrictions": [],
        "cost_factors": {},
        "vehicle_requirements": {}
    }
    
    if transport_job_type == "Container":
        info.update({
            "description": "Standardized container transport",
            "requirements": ["Container Type", "Container Number"],
            "restrictions": ["Standard Routes", "Container Handling Equipment"]
        })
    elif transport_job_type == "Heavy Haul":
        info.update({
            "description": "Heavy cargo transport requiring specialized equipment",
            "requirements": ["Heavy Vehicle Permit", "Route Clearance", "Special Equipment"],
            "restrictions": ["No Low Bridges", "Heavy Vehicle Routes Only"]
        })
    elif transport_job_type == "Oversized":
        info.update({
            "description": "Oversized cargo transport requiring special routing",
            "requirements": ["Oversize Load Permit", "Escort Vehicle", "Route Planning"],
            "restrictions": ["Oversize Load Routes", "Escort Required"]
        })
    elif transport_job_type == "Special":
        info.update({
            "description": "Special transport requiring custom handling",
            "requirements": ["Special Transport Permit", "Custom Equipment"],
            "restrictions": ["Special Routes", "Custom Handling"]
        })
    elif transport_job_type == "Multimodal":
        info.update({
            "description": "Transport involving multiple modes of transportation",
            "requirements": ["Multi-mode Coordination", "Transfer Planning"],
            "restrictions": ["Mode-specific Routes", "Transfer Points"]
        })
    elif transport_job_type == "Non-Container":
        info.update({
            "description": "General cargo transport without containers",
            "requirements": ["Standard Equipment"],
            "restrictions": ["Standard Routes"]
        })
    
    return info


@frappe.whitelist()
def get_vehicle_compatibility(transport_job_type: str, vehicle_type: str = None) -> Dict[str, Any]:
    """Get vehicle compatibility information for a transport job type."""
    if not transport_job_type:
        return {}
    
    compatibility = {
        "suitable_vehicle_types": [],
        "required_capacity": {},
        "special_equipment": [],
        "driver_qualifications": []
    }
    
    if transport_job_type == "Heavy Haul":
        compatibility.update({
            "suitable_vehicle_types": ["Heavy Truck", "Crane Truck", "Low Loader"],
            "required_capacity": {"min_weight": 50000, "min_volume": 0},
            "special_equipment": ["Heavy Duty Trailer", "Crane", "Winch"],
            "driver_qualifications": ["Heavy Vehicle License", "Crane Operator License"]
        })
    elif transport_job_type == "Oversized":
        compatibility.update({
            "suitable_vehicle_types": ["Oversize Truck", "Flatbed", "Low Loader"],
            "required_capacity": {"min_weight": 0, "min_volume": 100},
            "special_equipment": ["Oversize Trailer", "Escort Vehicle", "Warning Lights"],
            "driver_qualifications": ["Oversize Load License", "Escort Training"]
        })
    elif transport_job_type == "Container":
        compatibility.update({
            "suitable_vehicle_types": ["Container Truck", "Flatbed"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Container Chassis", "Twist Locks"],
            "driver_qualifications": ["Container Handling License"]
        })
    elif transport_job_type == "Special":
        compatibility.update({
            "suitable_vehicle_types": ["Specialized Vehicle", "Custom Truck"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Specialized Equipment", "Custom Trailer"],
            "driver_qualifications": ["Special Transport License", "Custom Training"]
        })
    elif transport_job_type == "Multimodal":
        compatibility.update({
            "suitable_vehicle_types": ["Multi-purpose Vehicle", "Transfer Truck"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Transfer Equipment", "Loading Equipment"],
            "driver_qualifications": ["Multi-mode License", "Transfer Training"]
        })
    else:  # Non-Container
        compatibility.update({
            "suitable_vehicle_types": ["Standard Truck", "Van", "Pickup"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Standard Equipment"],
            "driver_qualifications": ["Standard License"]
        })
    
    return compatibility


def _get_vehicle_type_container_field():
    """Return the Vehicle Type field name for container flag (container or containerized)."""
    meta = frappe.get_meta("Vehicle Type")
    if meta.has_field("container"):
        return "container"
    if meta.has_field("containerized"):
        return "containerized"
    return None


@frappe.whitelist()
def get_allowed_vehicle_types(transport_job_type: str, refrigeration: bool = False) -> Dict[str, Any]:
    """Get allowed vehicle types for a transport job type based on boolean columns and reefer.
    Uses ignore_permissions so link-field filtering works for users who cannot read
    restricted fields (e.g. container) on Vehicle Type."""
    if not transport_job_type:
        return {"vehicle_types": []}
    
    meta = frappe.get_meta("Vehicle Type")
    filters = {}
    
    # Filter by container flag (support both "container" and "containerized" field names)
    container_field = _get_vehicle_type_container_field()
    if container_field:
        if transport_job_type == "Container":
            filters[container_field] = 1
        elif transport_job_type == "Non-Container":
            filters[container_field] = 0
    
    # Filter by boolean columns for specific transport job types
    if transport_job_type == "Special":
        filters["special"] = 1
        filters["reefer"] = 1
    elif transport_job_type == "Oversized":
        filters["oversized"] = 1
    elif transport_job_type == "Heavy Haul":
        filters["heavy_haul"] = 1
    elif transport_job_type == "Multimodal":
        if meta.has_field("multimodal"):
            filters["multimodal"] = 1
    
    if refrigeration and transport_job_type != "Special":
        filters["reefer"] = 1
    
    # ignore_permissions=True so link dropdown can show allowed types without requiring
    # read permission on fields like container/containerized
    vehicle_types = frappe.get_all(
        "Vehicle Type",
        filters=filters,
        fields=["name", "code", "description"],
        order_by="code",
        ignore_permissions=True,
    )
    
    return {"vehicle_types": vehicle_types}


@frappe.whitelist()
def validate_vehicle_job_type_compatibility(transport_job_type: str, vehicle_type: str, refrigeration: bool = False) -> Dict[str, Any]:
    """Validate if a vehicle type is compatible with the transport job type based on boolean columns and refrigeration requirements."""
    if not transport_job_type or not vehicle_type:
        return {"compatible": True, "message": ""}
    
    # Get vehicle type details - fetch boolean fields dynamically
    meta = frappe.get_meta("Vehicle Type")
    container_field = _get_vehicle_type_container_field()
    fields_to_fetch = ["code", "reefer"]
    if container_field:
        fields_to_fetch.insert(0, container_field)
    
    # Add boolean fields if they exist
    boolean_fields = ["special", "oversized", "heavy_haul", "multimodal"]
    for field in boolean_fields:
        if meta.has_field(field):
            fields_to_fetch.append(field)
    
    vehicle_details = frappe.get_value(
        "Vehicle Type",
        vehicle_type,
        fields_to_fetch,
        as_dict=True
    )
    
    if not vehicle_details:
        return {"compatible": False, "message": f"Vehicle Type {vehicle_type} not found"}
    
    compatible = True
    messages = []
    
    # Check container compatibility (support both container and containerized field names)
    container_val = container_field and vehicle_details.get(container_field)
    if transport_job_type == "Container":
        if not container_val:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not container. Container job type requires a container vehicle type.")
    elif transport_job_type == "Non-Container":
        if container_val:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is container. Non-Container job type requires a non-container vehicle type.")
    
    # Check boolean field compatibility for specific job types
    if transport_job_type == "Special":
        if not vehicle_details.reefer:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} does not have reefer capability. Special job type requires a vehicle with reefer enabled.")
        if not getattr(vehicle_details, "special", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Special. Special job type requires a vehicle type with special capability.")
    elif transport_job_type == "Oversized":
        if not getattr(vehicle_details, "oversized", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Oversized. Oversized job type requires a vehicle type with oversized capability.")
    elif transport_job_type == "Heavy Haul":
        if not getattr(vehicle_details, "heavy_haul", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Heavy Haul. Heavy Haul job type requires a vehicle type with heavy haul capability.")
    elif transport_job_type == "Multimodal":
        if not getattr(vehicle_details, "multimodal", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Multimodal. Multimodal job type requires a vehicle type with multimodal capability.")
    
    # Check reefer requirement for other job types (only if refrigeration is actually checked)
    # Only check if refrigeration is explicitly True/1 and transport_job_type is not "Special"
    # Handle cases where refrigeration might be passed as 0, False, "0", None, etc.
    refrigeration_enabled = refrigeration in (True, 1) or (isinstance(refrigeration, str) and refrigeration == "1")
    if refrigeration_enabled and transport_job_type != "Special":
        if not vehicle_details.reefer:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} does not have reefer capability. Refrigerated transport requires a vehicle with reefer enabled.")
    
    return {"compatible": compatible, "message": " ".join(messages) if messages else ""}


@frappe.whitelist()
def get_vehicle_types_for_load_type(
    load_type: str,
    hazardous: bool = False,
    reefer: bool = False,
) -> Dict[str, Any]:
    """
    Get list of Vehicle Types that:
    - have the specified load_type in their allowed_load_types, and
    - if hazardous=True, have hazardous checkbox set, and
    - if reefer=True, have reefer checkbox set.

    Uses ignore_permissions so link filtering works without field-level read on hazardous/reefer.
    """
    if not load_type:
        return {"vehicle_types": []}

    if not frappe.db.exists("Load Type", load_type):
        return {"vehicle_types": []}

    # Vehicle Types that have this load_type in allowed_load_types (child table)
    vehicle_types = frappe.db.sql("""
        SELECT DISTINCT parent
        FROM `tabVehicle Type Load Types`
        WHERE load_type = %s
        AND parent IS NOT NULL
    """, (load_type,), as_dict=True)
    vehicle_type_names = [vt.parent for vt in vehicle_types if vt.parent]
    if not vehicle_type_names:
        return {"vehicle_types": []}

    # Optionally restrict by hazardous and/or reefer (ignore_permissions for link-filter use)
    need_hazardous = hazardous in (True, 1) or (isinstance(hazardous, str) and hazardous == "1")
    need_reefer = reefer in (True, 1) or (isinstance(reefer, str) and reefer == "1")
    if need_hazardous or need_reefer:
        filters = {"name": ["in", vehicle_type_names]}
        if need_hazardous:
            filters["hazardous"] = 1
        if need_reefer:
            filters["reefer"] = 1
        filtered = frappe.get_all(
            "Vehicle Type",
            filters=filters,
            pluck="name",
            ignore_permissions=True,
        )
        vehicle_type_names = list(filtered)

    return {"vehicle_types": vehicle_type_names}


@frappe.whitelist()
def get_cost_estimation(transport_job_type: str, base_cost: float = 1000) -> Dict[str, Any]:
    """Get cost estimation based on transport job type."""
    if not transport_job_type or not base_cost:
        return {}
    
    factors = {
        "base_cost": base_cost,
        "surcharge_rate": 0.0,
        "surcharge_amount": 0.0,
        "total_cost": base_cost,
        "special_handling": False
    }
    
    if transport_job_type == "Heavy Haul":
        factors["surcharge_rate"] = 0.5
        factors["special_handling"] = True
    elif transport_job_type == "Oversized":
        factors["surcharge_rate"] = 0.3
        factors["special_handling"] = True
    elif transport_job_type == "Special":
        factors["surcharge_rate"] = 0.4
        factors["special_handling"] = True
    elif transport_job_type == "Multimodal":
        factors["surcharge_rate"] = 0.2
    elif transport_job_type == "Container":
        factors["surcharge_rate"] = 0.1
    else:  # Non-Container
        factors["surcharge_rate"] = 0.0
    
    factors["surcharge_amount"] = base_cost * factors["surcharge_rate"]
    factors["total_cost"] = base_cost + factors["surcharge_amount"]
    
    return factors


@frappe.whitelist()
def get_available_one_off_quotes(transport_order_name: str = None) -> Dict[str, Any]:
    """Get list of One-Off Quotes that are not yet linked to a Transport Order and not converted.
    
    Excludes One-Off Quotes that are:
    1. Already linked to another Transport Order
    2. Already converted (status = "Converted" or converted_to_doc is set)
    
    This prevents users from selecting quotes that have already been converted or used.
    """
    try:
        # Get all One-Off Quotes already linked to Transport Orders (excluding current order)
        used_quotes = frappe.get_all(
            "Transport Order",
            filters={
                "quote_type": "One-Off Quote",
                "quote": ["is", "set"],
                "name": ["!=", transport_order_name or ""]
            },
            pluck="quote"
        )
        
        # Get all converted One-Off Quotes (status = "Converted" or converted_to_doc is set)
        converted_quotes = frappe.get_all(
            "One-Off Quote",
            filters={
                "status": "Converted"
            },
            pluck="name"
        )
        
        # Also get quotes with converted_to_doc set (in case status wasn't updated)
        quotes_with_conversion = frappe.get_all(
            "One-Off Quote",
            filters={
                "converted_to_doc": ["is", "set"]
            },
            pluck="name"
        )
        
        # Combine all excluded quotes
        excluded_quotes = list(set(used_quotes + converted_quotes + quotes_with_conversion))
        
        # Return filter to exclude used and converted quotes
        filters = {}
        if excluded_quotes:
            filters["name"] = ["not in", excluded_quotes]
        
        # Also filter to only show One-Off Quotes that have transport enabled
        # Check if One-Off Quote has is_transport field
        if _has_field("One-Off Quote", "is_transport"):
            filters["is_transport"] = 1
        
        return {"filters": filters}
    except Exception as e:
        frappe.log_error(
            f"Error getting available One-Off Quotes: {str(e)}",
            "Transport Order Quote Query Error"
        )
        return {"filters": {}}


@frappe.whitelist()
def get_consolidation_opportunities(transport_order_name: str) -> Dict[str, Any]:
    """Get consolidation opportunities for a transport order."""
    try:
        # Check if transport_order_name is a temporary name (starts with "new-")
        if transport_order_name and transport_order_name.startswith("new-"):
            return {"eligible": False}
        
        # Check if document exists before trying to get it
        if not frappe.db.exists("Transport Order", transport_order_name):
            return {"eligible": False}
        
        doc = frappe.get_doc("Transport Order", transport_order_name)
        
        if not doc.get_consolidation_eligibility():
            return {"eligible": False, "reason": "Transport order not eligible for consolidation"}
        
        order_meta = frappe.get_meta("Transport Order")
        filters = {
                "transport_job_type": doc.transport_job_type,
                "load_type": doc.load_type,
                "docstatus": 1,
            "name": ["!=", doc.name],
        }

        if order_meta.has_field("company") and getattr(doc, "company", None):
            filters["company"] = doc.company

        if order_meta.has_field("branch") and getattr(doc, "branch", None):
            filters["branch"] = doc.branch

        # Find other eligible transport orders
        try:
            eligible_orders = frappe.get_all(
                "Transport Order",
                filters=filters,
            fields=["name", "customer", "booking_date", "scheduled_date"],
                limit=10,
        )
        except ProgrammingError as err:
            frappe.log_error(f"Error fetching consolidation opportunities: {err}", "Transport Order Consolidation")
            return {"eligible": False, "error": str(err)}
        
        return {
            "eligible": True,
            "current_order": doc.name,
            "job_type": doc.transport_job_type,
            "load_type": doc.load_type,
            "opportunities": eligible_orders
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting consolidation opportunities: {str(e)}")
        return {"eligible": False, "error": str(e)}


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
        # Validate pick_mode and drop_mode are valid Pick and Drop Mode records if set
        # Ensure values are passed through unchanged and remain valid
        pick_mode = getattr(ol, "pick_mode", None)
        drop_mode = getattr(ol, "drop_mode", None)
        
        if pick_mode and not frappe.db.exists("Pick and Drop Mode", pick_mode):
            frappe.throw(_("Invalid pick_mode '{0}' in Transport Order Leg. Must be a valid Pick and Drop Mode record.").format(pick_mode))
        
        if drop_mode and not frappe.db.exists("Pick and Drop Mode", drop_mode):
            frappe.throw(_("Invalid drop_mode '{0}' in Transport Order Leg. Must be a valid Pick and Drop Mode record.").format(drop_mode))
        
        # Create top-level Transport Leg
        leg = frappe.new_doc("Transport Leg")
        _safe_set(leg, "transport_job", job_doc.name)  # back-reference to the Job
        _safe_set(leg, "date", order_doc.scheduled_date)  # back-reference to the Job

        _safe_set(leg, "facility_type_from", getattr(ol, "facility_type_from", None))
        _safe_set(leg, "facility_from", getattr(ol, "facility_from", None))
        _safe_set(leg, "pick_mode", pick_mode)  # Use validated value
        _safe_set(leg, "pick_address", getattr(ol, "pick_address", None))

        _safe_set(leg, "facility_type_to", getattr(ol, "facility_type_to", None))
        _safe_set(leg, "facility_to", getattr(ol, "facility_to", None))
        _safe_set(leg, "drop_mode", drop_mode)  # Use validated value
        _safe_set(leg, "drop_address", getattr(ol, "drop_address", None))
        
        # Map transport details from order leg
        _safe_set(leg, "vehicle_type", getattr(ol, "vehicle_type", None))
        _safe_set(leg, "transport_job_type", getattr(ol, "transport_job_type", None))

        leg.insert(ignore_permissions=False)

        # Link into Transport Job Legs child table (denormalized snapshot for quick view/filter)
        # Pass through pick_mode and drop_mode unchanged (already validated above)
        job_doc.append(
            job_legs_field,
            {
                "transport_leg": leg.name,
                "facility_type_from": getattr(ol, "facility_type_from", None),
                "facility_from": getattr(ol, "facility_from", None),
                "pick_mode": pick_mode,  # Use validated value, passed through unchanged
                "pick_address": getattr(ol, "pick_address", None),
                "facility_type_to": getattr(ol, "facility_type_to", None),
                "facility_to": getattr(ol, "facility_to", None),
                "drop_mode": drop_mode,  # Use validated value, passed through unchanged
                "drop_address": getattr(ol, "drop_address", None),
                "vehicle_type": getattr(ol, "vehicle_type", None),
                "transport_job_type": getattr(ol, "transport_job_type", None),
            },
        )


def _safe_set(doc: Document, fieldname: str, value):
    """Set a value only if the field exists on the document."""
    if value is None:
        return
    meta = frappe.get_meta(doc.doctype)
    if meta.has_field(fieldname):
        doc.set(fieldname, value)
