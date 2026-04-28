# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _
from logistics.utils.document_date_validation import (
    throw_if_left_date_after_right,
    is_future_date,
)
from logistics.utils.sea_fcl_container_validation import (
    validate_fcl_container_numbers_required,
)
from logistics.utils.dg_fields import update_parent_dg_compliance_status

# Virtual MBL display fields: (fieldname on Sea Shipment, column on Master Bill)
_MBL_VIRTUAL_FIELD_SOURCES = (
    ("mbl_master_type", "master_type"),
    ("mbl_shipping_line", "shipping_line"),
    ("mbl_vessel", "vessel"),
    ("mbl_voyage_no", "voyage_no"),
    ("mbl_voyage_status", "voyage_status"),
    ("mbl_vessel_date", "vessel_date"),
    ("mbl_origin_port", "origin_port"),
    ("mbl_destination_port", "destination_port"),
    ("mbl_scheduled_departure", "scheduled_departure"),
    ("mbl_scheduled_arrival", "scheduled_arrival"),
    ("mbl_booking_reference_no", "booking_reference_no"),
    ("mbl_agent_reference", "agent_reference"),
)


class SeaShipment(Document):
    def validate(self):
        """Validate Sea Shipment data"""
        from logistics.utils.charges_calculation import (
            clear_charge_resolution_parent,
            register_charge_resolution_parent,
        )

        register_charge_resolution_parent(self)
        try:
            from logistics.utils.internal_job_main_link import validate_internal_job_main_link_unchanged

            validate_internal_job_main_link_unchanged(self)
            from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

            apply_shipper_consignee_defaults(self)
            self._sync_freight_consolidator_from_sea_booking()
            if self.is_new():
                from logistics.sea_freight.sea_freight_settings_defaults import (
                    apply_accounting_defaults_from_sea_freight_settings,
                )

                apply_accounting_defaults_from_sea_freight_settings(self)
            # Normalize legacy house_type values
            self._normalize_house_type()
            update_parent_dg_compliance_status(self)
            self.validate_accounts()
            self.validate_dates()
            self.validate_duplicates()
            self._prepare_header_totals_for_charge_calculation()
            self._sync_charges_with_parent_actuals()
            self._update_packing_summary()
            self._apply_uom_defaults()
            self.validate_weight_volume()
            self.validate_packages()
            self.validate_containers()
            self.validate_master_bill()
            self.validate_main_routing_legs_by_entry_type()
            try:
                from logistics.job_management.recognition_engine import (
                    sync_job_recognition_fields_from_policy,
                )

                sync_job_recognition_fields_from_policy(self)
            except Exception:
                pass

            from logistics.utils.sales_quote_validity import msgprint_sales_quote_validity_warnings

            msgprint_sales_quote_validity_warnings(self)

            if getattr(self, "sales_quote", None):
                from frappe.utils import cint

                from logistics.pricing_center.doctype.sales_quote.sales_quote import (
                    resolve_allow_linked_freight_bookings_for_internal_job,
                    resolve_single_main_air_booking_for_sales_quote,
                    resolve_single_main_sea_booking_for_sales_quote,
                    validate_one_off_quote_not_converted,
                )

                allow_sea = (getattr(self, "sea_booking", None) or "").strip() or None
                allow_air = None
                r_sea, r_air = resolve_allow_linked_freight_bookings_for_internal_job(self)
                if r_sea:
                    allow_sea = allow_sea or (r_sea or "").strip() or None
                if r_air:
                    allow_air = (r_air or "").strip() or None
                if not allow_sea:
                    allow_sea = resolve_single_main_sea_booking_for_sales_quote(self.sales_quote)
                if not allow_air:
                    allow_air = resolve_single_main_air_booking_for_sales_quote(self.sales_quote)
                validate_one_off_quote_not_converted(
                    self.sales_quote,
                    self.doctype,
                    self.name,
                    allow_linked_sea_booking=allow_sea,
                    allow_linked_air_booking=allow_air,
                    allow_main_transport_if_converted_to_declaration_order=cint(getattr(self, "is_main_service", 0)) == 1,
                )

            from logistics.job_management.logistics_job_status import sync_sea_shipment_job_status

            sync_sea_shipment_job_status(self)

        finally:
            clear_charge_resolution_parent(self)

    def _prepare_header_totals_for_charge_calculation(self):
        try:
            from logistics.utils.measurements import apply_measurement_uom_conversion_to_children

            apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
        except Exception:
            pass
        if not getattr(self, "override_volume_weight", False):
            self.aggregate_volume_from_packages()
            self.aggregate_weight_from_packages()
        self._ensure_total_volume_weight()

    def _sync_charges_with_parent_actuals(self):
        if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
            return
        if getattr(self.flags, "ignore_charges_sync", False):
            return
        for charge in self.get("charges") or []:
            if hasattr(charge, "calculate_charge_amount"):
                charge.calculate_charge_amount(parent_doc=self)

    def _sync_freight_consolidator_from_sea_booking(self):
        """Keep Freight Consolidator aligned with the linked Sea Booking when set there."""
        if not getattr(self, "sea_booking", None):
            return
        booking_fc = frappe.db.get_value(
            "Sea Booking", self.sea_booking, "freight_consolidator"
        )
        if booking_fc:
            self.freight_consolidator = booking_fc

    def validate_main_routing_legs_by_entry_type(self):
        """Allow additional Main leg for Transit/Transshipment while keeping Direct capped at one."""
        entry_type = (getattr(self, "entry_type", "") or "").strip()
        if not entry_type:
            return

        main_leg_count = sum(
            1
            for leg in (getattr(self, "routing_legs", None) or [])
            if (getattr(leg, "type", "") or "").strip() == "Main"
        )

        if entry_type in {"Transit", "Transshipment"} and main_leg_count > 2:
            frappe.throw(
                _("For {0}, you can define at most two Main routing legs.").format(entry_type),
                title=_("Invalid Routing Legs"),
            )

        if entry_type == "Direct" and main_leg_count > 1:
            frappe.throw(
                _("For Direct entry type, only one Main routing leg is allowed."),
                title=_("Invalid Routing Legs"),
            )
    
    def before_submit(self):
        """Validate required data before submit; block DG non-compliance."""
        self.validate_required_fields_for_submit()
        validate_fcl_container_numbers_required(self)
        try:
            contains_dg = bool(getattr(self, "contains_dangerous_goods", 0))
            dg_status = (getattr(self, "dg_compliance_status", "") or "").strip()
            if contains_dg and dg_status == "Non-Compliant":
                frappe.throw(
                    _(
                        "Cannot submit Sea Shipment: DG Compliance Status is Non-Compliant while "
                        "this shipment contains dangerous goods. Please resolve compliance first."
                    ),
                    title=_("Dangerous Goods Non-Compliant"),
                )
        except Exception:
            # If any unexpected error occurs while checking, fail safe by throwing a clear message
            frappe.throw(
                _(
                    "Submission blocked due to Dangerous Goods compliance validation error. "
                    "Please review DG fields."
                ),
                title=_("Dangerous Goods Validation"),
            )

    def aggregate_volume_from_packages(self):
        """Set header volume from sum of package volumes, converted to m³."""
        if getattr(self, "override_volume_weight", False):
            return
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
            if total > 0:
                self.total_volume = total
        except Exception:
            pass

    def aggregate_weight_from_packages(self):
        """Set total_weight from sum of package weights, converted to default weight UOM."""
        if getattr(self, "override_volume_weight", False):
            return
        packages = getattr(self, "packages", []) or []
        if not packages:
            return
        try:
            from logistics.utils.measurements import convert_weight, get_default_uoms
            defaults = get_default_uoms(company=getattr(self, "company", None))
            target_weight_uom = defaults.get("weight")
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
            if total > 0:
                self.total_weight = total
        except Exception:
            pass

    def _ensure_total_volume_weight(self):
        """Ensure total_volume and total_weight are set; default to 0 when packages empty and not override."""
        if not getattr(self, "packages", None) and not getattr(self, "override_volume_weight", False):
            self.total_volume = 0
            self.total_weight = 0
        self.total_volume = flt(self.total_volume or 0)
        self.total_weight = flt(self.total_weight or 0)

    def _update_packing_summary(self):
        """Update total_containers, total_teus, total_packages from child tables."""
        containers = getattr(self, "containers", []) or []
        packages = getattr(self, "packages", []) or []
        self.total_containers = len(containers)
        total_teus = 0
        for c in containers:
            ct = getattr(c, "type", None)
            if ct:
                teu = frappe.db.get_value("Container Type", ct, "teu_count")
                total_teus += flt(teu) or 0
        self.total_teus = total_teus
        self.total_packages = sum(flt(getattr(p, "no_of_packs", 0) or 0) for p in packages)
        from logistics.sea_freight.container_row_metrics import sync_sea_freight_container_child_rows

        sync_sea_freight_container_child_rows(self)

    def _apply_uom_defaults(self):
        """Apply UOM defaults from Logistics Settings when not set."""
        try:
            from logistics.utils.measurements import get_default_uoms, get_aggregation_volume_uom
            defaults = get_default_uoms(company=getattr(self, "company", None))
            if not getattr(self, "total_volume_uom", None):
                vol_uom = get_aggregation_volume_uom(company=getattr(self, "company", None)) or defaults.get("volume")
                if vol_uom:
                    self.total_volume_uom = vol_uom
            if not getattr(self, "total_weight_uom", None) and defaults.get("weight"):
                self.total_weight_uom = defaults["weight"]
            if not getattr(self, "chargeable_weight_uom", None):
                self.chargeable_weight_uom = defaults.get("chargeable_weight") or defaults.get("weight")
        except Exception:
            pass
    
    @frappe.whitelist()
    def aggregate_volume_from_packages_api(self):
        """Whitelisted API: aggregate volume and weight from packages for client-side refresh when override is unchecked."""
        if not getattr(self, "override_volume_weight", False):
            self.aggregate_volume_from_packages()
            self.aggregate_weight_from_packages()
        self._update_packing_summary()
        return {
            "total_volume": getattr(self, "total_volume", 0),
            "total_weight": getattr(self, "total_weight", 0),
            "total_containers": getattr(self, "total_containers", 0),
            "total_teus": getattr(self, "total_teus", 0),
            "total_packages": getattr(self, "total_packages", 0),
        }
    
    def after_insert(self):
        """Create Job Number when document is first created. Defer to avoid 'not found' during conversion."""
        settings = frappe.get_single("Sea Freight Settings")
        if settings and not getattr(settings, "auto_create_job_costing", True):
            return
        frappe.enqueue(
            "logistics.sea_freight.doctype.sea_shipment.sea_shipment.create_job_number_for_shipment",
            queue="default",
            shipment_name=self.name,
            company=self.company,
            branch=self.branch,
            cost_center=self.cost_center,
            profit_center=self.profit_center,
            booking_date=self.booking_date,
        )
    
    def before_save(self):
        """Calculate sustainability metrics before saving"""
        self.calculate_sustainability_metrics()
        self.check_delays()
        self.calculate_penalties()
        # Auto-populate routing from origin/destination when routing legs are empty
        self._auto_populate_routing_from_ports()
        # Container Management: create/link containers and sync penalties
        try:
            from logistics.container_management.api import sync_shipment_containers_and_penalties
            sync_shipment_containers_and_penalties(self)
        except Exception as e:
            if not getattr(frappe.flags, "skip_container_sync", False):
                frappe.log_error(
                    "Sea Shipment container sync error: {0}".format(str(e)),
                    "Container Management"
                )
        
        # Create Job Number if missing and auto-create is enabled
        # Only create for existing documents (updates), not during insert
        # For new documents, after_insert will handle creation via background job
        if self.name and not self.job_number and frappe.db.exists("Sea Shipment", self.name):
            self.create_job_number_if_needed()
        
        # Sync Job Number to Booking if it was manually changed
        if self.name and self.job_number and self.has_value_changed("job_number"):
            self.sync_job_number_to_booking()
    
    def after_submit(self):
        """Record sustainability metrics after shipment submission"""
        self.record_sustainability_metrics()
    
    def calculate_sustainability_metrics(self):
        """Calculate sustainability metrics for this sea shipment"""
        try:
            # Calculate carbon footprint based on weight and distance
            if hasattr(self, 'total_weight') and hasattr(self, 'origin_port') and hasattr(self, 'destination_port'):
                # Get distance between ports (simplified calculation)
                distance = self._calculate_port_distance(self.origin_port, self.destination_port)
                if distance and self.total_weight:
                    # Use sea freight emission factor
                    emission_factor = 0.01  # kg CO2e per ton-km for sea freight
                    carbon_footprint = (flt(self.total_weight) / 1000) * distance * emission_factor
                    self.estimated_carbon_footprint = carbon_footprint
                    
                    # Calculate fuel consumption estimate
                    fuel_consumption = self._calculate_fuel_consumption(distance, flt(self.total_weight))
                    self.estimated_fuel_consumption = fuel_consumption
                
        except Exception as e:
            frappe.log_error(f"Error calculating sustainability metrics for Sea Shipment {self.name}: {e}", "Sea Shipment Sustainability Error")
    
    def record_sustainability_metrics(self):
        """Record sustainability metrics in the centralized system"""
        try:
            from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
            
            result = integrate_sustainability(
                doctype=self.doctype,
                docname=self.name,
                module="Sea Freight",
                doc=self
            )
            
            if result.get("status") == "success":
                frappe.msgprint(_("Sustainability metrics recorded successfully"))
            elif result.get("status") == "skipped":
                # Don't show message if sustainability is not enabled
                pass
            else:
                frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Sea Shipment Sustainability Error")
                
        except Exception as e:
            frappe.log_error(f"Error recording sustainability metrics for Sea Shipment {self.name}: {e}", "Sea Shipment Sustainability Error")
    
    def _calculate_port_distance(self, origin: str, destination: str) -> float:
        """Calculate distance between ports (simplified)"""
        # This would typically use a geocoding service or database
        # For now, return a default distance based on common sea routes
        # Supports both UNLOCO codes (5 chars) and legacy 3-letter codes
        route_distances = {
            # UNLOCO codes (5 characters)
            ("USLAX", "SGSIN"): 8500,  # Los Angeles to Singapore
            ("HKHKG", "USLAX"): 12000,  # Hong Kong to Los Angeles
            ("NLRTM", "USNYC"): 5800,  # Rotterdam to New York
            ("SGSIN", "HKHKG"): 2600,  # Singapore to Hong Kong
            # Legacy 3-letter codes (for backward compatibility)
            ("LAX", "SIN"): 8500,
            ("HKG", "LAX"): 12000,
            ("ROT", "NYC"): 5800,
            ("SIN", "HKG"): 2600,
        }
        
        # Try to find exact match
        key = (origin, destination)
        if key in route_distances:
            return route_distances[key]
        
        # Try reverse match
        key = (destination, origin)
        if key in route_distances:
            return route_distances[key]
        
        # If UNLOCO codes, try to get coordinates and calculate distance
        if origin and destination and len(origin) == 5 and len(destination) == 5:
            try:
                origin_coords = self._get_unloco_coordinates(origin)
                dest_coords = self._get_unloco_coordinates(destination)
                
                if origin_coords and dest_coords:
                    # Calculate distance using Haversine formula
                    from math import radians, sin, cos, sqrt, atan2
                    lat1, lon1 = radians(origin_coords[0]), radians(origin_coords[1])
                    lat2, lon2 = radians(dest_coords[0]), radians(dest_coords[1])
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    
                    # Earth radius in km
                    R = 6371
                    distance = R * c
                    
                    return distance
            except Exception:
                pass  # Fall through to default
        
        # Default distance for sea freight
        return 5000.0  # Default 5000 km
    
    def _get_unloco_coordinates(self, unloco_code: str) -> tuple:
        """Get latitude and longitude for UNLOCO code"""
        try:
            coords = frappe.db.get_value("UNLOCO", unloco_code, ["latitude", "longitude"], as_dict=True)
            if coords and coords.latitude and coords.longitude:
                return (coords.latitude, coords.longitude)
        except Exception:
            pass
        return None
    
    def _calculate_fuel_consumption(self, distance: float, weight: float) -> float:
        """Calculate estimated fuel consumption for sea freight"""
        # Sea freight fuel consumption is typically 0.1-0.2 L per 100 km per ton
        fuel_rate = 0.15  # L per 100 km per ton
        return (fuel_rate * distance * (weight / 1000)) / 100.0
    
    def _normalize_house_type(self):
        """Normalize legacy house_type values to current options.
        Converts 'Direct' -> 'Standard House' and 'Consolidation' -> 'Co-load Master'.
        """
        if not hasattr(self, 'house_type') or not self.house_type:
            return
        normalization_map = {
            "Direct": "Standard House",
            "Consolidation": "Co-load Master",
        }
        if self.house_type in normalization_map:
            self.house_type = normalization_map[self.house_type]
    
    def validate_accounts(self):
        """Validate that cost center, profit center, and branch belong to the company"""
        if not self.company:
            return  # Skip validation if company is not set
        
        if self.cost_center:
            cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
            if cost_center_company and cost_center_company != self.company:
                frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                    self.cost_center, self.company
                ))
        
        if self.profit_center:
            # Check if Profit Center doctype has a company field before validating
            # Profit Center may not have a company field in this installation (e.g. logistics custom)
            try:
                profit_center_meta = frappe.get_meta("Profit Center")
                if profit_center_meta.has_field("company"):
                    profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
                    if profit_center_company and profit_center_company != self.company:
                        frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                            self.profit_center, self.company
                        ))
            except Exception as e:
                if "Unknown column" in str(e) or "1054" in str(e):
                    pass  # Field doesn't exist in database, skip validation
                else:
                    raise
        
        if self.branch:
            # Check if Branch doctype has a company field before validating
            try:
                branch_meta = frappe.get_meta("Branch")
                if branch_meta.has_field("company"):
                    branch_company = frappe.db.get_value("Branch", self.branch, "company")
                    if branch_company and branch_company != self.company:
                        frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                            self.branch, self.company
                        ))
            except Exception as e:
                if "Unknown column" in str(e) or "1054" in str(e):
                    pass  # Field doesn't exist in database, skip validation
                else:
                    raise
    
    def create_job_number_if_needed(self):
        """Create Job Number when document is first saved"""
        # Check settings for auto-create job costing
        settings = frappe.get_single("Sea Freight Settings")
        if settings and not getattr(settings, "auto_create_job_costing", True):
            return
        
        # Only create if job_number is not set
        if not self.job_number:
            # Check if this is the first save (no existing Job Number)
            existing_job_ref = frappe.db.get_value("Job Number", {
                "job_type": "Sea Shipment",
                "job_no": self.name
            })
            
            if not existing_job_ref:
                # Create Job Number
                job_ref = frappe.new_doc("Job Number")
                job_ref.job_type = "Sea Shipment"
                job_ref.job_no = self.name
                job_ref.company = self.company
                job_ref.branch = self.branch
                job_ref.cost_center = self.cost_center
                job_ref.profit_center = self.profit_center
                # Leave recognition_date blank - will be filled in separate function
                # Use sea shipment's booking_date instead
                job_ref.job_open_date = self.booking_date
                job_ref.insert(ignore_permissions=True)
                
                # Set the job_number field
                self.job_number = job_ref.name
                
                frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))
                
                # Sync to related Sea Booking if it exists
                self.sync_job_number_to_booking()
    
    def sync_job_number_to_booking(self):
        """Sync Job Number from Shipment to related Sea Booking"""
        if not self.job_number:
            return
        
        if not getattr(self, "sea_booking", None):
            return
        
        try:
            # Check if Booking exists and get its current Job Number
            booking_jcn = frappe.db.get_value("Sea Booking", self.sea_booking, "job_number")
            
            # Update Booking if it doesn't have a Job Number or if it's different
            if booking_jcn != self.job_number:
                frappe.db.set_value("Sea Booking", self.sea_booking, "job_number", self.job_number)
                frappe.db.commit()
        except Exception as e:
            # Log error but don't fail the shipment save
            frappe.log_error(
                f"Error syncing Job Number to Sea Booking {self.sea_booking}: {str(e)}",
                "Job Number Sync Error"
            )

    def validate_required_fields_for_submit(self):
        """Enforce party/routing/booking links when submitting (draft saves may omit them)."""
        if not self.booking_date:
            frappe.throw(_("Booking Date is required"))
        
        if not self.sea_booking:
            frappe.throw(_("Sea Booking is required. Shipments can only be created by converting a Sea Booking."))
        
        if not self.shipper:
            frappe.throw(_("Shipper is required"))
        
        if not self.consignee:
            frappe.throw(_("Consignee is required"))
        
        if not self.origin_port:
            frappe.throw(_("Origin Port is required"))
        
        if not self.destination_port:
            frappe.throw(_("Destination Port is required"))
        
        if not self.direction:
            frappe.throw(_("Direction is required"))
        
        if not self.local_customer:
            frappe.throw(_("Local Customer is required for billing"))
        
        # Shipping line should be required unless master_bill is set
        if not self.shipping_line and not self.master_bill:
            frappe.throw(_("Shipping Line is required (or link a Master Bill)"))
    
    def validate_dates(self):
        """Validate date logic for Sea Shipment"""
        from logistics.utils.validation_user_messages import (
            atd_ata_freight_invalid_message,
            atd_ata_freight_title,
            etd_eta_freight_invalid_message,
            etd_eta_freight_title,
        )

        throw_if_left_date_after_right(
            self.etd, self.eta, etd_eta_freight_invalid_message, etd_eta_freight_title
        )
        throw_if_left_date_after_right(
            self.atd, self.ata, atd_ata_freight_invalid_message, atd_ata_freight_title
        )
        
        # Warn if booking date is in the future (only once per document lifecycle)
        if self.booking_date and is_future_date(self.booking_date):
            # Use a flag to prevent duplicate messages during insert/save
            if not hasattr(self, '_booking_date_warning_shown'):
                from logistics.utils.validation_user_messages import (
                    booking_date_future_warning_message,
                    booking_date_future_warning_title,
                )

                frappe.msgprint(
                    booking_date_future_warning_message(),
                    indicator="orange",
                    title=booking_date_future_warning_title(),
                )
                self._booking_date_warning_shown = True
    
    def validate_weight_volume(self):
        """Validate weight and volume for Sea Shipment"""
        # Weight and volume should be positive numbers
        if self.total_weight and self.total_weight <= 0:
            frappe.throw(_("Weight must be greater than zero"))
        
        if self.total_volume and self.total_volume <= 0:
            frappe.throw(_("Volume must be greater than zero"))
        
        # Chargeable weight should be >= actual weight
        if self.total_weight and self.chargeable:
            if self.chargeable < self.total_weight:
                frappe.msgprint(_("Chargeable weight ({0}) is less than actual weight ({1})").format(
                    self.chargeable, self.total_weight
                ), indicator="orange")
    
    def validate_packages(self):
        """Validate packages for Sea Shipment"""
        # If packages exist, validate them
        if hasattr(self, 'packages') and self.packages:
            total_package_weight = sum(flt(p.weight or 0) for p in self.packages)
            total_package_volume = sum(flt(p.volume or 0) for p in self.packages)
            
            # Check if package weights match total weight (with tolerance)
            if self.total_weight and total_package_weight > 0:
                weight_diff = abs(total_package_weight - flt(self.total_weight))
                if weight_diff > 0.01:  # Allow 0.01 kg tolerance
                    frappe.msgprint(_("Package weights ({0} kg) do not match total weight ({1} kg)").format(
                        total_package_weight, self.total_weight
                    ), indicator="orange")
            
            # Check if package volumes match total volume (with tolerance)
            if self.total_volume and total_package_volume > 0:
                volume_diff = abs(total_package_volume - flt(self.total_volume))
                if volume_diff > 0.01:  # Allow 0.01 cbm tolerance
                    frappe.msgprint(_("Package volumes ({0} cbm) do not match total volume ({1} cbm)").format(
                        total_package_volume, self.total_volume
                    ), indicator="orange")
            
            # Validate each package has commodity
            for i, package in enumerate(self.packages, 1):
                if not package.commodity:
                    frappe.msgprint(_("Package {0}: Commodity is not specified").format(i), indicator="orange")
    
    def validate_containers(self):
        """Validate containers for Sea Shipment"""
        # If containers exist, validate them
        if hasattr(self, 'containers') and self.containers:
            # Validate container count matches total
            container_count = len(self.containers)
            if self.total_containers and container_count != flt(self.total_containers):
                frappe.msgprint(_("Container count ({0}) does not match total containers ({1})").format(
                    container_count, self.total_containers
                ), indicator="orange")
            
            # Validate each container has required fields and ISO 6346 format
            from logistics.utils.container_validation import (
                validate_container_number,
                get_strict_validation_setting,
            )
            from logistics.container_management.api import sea_container_row_field_to_equipment_number

            strict = get_strict_validation_setting()
            seen = {}
            for i, container in enumerate(self.containers, 1):
                if not container.type:
                    frappe.msgprint(_("Container {0}: Container Type is required").format(i), indicator="orange")

                if container.container_no:
                    equip = sea_container_row_field_to_equipment_number(container.container_no)
                    valid, err = validate_container_number(equip, strict=strict)
                    if not valid:
                        frappe.throw(
                            _("Container {0}: {1}").format(i, err),
                            title=_("Invalid Container Number")
                        )
                    # In-table duplicate: same container number must not appear on multiple rows
                    if equip in seen:
                        frappe.throw(
                            _("Duplicate container number in this document: {0} appears on row {1} and row {2}.").format(
                                equip, seen[equip], i
                            ),
                            title=_("Duplicate Container Numbers"),
                        )
                    seen[equip] = i
    
    def validate_duplicates(self):
        """Check for duplicate Sea Shipments based on identifying fields"""
        # Build filter to exclude current document (works for both new and existing)
        name_filter = {}
        if self.name:
            name_filter = {"name": ["!=", self.name]}
        
        # Check for duplicate House BL number
        if getattr(self, "house_bl", None):
            filters = {
                "house_bl": self.house_bl,
                "docstatus": ["!=", 2]  # Exclude cancelled documents
            }
            filters.update(name_filter)
            existing = frappe.db.exists("Sea Shipment", filters)
            if existing:
                frappe.throw(
                    _("A Sea Shipment with House BL '{0}' already exists: {1}").format(
                        self.house_bl, existing
                    ),
                    title=_("Duplicate House BL")
                )
        
        # Check for duplicate Sea Booking reference
        if getattr(self, "sea_booking", None):
            filters = {
                "sea_booking": self.sea_booking,
                "docstatus": ["!=", 2]
            }
            filters.update(name_filter)
            existing = frappe.db.get_value("Sea Shipment", filters, "name")
            if existing:
                frappe.throw(
                    _("Sea Booking '{0}' is already linked to another Sea Shipment: {1}").format(
                        self.sea_booking, existing
                    ),
                    title=_("Duplicate Sea Booking Reference")
                )
        
        # Check for duplicate container numbers (allow reuse when other shipment is submitted and container returned)
        if hasattr(self, "containers") and self.containers:
            from logistics.container_management.api import (
                expand_sea_container_no_for_sql_in,
                sea_container_row_field_to_equipment_number,
            )

            container_numbers = []
            for c in self.containers:
                cn = getattr(c, "container_no", None)
                if cn:
                    container_numbers.extend(expand_sea_container_no_for_sql_in(cn))
            container_numbers = list(set(container_numbers))
            if container_numbers:
                if self.name:
                    candidates = frappe.db.sql("""
                        SELECT DISTINCT ss.name, ss.docstatus, sfc.container_no
                        FROM `tabSea Shipment` ss
                        INNER JOIN `tabSea Freight Containers` sfc ON sfc.parent = ss.name
                        WHERE sfc.container_no IN %(container_numbers)s
                        AND ss.name != %(shipment_name)s
                        AND ss.docstatus != 2
                    """, {
                        "container_numbers": container_numbers,
                        "shipment_name": self.name
                    }, as_dict=True)
                else:
                    candidates = frappe.db.sql("""
                        SELECT DISTINCT ss.name, ss.docstatus, sfc.container_no
                        FROM `tabSea Shipment` ss
                        INNER JOIN `tabSea Freight Containers` sfc ON sfc.parent = ss.name
                        WHERE sfc.container_no IN %(container_numbers)s
                        AND ss.docstatus != 2
                    """, {
                        "container_numbers": container_numbers
                    }, as_dict=True)
                # Block only when container is not returned: draft always blocks; submitted blocks unless returned
                existing_containers = [
                    c for c in candidates
                    if c.docstatus == 0 or not self._container_returned_for_shipment(c.container_no, c.name)
                ]
                if existing_containers:
                    container_list = ", ".join(
                        sorted(
                            set(
                                sea_container_row_field_to_equipment_number(x.container_no)
                                for x in existing_containers
                                if x.container_no
                            )
                        )
                    )
                    shipment_list = ", ".join(set([c.name for c in existing_containers]))
                    frappe.throw(
                        _("Container number(s) {0} are already used in Sea Shipment(s): {1}").format(
                            container_list, shipment_list
                        ),
                        title=_("Duplicate Container Numbers")
                    )
        
        # Check for duplicate based on key identifying fields combination
        # This is a softer check - it warns but doesn't block
        if (getattr(self, "shipper", None) and 
            getattr(self, "consignee", None) and 
            getattr(self, "origin_port", None) and 
            getattr(self, "destination_port", None) and 
            getattr(self, "booking_date", None)):
            
            filters = {
                "shipper": self.shipper,
                "consignee": self.consignee,
                "origin_port": self.origin_port,
                "destination_port": self.destination_port,
                "booking_date": self.booking_date,
                "docstatus": ["!=", 2]
            }
            filters.update(name_filter)
            existing = frappe.db.get_value("Sea Shipment", filters, "name")
            
            if existing:
                # Show warning but allow save (user can override if needed)
                frappe.msgprint(
                    _("Warning: A similar Sea Shipment already exists ({0}) with the same Shipper, Consignee, Ports, and Booking Date. Please verify this is not a duplicate.").format(
                        existing
                    ),
                    indicator="orange",
                    title=_("Possible Duplicate")
                )

    def _container_returned_for_shipment(self, container_no, other_shipment_name):
        """
        Return True if the container is considered returned so reuse on another shipment is allowed.
        When the other shipment is submitted, we allow reuse if the container has been returned
        (Container return_status/status or that shipment's shipping_status indicates returned).
        """
        if not container_no:
            return False
        try:
            from logistics.container_management.api import (
                container_row_indicates_empty_returned,
                is_container_management_enabled,
            )
            if is_container_management_enabled() and container_row_indicates_empty_returned(container_no):
                return True
        except Exception:
            pass
        # Fallback: use the other shipment's job/shipping status
        row = frappe.db.get_value(
            "Sea Shipment",
            other_shipment_name,
            ["shipping_status", "job_status"],
            as_dict=True,
        )
        if not row:
            return False
        if (row.get("job_status") or "") in ("Completed", "Closed", "Cancelled"):
            return True
        return (row.get("shipping_status") or "") in ("Empty Container Returned", "Closed")
    
    def validate_master_bill(self):
        """Validate Master Bill if linked"""
        if self.master_bill:
            # Validate master bill exists
            if not frappe.db.exists("Master Bill", self.master_bill):
                frappe.throw(_("Master Bill {0} does not exist").format(self.master_bill))
            
            # Get master bill document
            master_bill = frappe.get_doc("Master Bill", self.master_bill)
            
            # Validate vessel and voyage match if both are set (use getattr in case fields are not on doctype)
            vessel = getattr(self, "vessel", None)
            voyage_no = getattr(self, "voyage_no", None)
            if vessel and master_bill.vessel:
                if vessel != master_bill.vessel:
                    frappe.msgprint(_("Vessel ({0}) does not match Master Bill vessel ({1})").format(
                        vessel, master_bill.vessel
                    ), indicator="orange")
            
            if voyage_no and master_bill.voyage_no:
                if voyage_no != master_bill.voyage_no:
                    frappe.msgprint(_("Voyage No ({0}) does not match Master Bill voyage ({1})").format(
                        voyage_no, master_bill.voyage_no
                    ), indicator="orange")
            
            # Validate ports match if both are set
            if self.origin_port and master_bill.origin_cto:
                # Note: Master Bill uses origin_cto, origin_cfs, origin_cy - we should check if any match
                pass  # This could be enhanced based on business requirements
            
            if self.destination_port and master_bill.destination_cto:
                # Note: Master Bill uses destination_cto, destination_cfs, destination_cy - we should check if any match
                pass  # This could be enhanced based on business requirements
            
            # Validate shipping line matches
            if self.shipping_line and master_bill.shipping_line:
                if self.shipping_line != master_bill.shipping_line:
                    frappe.msgprint(_("Shipping Line ({0}) does not match Master Bill shipping line ({1})").format(
                        self.shipping_line, master_bill.shipping_line
                    ), indicator="orange")

    def _get_mbl_row(self):
        """Single-row cache from Master Bill for virtual MBL fields."""
        key = self.get("master_bill")
        if not key:
            self._sea_mbl_row_cache_key = None
            self._sea_mbl_row_cache = None
            return None
        if getattr(self, "_sea_mbl_row_cache_key", None) != key:
            self._sea_mbl_row_cache = frappe.db.get_value(
                "Master Bill",
                key,
                [src for _, src in _MBL_VIRTUAL_FIELD_SOURCES],
                as_dict=True,
            )
            self._sea_mbl_row_cache_key = key
        return self._sea_mbl_row_cache

    @frappe.whitelist()
    def get_dashboard_html(self):
        """Generate HTML for Dashboard tab: tabbed layout with map, milestones, alerts."""
        try:
            from logistics.document_management.logistics_form_dashboard import (
                build_sea_shipment_dashboard_config,
                render_logistics_form_dashboard_html,
            )
            from logistics.utils.sales_quote_validity import get_sales_quote_validity_dashboard_html

            dash = render_logistics_form_dashboard_html(
                self, build_sea_shipment_dashboard_config(self)
            )
            return get_sales_quote_validity_dashboard_html(self) + dash
        except Exception as e:
            frappe.log_error(f"Sea Shipment get_dashboard_html: {str(e)}", "Sea Shipment Dashboard")
            return "<div class='alert alert-warning'>Error loading dashboard.</div>"

    def _auto_populate_routing_from_ports(self):
        """Auto-populate routing legs from origin/destination ports when empty."""
        routing_legs = getattr(self, "routing_legs", None) or []
        if routing_legs or not self.origin_port or not self.destination_port:
            return
        self._append_main_routing_leg()

    def _append_main_routing_leg(self):
        """Append a single Main leg from origin_port to destination_port."""
        if not self.origin_port or not self.destination_port:
            return
        leg_mode = getattr(self, "load_type", None)
        if leg_mode and not frappe.db.exists("Load Type", leg_mode):
            leg_mode = None
        leg = {
            "leg_order": 1,
            "mode": leg_mode,
            "type": "Main",
            "status": "Planned",
            "load_port": self.origin_port,
            "discharge_port": self.destination_port,
            "etd": self.etd,
            "eta": self.eta,
        }
        self.append("routing_legs", leg)

    @frappe.whitelist()
    def populate_routing_from_ports(self):
        """Manually populate routing legs from origin/destination ports. Replaces existing legs with a single Main leg."""
        if not self.origin_port or not self.destination_port:
            return {"message": _("Set Origin Port and Destination Port first.")}
        # Clear existing legs and add single Main leg
        self.set("routing_legs", [])
        self._append_main_routing_leg()
        self.save()
        return {"message": _("Routing leg created from origin to destination.")}

    def format_datetime(self, dt):
        """Format datetime for display"""
        if not dt:
            return None
        try:
            from frappe.utils import format_datetime
            return format_datetime(dt, "dd-MM-yyyy HH:mm")
        except Exception:
            return str(dt)
    
    def check_delays(self):
        """Check for delays in milestones and update delay tracking fields"""
        try:
            from frappe.utils import now_datetime
            
            # Get milestones from child table
            milestones = list(self.get("milestones") or [])
            
            delay_count = 0
            has_delays = False
            
            for milestone in milestones:
                if milestone.planned_end:
                    planned_end = frappe.utils.get_datetime(milestone.planned_end)
                    now = now_datetime()
                    
                    # Check if milestone is delayed
                    if not milestone.actual_end:
                        # Milestone not completed yet - check if planned end has passed
                        if planned_end < now:
                            delay_count += 1
                            has_delays = True
                    else:
                        # Milestone completed - check if it was completed late
                        actual_end = frappe.utils.get_datetime(milestone.actual_end)
                        if actual_end > planned_end:
                            delay_count += 1
                            has_delays = True
            
            # Update delay tracking fields
            self.has_delays = 1 if has_delays else 0
            self.delay_count = delay_count
            self.last_delay_check = now_datetime()
            
            # Send alert if delays detected and alert not sent yet
            settings = frappe.get_single("Sea Freight Settings")
            if has_delays and not self.delay_alert_sent and getattr(settings, "enable_delay_alerts", 1):
                self.send_delay_alert()
                self.delay_alert_sent = 1
                
        except Exception as e:
            frappe.log_error(f"Error checking delays for Sea Shipment {self.name}: {str(e)}", "Sea Shipment Delay Check")
    
    def calculate_penalties(self):
        """Calculate detention and demurrage penalties (aggregated per container row when present)."""
        try:
            from frappe.utils import now_datetime, getdate
            from logistics.sea_freight.penalty_utils import compute_penalty_totals_for_sea_shipment

            settings = frappe.get_single("Sea Freight Settings")
            today = getdate(now_datetime())

            totals = compute_penalty_totals_for_sea_shipment(self, settings, today)

            self.detention_days = totals["detention_days"]
            self.demurrage_days = totals["demurrage_days"]
            self.estimated_penalty_amount = totals["estimated_penalty_amount"]
            self.free_time_days = totals["free_time_days_summary"]
            self.has_penalties = 1 if (self.detention_days > 0 or self.demurrage_days > 0) else 0

            self.last_penalty_check = now_datetime()

            if self.has_penalties and not self.penalty_alert_sent and getattr(settings, "enable_penalty_alerts", 1):
                self.send_penalty_alert()
                self.penalty_alert_sent = 1

        except Exception as e:
            frappe.log_error(f"Error calculating penalties for Sea Shipment {self.name}: {str(e)}", "Sea Shipment Penalty Calculation")

    def send_delay_alert(self):
        """Send delay alert notification"""
        try:
            if not self.has_delays:
                return
            
            # Create notification
            notification_message = _("Sea Shipment {0} has {1} delayed milestone(s)").format(
                self.name, self.delay_count
            )
            
            # Get users to notify
            users_to_notify = self._get_users_to_notify()
            
            for user in users_to_notify:
                frappe.publish_realtime(
                    event='sea_shipment_delayed',
                    message={
                        'shipment': self.name,
                        'delay_count': self.delay_count,
                        'message': notification_message,
                        'severity': 'critical',  # Delay incurred = Red
                    },
                    user=user
                )
                
                # Create notification document
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Sea Shipment",
                    "document_name": self.name,
                    "subject": _("Delay Alert: Sea Shipment {0}").format(self.name),
                    "email_content": notification_message
                }).insert(ignore_permissions=True)
            
            frappe.msgprint(_("Delay alert sent for {0} delayed milestone(s)").format(self.delay_count),
                indicator="red")
            
        except Exception as e:
            frappe.log_error(f"Error sending delay alert: {str(e)}", "Sea Shipment Delay Alert")
    
    def send_penalty_alert(self):
        """Send penalty alert notification"""
        try:
            if not self.has_penalties:
                return
            
            # Create notification
            notification_message = _("Sea Shipment {0} has penalties: Detention {1} days, Demurrage {2} days. Estimated amount: {3}").format(
                self.name,
                self.detention_days or 0,
                self.demurrage_days or 0,
                frappe.utils.fmt_money(self.estimated_penalty_amount or 0)
            )
            
            # Get users to notify
            users_to_notify = self._get_users_to_notify()
            
            for user in users_to_notify:
                frappe.publish_realtime(
                    event='sea_shipment_penalty',
                    message={
                        'shipment': self.name,
                        'detention_days': self.detention_days or 0,
                        'demurrage_days': self.demurrage_days or 0,
                        'estimated_amount': self.estimated_penalty_amount or 0,
                        'message': notification_message,
                        'severity': 'critical',  # Penalty incurred = Red
                    },
                    user=user
                )
                
                # Create notification document
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Sea Shipment",
                    "document_name": self.name,
                    "subject": _("Penalty Alert: Sea Shipment {0}").format(self.name),
                    "email_content": notification_message
                }).insert(ignore_permissions=True)
            
            frappe.msgprint(_("Penalty alert sent. Estimated penalty: {0}").format(
                frappe.utils.fmt_money(self.estimated_penalty_amount or 0)
            ), indicator="red")
            
        except Exception as e:
            frappe.log_error(f"Error sending penalty alert: {str(e)}", "Sea Shipment Penalty Alert")
    
    def _get_users_to_notify(self):
        """Get list of users who should be notified about this shipment"""
        users = []
        
        try:
            # Add owner and modified_by
            if self.owner:
                users.append(self.owner)
            if self.modified_by:
                users.append(self.modified_by)
            
            # Add users from local_customer
            if self.local_customer:
                customer_doc = frappe.get_doc("Customer", self.local_customer)
                # Get users linked to customer (if any)
                # This could be extended based on business requirements
            
            # Add users from handling branch/department
            if self.handling_branch:
                # Get users from branch (if any user assignment exists)
                pass
            
            # Remove duplicates
            users = list(set(users))
            
        except Exception as e:
            frappe.log_error(f"Error getting users to notify: {str(e)}")
        
        return users
    
    def _send_impending_penalty_alert(self, days_since_discharge, free_time_days):
        """Send alert for impending penalty"""
        try:
            remaining_days = free_time_days - days_since_discharge
            
            notification_message = _("Sea Shipment {0} is approaching penalty threshold. {1} days remaining before penalties apply.").format(
                self.name, remaining_days
            )
            
            users_to_notify = self._get_users_to_notify()
            
            for user in users_to_notify:
                frappe.publish_realtime(
                    event='sea_shipment_impending_penalty',
                    message={
                        'shipment': self.name,
                        'remaining_days': remaining_days,
                        'message': notification_message
                    },
                    user=user
                )
                
                # Create notification document
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Sea Shipment",
                    "document_name": self.name,
                    "subject": _("Impending Penalty Alert: Sea Shipment {0}").format(self.name),
                    "email_content": notification_message
                }).insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error sending impending penalty alert: {str(e)}", "Sea Shipment Impending Penalty Alert")

    @frappe.whitelist()
    def populate_charges_from_sales_quote(self):
        """Populate charges from Sales Quote Sea Freight"""
        if not self.sales_quote:
            frappe.throw(_("Sales Quote is not set for this Sea Shipment"))
        
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
            
            from logistics.utils.charge_service_type import (
                filter_sales_quote_charge_rows_for_operational_doc,
                sales_quote_charge_filters,
            )

            sq_doc = frappe.get_doc("Sales Quote", self.sales_quote)
            filters = sales_quote_charge_filters(self, sq_doc)

            # Get from Sales Quote Charge (filtered) or Sales Quote Sea Freight (legacy)
            from logistics.utils.sales_quote_charge_parameters import (
                SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
                filter_fields_existing_in_doctype,
            )

            charge_fields = [
                "item_code", "item_name", "revenue_calculation_method", "calculation_method", "uom", "currency",
                "unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
                "maximum_charge", "base_amount", "estimated_revenue", "service_type",
            ] + list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
            sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
            sales_quote_sea_freight_records = frappe.get_all(
                "Sales Quote Charge",
                filters=filters,
                fields=sqc_fields,
                order_by="idx"
            )
            if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
                legacy_wanted = charge_fields + ["minimum_unit_rate", "base_quantity"]
                legacy_fields = filter_fields_existing_in_doctype("Sales Quote Sea Freight", legacy_wanted)
                sales_quote_sea_freight_records = frappe.get_all(
                    "Sales Quote Sea Freight",
                    filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
                    fields=legacy_fields,
                    order_by="idx"
                )
            sales_quote_sea_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
                self, sales_quote_sea_freight_records
            )
            
            if not sales_quote_sea_freight_records:
                frappe.msgprint(
                    f"No Sea Freight charges found in Sales Quote: {self.sales_quote}",
                    title="No Charges Found",
                    indicator="orange"
                )
                from logistics.utils.sync_internal_job_details_from_sales_quote import sync_internal_job_details_from_sales_quote

                sync_internal_job_details_from_sales_quote(self, sq_doc)
                self.save(ignore_permissions=True)
                return
            
            # Import the mapping function from Sales Quote
            from logistics.pricing_center.doctype.sales_quote.sales_quote import _map_sales_quote_sea_freight_to_charge
            
            # Map and populate charges
            charges_added = 0
            for sqsf_record in sales_quote_sea_freight_records:
                charge_row = _map_sales_quote_sea_freight_to_charge(sqsf_record, self)
                if charge_row:
                    self.append("charges", charge_row)
                    charges_added += 1

            from logistics.utils.sync_internal_job_details_from_sales_quote import sync_internal_job_details_from_sales_quote

            sync_internal_job_details_from_sales_quote(self, sq_doc)

            self.save(ignore_permissions=True)
            
            if charges_added > 0:
                frappe.msgprint(
                    f"Successfully populated {charges_added} charges from Sales Quote",
                    title="Charges Updated",
                    indicator="green"
                )
            
            return {
                "success": True,
                "message": f"Successfully populated {charges_added} charges",
                "charges_added": charges_added
            }
            
        except Exception as e:
            frappe.log_error(
                f"Error populating charges from Sales Quote: {str(e)}",
                "Sea Shipment - Populate Charges Error"
            )
            frappe.throw(_("Error populating charges: {0}").format(str(e)))


