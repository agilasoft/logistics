# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, now_datetime, getdate
from datetime import datetime, timedelta


class SeaConsolidation(Document):
    def validate(self):
        """Validate Sea Consolidation document"""
        self.validate_dates()
        self.validate_consolidation_data()
        self.validate_route_consistency()
        self.validate_capacity_constraints()
        self.validate_attached_shipments_compatibility()
        self.validate_shipments_not_in_multiple_consolidations()
        self.calculate_consolidation_metrics()
        self.validate_dangerous_goods_compliance()
        self.validate_accounts()
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_consolidation_status()
        self.calculate_total_charges()
        self.optimize_consolidation_ratio()
        # Job Costing Number will be created in after_insert method
    
    def after_insert(self):
        """Create Job Costing Number after document is inserted"""
        self.create_job_costing_number_if_needed()
        # Save the document to persist the job_costing_number field
        if self.job_costing_number:
            self.save(ignore_permissions=True)
    
    def on_update(self):
        """Actions after document update"""
        self.update_related_sea_shipments()
        self.update_attached_shipments_table()
        self.send_consolidation_notifications()
    
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
            if self.etd and self.consolidation_date > getdate(self.etd):
                frappe.throw(_("Consolidation date cannot be later than ETD"))
    
    def validate_route_consistency(self):
        """Validate route consistency and connectivity"""
        if len(self.consolidation_routes) > 1:
            for i, route in enumerate(self.consolidation_routes):
                if i > 0:
                    # Check if destination of previous route matches origin of current route
                    prev_route = self.consolidation_routes[i-1]
                    if prev_route.destination_port != route.origin_port:
                        frappe.throw(_("Route {0}: Origin port must match destination of previous route").format(route.route_sequence))
    
    def validate_capacity_constraints(self):
        """Validate capacity constraints for all routes"""
        for route in self.consolidation_routes:
            if route.container_capacity and self.total_containers > route.container_capacity:
                frappe.throw(_("Route {0}: Total containers exceed container capacity").format(route.route_sequence))
            
            if route.cargo_capacity_kg and self.total_weight > route.cargo_capacity_kg:
                frappe.throw(_("Route {0}: Total weight exceeds cargo capacity").format(route.route_sequence))
            
            if route.cargo_capacity_volume and self.total_volume > route.cargo_capacity_volume:
                frappe.throw(_("Route {0}: Total volume exceeds cargo capacity").format(route.route_sequence))
    
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
            for route in self.consolidation_routes:
                if not route.dangerous_goods_allowed:
                    frappe.throw(_("Route {0} does not allow dangerous goods, but consolidation contains DG packages").format(route.route_sequence))
            
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
            profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
            if profit_center_company and profit_center_company != self.company:
                frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                    self.profit_center, self.company
                ))
        
        if self.branch:
            branch_company = frappe.db.get_value("Branch", self.branch, "company")
            if branch_company and branch_company != self.company:
                frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                    self.branch, self.company
                ))
    
    def create_job_costing_number_if_needed(self):
        """Create Job Costing Number if not already linked"""
        if not self.job_costing_number and self.company:
            try:
                job_costing = frappe.new_doc("Job Costing Number")
                job_costing.job_name = self.name
                job_costing.job_type = "Sea Consolidation"
                job_costing.company = self.company
                job_costing.branch = self.branch
                job_costing.cost_center = self.cost_center
                job_costing.profit_center = self.profit_center
                job_costing.insert(ignore_permissions=True)
                
                self.job_costing_number = job_costing.name
            except Exception as e:
                frappe.log_error(f"Error creating Job Costing Number for Sea Consolidation {self.name}: {str(e)}")
    
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
        """Update attached shipments table with latest data"""
        if not self.consolidation_packages:
            return
        
        # Clear existing attached shipments
        self.attached_sea_shipments = []
        
        # Get unique shipments from packages
        unique_shipments = set()
        for package in self.consolidation_packages:
            if package.sea_shipment:
                unique_shipments.add(package.sea_shipment)
        
        # Add shipments to attached table
        for shipment_name in unique_shipments:
            try:
                shipment = frappe.get_doc("Sea Shipment", shipment_name)
                attached = self.append("attached_sea_shipments", {})
                attached.sea_shipment = shipment.name
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
    def allocate_costs(self, allocation_method="weight"):
        """Allocate consolidation costs to individual shipments"""
        total_cost = self.calculate_total_charges()
        
        if allocation_method == "weight":
            # Allocate based on weight
            total_weight = self.total_weight or 1
            for shipment in self.attached_sea_shipments:
                if shipment.weight:
                    allocation_pct = (shipment.weight / total_weight) * 100
                    shipment.cost_allocation_percentage = allocation_pct
                    shipment.total_charge = (total_cost * allocation_pct) / 100
        
        elif allocation_method == "volume":
            # Allocate based on volume
            total_volume = self.total_volume or 1
            for shipment in self.attached_sea_shipments:
                if shipment.volume:
                    allocation_pct = (shipment.volume / total_volume) * 100
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

