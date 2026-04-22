# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, now_datetime, getdate
from datetime import datetime, timedelta

from logistics.utils.consolidation_plan import (
	assert_sea_consolidation_plan_requirements,
	clear_sea_plan_links_for_consolidation,
	sync_sea_plan_item_links,
)


class SeaConsolidation(Document):
    def validate(self):
        """Validate Sea Consolidation document"""
        self.validate_dates()
        self.validate_containers_iso6346()
        self.validate_consolidation_data()
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
        assert_sea_consolidation_plan_requirements(self)
    
    def before_save(self):
        """Actions before saving the document"""
        self._auto_populate_routing_from_ports()
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
    
    def on_update(self):
        """Actions after document update"""
        self.update_related_sea_shipments()
        self.update_attached_shipments_table()
        self.send_consolidation_notifications()
        sync_sea_plan_item_links(self)
    
    def on_cancel(self):
        clear_sea_plan_links_for_consolidation(self.name)
    
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

    def validate_consolidation_data(self):
        """Validate consolidation data integrity"""
        if not self.consolidation_packages and not self.consolidation_containers:
            frappe.throw(_("At least one package or container must be added to the consolidation"))
        
        if not self.consolidation_routes:
            frappe.throw(_("At least one route must be defined for the consolidation"))
    
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
        # Calculate totals from packages
        if self.consolidation_packages:
            self.total_packages = sum(package.package_count or 0 for package in self.consolidation_packages)
            self.total_weight = sum(package.package_weight or 0 for package in self.consolidation_packages)
            self.total_volume = sum(package.package_volume or 0 for package in self.consolidation_packages)
        
        # Calculate totals from containers
        if self.consolidation_containers:
            self.total_containers = len(self.consolidation_containers)
            container_weight = sum(container.weight_in_container or 0 for container in self.consolidation_containers)
            container_volume = sum(container.volume_in_container or 0 for container in self.consolidation_containers)
            
            # Add container totals to package totals if packages exist
            if self.consolidation_packages:
                self.total_weight += container_weight
                self.total_volume += container_volume
            else:
                self.total_weight = container_weight
                self.total_volume = container_volume
        
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
            total_cost = sum(charge.total_amount or 0 for charge in self.consolidation_charges)
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
    
    def _auto_populate_routing_from_ports(self):
        """Auto-populate routing from origin/destination when routing legs are empty (aligned with Sea Shipment)."""
        routes = getattr(self, "consolidation_routes", None) or []
        if routes or not self.origin_port or not self.destination_port:
            return
        self._append_main_route()

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
        """Calculate total charges from consolidation charges"""
        total = 0
        for charge in self.consolidation_charges:
            if charge.total_amount:
                total += flt(charge.total_amount)
        
        return total
    
    def optimize_consolidation_ratio(self):
        """Optimize consolidation ratio for better cost efficiency"""
        # This can be enhanced with more sophisticated algorithms
        if self.chargeable_weight and self.total_weight:
            current_ratio = (self.chargeable_weight / self.total_weight) * 100
            if current_ratio > 100:
                # Consolidation is efficient
                pass
    
    def update_related_sea_shipments(self):
        """Update related Sea Shipments with consolidation information"""
        if not self.consolidation_packages:
            return
        
        try:
            for package in self.consolidation_packages:
                if package.sea_shipment:
                    shipment = frappe.get_doc("Sea Shipment", package.sea_shipment)
                    # Update shipment with consolidation reference
                    if not hasattr(shipment, 'consolidation') or shipment.consolidation != self.name:
                        shipment.consolidation = self.name
                        shipment.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Error updating related Sea Shipments: {str(e)}")
    
    def update_attached_shipments_table(self):
        """Update attached shipments table with latest data from packages.
        Preserves manually added rows that don't correspond to packages."""
        if not self.consolidation_packages:
            return
        
        # Get unique shipments from packages
        unique_shipments = set()
        for package in self.consolidation_packages:
            if package.sea_shipment:
                unique_shipments.add(package.sea_shipment)
        
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
                attached.value = shipment.total_value
                attached.currency = shipment.currency
                attached.incoterm = shipment.incoterm
                attached.contains_dangerous_goods = shipment.contains_dangerous_goods or 0
                attached.container_count = shipment.total_containers or 0
                
                # Calculate cost allocation
                if self.total_weight and self.total_weight > 0:
                    attached.cost_allocation_percentage = (shipment.total_weight / self.total_weight) * 100
            except Exception as e:
                frappe.log_error(f"Error updating attached shipment {shipment_name}: {str(e)}")
        
        # Note: Manually added rows (those not in unique_shipments) are preserved
    
    def send_consolidation_notifications(self):
        """Send notifications for consolidation updates"""
        # This can be enhanced with email/notification logic
        pass
    
    @frappe.whitelist()
    def add_sea_shipment(self, sea_shipment):
        """Add a Sea Shipment to the consolidation"""
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
        
        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.sea_shipment = sea_shipment
        
        # Get shipment details (shipment already fetched above for house_type validation)
        package.shipper = shipment.shipper
        package.consignee = shipment.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = shipment.total_packages or 1
        package.package_weight = shipment.total_weight or 0
        package.package_volume = shipment.total_volume or 0
        package.commodity = shipment.commodity
        package.contains_dangerous_goods = shipment.contains_dangerous_goods or 0
        
        # Update the attached shipments table
        self.update_attached_shipments_table()
        
        self.save()
        return package
    
    @frappe.whitelist()
    def remove_sea_shipment(self, sea_shipment):
        """Remove a Sea Shipment from the consolidation"""
        # Remove from packages
        packages_to_remove = [p for p in self.consolidation_packages if p.sea_shipment == sea_shipment]
        for package in packages_to_remove:
            self.remove(package)
        
        # Update attached shipments table
        self.update_attached_shipments_table()
        
        self.save()
        return True
    
    @frappe.whitelist()
    def get_dashboard_html(self):
        """Generate HTML for Dashboard tab: Run Sheet layout with map and milestones (aligned with Sea Shipment)."""
        try:
            from logistics.document_management.api import get_document_alerts_html, get_dashboard_alerts_html
            from logistics.document_management.dashboard_layout import (
                build_run_sheet_style_dashboard,
                build_map_segments_from_routing_legs,
                get_unloco_coords,
            )
            status = self.get("status") or "Draft"
            header_items = [
                ("Status", status),
                ("ETD", str(self.etd) if self.etd else "—"),
                ("ETA", str(self.eta) if self.eta else "—"),
                ("Packages", str(sum(getattr(p, "package_count", 0) or 0 for p in (self.consolidation_packages or [])))),
                ("Weight", frappe.format_value(self.total_weight or 0, df=dict(fieldtype="Float"))),
            ]
            if self.shipping_line:
                header_items.append(("Shipping Line", self.shipping_line))
            try:
                doc_alerts = get_document_alerts_html("Sea Consolidation", self.name or "new")
            except Exception:
                doc_alerts = ""
            milestone_rows = list(self.get("milestones") or [])
            milestone_details = {}
            if milestone_rows:
                names = [m.milestone for m in milestone_rows if m.milestone]
                if names:
                    for lm in frappe.get_all("Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]):
                        milestone_details[lm.name] = lm.description or lm.name
            cards_html = ""
            for i, m in enumerate(milestone_rows, 1):
                st = (m.status or "Planned").lower().replace(" ", "-")
                desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
                planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
                actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
                cards_html += f"""
                <div class="dash-card {st}">
                    <div class="card-header"><h5>{desc}</h5><span class="card-num">#{i}</span></div>
                    <div class="card-details">Planned: {planned}<br>Actual: {actual}</div>
                    <span class="card-badge {st}">{m.status or "Planned"}</span>
                </div>"""
            routes = getattr(self, "consolidation_routes", None) or []
            legs_for_map = [{"idx": i, "load_port": getattr(r, "origin_port", None), "discharge_port": getattr(r, "destination_port", None), "type": getattr(r, "route_type", "Direct")} for i, r in enumerate(routes, 1)]
            map_segments = build_map_segments_from_routing_legs(legs_for_map)
            map_points = []
            if not map_segments:
                o = get_unloco_coords(self.origin_port)
                d = get_unloco_coords(self.destination_port)
                if o:
                    map_points.append(o)
                if d and (not map_points or (d.get("lat") != map_points[-1].get("lat")) or (d.get("lon") != map_points[-1].get("lon"))):
                    map_points.append(d)
            alerts_html = get_dashboard_alerts_html("Sea Consolidation", self.name or "new")
            return build_run_sheet_style_dashboard(
                header_title=self.name or "Sea Consolidation",
                header_subtitle="Sea Consolidation",
                header_items=header_items,
                cards_html=cards_html or "<div class=\"text-muted\">No milestones. Use Get Milestones in Milestones tab.</div>",
                map_points=map_points,
                map_segments=map_segments,
                map_id_prefix="sea-cons-dash-map",
                doc_alerts_html=doc_alerts,
                alerts_html=alerts_html,
                straight_line=True,
                origin_label=self.origin_port or None,
                destination_label=self.destination_port or None,
                route_below_html="",
            )
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

