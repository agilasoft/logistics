# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import math
import frappe
from frappe.exceptions import ValidationError
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, cstr, flt, now_datetime, getdate
from datetime import datetime, timedelta

from logistics.utils.consolidation_plan import (
	SEA_ALIGNMENT_DIALOG_FILTER_KEYS,
	assert_sea_consolidation_plan_requirements,
	assert_sea_plan_fields_for_filter_match,
	conflicting_submitted_sea_planning_elsewhere,
	prevent_consolidation_cargo_edit_when_planning_submitted,
	get_linked_sea_shipment_names_for_consolidation_tagging,
	get_previous_linked_sea_shipment_names_for_consolidation,
	get_sea_shipment_names_from_consolidation,
	get_sea_shipment_names_from_consolidation_cargo,
	get_strict_matching_sea_shipment_names,
	sea_alignment_plan_has_any_filter,
	sea_shipment_allowed_on_plan,
	sea_shipment_can_be_consolidated,
	validate_minimum_sea_consolidation_shipments,
	validate_minimum_sea_planning_shipments,
)
from logistics.utils.container_validation import normalize_container_number



def _consolidation_has_custom_allocation_charge(doc):
    """True when any consolidation charge uses Custom allocation for PI splits."""
    for ch in doc.get("consolidation_charges") or []:
        if (getattr(ch, "allocation_method", None) or "").strip() == "Custom":
            return True
    return False


def _custom_allocation_planning_rows(doc):
    """Planned shipment rows with a Sea Shipment link (Custom % lives on this table)."""
    return [
        r
        for r in (doc.get("consolidation_planning_lines") or [])
        if getattr(r, "sea_shipment", None)
    ]


