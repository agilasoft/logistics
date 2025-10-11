import frappe
from frappe.model.document import Document
from frappe import _
import json
from datetime import datetime, timedelta


class AirConsolidation(Document):
    def validate(self):
        """Validate Air Consolidation document"""
        self.validate_consolidation_data()
        self.validate_route_consistency()
        self.validate_capacity_constraints()
        self.calculate_consolidation_metrics()
        self.validate_dangerous_goods_compliance()
        self.validate_accounts()
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_consolidation_status()
        self.calculate_total_charges()
        self.optimize_consolidation_ratio()
        # Create Job Reference if this is the first save
        self.create_job_reference_if_needed()
    
    def on_update(self):
        """Actions after document update"""
        self.update_related_air_freight_jobs()
        self.update_attached_jobs_table()
        self.send_consolidation_notifications()
    
    def validate_consolidation_data(self):
        """Validate consolidation data integrity"""
        if not self.consolidation_packages:
            frappe.throw(_("At least one package must be added to the consolidation"))
        
        if not self.consolidation_routes:
            frappe.throw(_("At least one route must be defined for the consolidation"))
        
        # Validate dates
        if self.departure_date and self.arrival_date:
            if self.departure_date >= self.arrival_date:
                frappe.throw(_("Departure date must be before arrival date"))
    
    def validate_route_consistency(self):
        """Validate route consistency and connectivity"""
        if len(self.consolidation_routes) > 1:
            for i, route in enumerate(self.consolidation_routes):
                if i > 0:
                    # Check if destination of previous route matches origin of current route
                    prev_route = self.consolidation_routes[i-1]
                    if prev_route.destination_airport != route.origin_airport:
                        frappe.throw(_("Route {0}: Origin airport must match destination of previous route".format(route.route_sequence)))
    
    def validate_capacity_constraints(self):
        """Validate capacity constraints for all routes"""
        for route in self.consolidation_routes:
            if route.cargo_capacity_kg and self.total_weight > route.cargo_capacity_kg:
                frappe.throw(_("Route {0}: Total weight exceeds cargo capacity".format(route.route_sequence)))
            
            if route.cargo_capacity_volume and self.total_volume > route.cargo_capacity_volume:
                frappe.throw(_("Route {0}: Total volume exceeds cargo capacity".format(route.route_sequence)))
    
    def calculate_consolidation_metrics(self):
        """Calculate consolidation metrics"""
        if self.consolidation_packages:
            # Calculate totals
            self.total_packages = sum(package.package_count for package in self.consolidation_packages)
            self.total_weight = sum(package.package_weight for package in self.consolidation_packages)
            self.total_volume = sum(package.package_volume or 0 for package in self.consolidation_packages)
            
            # Calculate chargeable weight (higher of actual weight or volume weight)
            volume_weight = self.total_volume * 167  # Standard IATA volume weight factor
            self.chargeable_weight = max(self.total_weight, volume_weight)
            
            # Calculate consolidation ratio
            if self.total_weight > 0:
                self.consolidation_ratio = (self.chargeable_weight / self.total_weight) * 100
    
    def validate_dangerous_goods_compliance(self):
        """Validate dangerous goods compliance for consolidation"""
        dg_packages = [p for p in self.consolidation_packages if p.contains_dangerous_goods]
        
        if dg_packages:
            # Check if all routes allow dangerous goods
            for route in self.consolidation_routes:
                if not route.dangerous_goods_allowed:
                    frappe.throw(_("Route {0} does not allow dangerous goods, but consolidation contains DG packages".format(route.route_sequence)))
            
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
                frappe.throw(_("Incompatible dangerous goods classes {0} and {1} cannot be consolidated together".format(class1, class2)))
    
    def update_consolidation_status(self):
        """Update consolidation status based on current data"""
        if self.status == "Draft":
            if self.consolidation_packages and self.consolidation_routes:
                self.status = "Planning"
        elif self.status == "Planning":
            if self.master_awb:
                self.status = "Ready for Departure"
        elif self.status == "Ready for Departure":
            if self.departure_date and self.departure_date <= frappe.utils.now():
                self.status = "In Transit"
        elif self.status == "In Transit":
            if self.arrival_date and self.arrival_date <= frappe.utils.now():
                self.status = "Delivered"
    
    def calculate_total_charges(self):
        """Calculate total charges for the consolidation"""
        total_charges = 0
        
        for charge in self.consolidation_charges:
            if charge.charge_basis == "Per kg":
                charge.base_amount = charge.rate * self.chargeable_weight
            elif charge.charge_basis == "Per m³":
                charge.base_amount = charge.rate * self.total_volume
            elif charge.charge_basis == "Per package":
                charge.base_amount = charge.rate * self.total_packages
            elif charge.charge_basis == "Fixed amount":
                charge.base_amount = charge.rate
            elif charge.charge_basis == "Percentage":
                charge.base_amount = charge.rate * (self.chargeable_weight * 0.01)
            
            # Calculate discount
            if charge.discount_percentage:
                charge.discount_amount = charge.base_amount * (charge.discount_percentage / 100)
            
            # Calculate total amount
            charge.total_amount = charge.base_amount - charge.discount_amount + charge.surcharge_amount
            
            total_charges += charge.total_amount
        
        # Calculate cost per kg
        if self.chargeable_weight > 0:
            self.cost_per_kg = total_charges / self.chargeable_weight
    
    def optimize_consolidation_ratio(self):
        """Optimize consolidation ratio for better space utilization"""
        if self.total_weight > 0 and self.total_volume > 0:
            # Calculate density
            density = self.total_weight / self.total_volume
            
            # IATA standard density for air cargo
            standard_density = 167  # kg/m³
            
            if density < standard_density:
                # Low density cargo - volume weight applies
                self.consolidation_ratio = (self.chargeable_weight / self.total_weight) * 100
            else:
                # High density cargo - actual weight applies
                self.consolidation_ratio = 100
    
    def update_related_air_freight_jobs(self):
        """Update related Air Shipments with consolidation information"""
        for package in self.consolidation_packages:
            if package.air_freight_job:
                # Update the Air Shipment with consolidation reference
                frappe.db.set_value("Air Shipment", package.air_freight_job, {
                    "consolidation_reference": self.name,
                    "consolidation_status": package.consolidation_status
                })
    
    def send_consolidation_notifications(self):
        """Send notifications for consolidation status changes"""
        if self.status in ["Ready for Departure", "In Transit", "Delivered"]:
            # Get all related customers
            customers = set()
            for package in self.consolidation_packages:
                if package.shipper:
                    customers.add(package.shipper)
                if package.consignee:
                    customers.add(package.consignee)
            
            # Send notifications
            for customer in customers:
                self.send_customer_notification(customer)
    
    def send_customer_notification(self, customer):
        """Send notification to customer about consolidation status"""
        subject = f"Consolidation {self.name} - Status Update"
        message = f"""
        Your consolidation {self.name} status has been updated to: {self.status}
        
        Route: {self.origin_airport} → {self.destination_airport}
        Departure: {self.departure_date}
        Arrival: {self.arrival_date}
        
        Please contact us for any questions.
        """
        
        frappe.sendmail(
            recipients=[customer],
            subject=subject,
            message=message
        )
    
    @frappe.whitelist()
    def add_package_from_job(self, air_freight_job):
        """Add package from Air Shipment to consolidation"""
        job = frappe.get_doc("Air Shipment", air_freight_job)
        
        # Check if job is already in consolidation
        existing_package = frappe.db.exists("Air Consolidation Packages", {
            "air_freight_job": air_freight_job,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Air Shipment is already included in this consolidation"))
        
        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.air_freight_job = air_freight_job
        package.shipper = job.shipper
        package.consignee = job.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = job.packs or 1
        package.package_weight = job.weight or 0
        package.package_volume = job.volume or 0
        package.commodity = job.description
        package.contains_dangerous_goods = job.contains_dangerous_goods or 0
        
        self.save()
        return package
    
    @frappe.whitelist()
    def optimize_route_selection(self):
        """Optimize route selection based on cost and time"""
        if not self.consolidation_routes:
            return
        
        # Calculate cost and time for each route
        route_scores = []
        for route in self.consolidation_routes:
            score = self.calculate_route_score(route)
            route_scores.append((route, score))
        
        # Sort by score (lower is better)
        route_scores.sort(key=lambda x: x[1])
        
        # Update route sequence based on optimization
        for i, (route, score) in enumerate(route_scores):
            route.route_sequence = i + 1
        
        self.save()
        return route_scores
    
    def calculate_route_score(self, route):
        """Calculate optimization score for a route"""
        # Factors: cost, time, capacity utilization
        cost_factor = route.total_cost_per_kg or 0
        time_factor = route.transit_time_hours or 0
        capacity_factor = 1 - (route.utilization_percentage or 0) / 100
        
        # Weighted score (lower is better)
        score = (cost_factor * 0.5) + (time_factor * 0.3) + (capacity_factor * 0.2)
        return score
    
    @frappe.whitelist()
    def generate_consolidation_report(self):
        """Generate consolidation report"""
        report_data = {
            "consolidation_id": self.name,
            "status": self.status,
            "total_packages": self.total_packages,
            "total_weight": self.total_weight,
            "total_volume": self.total_volume,
            "chargeable_weight": self.chargeable_weight,
            "consolidation_ratio": self.consolidation_ratio,
            "cost_per_kg": self.cost_per_kg,
            "routes": [],
            "packages": []
        }
        
        # Add route information
        for route in self.consolidation_routes:
            report_data["routes"].append({
                "sequence": route.route_sequence,
                "origin": route.origin_airport,
                "destination": route.destination_airport,
                "airline": route.airline,
                "flight_number": route.flight_number,
                "departure": route.departure_date,
                "arrival": route.arrival_date,
                "status": route.route_status
            })
        
        # Add package information
        for package in self.consolidation_packages:
            report_data["packages"].append({
                "reference": package.package_reference,
                "air_freight_job": package.air_freight_job,
                "shipper": package.shipper,
                "consignee": package.consignee,
                "weight": package.package_weight,
                "volume": package.package_volume,
                "status": package.consolidation_status
            })
        
        return report_data
    
    @frappe.whitelist()
    def check_capacity_availability(self):
        """Check capacity availability for all routes"""
        capacity_info = []
        
        for route in self.consolidation_routes:
            available_weight = route.available_capacity_kg or 0
            available_volume = route.available_capacity_volume or 0
            
            weight_utilization = (self.total_weight / available_weight * 100) if available_weight > 0 else 0
            volume_utilization = (self.total_volume / available_volume * 100) if available_volume > 0 else 0
            
            capacity_info.append({
                "route_sequence": route.route_sequence,
                "available_weight": available_weight,
                "available_volume": available_volume,
                "weight_utilization": weight_utilization,
                "volume_utilization": volume_utilization,
                "status": "Available" if weight_utilization < 100 and volume_utilization < 100 else "Full"
            })
        
        return capacity_info
    
    @frappe.whitelist()
    def calculate_cost_breakdown(self):
        """Calculate detailed cost breakdown for consolidation"""
        cost_breakdown = {
            "total_cost": 0,
            "cost_per_kg": 0,
            "charges": []
        }
        
        for charge in self.consolidation_charges:
            charge_info = {
                "type": charge.charge_type,
                "category": charge.charge_category,
                "basis": charge.charge_basis,
                "rate": charge.rate,
                "quantity": charge.quantity,
                "base_amount": charge.base_amount,
                "discount": charge.discount_amount,
                "surcharge": charge.surcharge_amount,
                "total": charge.total_amount
            }
            cost_breakdown["charges"].append(charge_info)
            cost_breakdown["total_cost"] += charge.total_amount
        
        if self.chargeable_weight > 0:
            cost_breakdown["cost_per_kg"] = cost_breakdown["total_cost"] / self.chargeable_weight
        
        return cost_breakdown
    
    def update_attached_jobs_table(self):
        """Update the virtual child table with attached Air Shipments"""
        # Clear existing attached jobs
        self.attached_air_freight_jobs = []
        
        # Get all Air Shipments from consolidation packages
        job_ids = [package.air_freight_job for package in self.consolidation_packages if package.air_freight_job]
        
        for i, job_id in enumerate(job_ids):
            job = frappe.get_doc("Air Shipment", job_id)
            
            # Create attached job entry
            attached_job = self.append("attached_air_freight_jobs", {})
            attached_job.air_freight_job = job_id
            attached_job.job_status = job.status
            attached_job.booking_date = job.booking_date
            attached_job.shipper = job.shipper
            attached_job.consignee = job.consignee
            attached_job.origin_port = job.origin_port
            attached_job.destination_port = job.destination_port
            attached_job.weight = job.weight
            attached_job.volume = job.volume
            attached_job.packs = job.packs
            attached_job.value = job.gooda_value
            attached_job.currency = job.currency
            attached_job.incoterm = job.incoterm
            attached_job.contains_dangerous_goods = job.contains_dangerous_goods or 0
            attached_job.dg_compliance_status = job.dg_compliance_status
            attached_job.dg_declaration_complete = job.dg_declaration_complete
            attached_job.consolidation_status = "Pending"
            attached_job.position_in_consolidation = i + 1
            
            # Calculate cost allocation
            if self.total_weight > 0:
                attached_job.cost_allocation_percentage = (job.weight / self.total_weight) * 100
            else:
                attached_job.cost_allocation_percentage = 0
    
    @frappe.whitelist()
    def add_air_freight_job(self, air_freight_job):
        """Add an Air Shipment to the consolidation"""
        # Check if job is already in consolidation
        existing_package = frappe.db.exists("Air Consolidation Packages", {
            "air_freight_job": air_freight_job,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Air Shipment is already included in this consolidation"))
        
        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.air_freight_job = air_freight_job
        
        # Get job details
        job = frappe.get_doc("Air Shipment", air_freight_job)
        package.shipper = job.shipper
        package.consignee = job.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = job.packs or 1
        package.package_weight = job.weight or 0
        package.package_volume = job.volume or 0
        package.commodity = job.description
        package.contains_dangerous_goods = job.contains_dangerous_goods or 0
        
        # Update the attached jobs table
        self.update_attached_jobs_table()
        
        self.save()
        return package
    
    @frappe.whitelist()
    def remove_air_freight_job(self, air_freight_job):
        """Remove an Air Shipment from the consolidation"""
        # Remove from consolidation packages
        packages_to_remove = []
        for package in self.consolidation_packages:
            if package.air_freight_job == air_freight_job:
                packages_to_remove.append(package)
        
        for package in packages_to_remove:
            self.remove(package)
        
        # Update the attached jobs table
        self.update_attached_jobs_table()
        
        # Clear consolidation reference from the job
        frappe.db.set_value("Air Shipment", air_freight_job, {
            "consolidation_reference": None,
            "consolidation_status": None
        })
        
        self.save()
        return True
    
    @frappe.whitelist()
    def get_consolidation_summary(self):
        """Get comprehensive consolidation summary"""
        summary = {
            "consolidation_id": self.name,
            "status": self.status,
            "consolidation_type": self.consolidation_type,
            "route": f"{self.origin_airport} → {self.destination_airport}",
            "departure": self.departure_date,
            "arrival": self.arrival_date,
            "airline": self.airline,
            "flight_number": self.flight_number,
            "total_jobs": len(self.attached_air_freight_jobs),
            "total_packages": self.total_packages,
            "total_weight": self.total_weight,
            "total_volume": self.total_volume,
            "chargeable_weight": self.chargeable_weight,
            "consolidation_ratio": self.consolidation_ratio,
            "cost_per_kg": self.cost_per_kg,
            "attached_jobs": [],
            "routes": [],
            "charges": []
        }
        
        # Add attached jobs information
        for job in self.attached_air_freight_jobs:
            summary["attached_jobs"].append({
                "air_freight_job": job.air_freight_job,
                "shipper": job.shipper,
                "consignee": job.consignee,
                "route": f"{job.origin_port} → {job.destination_port}",
                "weight": job.weight,
                "volume": job.volume,
                "value": job.value,
                "currency": job.currency,
                "dangerous_goods": job.contains_dangerous_goods,
                "dg_status": job.dg_compliance_status,
                "consolidation_status": job.consolidation_status,
                "cost_allocation": job.cost_allocation_percentage
            })
        
        # Add route information
        for route in self.consolidation_routes:
            summary["routes"].append({
                "sequence": route.route_sequence,
                "origin": route.origin_airport,
                "destination": route.destination_airport,
                "airline": route.airline,
                "flight_number": route.flight_number,
                "departure": route.departure_date,
                "arrival": route.arrival_date,
                "status": route.route_status,
                "capacity_kg": route.cargo_capacity_kg,
                "capacity_volume": route.cargo_capacity_volume,
                "utilization": route.utilization_percentage
            })
        
        # Add charges information
        for charge in self.consolidation_charges:
            summary["charges"].append({
                "type": charge.charge_type,
                "category": charge.charge_category,
                "basis": charge.charge_basis,
                "rate": charge.rate,
                "total_amount": charge.total_amount,
                "status": charge.charge_status
            })
        
        return summary
    
    def validate_accounts(self):
        """Validate accounting fields"""
        if not self.company:
            frappe.throw(_("Company is required"))
        
        # Validate cost center belongs to company
        if self.cost_center:
            cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
            if cost_center_company and cost_center_company != self.company:
                frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                    self.cost_center, self.company))
        
        # Validate profit center belongs to company
        if self.profit_center:
            profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
            if profit_center_company and profit_center_company != self.company:
                frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                    self.profit_center, self.company))
        
        # Validate branch belongs to company
        if self.branch:
            branch_company = frappe.db.get_value("Branch", self.branch, "company")
            if branch_company and branch_company != self.company:
                frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                    self.branch, self.company))
    
    def create_job_reference_if_needed(self):
        """Create Job Reference when document is first saved"""
        # Only create if this is a new document and job_reference is not set
        if not self.job_reference and not self.get("__islocal"):
            # Check if this is the first save (no existing Job Reference)
            existing_job_ref = frappe.db.get_value("Job Reference", {
                "job_type": "Air Consolidation",
                "job_no": self.name
            })
            
            if not existing_job_ref:
                # Create Job Reference
                job_ref = frappe.new_doc("Job Reference")
                job_ref.job_type = "Air Consolidation"
                job_ref.job_no = self.name
                job_ref.company = self.company
                job_ref.branch = self.branch
                job_ref.cost_center = self.cost_center
                job_ref.profit_center = self.profit_center
                job_ref.recognition_date = frappe.utils.today()
                job_ref.insert(ignore_permissions=True)
                
                # Set the job_reference field
                self.job_reference = job_ref.name
                
                frappe.msgprint(_("Job Reference {0} created successfully").format(job_ref.name))
