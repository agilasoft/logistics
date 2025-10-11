import frappe
from frappe.model.document import Document
from frappe import _


class AirConsolidationPackages(Document):
    website = frappe._dict(
        condition_field="consolidation_status",
        template="templates/air_consolidation_packages.html"
    )
    def validate(self):
        """Validate Air Consolidation Packages document"""
        self.validate_package_data()
        self.calculate_total_charge()
        self.validate_dangerous_goods()
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_consolidation_status()
        self.calculate_cost_allocation()
    
    def validate_package_data(self):
        """Validate package data integrity"""
        if not self.package_weight or self.package_weight <= 0:
            frappe.throw(_("Package weight must be greater than 0"))
        
        if not self.package_count or self.package_count <= 0:
            frappe.throw(_("Package count must be greater than 0"))
        
        # Validate temperature range
        if self.temperature_controlled:
            if self.min_temperature and self.max_temperature:
                if self.min_temperature >= self.max_temperature:
                    frappe.throw(_("Minimum temperature must be less than maximum temperature"))
    
    def calculate_total_charge(self):
        """Calculate total charge for the package"""
        total = 0
        
        # Add base charges
        if self.base_charge:
            total += self.base_charge
        
        if self.weight_charge:
            total += self.weight_charge
        
        if self.volume_charge:
            total += self.volume_charge
        
        if self.surcharges:
            total += self.surcharges
        
        self.total_charge = total
    
    def validate_dangerous_goods(self):
        """Validate dangerous goods requirements"""
        if self.contains_dangerous_goods:
            if not self.dg_class:
                frappe.throw(_("DG Class is required for dangerous goods"))
            
            if not self.un_number:
                frappe.throw(_("UN Number is required for dangerous goods"))
            
            if not self.proper_shipping_name:
                frappe.throw(_("Proper Shipping Name is required for dangerous goods"))
            
            if not self.emergency_contact:
                frappe.throw(_("Emergency Contact is required for dangerous goods"))
    
    def update_consolidation_status(self):
        """Update consolidation status based on package status"""
        if self.consolidation_status == "Pending":
            if self.check_in_time:
                self.consolidation_status = "Accepted"
        elif self.consolidation_status == "Accepted":
            if self.check_out_time:
                self.consolidation_status = "In Transit"
        elif self.consolidation_status == "In Transit":
            # Status will be updated by parent consolidation
            pass
    
    def calculate_cost_allocation(self):
        """Calculate cost allocation percentage"""
        if self.parent:
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            
            if consolidation.total_weight > 0:
                self.cost_allocation = (self.package_weight / consolidation.total_weight) * 100
            else:
                self.cost_allocation = 0
    
    @frappe.whitelist()
    def get_package_details(self):
        """Get detailed package information"""
        return {
            "package_reference": self.package_reference,
            "air_freight_job": self.air_freight_job,
            "shipper": self.shipper,
            "consignee": self.consignee,
            "weight": self.package_weight,
            "volume": self.package_volume,
            "value": self.value,
            "currency": self.currency,
            "dangerous_goods": self.contains_dangerous_goods,
            "dg_class": self.dg_class,
            "un_number": self.un_number,
            "status": self.consolidation_status,
            "total_charge": self.total_charge
        }
    
    @frappe.whitelist()
    def update_package_status(self, new_status):
        """Update package consolidation status"""
        if new_status not in ["Pending", "Accepted", "In Transit", "Delivered", "Exception"]:
            frappe.throw(_("Invalid status: {0}".format(new_status)))
        
        self.consolidation_status = new_status
        
        # Update timestamps based on status
        if new_status == "Accepted" and not self.check_in_time:
            self.check_in_time = frappe.utils.now()
        elif new_status == "In Transit" and not self.check_out_time:
            self.check_out_time = frappe.utils.now()
        
        self.save()
        
        # Update parent consolidation status
        if self.parent:
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            consolidation.update_consolidation_status()
            consolidation.save()
    
    @frappe.whitelist()
    def calculate_volume_weight(self):
        """Calculate volume weight for the package"""
        if self.package_volume:
            # IATA standard volume weight factor: 167 kg/m³
            volume_weight = self.package_volume * 167
            return volume_weight
        return 0
    
    @frappe.whitelist()
    def get_chargeable_weight(self):
        """Get chargeable weight (higher of actual weight or volume weight)"""
        actual_weight = self.package_weight or 0
        volume_weight = self.calculate_volume_weight()
        
        return max(actual_weight, volume_weight)
    
    @frappe.whitelist()
    def validate_compatibility(self, other_package_id):
        """Validate compatibility with another package"""
        other_package = frappe.get_doc("Air Consolidation Packages", other_package_id)
        
        # Check dangerous goods compatibility
        if self.contains_dangerous_goods and other_package.contains_dangerous_goods:
            if not self.is_dg_compatible(other_package):
                return {
                    "compatible": False,
                    "reason": "Incompatible dangerous goods classes"
                }
        
        # Check temperature requirements
        if self.temperature_controlled and other_package.temperature_controlled:
            if not self.is_temperature_compatible(other_package):
                return {
                    "compatible": False,
                    "reason": "Incompatible temperature requirements"
                }
        
        return {"compatible": True}
    
    def is_dg_compatible(self, other_package):
        """Check if dangerous goods are compatible"""
        if not self.dg_class or not other_package.dg_class:
            return True
        
        # Define incompatible DG class pairs
        incompatible_pairs = [
            ("1", "2"),  # Explosives with gases
            ("3", "5"),  # Flammable liquids with oxidizing substances
            ("4", "5"),  # Flammable solids with oxidizing substances
        ]
        
        for class1, class2 in incompatible_pairs:
            if (self.dg_class == class1 and other_package.dg_class == class2) or \
               (self.dg_class == class2 and other_package.dg_class == class1):
                return False
        
        return True
    
    def is_temperature_compatible(self, other_package):
        """Check if temperature requirements are compatible"""
        if not self.temperature_controlled or not other_package.temperature_controlled:
            return True
        
        # Check if temperature ranges overlap
        self_min = self.min_temperature or -273
        self_max = self.max_temperature or 1000
        other_min = other_package.min_temperature or -273
        other_max = other_package.max_temperature or 1000
        
        # Ranges overlap if max of min values is less than min of max values
        return max(self_min, other_min) < min(self_max, other_max)