for _fname, _src in _MBL_VIRTUAL_FIELD_SOURCES:
    setattr(
        SeaShipment,
        _fname,
        property(lambda self, s=_src: (self._get_mbl_row() or {}).get(s)),
    )


@frappe.whitelist()
def get_master_bill_virtuals(master_bill=None):
    """Desk: values for virtual MBL fields when Master BL link changes (no DB columns)."""
    if not master_bill:
        return {fk: None for fk, _ in _MBL_VIRTUAL_FIELD_SOURCES}
    row = frappe.db.get_value(
        "Master Bill",
        master_bill,
        [src for _, src in _MBL_VIRTUAL_FIELD_SOURCES],
        as_dict=True,
    )
    row = row or {}
    return {fk: row.get(src) for fk, src in _MBL_VIRTUAL_FIELD_SOURCES}


@frappe.whitelist()
def recalculate_all_charges(docname):
	"""Recalculate all charges based on current Sea Shipment data."""
	shipment = frappe.get_doc("Sea Shipment", docname)
	if not shipment.charges:
		return {"success": False, "message": _("No charges found to recalculate")}
	try:
		charges_recalculated = 0
		for charge in shipment.charges:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=shipment)
				charges_recalculated += 1
		shipment.save()
		return {
			"success": True,
			"message": _("Successfully recalculated {0} charges").format(charges_recalculated),
			"charges_recalculated": charges_recalculated,
		}
	except Exception as e:
		frappe.log_error(str(e), "Sea Shipment - Recalculate Charges Error")
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


