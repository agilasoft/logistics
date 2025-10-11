import frappe
from frappe.model.document import Document
from frappe import _


class AirConsolidationRoutes(Document):
    website = frappe._dict(
        condition_field="route_status",
        template="templates/air_consolidation_routes.html"
    )
    def validate(self):
        """Validate Air Consolidation Routes document"""
        self.validate_route_data()
        self.calculate_transit_time()
        self.calculate_capacity_utilization()
        self.calculate_total_cost()
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_route_status()
    
    def validate_route_data(self):
        """Validate route data integrity"""
        if not self.origin_airport or not self.destination_airport:
            frappe.throw(_("Origin and destination airports are required"))
        
        if self.origin_airport == self.destination_airport:
            frappe.throw(_("Origin and destination airports cannot be the same"))
        
        if not self.airline or not self.flight_number:
            frappe.throw(_("Airline and flight number are required"))
        
        # Validate dates
        if self.departure_date and self.arrival_date:
            if self.departure_date >= self.arrival_date:
                frappe.throw(_("Departure date must be before arrival date"))
    
    def calculate_transit_time(self):
        """Calculate transit time between departure and arrival"""
        if self.departure_date and self.arrival_date:
            departure = frappe.utils.get_datetime(f"{self.departure_date} {self.departure_time}")
            arrival = frappe.utils.get_datetime(f"{self.arrival_date} {self.arrival_time}")
            
            transit_time = (arrival - departure).total_seconds() / 3600  # hours
            self.transit_time_hours = round(transit_time, 1)
    
    def calculate_capacity_utilization(self):
        """Calculate capacity utilization for the route"""
        if self.cargo_capacity_kg and self.parent:
            # Get total weight from parent consolidation
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            if consolidation.total_weight:
                utilization = (consolidation.total_weight / self.cargo_capacity_kg) * 100
                self.utilization_percentage = round(utilization, 1)
                
                # Calculate available capacity
                self.available_capacity_kg = self.cargo_capacity_kg - consolidation.total_weight
                
                if self.available_capacity_kg < 0:
                    self.available_capacity_kg = 0
        
        if self.cargo_capacity_volume and self.parent:
            # Get total volume from parent consolidation
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            if consolidation.total_volume:
                volume_utilization = (consolidation.total_volume / self.cargo_capacity_volume) * 100
                
                # Calculate available volume capacity
                self.available_capacity_volume = self.cargo_capacity_volume - consolidation.total_volume
                
                if self.available_capacity_volume < 0:
                    self.available_capacity_volume = 0
    
    def calculate_total_cost(self):
        """Calculate total cost per kg for the route"""
        total_cost = 0
        
        # Add base rate
        if self.base_rate_per_kg:
            total_cost += self.base_rate_per_kg
        
        # Add surcharges
        if self.fuel_surcharge_rate:
            total_cost += self.fuel_surcharge_rate
        
        if self.security_surcharge_rate:
            total_cost += self.security_surcharge_rate
        
        if self.war_risk_surcharge:
            total_cost += self.war_risk_surcharge
        
        if self.terminal_handling_charges:
            total_cost += self.terminal_handling_charges
        
        self.total_cost_per_kg = total_cost
    
    def update_route_status(self):
        """Update route status based on current data"""
        if not self.route_status or self.route_status == "Available":
            if self.departure_date and self.departure_date <= frappe.utils.today():
                self.route_status = "Booked"
            elif self.arrival_date and self.arrival_date <= frappe.utils.today():
                self.route_status = "Completed"
    
    @frappe.whitelist()
    def get_route_summary(self):
        """Get summary information for the route"""
        return {
            "route_sequence": self.route_sequence,
            "route_type": self.route_type,
            "origin": self.origin_airport,
            "destination": self.destination_airport,
            "airline": self.airline,
            "flight_number": self.flight_number,
            "departure": f"{self.departure_date} {self.departure_time}",
            "arrival": f"{self.arrival_date} {self.arrival_time}",
            "transit_time": self.transit_time_hours,
            "capacity_kg": self.cargo_capacity_kg,
            "capacity_volume": self.cargo_capacity_volume,
            "utilization": self.utilization_percentage,
            "available_capacity": self.available_capacity_kg,
            "total_cost_per_kg": self.total_cost_per_kg,
            "status": self.route_status,
            "booking_status": self.booking_status
        }
    
    @frappe.whitelist()
    def check_cargo_compatibility(self, cargo_type, weight, volume):
        """Check if cargo is compatible with this route"""
        compatibility = {
            "compatible": True,
            "issues": []
        }
        
        # Check weight capacity
        if self.cargo_capacity_kg and weight > self.available_capacity_kg:
            compatibility["compatible"] = False
            compatibility["issues"].append("Weight exceeds available capacity")
        
        # Check volume capacity
        if self.cargo_capacity_volume and volume > self.available_capacity_volume:
            compatibility["compatible"] = False
            compatibility["issues"].append("Volume exceeds available capacity")
        
        # Check cargo type restrictions
        if cargo_type == "dangerous_goods" and not self.dangerous_goods_allowed:
            compatibility["compatible"] = False
            compatibility["issues"].append("Dangerous goods not allowed on this route")
        
        if cargo_type == "live_animals" and not self.live_animals_allowed:
            compatibility["compatible"] = False
            compatibility["issues"].append("Live animals not allowed on this route")
        
        if cargo_type == "refrigerated" and not self.refrigerated_cargo_allowed:
            compatibility["compatible"] = False
            compatibility["issues"].append("Refrigerated cargo not allowed on this route")
        
        if cargo_type == "oversized" and not self.oversized_cargo_allowed:
            compatibility["compatible"] = False
            compatibility["issues"].append("Oversized cargo not allowed on this route")
        
        return compatibility
    
    @frappe.whitelist()
    def update_booking_status(self, new_status):
        """Update booking status for the route"""
        if new_status not in ["Pending", "Confirmed", "Cancelled", "Completed"]:
            frappe.throw(_("Invalid booking status: {0}".format(new_status)))
        
        self.booking_status = new_status
        
        # Update route status based on booking status
        if new_status == "Confirmed":
            self.route_status = "Booked"
        elif new_status == "Cancelled":
            self.route_status = "Cancelled"
        elif new_status == "Completed":
            self.route_status = "Completed"
        
        self.save()
        
        # Update parent consolidation if needed
        if self.parent:
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            consolidation.update_consolidation_status()
            consolidation.save()
    
    @frappe.whitelist()
    def calculate_route_score(self):
        """Calculate optimization score for this route"""
        score = 0
        
        # Cost factor (lower is better)
        if self.total_cost_per_kg:
            score += self.total_cost_per_kg * 0.4
        
        # Time factor (lower is better)
        if self.transit_time_hours:
            score += self.transit_time_hours * 0.3
        
        # Capacity utilization factor (higher utilization is better)
        if self.utilization_percentage:
            score -= (self.utilization_percentage / 100) * 0.2
        
        # Connection time factor (shorter is better)
        if self.connection_time_hours:
            score += self.connection_time_hours * 0.1
        
        return round(score, 2)
    
    @frappe.whitelist()
    def get_route_alternatives(self):
        """Get alternative routes for the same origin-destination pair"""
        if not self.origin_airport or not self.destination_airport:
            return []
        
        # Find other routes with same origin-destination
        alternatives = frappe.get_all("Air Consolidation Routes", 
            filters={
                "origin_airport": self.origin_airport,
                "destination_airport": self.destination_airport,
                "name": ["!=", self.name]
            },
            fields=["name", "airline", "flight_number", "departure_date", "arrival_date", 
                   "total_cost_per_kg", "transit_time_hours", "route_status"],
            order_by="total_cost_per_kg"
        )
        
        return alternatives