class SeaConsolidation(Document):
    def validate(self):
        """Validate Sea Consolidation document"""
        from logistics.utils.charges_calculation import (
            clear_charge_resolution_parent,
            register_charge_resolution_parent,
        )

        register_charge_resolution_parent(self)
        try:
            self._prevent_planning_lines_edit_when_submitted()
            self._prevent_cargo_edit_when_planning_submitted()
            self.validate_dates()
            self.validate_route_consistency()
            self.validate_capacity_constraints()
            self.validate_attached_shipments_compatibility()
            self.validate_shipments_not_in_multiple_consolidations()
            self.calculate_consolidation_metrics()
            self.validate_dangerous_goods_compliance()
            self.validate_accounts()
            self.validate_packages()
            self.validate_containers()
            self.validate_duplicate_containers()
            self._validate_consolidation_planning_lines()
            self._rollup_is_high_value_from_shipments()
            assert_sea_consolidation_plan_requirements(self)
            self.validate_custom_cost_allocation_percentages(strict=False)
            self._sync_charges_with_parent_actuals()
    
        finally:
            clear_charge_resolution_parent(self)

    def _rollup_is_high_value_from_shipments(self):
        """Set is_high_value=1 if any linked Sea Shipment is tagged high value."""
        shipments = [
            getattr(r, "sea_shipment", None)
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "sea_shipment", None)
        ]
        if not shipments:
            return
        try:
            hv = frappe.db.get_all(
                "Sea Shipment",
                filters={"name": ["in", shipments], "is_high_value": 1},
                limit=1,
                pluck="name",
            )
        except Exception:
            return
        if hv:
            self.is_high_value = 1

    def _prevent_planning_lines_edit_when_submitted(self):
        """Planning lines are immutable while Planning Status is Submitted (until reset to draft)."""
        if getattr(self.flags, "ignore_planning_lines_lock", False):
            return
        if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
            return
        if getattr(frappe.flags, "in_import", False):
            return
        if self.is_new():
            return
        if (self.sea_planning_status or "Draft") != "Submitted":
            return
        prev = self.get_doc_before_save()
        if not prev:
            return

        def shipment_tuple(doc):
            return tuple(
                sorted(
                    getattr(r, "sea_shipment", None)
                    for r in (doc.consolidation_planning_lines or [])
                    if getattr(r, "sea_shipment", None)
                )
            )

        if shipment_tuple(prev) != shipment_tuple(self):
            frappe.throw(
                _(
                    "Planned shipments cannot be changed while planning status is Submitted. "
                    "Reset planned shipments to draft if you need to edit the list."
                ),
                title=_("Planning locked"),
            )

    def _prevent_cargo_edit_when_planning_submitted(self):
        prevent_consolidation_cargo_edit_when_planning_submitted(
            self, planning_status_field="sea_planning_status"
        )

    def _sync_charges_with_parent_actuals(self):
        if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
            return
        if getattr(self.flags, "ignore_charges_sync", False):
            return
        for charge in self.get("consolidation_charges") or []:
            if hasattr(charge, "calculate_charge_amount"):
                charge.calculate_charge_amount(parent_doc=self)

    def before_save(self):
        """Actions before saving the document"""
        self.update_consolidation_status()
        self.calculate_total_charges()
        self.optimize_consolidation_ratio()
        # Job Number will be created in after_insert method
    
    def after_insert(self):
        """Create Job Number after document is inserted"""
        self.create_job_number_if_needed()
        # Save the document to persist the job_number field
        if self.job_number:
            self.save(ignore_permissions=True)
        else:
            self._sync_house_bl_prefix_to_shipments()
        self.update_related_sea_shipments()

    def on_update(self):
        """Actions after document update"""
        self.update_related_sea_shipments()
        self._sync_house_bl_prefix_to_shipments()
        self.update_attached_shipments_table()
        self.send_consolidation_notifications()

    def before_submit(self):
        if not self.consolidation_packages and not self.consolidation_containers:
            frappe.throw(_("At least one package or container must be added to the consolidation"))
        if not self.consolidation_routes:
            frappe.throw(_("At least one route must be defined for the consolidation"))
        self.validate_containers_iso6346()
        validate_minimum_sea_consolidation_shipments(self)
        self.validate_custom_cost_allocation_percentages(strict=True)

        if get_sea_shipment_names_from_consolidation_cargo(self) and (self.sea_planning_status or "Draft") != "Submitted":
            frappe.throw(
                _("Submit the planned shipment list (Planning Status) before submitting the consolidation."),
                title=_("Planning required"),
            )
    
    def validate_containers_iso6346(self):
        """Validate container numbers per ISO 6346."""
        from logistics.utils.container_validation import validate_container_number, get_strict_validation_setting
        containers = getattr(self, "consolidation_containers", []) or []
        strict = get_strict_validation_setting()
        for i, c in enumerate(containers, 1):
            container_no = getattr(c, "container_number", None)
            if container_no and str(container_no).strip():
                valid, err = validate_container_number(container_no, strict=strict)
                if not valid:
                    frappe.throw(_("Container {0}: {1}").format(i, err), title=_("Invalid Container Number"))

    def validate_dates(self):
        """Validate date consistency"""
        if self.etd and self.eta:
            if self.eta < self.etd:
                frappe.throw(_("ETA cannot be earlier than ETD"))
        
        if self.consolidation_date:
            if self.etd and getdate(self.consolidation_date) > getdate(self.etd):
                frappe.throw(_("Consolidation date cannot be later than ETD"))
    
    def validate_route_consistency(self):
        """Validate route consistency and connectivity"""
        if len(self.consolidation_routes) > 1:
            for i, route in enumerate(self.consolidation_routes):
                if i > 0:
                    # Check if destination of previous route matches origin of current route
                    prev_route = self.consolidation_routes[i-1]
                    if prev_route.destination_port != route.origin_port:
                        frappe.throw(_("Route {0}: Origin port must match destination of previous route").format(i + 1))
    
    def validate_capacity_constraints(self):
        """Validate capacity constraints for all routes"""
        for i, route in enumerate(self.consolidation_routes, 1):
            if route.container_capacity and self.total_containers > route.container_capacity:
                frappe.throw(_("Route {0}: Total containers exceed container capacity").format(i))
            
            if route.cargo_capacity_kg and self.total_weight > route.cargo_capacity_kg:
                frappe.throw(_("Route {0}: Total weight exceeds cargo capacity").format(i))
            
            if route.cargo_capacity_volume and self.total_volume > route.cargo_capacity_volume:
                frappe.throw(_("Route {0}: Total volume exceeds cargo capacity").format(i))
    
    def validate_attached_shipments_compatibility(self):
        """Validate that attached Sea Shipments are compatible for consolidation"""
        if not self.consolidation_packages:
            return
        
        # Get all attached Sea Shipments
        attached_shipments = []
        for package in self.consolidation_packages:
            if package.sea_shipment:
                attached_shipments.append(package.sea_shipment)
        
        if not attached_shipments:
            return
        
        # Get shipment details
        shipments_data = frappe.get_all(
            "Sea Shipment",
            filters={"name": ["in", attached_shipments]},
            fields=["name", "origin_port", "destination_port", "direction"]
        )
        
        if not shipments_data:
            return
        
        # Check all shipments have same origin and destination ports
        first_shipment = shipments_data[0]
        for shipment in shipments_data[1:]:
            if shipment.origin_port != first_shipment.origin_port:
                frappe.throw(
                    _("Sea Shipment {0} has different origin port ({1}) than other shipments ({2}). All shipments in a consolidation must have the same origin and destination.").format(
                        shipment.name, shipment.origin_port, first_shipment.origin_port
                    ),
                    title=_("Consolidation Compatibility Error")
                )
            
            if shipment.destination_port != first_shipment.destination_port:
                frappe.throw(
                    _("Sea Shipment {0} has different destination port ({1}) than other shipments ({2}). All shipments in a consolidation must have the same origin and destination.").format(
                        shipment.name, shipment.destination_port, first_shipment.destination_port
                    ),
                    title=_("Consolidation Compatibility Error")
                )
            
            # Check direction compatibility
            if shipment.direction != first_shipment.direction:
                frappe.throw(
                    _("Sea Shipment {0} has different direction ({1}) than other shipments ({2}). All shipments in a consolidation must have the same direction.").format(
                        shipment.name, shipment.direction, first_shipment.direction
                    ),
                    title=_("Consolidation Compatibility Error")
                )
    
    def validate_shipments_not_in_multiple_consolidations(self):
        """Validate that Sea Shipments are not already in another consolidation"""
        if not self.consolidation_packages:
            return
        
        # Get all attached Sea Shipments
        attached_shipments = []
        for package in self.consolidation_packages:
            if package.sea_shipment:
                attached_shipments.append(package.sea_shipment)
        
        if not attached_shipments:
            return
        
        # Check if any of these shipments are already in another consolidation
        existing_consolidations = frappe.get_all(
            "Sea Consolidation Packages",
            filters={
                "sea_shipment": ["in", attached_shipments],
                "parent": ["!=", self.name]
            },
            fields=["parent", "sea_shipment"],
            group_by="sea_shipment"
        )
        
        if existing_consolidations:
            for consolidation in existing_consolidations:
                frappe.throw(
                    _("Sea Shipment {0} is already included in consolidation {1}. A shipment can only be in one consolidation at a time.").format(
                        consolidation.sea_shipment, consolidation.parent
                    ),
                    title=_("Consolidation Conflict Error")
                )
    
    def calculate_consolidation_metrics(self):
        """Calculate consolidation metrics"""
        packages = self.consolidation_packages or []
        containers = self.consolidation_containers or []

        if packages:
            self.total_packages = sum(package.package_count or 0 for package in packages)
            self.total_weight = sum(package.package_weight or 0 for package in packages)
            self.total_volume = sum(package.package_volume or 0 for package in packages)
        else:
            self.total_packages = 0
            self.total_weight = 0
            self.total_volume = 0

        self.total_containers = len(containers)
        if containers:
            container_weight = sum(container.weight_in_container or 0 for container in containers)
            container_volume = sum(container.volume_in_container or 0 for container in containers)
            self.total_weight = (self.total_weight or 0) + container_weight
            self.total_volume = (self.total_volume or 0) + container_volume
        
        # Calculate chargeable weight (higher of actual weight or volume weight)
        # For sea freight, volume weight factor is typically 1000 kg per m³
        volume_weight = self.total_volume * 1000 if self.total_volume else 0
        self.chargeable_weight = max(self.total_weight or 0, volume_weight)
        
        # Calculate consolidation ratio
        if self.total_weight and self.total_weight > 0:
            self.consolidation_ratio = (self.chargeable_weight / self.total_weight) * 100
        else:
            self.consolidation_ratio = 0
        
        # Calculate cost per kg
        if self.chargeable_weight and self.chargeable_weight > 0:
            total_cost = sum(
                flt(charge.estimated_cost or charge.buying_amount or 0)
                for charge in self.consolidation_charges
            )
            self.cost_per_kg = total_cost / self.chargeable_weight
        else:
            self.cost_per_kg = 0
    
    def validate_dangerous_goods_compliance(self):
        """Validate dangerous goods compliance for consolidation"""
        dg_packages = [p for p in self.consolidation_packages if p.contains_dangerous_goods]
        
        if dg_packages:
            # Check if all routes allow dangerous goods
            for i, route in enumerate(self.consolidation_routes, 1):
                if not route.dangerous_goods_allowed:
                    frappe.throw(_("Route {0} does not allow dangerous goods, but consolidation contains DG packages").format(i))
            
            # Validate DG segregation requirements
            self.validate_dg_segregation(dg_packages)
    
    def validate_dg_segregation(self, dg_packages):
        """Validate dangerous goods segregation requirements"""
        dg_classes = [p.dg_class for p in dg_packages if p.dg_class]
        
        # Check for incompatible DG classes
        incompatible_pairs = [
            ("1", "2"),  # Explosives with gases
            ("3", "5"),  # Flammable liquids with oxidizing substances
            ("4", "5"),  # Flammable solids with oxidizing substances
        ]
        
        for class1, class2 in incompatible_pairs:
            if class1 in dg_classes and class2 in dg_classes:
                frappe.throw(_("Incompatible dangerous goods classes {0} and {1} cannot be consolidated together").format(class1, class2))
    

    def validate_custom_cost_allocation_percentages(self, strict=False):
        """When any charge uses Custom allocation, validate planned shipment % splits.

        During normal save (strict=False), allow setup before planned shipments exist unless
        cargo already references Sea Shipments. On submit (strict=True), planned shipments are
        always required when Custom allocation is used.
        """
        if not _consolidation_has_custom_allocation_charge(self):
            return
        rows = _custom_allocation_planning_rows(self)
        total = sum(flt(getattr(r, "cost_allocation_percentage", None) or 0) for r in rows)

        if not rows:
            cargo = get_sea_shipment_names_from_consolidation_cargo(self)
            if cargo:
                frappe.throw(
                    _(
                        "Custom allocation requires each cargo Sea Shipment on the planned "
                        "shipment list (Shipments → Planned shipments) with Cost Allocation % "
                        "that sums to 100%."
                    ),
                    title=_("Cost allocation"),
                )
            if strict or (self.sea_planning_status or "Draft") == "Submitted":
                frappe.throw(
                    _(
                        "Custom allocation requires planned shipments with Cost Allocation % "
                        "(Shipments tab → Planned shipments), or change the charge Allocation "
                        "Method to Weight-based, Volume-based, or Equal."
                    ),
                    title=_("Cost allocation"),
                )
            return

        if total <= 0:
            return
        if abs(total - 100.0) > 0.01:
            frappe.throw(
                _(
                    "Cost Allocation % on planned shipments must sum to 100% when using "
                    "Custom allocation (current total: {0}%)."
                ).format(flt(total, 2)),
                title=_("Cost allocation"),
            )

    def validate_accounts(self):
        """Validate accounting dimensions"""
        if not self.company:
            frappe.throw(_("Company is required"))
        
        if self.cost_center:
            cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
            if cost_center_company and cost_center_company != self.company:
                frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                    self.cost_center, self.company
                ))
        
        if self.profit_center:
            # Check if Profit Center doctype has a company field before validating
            # Profit Center may not have a company field in this installation
            try:
                profit_center_meta = frappe.get_meta("Profit Center")
                if profit_center_meta.has_field("company"):
                    try:
                        profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
                        if profit_center_company and profit_center_company != self.company:
                            frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                                self.profit_center, self.company
                            ))
                    except Exception as db_error:
                        # If Profit Center doesn't have company field in database, skip validation
                        # Check if it's a missing column error (1054: Unknown column)
                        if "Unknown column" in str(db_error) or "1054" in str(db_error):
                            # Field doesn't exist in database, skip validation
                            pass
                        else:
                            # Re-raise other exceptions
                            raise
            except Exception as e:
                # If there's an error getting meta or other issues, skip validation
                if "Unknown column" in str(e) or "1054" in str(e):
                    pass
                else:
                    raise
        
        if self.branch:
            # Check if Branch doctype has a company field before validating
            try:
                branch_meta = frappe.get_meta("Branch")
                if branch_meta.has_field("company"):
                    try:
                        branch_company = frappe.db.get_value("Branch", self.branch, "company")
                        if branch_company and branch_company != self.company:
                            frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                                self.branch, self.company
                            ))
                    except Exception as db_error:
                        # If Branch doesn't have company field in database, skip validation
                        # Check if it's a missing column error (1054: Unknown column)
                        if "Unknown column" in str(db_error) or "1054" in str(db_error):
                            # Field doesn't exist in database, skip validation
                            pass
                        else:
                            # Re-raise other exceptions
                            raise
            except Exception as e:
                # If there's an error getting meta or other issues, skip validation
                if "Unknown column" in str(e) or "1054" in str(e):
                    pass
                else:
                    raise
    
    def validate_packages(self):
        """Validate packages for Sea Consolidation (aligned with Sea Shipment)."""
        packages = getattr(self, "consolidation_packages", []) or []
        if not packages:
            return
        total_pkg_weight = sum(flt(getattr(p, "package_weight", 0) or 0) for p in packages)
        total_pkg_volume = sum(flt(getattr(p, "package_volume", 0) or 0) for p in packages)
        if self.total_weight and total_pkg_weight > 0:
            weight_diff = abs(total_pkg_weight - flt(self.total_weight))
            if weight_diff > 0.01:
                frappe.msgprint(
                    _("Package weights ({0} kg) do not match total weight ({1} kg)").format(
                        total_pkg_weight, self.total_weight
                    ),
                    indicator="orange",
                )
        if self.total_volume and total_pkg_volume > 0:
            volume_diff = abs(total_pkg_volume - flt(self.total_volume))
            if volume_diff > 0.01:
                frappe.msgprint(
                    _("Package volumes ({0} m³) do not match total volume ({1} m³)").format(
                        total_pkg_volume, self.total_volume
                    ),
                    indicator="orange",
                )
        for i, package in enumerate(packages, 1):
            if not getattr(package, "package_type", None):
                frappe.msgprint(_("Package row {0}: Package Type is recommended").format(i), indicator="orange")
    
    def validate_containers(self):
        """Validate containers for Sea Consolidation (aligned with Sea Shipment)."""
        containers = getattr(self, "consolidation_containers", []) or []
        if not containers:
            return
        container_count = len(containers)
        if self.total_containers and container_count != flt(self.total_containers):
            frappe.msgprint(
                _("Container count ({0}) does not match total containers ({1})").format(
                    container_count, self.total_containers
                ),
                indicator="orange",
            )
        for i, container in enumerate(containers, 1):
            if not getattr(container, "container_type", None):
                frappe.msgprint(_("Container {0}: Container Type is required").format(i), indicator="orange")
    
    def validate_duplicate_containers(self):
        """Check container numbers are not already used in another consolidation/shipment."""
        containers = getattr(self, "consolidation_containers", []) or []
        container_numbers = [
            getattr(c, "container_number", None) for c in containers
            if getattr(c, "container_number", None)
        ]
        if not container_numbers:
            return
        if self.name:
            existing = frappe.db.sql("""
                SELECT DISTINCT parent, parenttype, container_number
                FROM `tabSea Consolidation Containers`
                WHERE container_number IN %(nums)s AND parent != %(docname)s
                LIMIT 10
            """, {"nums": container_numbers, "docname": self.name}, as_dict=True)
        else:
            existing = frappe.db.sql("""
                SELECT DISTINCT parent, parenttype, container_number
                FROM `tabSea Consolidation Containers`
                WHERE container_number IN %(nums)s
                LIMIT 10
            """, {"nums": container_numbers}, as_dict=True)
        if existing:
            nums = ", ".join(set(c.container_number for c in existing))
            parents = ", ".join(set(c.parent for c in existing))
            frappe.throw(
                _("Container number(s) {0} are already used in: {1}").format(nums, parents),
                title=_("Duplicate Container Numbers"),
            )
    
    def _append_main_route(self):
        """Append a single Direct route from origin to destination using header vessel/etd/eta."""
        if not self.origin_port or not self.destination_port:
            return
        route = {
            "route_type": "Direct",
            "origin_port": self.origin_port,
            "destination_port": self.destination_port,
            "shipping_line": self.shipping_line,
            "vessel_name": getattr(self, "vessel_name", None),
            "voyage_number": getattr(self, "voyage_number", None),
            "etd": self.etd,
            "eta": self.eta,
        }
        self.append("consolidation_routes", route)
    
    @frappe.whitelist()
    def populate_routing_from_ports(self):
        """Manually populate routing from origin/destination. Replaces existing routes with one Direct leg (aligned with Sea Shipment)."""
        if not self.origin_port or not self.destination_port:
            return {"message": _("Set Origin Port and Destination Port first.")}
        self.set("consolidation_routes", [])
        self._append_main_route()
        self.save()
        return {"message": _("Routing leg created from origin to destination.")}
    
    def create_job_number_if_needed(self):
        """Create Job Number if not already linked"""
        if not self.job_number and self.company:
            try:
                job_costing = frappe.new_doc("Job Number")
                job_costing.job_name = self.name
                job_costing.job_type = "Sea Consolidation"
                job_costing.company = self.company
                job_costing.branch = self.branch
                job_costing.cost_center = self.cost_center
                job_costing.profit_center = self.profit_center
                job_costing.insert(ignore_permissions=True)
                
                self.job_number = job_costing.name
            except Exception as e:
                frappe.log_error(f"Error creating Job Number for Sea Consolidation {self.name}: {str(e)}")
    
    def update_consolidation_status(self):
        """Update consolidation status based on current state"""
        if not self.status:
            self.status = "Draft"
        
        # Auto-update status based on conditions
        if self.status == "Draft" and self.consolidation_packages:
            self.status = "Planning"
        
        if self.status == "Planning" and self.consolidation_routes:
            self.status = "In Progress"
    
    def calculate_total_charges(self):
        """Sum consolidation charge costs (estimated cost, else buying amount)."""
        total = 0
        for charge in self.consolidation_charges:
            total += flt(charge.estimated_cost or charge.buying_amount or 0)

        return total
    
    def optimize_consolidation_ratio(self):
        """Optimize consolidation ratio for better cost efficiency"""
        # This can be enhanced with more sophisticated algorithms
        if self.chargeable_weight and self.total_weight:
            current_ratio = (self.chargeable_weight / self.total_weight) * 100
            if current_ratio > 100:
                # Consolidation is efficient
                pass
    
    def _consolidation_status_for_sea_shipment(self, sea_shipment):
        """Package consolidation_status when present, else Pending."""
        for package in self.get("consolidation_packages") or []:
            if getattr(package, "sea_shipment", None) == sea_shipment:
                status = getattr(package, "consolidation_status", None)
                if status:
                    return status
        return "Pending"

    def _clear_sea_shipment_consolidation_tag(self, sea_shipment):
        """Clear back-reference when this consolidation no longer links the shipment."""
        if not sea_shipment or not frappe.get_meta("Sea Shipment").has_field("consolidation_reference"):
            return
        try:
            current = frappe.db.get_value("Sea Shipment", sea_shipment, "consolidation_reference")
            if current != self.name:
                return
            frappe.db.set_value(
                "Sea Shipment",
                sea_shipment,
                {"consolidation_reference": None, "consolidation_status": None},
                update_modified=True,
            )
        except Exception:
            frappe.log_error(
                title=f"Error clearing consolidation on Sea Shipment {sea_shipment}",
                message=frappe.get_traceback(),
            )

    def _set_sea_shipment_consolidation_tag(self, sea_shipment):
        """Set back-reference for consolidatable shipments linked on this document."""
        if not sea_shipment or not sea_shipment_can_be_consolidated(sea_shipment):
            return
        if not frappe.get_meta("Sea Shipment").has_field("consolidation_reference"):
            return
        try:
            frappe.db.set_value(
                "Sea Shipment",
                sea_shipment,
                {
                    "consolidation_reference": self.name,
                    "consolidation_status": self._consolidation_status_for_sea_shipment(sea_shipment),
                },
                update_modified=True,
            )
        except Exception:
            frappe.log_error(
                title=f"Error updating consolidation on Sea Shipment {sea_shipment}",
                message=frappe.get_traceback(),
            )

    def update_related_sea_shipments(self):
        """Sync consolidation_reference on linked Sea Shipments (consolidatable load types only).

        A full ``Sea Shipment.save()`` would re-run link validation on every shipment field
        (e.g. Broker); a bad or legacy broker value would then block saving the consolidation
        even though we only need to update the back-reference.
        """
        if not frappe.get_meta("Sea Shipment").has_field("consolidation_reference"):
            return

        current = get_linked_sea_shipment_names_for_consolidation_tagging(self)
        previous = (
            get_previous_linked_sea_shipment_names_for_consolidation(self.name)
            if self.name and not self.is_new()
            else set()
        )
        removed = previous - current
        for sea_shipment in removed:
            self._clear_sea_shipment_consolidation_tag(sea_shipment)
        for sea_shipment in current:
            self._set_sea_shipment_consolidation_tag(sea_shipment)

    def on_trash(self):
        """Clear consolidation tags from shipments that pointed at this document."""
        if not frappe.get_meta("Sea Shipment").has_field("consolidation_reference"):
            return
        for sea_shipment in frappe.get_all(
            "Sea Shipment",
            filters={"consolidation_reference": self.name},
            pluck="name",
        ):
            self._clear_sea_shipment_consolidation_tag(sea_shipment)

    def _sea_shipment_names_for_house_bill_sync(self):
        """Sea Shipments on cargo (packages/containers) plus planning lines."""
        names = set(get_sea_shipment_names_from_consolidation_cargo(self))
        for row in self.get("consolidation_planning_lines") or []:
            sh = getattr(row, "sea_shipment", None)
            if sh:
                names.add(sh)
        return sorted(names)

    def _sync_house_bl_prefix_to_shipments(self):
        """Fill blank House B/L on linked Sea Shipments using ``house_bill_prefix``.

        Each new number is ``{prefix}-{NNNN}`` where *NNNN* is chosen so the value is unique
        among non-cancelled Sea Shipments (same rule as duplicate House B/L validation).
        Non-blank House B/L is never overwritten. Clearing the prefix does not clear shipments.
        """
        if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
            return
        if getattr(frappe.flags, "in_import", False):
            return
        if getattr(self.flags, "ignore_house_bl_prefix_sync", False):
            return

        prefix = (self.house_bill_prefix or "").strip()
        if not prefix:
            return

        shipment_names = self._sea_shipment_names_for_house_bill_sync()
        if not shipment_names:
            return

        prefix_core = prefix.rstrip("-_ /")
        if not prefix_core:
            return

        reserved_in_batch = set()

        def house_bl_taken(candidate, shipment_name):
            return bool(
                frappe.db.get_value(
                    "Sea Shipment",
                    {
                        "house_bl": candidate,
                        "name": ["!=", shipment_name],
                        "docstatus": ["!=", 2],
                    },
                    "name",
                )
            )

        for shipment_name in shipment_names:
            current = (frappe.db.get_value("Sea Shipment", shipment_name, "house_bl") or "").strip()
            if current:
                continue

            seq = 1
            while True:
                candidate = "{0}-{1:04d}".format(prefix_core, seq)
                seq += 1
                if candidate in reserved_in_batch:
                    continue
                if house_bl_taken(candidate, shipment_name):
                    continue
                reserved_in_batch.add(candidate)
                frappe.db.set_value(
                    "Sea Shipment",
                    shipment_name,
                    "house_bl",
                    candidate,
                    update_modified=True,
                )
                break

    def update_attached_shipments_table(self):
        """Update attached shipments table with latest data from packages.
        Preserves manually added rows that don't correspond to packages."""
        packages = self.get("consolidation_packages") or []

        # Get unique shipments from packages
        unique_shipments = set()
        for package in packages:
            if getattr(package, "sea_shipment", None):
                unique_shipments.add(package.sea_shipment)

        if not unique_shipments:
            # No cargo references a shipment; remove stale attached lines (otherwise
            # planning reset / validation still see ghost links after packages are cleared).
            for attached in list(self.get("attached_sea_shipments") or []):
                if getattr(attached, "sea_shipment", None):
                    self.remove(attached)
            return
        
        # Create a map of existing attached shipments by sea_shipment
        existing_attached = {}
        for attached in self.attached_sea_shipments:
            if attached.sea_shipment:
                existing_attached[attached.sea_shipment] = attached
        
        # Update or add shipments from packages
        for shipment_name in unique_shipments:
            try:
                shipment = frappe.get_doc("Sea Shipment", shipment_name)
                
                # Check if row already exists
                if shipment_name in existing_attached:
                    # Update existing row with latest data
                    attached = existing_attached[shipment_name]
                else:
                    # Add new row
                    attached = self.append("attached_sea_shipments", {})
                    attached.sea_shipment = shipment.name
                
                # Update/sync all fields from shipment
                attached.job_status = shipment.shipping_status
                attached.booking_date = shipment.booking_date
                attached.shipper = shipment.shipper
                attached.consignee = shipment.consignee
                attached.origin_port = shipment.origin_port
                attached.destination_port = shipment.destination_port
                attached.weight = shipment.total_weight
                attached.volume = shipment.total_volume
                attached.packs = shipment.total_packages
                attached.value = getattr(shipment, "goods_value", None) or 0
                attached.currency = shipment.currency
                attached.incoterm = shipment.incoterm
                attached.contains_dangerous_goods = shipment.contains_dangerous_goods or 0
                attached.container_count = shipment.total_containers or 0
                
                # Weight-based cost allocation unless Custom charges preserve manual %
                if (
                    not _consolidation_has_custom_allocation_charge(self)
                    and self.total_weight
                    and self.total_weight > 0
                ):
                    attached.cost_allocation_percentage = (
                        shipment.total_weight / self.total_weight
                    ) * 100
            except Exception as e:
                frappe.log_error(f"Error updating attached shipment {shipment_name}: {str(e)}")
        
        # Note: Manually added rows (those not in unique_shipments) are preserved
    
    def send_consolidation_notifications(self):
        """Send notifications for consolidation updates"""
        # This can be enhanced with email/notification logic
        pass

    def _package_references_in_use(self):
        refs = set()
        for row in self.get("consolidation_packages") or []:
            ref = getattr(row, "package_reference", None)
            if ref:
                refs.add(ref)
        return refs

    def _allocate_consolidation_package_reference(self, sea_shipment, idx, line_reference_no, used_refs):
        """Stable unique package_reference for Sea Consolidation Packages (autoname field).

        The child doctype is autonamed by ``package_reference`` and the field is marked
        unique, so the value becomes the primary key of ``tabSea Consolidation Packages``
        and must be unique across ALL consolidations, not just within this document.
        """

        def _is_free(candidate):
            if not candidate:
                return False
            if candidate in used_refs:
                return False
            return not frappe.db.exists("Sea Consolidation Packages", candidate)

        raw = (line_reference_no or "").strip()
        if _is_free(raw):
            used_refs.add(raw)
            return raw
        base = "{0}-P{1}".format(sea_shipment, idx)
        ref = base
        suffix = 1
        while not _is_free(ref):
            suffix += 1
            ref = "{0}-{1}".format(base, suffix)
        used_refs.add(ref)
        return ref

    def _append_one_consolidation_package_row(
        self,
        sea_shipment,
        shipment,
        *,
        package_reference,
        package_type,
        package_count,
        package_weight,
        package_volume,
        commodity,
        description,
        contains_dangerous_goods,
        dg_class,
        temperature_controlled,
        min_temperature,
        max_temperature,
    ):
        row = self.append(
            "consolidation_packages",
            {
                "package_reference": package_reference,
                "sea_shipment": sea_shipment,
                "shipper": shipment.shipper,
                "consignee": shipment.consignee,
                "package_type": package_type,
                "package_count": package_count,
                "package_weight": package_weight,
                "package_volume": package_volume,
                "commodity": commodity,
                "description": description,
                "contains_dangerous_goods": 1 if contains_dangerous_goods else 0,
                "dg_class": dg_class or None,
                "temperature_controlled": 1 if temperature_controlled else 0,
                "min_temperature": min_temperature,
                "max_temperature": max_temperature,
            },
        )
        return row

    def _append_consolidation_packages_from_sea_shipment(self, sea_shipment):
        """Mirror Sea Shipment package lines into consolidation_packages (or one header summary row).

        Skips if any consolidation package row already exists for this shipment on this document.
        """
        if not sea_shipment:
            return []
        if self.name and frappe.db.exists(
            "Sea Consolidation Packages",
            {"sea_shipment": sea_shipment, "parent": self.name},
        ):
            return []

        shipment = frappe.get_doc("Sea Shipment", sea_shipment)
        used_refs = self._package_references_in_use()
        appended = []
        pkg_lines = [r for r in (shipment.get("packages") or []) if r is not None]

        if pkg_lines:
            for i, sp in enumerate(pkg_lines, start=1):
                n_packs = flt(getattr(sp, "no_of_packs", 0) or 0)
                if n_packs > 0:
                    pack_count = max(1, cint(math.ceil(n_packs)))
                else:
                    pack_count = 1
                w = flt(getattr(sp, "weight", 0) or 0)
                v = flt(getattr(sp, "volume", 0) or 0)
                if w <= 0:
                    w = flt(shipment.total_weight or 0) / len(pkg_lines) if flt(shipment.total_weight or 0) else 0
                if w <= 0:
                    w = 0.01
                line_ref = getattr(sp, "reference_no", None)
                pkg_ref = self._allocate_consolidation_package_reference(
                    sea_shipment, i, line_ref, used_refs
                )
                container_txt = (getattr(sp, "container", None) or "").strip()
                pkg_type = "Container" if container_txt else "Other"
                line_dg = bool(getattr(sp, "dg_substance", None) or (getattr(sp, "dg_class", None) or "").strip())
                hdr_dg = bool(shipment.contains_dangerous_goods)
                dg_flag = line_dg or hdr_dg
                temp_flag = bool(getattr(sp, "temp_controlled", 0))
                row = self._append_one_consolidation_package_row(
                    sea_shipment,
                    shipment,
                    package_reference=pkg_ref,
                    package_type=pkg_type,
                    package_count=pack_count,
                    package_weight=w,
                    package_volume=v,
                    commodity=getattr(sp, "commodity", None) or getattr(shipment, "commodity", None),
                    description=getattr(sp, "goods_description", None) or "",
                    contains_dangerous_goods=1 if dg_flag else 0,
                    dg_class=(getattr(sp, "dg_class", None) or None) if dg_flag else None,
                    temperature_controlled=1 if temp_flag else 0,
                    min_temperature=getattr(sp, "min_temperature", None) if temp_flag else None,
                    max_temperature=getattr(sp, "max_temperature", None) if temp_flag else None,
                )
                appended.append(row)
        else:
            pkg_ref = self._allocate_consolidation_package_reference(sea_shipment, 1, None, used_refs)
            row = self._append_one_consolidation_package_row(
                sea_shipment,
                shipment,
                package_reference=pkg_ref,
                package_type="Box",
                package_count=shipment.total_packages or 1,
                package_weight=flt(shipment.total_weight or 0),
                package_volume=flt(shipment.total_volume or 0),
                commodity=getattr(shipment, "commodity", None),
                description="",
                contains_dangerous_goods=1 if shipment.contains_dangerous_goods else 0,
                dg_class=None,
                temperature_controlled=0,
                min_temperature=None,
                max_temperature=None,
            )
            appended.append(row)

        return appended

    _CONSOLIDATION_DELIVERY_MODES = frozenset({"CY/CY", "CY/CFS", "CFS/CY", "CFS/CFS"})

    def _append_consolidation_containers_from_sea_shipment(self, sea_shipment):
        """Mirror Sea Shipment container lines into consolidation_containers.

        Skips if any consolidation container row already exists for this shipment on this document.
        Skips shipment container rows without a resolvable ISO number and container type.
        """
        if not sea_shipment:
            return
        if self.name and frappe.db.exists(
            "Sea Consolidation Containers",
            {"sea_shipment": sea_shipment, "parent": self.name},
        ):
            return

        shipment = frappe.get_doc("Sea Shipment", sea_shipment)
        existing_nums = {
            normalize_container_number(getattr(r, "container_number", None) or "")
            for r in (self.get("consolidation_containers") or [])
            if getattr(r, "container_number", None)
        }
        existing_nums.discard("")

        for row in shipment.get("containers") or []:
            container_doc_name = getattr(row, "container_no", None)
            if not container_doc_name:
                continue
            master_vals = frappe.db.get_value(
                "Container",
                container_doc_name,
                ["container_number", "container_type"],
                as_dict=True,
            )
            if not master_vals:
                continue
            cn_norm = normalize_container_number(master_vals.get("container_number") or "")
            if not cn_norm:
                continue
            if cn_norm in existing_nums:
                continue
            ctype = getattr(row, "type", None) or master_vals.get("container_type")
            if not ctype:
                continue
            dm = (getattr(row, "delivery_modes", None) or "").strip() or None
            if dm and dm not in self._CONSOLIDATION_DELIVERY_MODES:
                dm = None
            self.append(
                "consolidation_containers",
                {
                    "container_number": cn_norm,
                    "container_type": ctype,
                    "seal_number": getattr(row, "seal_no", None) or None,
                    "size": getattr(row, "size", None) or None,
                    "mode": getattr(row, "mode", None) or None,
                    "delivery_mode": dm,
                    "packages_in_container": getattr(row, "packages_in_container", None),
                    "weight_in_container": flt(getattr(row, "weight_in_container", None)),
                    "volume_in_container": flt(getattr(row, "volume_in_container", None)),
                    "max_weight": flt(getattr(row, "max_weight", None)),
                    "max_volume": flt(getattr(row, "max_volume", None)),
                    "utilization_percentage": flt(getattr(row, "utilization_percentage", None)),
                    "sea_shipment": sea_shipment,
                },
            )
            existing_nums.add(cn_norm)
    
    @frappe.whitelist()
    def add_sea_shipment(self, sea_shipment):
        """Add a Sea Shipment to the consolidation"""
        if (self.sea_planning_status or "Draft") == "Submitted":
            frappe.throw(
                _("Cannot add cargo while planning status is Submitted. Reset planned shipments to draft first."),
                title=_("Cargo locked"),
            )
        # Check if shipment is already in consolidation
        existing_package = frappe.db.exists("Sea Consolidation Packages", {
            "sea_shipment": sea_shipment,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Sea Shipment is already included in this consolidation"))
        
        # Validate house type: only consolidation types can be added (not Standard House or Break Bulk)
        shipment = frappe.get_doc("Sea Shipment", sea_shipment)
        allowed = ("Co-load Master", "Blind Co-load Master", "Co-load House", "Buyer's Consol Lead", "Shipper's Consol Lead")
        if shipment.house_type not in allowed:
            frappe.throw(_(
                "Sea Shipment with House Type '{0}' cannot be added to consolidation. "
                "Only Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, or Shipper's Consol Lead are allowed."
            ).format(shipment.house_type or "Standard House"))

        ok, msg = sea_shipment_allowed_on_plan(sea_shipment)
        if not ok:
            frappe.throw(msg)

        self._append_consolidation_packages_from_sea_shipment(sea_shipment)
        self._append_consolidation_containers_from_sea_shipment(sea_shipment)
        
        # Update the attached shipments table
        self.update_attached_shipments_table()
        
        self.save()
        rows = [p for p in (self.consolidation_packages or []) if getattr(p, "sea_shipment", None) == sea_shipment]
        return rows[-1] if rows else None
    
    @frappe.whitelist()
    def remove_sea_shipment(self, sea_shipment):
        """Remove a Sea Shipment from the consolidation"""
        if (self.sea_planning_status or "Draft") == "Submitted":
            frappe.throw(
                _("Cannot remove cargo while planning status is Submitted. Reset planned shipments to draft first."),
                title=_("Cargo locked"),
            )
        # Remove from packages
        packages_to_remove = [p for p in self.consolidation_packages if p.sea_shipment == sea_shipment]
        for package in packages_to_remove:
            self.remove(package)

        containers_to_remove = [
            c
            for c in (self.consolidation_containers or [])
            if getattr(c, "sea_shipment", None) == sea_shipment
        ]
        for c in containers_to_remove:
            self.remove(c)

        self._clear_sea_shipment_consolidation_tag(sea_shipment)

        # Update attached shipments table
        self.update_attached_shipments_table()
        
        self.save()
        return True

    def _sea_plan_route_fallback_row(self):
        """Prefer child route matching header O/D; else first route (ETD / carrier often live here only)."""
        routes = self.get("consolidation_routes") or []
        if not routes:
            return None
        ho, hd = self.origin_port, self.destination_port
        for row in routes:
            ro = getattr(row, "origin_port", None)
            rd = getattr(row, "destination_port", None)
            if ho and hd and ro == ho and rd == hd:
                return row
        return routes[0]

    def _sea_plan_match_dict(self):
        etd = self.etd
        shipping_line = self.shipping_line
        vessel_name = self.vessel_name
        voyage_number = self.voyage_number
        r = self._sea_plan_route_fallback_row()
        if r:
            if not etd:
                etd = getattr(r, "etd", None) or etd
            if not shipping_line:
                shipping_line = getattr(r, "shipping_line", None)
            if not (vessel_name or "").strip():
                vessel_name = getattr(r, "vessel_name", None)
            if not (voyage_number or "").strip():
                voyage_number = getattr(r, "voyage_number", None)
        return {
            "company": self.company,
            "branch": self.branch,
            "origin_port": self.origin_port,
            "destination_port": self.destination_port,
            "target_etd": etd,
            "shipping_line": shipping_line,
            "vessel_name": vessel_name,
            "voyage_number": voyage_number,
        }

    def _merged_sea_plan_match_dict_from_dialog(self, filter_overrides):
        keys = (
            "company",
            "branch",
            "origin_port",
            "destination_port",
            "target_etd",
            "shipping_line",
            "vessel_name",
            "voyage_number",
        )
        base = dict(self._sea_plan_match_dict())
        o = filter_overrides or {}
        if isinstance(o, str):
            o = frappe.parse_json(o) or {}
        if not isinstance(o, dict):
            o = {}
        for key in keys:
            if key not in o:
                continue
            val = o[key]
            if val is None or (isinstance(val, str) and not str(val).strip()):
                base[key] = None
            else:
                base[key] = val
        return base

    def _sea_plan_dict_from_dialog_full(self, raw):
        """Build alignment plan from dialog field values only (cleared fields = no filter)."""
        o = raw or {}
        if isinstance(o, str):
            o = frappe.parse_json(o) or {}
        if not isinstance(o, dict):
            o = {}
        plan = {}
        for k in SEA_ALIGNMENT_DIALOG_FILTER_KEYS:
            if k not in o:
                plan[k] = None
                continue
            val = o[k]
            if val is None or (isinstance(val, str) and not str(val).strip()):
                plan[k] = None
            else:
                plan[k] = val
        return plan

    def _sea_alignment_apply_company_scope_if_empty(self, merged):
        """If every criterion is empty, list draft jobs for this consolidation's company only."""
        if sea_alignment_plan_has_any_filter(merged):
            return merged
        if not self.company:
            frappe.throw(
                _("Set Company on this consolidation to search with no filters."),
                title=_("Company required"),
            )
        broad = {k: None for k in SEA_ALIGNMENT_DIALOG_FILTER_KEYS}
        broad["company"] = self.company
        return broad

    def _sea_alignment_plan_for_preview(self, filter_values=None, filter_overrides=None):
        """Posted dialog uses *filter_values* (full field map); legacy callers use *filter_overrides* diffs."""
        if filter_values is not None:
            merged = self._sea_plan_dict_from_dialog_full(filter_values)
        else:
            merged = self._merged_sea_plan_match_dict_from_dialog(filter_overrides)
        return self._sea_alignment_apply_company_scope_if_empty(merged)

    @frappe.whitelist()
    def preview_matching_sea_shipments(self, filter_values=None, filter_overrides=None):
        """Return strict-matching shipments with eligibility for each row (no save)."""
        # Do not reload from DB: preview must use the document posted from the form (see Air Consolidation).
        if self.is_new():
            return {"error": _("Save the consolidation first.")}

        merged = self._sea_alignment_plan_for_preview(
            filter_values=filter_values,
            filter_overrides=filter_overrides,
        )
        try:
            assert_sea_plan_fields_for_filter_match(merged)
        except ValidationError as e:
            return {"error": cstr(getattr(e, "message", e))}


        candidates = get_strict_matching_sea_shipment_names(merged)
        present = {
            r.sea_shipment
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "sea_shipment", None)
        }

        rows = []
        for name in candidates:
            shipment = frappe.db.get_value(
                "Sea Shipment",
                name,
                [
                    "name",
                    "job_status",
                    "origin_port",
                    "destination_port",
                    "shipping_line",
                    "etd",
                    "house_type",
                    "company",
                    "branch",
                ],
                as_dict=True,
            ) or {}

            row = {"name": name, "job_status": shipment.get("job_status") or "", "row_type": "eligible"}
            if shipment.get("company") and shipment.get("branch"):
                row["subtitle"] = "{0} · {1}".format(
                    shipment.get("company"),
                    shipment.get("branch"),
                )
            if name in present:
                row["row_type"] = "already"
                row["origin_port"] = shipment.get("origin_port") or ""
                row["destination_port"] = shipment.get("destination_port") or ""
                row["shipping_line"] = shipment.get("shipping_line") or ""
                row["etd"] = shipment.get("etd")
                rows.append(row)
                continue
            ok, msg = sea_shipment_allowed_on_plan(name)
            if not ok:
                row["row_type"] = "blocked"
                row["reason"] = cstr(msg)
                rows.append(row)
                continue
            if conflicting_submitted_sea_planning_elsewhere(name, self.name):
                row["row_type"] = "blocked"
                row["reason"] = _("Reserved on another consolidation submitted planning.")
                rows.append(row)
                continue
            row["origin_port"] = shipment.get("origin_port") or ""
            row["destination_port"] = shipment.get("destination_port") or ""
            row["shipping_line"] = shipment.get("shipping_line") or ""
            row["etd"] = shipment.get("etd")
            rows.append(row)

        banner = _("{0} candidate(s); {1} can be added").format(
            len(candidates), len([r for r in rows if r.get("row_type") == "eligible"])
        )
        return {"rows": rows, "message": banner}

    @frappe.whitelist()
    def apply_selected_sea_shipments_to_planning(
        self, shipment_names, filter_values=None, filter_overrides=None
    ):
        """Append shipments chosen in the alignment dialog."""
        names = frappe.parse_json(shipment_names) if isinstance(shipment_names, str) else shipment_names
        if not names:
            frappe.throw(_("Select at least one shipment."), title=_("Nothing selected"))

        preview = self.preview_matching_sea_shipments(
            filter_values=filter_values,
            filter_overrides=filter_overrides,
        )
        if isinstance(preview, dict) and preview.get("error"):
            frappe.throw(preview["error"])

        preview_rows = {
            r["name"]: r for r in (preview.get("rows") or []) if r.get("name")
        }

        self.reload()
        if self.sea_planning_status == "Submitted":
            frappe.throw(_("Cannot add shipments after planning is submitted."), title=_("Planning locked"))

        present = {
            getattr(r, "sea_shipment", None)
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "sea_shipment", None)
        }

        added, skipped, already_present = [], [], []
        seen = set()
        for nm in names:
            if nm in seen:
                continue
            seen.add(nm)
            if nm in present:
                already_present.append(nm)
                continue
            row = preview_rows.get(nm)
            if not row or row.get("row_type") != "eligible":
                reason = (row or {}).get("reason") or _("Not eligible for this consolidation.")
                skipped.append({"shipment": nm, "reason": cstr(reason)})
                continue
            ok, msg = sea_shipment_allowed_on_plan(nm)
            if not ok:
                skipped.append({"shipment": nm, "reason": cstr(msg)})
                continue
            if conflicting_submitted_sea_planning_elsewhere(nm, self.name):
                skipped.append(
                    {
                        "shipment": nm,
                        "reason": _("Reserved on another consolidation's submitted planning."),
                    }
                )
                continue
            self.append("consolidation_planning_lines", {"sea_shipment": nm})
            self._append_consolidation_packages_from_sea_shipment(nm)
            self._append_consolidation_containers_from_sea_shipment(nm)
            added.append(nm)
            present.add(nm)

        if not added and not already_present:
            frappe.throw(
                _("No shipments were added. Eligible rows can be selected; blocked rows show a reason in Details."),
                title=_("Nothing added"),
            )

        self.save()
        parts = []
        if added:
            parts.append(_("{0} added").format(len(added)))
        if already_present:
            parts.append(_("{0} already on planned list").format(len(already_present)))
        if skipped:
            parts.append(_("{0} skipped").format(len(skipped)))
        return {
            "added": added,
            "skipped": skipped,
            "already_present": already_present,
            "message": " · ".join(parts) if parts else _("No changes"),
        }

    def _validate_consolidation_planning_lines(self):
        from logistics.utils.consolidation_plan import get_previous_planning_line_shipments

        rows = self.get("consolidation_planning_lines") or []
        prev_planned = get_previous_planning_line_shipments(self, "sea_shipment")
        seen = set()
        for row in rows:
            sh = row.sea_shipment
            if not sh:
                continue
            if sh in seen:
                frappe.throw(_("Sea Shipment {0} is duplicated in planning lines.").format(sh))
            seen.add(sh)
            ok, msg = sea_shipment_allowed_on_plan(sh, retain_existing=(sh in prev_planned))
            if not ok:
                frappe.throw(msg)
            origin = frappe.db.get_value("Sea Shipment", sh, "origin_port")
            dest = frappe.db.get_value("Sea Shipment", sh, "destination_port")
            if self.origin_port and origin and origin != self.origin_port:
                frappe.throw(
                    _("Sea Shipment {0} origin {1} does not match consolidation origin {2}.").format(
                        sh, origin, self.origin_port
                    )
                )
            if self.destination_port and dest and dest != self.destination_port:
                frappe.throw(
                    _("Sea Shipment {0} destination {1} does not match consolidation destination {2}.").format(
                        sh, dest, self.destination_port
                    )
                )
            if (self.sea_planning_status or "Draft") == "Draft":
                if conflicting_submitted_sea_planning_elsewhere(
                    sh, self.name if not self.is_new() else None
                ):
                    frappe.throw(
                        _(
                            "Sea Shipment {0} is already reserved on another consolidation's submitted planning."
                        ).format(sh),
                        title=_("Planning Conflict"),
                    )

    @frappe.whitelist()
    def fetch_matching_sea_shipments(self):
        self.reload()
        if self.sea_planning_status == "Submitted":
            frappe.throw(_("Cannot fetch shipments after planning is submitted."), title=_("Planning locked"))
        if self.is_new():
            frappe.throw(_("Save the consolidation before fetching shipments."), title=_("Save required"))
        assert_sea_plan_fields_for_filter_match(self._sea_plan_match_dict())
        candidates = get_strict_matching_sea_shipment_names(self._sea_plan_match_dict())
        present = {
            r.sea_shipment
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "sea_shipment", None)
        }
        added, already_present, skipped = [], [], []
        for name in candidates:
            if name in present:
                already_present.append(name)
                continue
            ok, msg = sea_shipment_allowed_on_plan(name)
            if not ok:
                skipped.append({"shipment": name, "reason": msg})
                continue
            if conflicting_submitted_sea_planning_elsewhere(name, self.name):
                skipped.append(
                    {
                        "shipment": name,
                        "reason": _("Reserved on another consolidation's submitted planning."),
                    }
                )
                continue
            self.append("consolidation_planning_lines", {"sea_shipment": name})
            self._append_consolidation_packages_from_sea_shipment(name)
            self._append_consolidation_containers_from_sea_shipment(name)
            added.append(name)
            present.add(name)
        self.save()
        return {"added": added, "already_present": already_present, "skipped": skipped}

    @frappe.whitelist()
    def submit_sea_planning(self):
        self.reload()
        if self.sea_planning_status == "Submitted":
            frappe.throw(_("Planning is already submitted."), title=_("Already submitted"))
        if not self.get("consolidation_planning_lines"):
            frappe.throw(
                _("Add at least one shipment to planning before submitting."), title=_("No Lines")
            )
        validate_minimum_sea_planning_shipments(self)
        self.sea_planning_status = "Submitted"
        if not self.planning_owner:
            self.planning_owner = frappe.session.user
        self.save()
        return self.sea_planning_status

    @frappe.whitelist()
    def cancel_sea_planning_submit(self):
        self.reload()
        if self.sea_planning_status != "Submitted":
            frappe.throw(_("Planning is not submitted."), title=_("Not submitted"))
        if self.docstatus != 0:
            frappe.throw(
                _("Cancel planning only while the consolidation is still draft (not submitted)."),
                title=_("Not allowed"),
            )
        self.sea_planning_status = "Draft"
        self.planning_owner = None
        self.save()
        return self.sea_planning_status

    @frappe.whitelist()
    def get_dashboard_html(self):
        """Generate HTML for Dashboard tab: same tabbed layout as Sea Booking / Sea Shipment (Route, Milestones, Alerts)."""
        try:
            from logistics.document_management.logistics_form_dashboard import (
                build_sea_consolidation_dashboard_config,
                render_logistics_form_dashboard_html,
            )
            from logistics.utils.sales_quote_validity import get_sales_quote_validity_dashboard_html

            dash = render_logistics_form_dashboard_html(
                self, build_sea_consolidation_dashboard_config(self)
            )
            return get_sales_quote_validity_dashboard_html(self) + dash
        except Exception as e:
            frappe.log_error(f"Sea Consolidation get_dashboard_html: {str(e)}", "Sea Consolidation Dashboard")
            return "<div class='alert alert-warning'>Error loading dashboard.</div>"

    @frappe.whitelist()
    def recalculate_all_charges_api(self):
        """Recalculate all consolidation charges based on current document data."""
        return recalculate_all_charges(self.name)

    @frappe.whitelist()
    def allocate_costs(self, allocation_method="weight"):
        """Allocate consolidation costs to individual shipments"""
        total_cost = self.calculate_total_charges()
        
        if allocation_method == "weight":
            # Allocate based on weight
            total_weight = self.total_weight or 1
            for shipment in self.attached_sea_shipments:
                if getattr(shipment, "total_weight", None) or getattr(shipment, "weight", None):
                    sw = getattr(shipment, "total_weight", None) or getattr(shipment, "weight", None) or 0
                    allocation_pct = (sw / total_weight) * 100
                    shipment.cost_allocation_percentage = allocation_pct
                    shipment.total_charge = (total_cost * allocation_pct) / 100
        
        elif allocation_method == "volume":
            # Allocate based on volume
            total_volume = self.total_volume or 1
            for shipment in self.attached_sea_shipments:
                if getattr(shipment, "total_volume", None) or getattr(shipment, "volume", None):
                    sv = getattr(shipment, "total_volume", None) or getattr(shipment, "volume", None) or 0
                    allocation_pct = (sv / total_volume) * 100
                    shipment.cost_allocation_percentage = allocation_pct
                    shipment.total_charge = (total_cost * allocation_pct) / 100
        
        elif allocation_method == "equal":
            # Equal allocation
            shipment_count = len(self.attached_sea_shipments) or 1
            allocation_pct = 100 / shipment_count
            for shipment in self.attached_sea_shipments:
                shipment.cost_allocation_percentage = allocation_pct
                shipment.total_charge = (total_cost * allocation_pct) / 100
        
        self.save()
        return True


@frappe.whitelist()
def populate_routing_from_ports(docname):
    """API: Populate routing from origin/destination ports."""
    doc = frappe.get_doc("Sea Consolidation", docname)
    return doc.populate_routing_from_ports()


@frappe.whitelist()
def recalculate_all_charges(docname):
    """Recalculate all charges based on current Sea Consolidation data."""
    doc = frappe.get_doc("Sea Consolidation", docname)
    from logistics.utils.menu_permission import assert_perm

    assert_perm("Sea Consolidation", "write", doc=doc)
    if not doc.consolidation_charges:
        return {"success": False, "message": _("No charges found to recalculate")}
    try:
        charges_recalculated = 0
        for charge in doc.consolidation_charges:
            if hasattr(charge, "calculate_charge_amount"):
                charge.calculate_charge_amount(parent_doc=doc)
                charges_recalculated += 1
        doc.save()
        return {
            "success": True,
            "message": _("Successfully recalculated {0} charges").format(charges_recalculated),
            "charges_recalculated": charges_recalculated,
        }
    except Exception as e:
        frappe.log_error(str(e), "Sea Consolidation - Recalculate Charges Error")
        frappe.throw(_("Error recalculating charges: {0}").format(str(e)))