@frappe.whitelist()
def post_standard_costs(docname):
	"""Post standard costs for Sea Shipment charges. No-op if charges do not support standard costs."""
	shipment = frappe.get_doc("Sea Shipment", docname)
	posted = 0
	for ch in (shipment.charges or []):
		if getattr(ch, "total_standard_cost", None) and flt(ch.total_standard_cost) > 0 and not getattr(ch, "standard_cost_posted", False):
			if frappe.get_meta(ch.doctype).get_field("standard_cost_posted"):
				ch.standard_cost_posted = 1
				ch.standard_cost_posted_at = frappe.utils.now()
				posted += 1
	if posted > 0:
		shipment.save()
	return {"message": _("Posted {0} standard cost(s).").format(posted) if posted else _("No standard costs to post.")}


@frappe.whitelist()
def create_sales_invoice(shipment_name, posting_date, customer, tax_category=None, invoice_type=None):
    """Create Sales Invoice from Sea Shipment"""
    if not shipment_name:
        frappe.throw(_("Sea Shipment name is required."))
    
    shipment = frappe.get_doc('Sea Shipment', shipment_name)
    
    if shipment.docstatus != 1:
        frappe.throw(_("Sea Shipment must be submitted to create Sales Invoice."))

    # Fetch naming series from the Invoice Type doctype
    naming_series = None
    if invoice_type:
        naming_series = frappe.db.get_value("Invoice Type", invoice_type, "naming_series")

    invoice = frappe.new_doc('Sales Invoice')
    invoice.customer = customer
    invoice.company = shipment.company
    invoice.posting_date = posting_date
    invoice.tax_category = tax_category or None
    invoice.naming_series = naming_series or None
    invoice.invoice_type = invoice_type or None  # Optional: standard field if exists
    invoice.custom_invoice_type = invoice_type or None  # Custom field explicitly filled
    
    # Add accounting fields from Sea Shipment
    if getattr(shipment, "branch", None):
        invoice.branch = shipment.branch
    if getattr(shipment, "cost_center", None):
        invoice.cost_center = shipment.cost_center
    if getattr(shipment, "profit_center", None):
        invoice.profit_center = shipment.profit_center
    
    # Add reference to Job Number if it exists
    if getattr(shipment, "job_number", None):
        invoice.job_number = shipment.job_number
    
    # Add reference in remarks
    base_remarks = invoice.remarks or ""
    note = _("Auto-created from Sea Shipment {0}").format(shipment.name)
    invoice.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    # Add items from charges (bill_to on row, else shipment local_customer, else dialog customer)
    from logistics.utils.charges_calculation import get_charge_bill_to_customers

    def _si_customers_for_charge(ch):
        billed = get_charge_bill_to_customers(ch)
        if billed:
            return billed
        if getattr(shipment, "local_customer", None):
            return [shipment.local_customer]
        return [customer]

    from logistics.utils.freight_95_5 import (
        apply_freight_95_post_missing_values,
        build_sales_invoice_item_payloads_for_charge,
    )

    si_item_meta = frappe.get_meta("Sales Invoice Item")
    freight_95_line_indices = []
    for charge in shipment.charges or []:
        if customer not in _si_customers_for_charge(charge):
            continue
        if invoice_type and getattr(charge, "invoice_type", None) != invoice_type:
            continue
        selling_rate = (
            flt(getattr(charge, "selling_amount", None))
            or flt(getattr(charge, "base_amount", None))
            or flt(getattr(charge, "estimated_revenue", None))
        )
        item_code = getattr(charge, "item_code", None) or getattr(charge, "charge_item", None)
        if not item_code:
            continue
        item_name = getattr(charge, "item_name", None) or getattr(charge, "charge_name", None) or item_code
        description = getattr(charge, "charge_description", None) or getattr(charge, "description", None)
        job_ref = getattr(shipment, "job_number", None)
        payloads, clear_rel = build_sales_invoice_item_payloads_for_charge(
            charge,
            flt(selling_rate),
            item_code=item_code,
            item_name=item_name,
            description=description,
            job_type="Sea Shipment",
            company=shipment.company,
            currency=getattr(charge, "selling_currency", None) or getattr(charge, "currency", None),
            cost_center=getattr(shipment, "cost_center", None),
            profit_center=getattr(shipment, "profit_center", None),
            job_ref=job_ref,
            si_item_meta=si_item_meta,
            reference_doctype="Sea Shipment",
            reference_name=shipment.name,
        )
        start_idx = len(invoice.items)
        for p in payloads:
            invoice.append("items", p)
        for rel in clear_rel:
            freight_95_line_indices.append(start_idx + rel)

    if not invoice.items:
        frappe.throw(_("No matching charges found for the selected customer and invoice type."))

    invoice.set_missing_values()
    apply_freight_95_post_missing_values(invoice, freight_95_line_indices)
    invoice.insert(ignore_permissions=True)
    
    # Update Sea Shipment with Sales Invoice reference and lifecycle
    from frappe.utils import today
    updates = {"sales_invoice": invoice.name, "date_sales_invoice_requested": today()}
    for k, v in updates.items():
        if frappe.get_meta("Sea Shipment").get_field(k):
            frappe.db.set_value("Sea Shipment", shipment.name, k, v, update_modified=False)
    
    return invoice

