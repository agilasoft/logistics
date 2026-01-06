import frappe
from frappe.model.document import Document
from frappe import _


class AirConsolidationCharges(Document):
    website = frappe._dict(
        condition_field="charge_status",
        template="templates/air_consolidation_charges.html"
    )
    def validate(self):
        """Validate Air Consolidation Charges document"""
        self.validate_charge_data()
        self.calculate_charge_amount()
        self.calculate_allocated_amount()
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_charge_status()
    
    def validate_charge_data(self):
        """Validate charge data integrity"""
        if not self.charge_type:
            frappe.throw(_("Charge type is required"))
        
        if not self.charge_basis:
            frappe.throw(_("Charge basis is required"))
        
        if not self.rate or self.rate <= 0:
            frappe.throw(_("Rate must be greater than 0"))
        
        if not self.currency:
            frappe.throw(_("Currency is required"))
    
    def calculate_charge_amount(self):
        """Calculate charge amount based on basis and quantity"""
        if not self.rate or not self.quantity:
            return
        
        # Calculate base amount based on charge basis
        if self.charge_basis == "Per kg":
            self.base_amount = self.rate * self.quantity
        elif self.charge_basis == "Per m³":
            self.base_amount = self.rate * self.quantity
        elif self.charge_basis == "Per package":
            self.base_amount = self.rate * self.quantity
        elif self.charge_basis == "Per shipment":
            self.base_amount = self.rate
        elif self.charge_basis == "Fixed amount":
            self.base_amount = self.rate
        elif self.charge_basis == "Percentage":
            # For percentage, we need the base amount from parent consolidation
            if self.parent:
                consolidation = frappe.get_doc("Air Consolidation", self.parent)
                if consolidation.chargeable_weight:
                    self.base_amount = self.rate * (consolidation.chargeable_weight * 0.01)
                else:
                    self.base_amount = 0
            else:
                self.base_amount = 0
        
        # Calculate discount amount
        if self.discount_percentage and self.base_amount:
            self.discount_amount = self.base_amount * (self.discount_percentage / 100)
        else:
            self.discount_amount = 0
        
        # Calculate total amount
        self.total_amount = self.base_amount - self.discount_amount + (self.surcharge_amount or 0)
    
    def calculate_allocated_amount(self):
        """Calculate allocated amount based on allocation method"""
        if not self.parent or not self.total_amount:
            return
        
        consolidation = frappe.get_doc("Air Consolidation", self.parent)
        
        if self.allocation_method == "Equal":
            # Equal allocation among all attached jobs
            total_jobs = len(consolidation.attached_air_freight_jobs)
            if total_jobs > 0:
                self.allocated_amount = self.total_amount / total_jobs
            else:
                self.allocated_amount = 0
        
        elif self.allocation_method == "Weight-based":
            # Allocation based on weight percentage
            if self.allocation_percentage:
                self.allocated_amount = self.total_amount * (self.allocation_percentage / 100)
            else:
                self.allocated_amount = 0
        
        elif self.allocation_method == "Volume-based":
            # Allocation based on volume percentage
            if self.allocation_percentage:
                self.allocated_amount = self.total_amount * (self.allocation_percentage / 100)
            else:
                self.allocated_amount = 0
        
        elif self.allocation_method == "Value-based":
            # Allocation based on cargo value percentage
            if self.allocation_percentage:
                self.allocated_amount = self.total_amount * (self.allocation_percentage / 100)
            else:
                self.allocated_amount = 0
        
        else:
            # Custom allocation
            if self.allocation_percentage:
                self.allocated_amount = self.total_amount * (self.allocation_percentage / 100)
            else:
                self.allocated_amount = 0
    
    def update_charge_status(self):
        """Update charge status based on current data"""
        if not self.charge_status or self.charge_status == "Draft":
            if self.total_amount and self.total_amount > 0:
                self.charge_status = "Calculated"
    
    @frappe.whitelist()
    def get_charge_summary(self):
        """Get summary information for the charge"""
        return {
            "charge_type": self.charge_type,
            "charge_category": self.charge_category,
            "charge_basis": self.charge_basis,
            "rate": self.rate,
            "currency": self.currency,
            "quantity": self.quantity,
            "base_amount": self.base_amount,
            "discount_amount": self.discount_amount,
            "surcharge_amount": self.surcharge_amount,
            "total_amount": self.total_amount,
            "allocation_method": self.allocation_method,
            "allocation_percentage": self.allocation_percentage,
            "allocated_amount": self.allocated_amount,
            "charge_status": self.charge_status,
            "billing_status": self.billing_status,
            "payment_status": self.payment_status
        }
    
    @frappe.whitelist()
    def update_billing_status(self, new_status):
        """Update billing status for the charge"""
        if new_status not in ["Pending", "Billed", "Paid", "Overdue", "Cancelled"]:
            frappe.throw(_("Invalid billing status: {0}".format(new_status)))
        
        self.billing_status = new_status
        
        # Update payment status based on billing status
        if new_status == "Paid":
            self.payment_status = "Paid"
        elif new_status == "Overdue":
            self.payment_status = "Overdue"
        elif new_status == "Cancelled":
            self.payment_status = "Cancelled"
        else:
            self.payment_status = "Pending"
        
        self.save()
    
    @frappe.whitelist()
    def calculate_individual_allocation(self, job_weight, total_weight):
        """Calculate individual allocation for a specific job"""
        if not self.total_amount or total_weight <= 0:
            return 0
        
        # Calculate weight percentage
        weight_percentage = (job_weight / total_weight) * 100
        
        # Calculate allocated amount
        allocated_amount = self.total_amount * (weight_percentage / 100)
        
        return round(allocated_amount, 2)
    
    @frappe.whitelist()
    def get_charge_breakdown(self):
        """Get detailed charge breakdown"""
        breakdown = {
            "charge_type": self.charge_type,
            "charge_category": self.charge_category,
            "description": self.description,
            "charge_basis": self.charge_basis,
            "rate": self.rate,
            "currency": self.currency,
            "quantity": self.quantity,
            "unit_of_measure": self.unit_of_measure,
            "calculation_method": self.calculation_method,
            "base_amount": self.base_amount,
            "discount_percentage": self.discount_percentage,
            "discount_amount": self.discount_amount,
            "surcharge_amount": self.surcharge_amount,
            "total_amount": self.total_amount,
            "allocation_method": self.allocation_method,
            "allocation_percentage": self.allocation_percentage,
            "allocated_amount": self.allocated_amount,
            "charge_status": self.charge_status,
            "billing_status": self.billing_status,
            "payment_status": self.payment_status,
            "invoice_reference": self.invoice_reference
        }
        
        return breakdown
    
    @frappe.whitelist()
    def validate_charge_calculation(self):
        """Validate charge calculation for accuracy"""
        validation_result = {
            "valid": True,
            "issues": []
        }
        
        # Check if base amount calculation is correct
        if self.charge_basis in ["Per kg", "Per m³", "Per package"]:
            expected_base = self.rate * self.quantity
            if abs(self.base_amount - expected_base) > 0.01:
                validation_result["valid"] = False
                validation_result["issues"].append("Base amount calculation is incorrect")
        
        # Check if discount calculation is correct
        if self.discount_percentage and self.base_amount:
            expected_discount = self.base_amount * (self.discount_percentage / 100)
            if abs(self.discount_amount - expected_discount) > 0.01:
                validation_result["valid"] = False
                validation_result["issues"].append("Discount calculation is incorrect")
        
        # Check if total amount calculation is correct
        expected_total = self.base_amount - self.discount_amount + (self.surcharge_amount or 0)
        if abs(self.total_amount - expected_total) > 0.01:
            validation_result["valid"] = False
            validation_result["issues"].append("Total amount calculation is incorrect")
        
        return validation_result
    
    @frappe.whitelist()
    def apply_discount(self, discount_percentage):
        """Apply discount to the charge"""
        if not 0 <= discount_percentage <= 100:
            frappe.throw(_("Discount percentage must be between 0 and 100"))
        
        self.discount_percentage = discount_percentage
        self.calculate_charge_amount()
        self.save()
        
        return {
            "discount_percentage": self.discount_percentage,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount
        }
    
    @frappe.whitelist()
    def add_surcharge(self, surcharge_amount, description=""):
        """Add surcharge to the charge"""
        if surcharge_amount < 0:
            frappe.throw(_("Surcharge amount cannot be negative"))
        
        self.surcharge_amount = (self.surcharge_amount or 0) + surcharge_amount
        self.calculate_charge_amount()
        self.save()
        
        return {
            "surcharge_amount": self.surcharge_amount,
            "total_amount": self.total_amount
        }