@frappe.whitelist()
def compute_chargeable(self):
    """Calculate chargeable weight based on volume and weight using Sea Freight Settings.
    Respects chargeable_weight_calculation setting: 'Actual Weight', 'Volume Weight', or 'Higher of Both'.
    """
    if not self.total_volume and not self.total_weight:
        self.chargeable = 0
        return
    
    # Get volume to weight divisor and calculation method from Sea Freight Settings
    divisor = _get_volume_to_weight_divisor()
    calculation_method = _get_chargeable_weight_calculation_method()
    
    # Calculate volume weight
    volume_weight = 0
    if self.total_volume and divisor:
        # Convert volume from m³ to cm³, then divide by divisor
        # Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
        volume_weight = flt(self.total_volume) * (1000000.0 / divisor)
    
    # Get actual weight
    actual_weight = flt(self.total_weight) or 0
    
    # Calculate chargeable weight based on calculation method
    if calculation_method == "Actual Weight":
        # Use only actual weight
        self.chargeable = actual_weight
    elif calculation_method == "Volume Weight":
        # Use only volume weight
        self.chargeable = volume_weight
    else:  # "Higher of Both" (default)
        # Use the higher of actual weight or volume weight
        if actual_weight > 0 and volume_weight > 0:
            self.chargeable = max(actual_weight, volume_weight)
        elif actual_weight > 0:
            self.chargeable = actual_weight
        elif volume_weight > 0:
            self.chargeable = volume_weight
        else:
            self.chargeable = 0

def _get_volume_to_weight_divisor():
    """Get the volume to weight divisor from Sea Freight Settings.
    Converts volume_to_weight_factor (kg/m³) to divisor format.
    Formula: divisor = 1,000,000 / factor
    Example: factor = 1000 kg/m³ → divisor = 1000
    """
    try:
        settings = frappe.get_single("Sea Freight Settings")
        factor = getattr(settings, "volume_to_weight_factor", None)
        if factor:
            # Convert factor (kg/m³) to divisor: divisor = 1,000,000 / factor
            return flt(1000000.0 / flt(factor))
    except Exception:
        pass
    # Default to 1000 (equivalent to 1000 kg/m³ factor, common sea freight standard)
    return 1000.0

def _get_chargeable_weight_calculation_method():
    """Get the chargeable weight calculation method from Sea Freight Settings.
    Returns: 'Actual Weight', 'Volume Weight', or 'Higher of Both' (default)
    """
    try:
        settings = frappe.get_single("Sea Freight Settings")
        method = getattr(settings, "chargeable_weight_calculation", None)
        if method in ["Actual Weight", "Volume Weight", "Higher of Both"]:
            return method
    except Exception:
        pass
    # Default to "Higher of Both" (common sea freight standard)
    return "Higher of Both"

def create_job_number_for_shipment(
	shipment_name,
	company,
	branch=None,
	cost_center=None,
	profit_center=None,
	booking_date=None,
):
	"""Deferred: create Job Number for Sea Shipment after commit (avoids 'not found' during conversion)."""
	if not frappe.db.exists("Sea Shipment", shipment_name):
		return
	if frappe.db.get_value("Sea Shipment", shipment_name, "job_number"):
		return
	if frappe.db.get_value("Job Number", {"job_type": "Sea Shipment", "job_no": shipment_name}):
		return
	job_ref = frappe.new_doc("Job Number")
	job_ref.job_type = "Sea Shipment"
	job_ref.job_no = shipment_name
	job_ref.company = company
	job_ref.branch = branch
	job_ref.cost_center = cost_center
	job_ref.profit_center = profit_center
	job_ref.job_open_date = booking_date
	job_ref.insert(ignore_permissions=True)
	frappe.db.set_value("Sea Shipment", shipment_name, "job_number", job_ref.name)
	
	# Sync to related Sea Booking if it exists
	sea_booking = frappe.db.get_value("Sea Shipment", shipment_name, "sea_booking")
	if sea_booking:
		booking_jcn = frappe.db.get_value("Sea Booking", sea_booking, "job_number")
		if booking_jcn != job_ref.name:
			frappe.db.set_value("Sea Booking", sea_booking, "job_number", job_ref.name)
	
	frappe.db.commit()


@frappe.whitelist()
def sea_shipment_exists(docname):
	"""Return True if the Sea Shipment exists. Used by client to poll before navigating so form load does not show 'not found'."""
	if not docname or docname == "new":
		return False
	return bool(frappe.db.exists("Sea Shipment", docname))
