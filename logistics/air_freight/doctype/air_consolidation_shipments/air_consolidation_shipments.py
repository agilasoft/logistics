import frappe
from frappe.model.document import Document
from frappe import _


class AirConsolidationShipments(Document):
    website = frappe._dict(
        condition_field="consolidation_status",
        template="templates/air_consolidation_shipments.html"
    )
    def validate(self):
        """Validate Air Consolidation Shipments document"""
        self.validate_air_freight_job()
        self.update_job_data()
        self.calculate_total_charge()
        self.calculate_cost_allocation()
    
    def before_save(self):
        """Actions before saving the document"""
        self.update_consolidation_status()
    
    def validate_air_freight_job(self):
        """Validate that the Air Shipment exists and is not already in another consolidation"""
        if not self.air_freight_job:
            frappe.throw(_("Air Shipment is required"))
        
        # Check if job exists
        if not frappe.db.exists("Air Shipment", self.air_freight_job):
            frappe.throw(_("Air Shipment {0} does not exist".format(self.air_freight_job)))
        
        # Check if job is already in another consolidation
        existing_consolidation = frappe.db.get_value("Air Consolidation Packages", {
            "air_freight_job": self.air_freight_job,
            "parent": ["!=", self.parent]
        }, "parent")
        
        if existing_consolidation:
            frappe.throw(_("Air Shipment {0} is already part of consolidation {1}".format(
                self.air_freight_job, existing_consolidation)))
    
    def update_job_data(self):
        """Update data from the Air Shipment"""
        if self.air_freight_job:
            job = frappe.get_doc("Air Shipment", self.air_freight_job)
            
            # Update basic information
            self.job_status = job.status
            self.booking_date = job.booking_date
            self.shipper = job.shipper
            self.consignee = job.consignee
            self.origin_port = job.origin_port
            self.destination_port = job.destination_port
            
            # Update cargo details
            self.weight = job.weight
            self.volume = job.volume
            self.packs = job.packs
            self.value = job.gooda_value
            self.currency = job.currency
            self.incoterm = job.incoterm
            
            # Update dangerous goods information
            self.contains_dangerous_goods = job.contains_dangerous_goods or 0
            self.dg_compliance_status = job.dg_compliance_status
            self.dg_declaration_complete = job.dg_declaration_complete
    
    def calculate_total_charge(self):
        """Calculate total charge for the attached job"""
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
    
    def calculate_cost_allocation(self):
        """Calculate cost allocation percentage based on weight"""
        if self.parent and self.weight:
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            
            if consolidation.total_weight > 0:
                self.cost_allocation_percentage = (self.weight / consolidation.total_weight) * 100
            else:
                self.cost_allocation_percentage = 0
    
    def update_consolidation_status(self):
        """Update consolidation status based on job status"""
        if self.consolidation_status == "Pending":
            if self.check_in_time:
                self.consolidation_status = "Accepted"
        elif self.consolidation_status == "Accepted":
            if self.check_out_time:
                self.consolidation_status = "In Transit"
        elif self.consolidation_status == "In Transit":
            # Status will be updated by parent consolidation
            pass
    
    @frappe.whitelist()
    def get_job_summary(self):
        """Get summary information for the attached job"""
        return {
            "air_freight_job": self.air_freight_job,
            "job_status": self.job_status,
            "shipper": self.shipper,
            "consignee": self.consignee,
            "route": f"{self.origin_port} → {self.destination_port}",
            "weight": self.weight,
            "volume": self.volume,
            "value": self.value,
            "currency": self.currency,
            "dangerous_goods": self.contains_dangerous_goods,
            "dg_status": self.dg_compliance_status,
            "consolidation_status": self.consolidation_status,
            "total_charge": self.total_charge,
            "cost_allocation": self.cost_allocation_percentage
        }
    
    @frappe.whitelist()
    def update_job_status(self, new_status):
        """Update the consolidation status of the attached job"""
        if new_status not in ["Pending", "Accepted", "In Transit", "Delivered", "Exception"]:
            frappe.throw(_("Invalid status: {0}".format(new_status)))
        
        self.consolidation_status = new_status
        
        # Update timestamps based on status
        if new_status == "Accepted" and not self.check_in_time:
            self.check_in_time = frappe.utils.now()
        elif new_status == "In Transit" and not self.check_out_time:
            self.check_out_time = frappe.utils.now()
        
        self.save()
        
        # Update the original Air Shipment
        frappe.db.set_value("Air Shipment", self.air_freight_job, {
            "consolidation_reference": self.parent,
            "consolidation_status": new_status
        })
        
        # Update parent consolidation status
        if self.parent:
            consolidation = frappe.get_doc("Air Consolidation", self.parent)
            consolidation.update_consolidation_status()
            consolidation.save()
    
    @frappe.whitelist()
    def open_air_freight_job(self):
        """Open the Air Shipment in a new window"""
        return {
            "url": frappe.utils.get_url_to_form("Air Shipment", self.air_freight_job)
        }
    
    @frappe.whitelist()
    def get_consolidation_position(self):
        """Get the position of this job in the consolidation"""
        if self.parent:
            # Get all attached jobs sorted by position
            attached_jobs = frappe.get_all("Air Consolidation Shipments", 
                filters={"parent": self.parent},
                fields=["name", "position_in_consolidation", "air_freight_job"],
                order_by="position_in_consolidation"
            )
            
            for i, job in enumerate(attached_jobs):
                if job.air_freight_job == self.air_freight_job:
                    return {
                        "position": i + 1,
                        "total_jobs": len(attached_jobs)
                    }
        
        return {"position": 0, "total_jobs": 0}
    
    @frappe.whitelist()
    def calculate_individual_charges(self):
        """Calculate individual charges for this job within the consolidation"""
        if not self.parent:
            return {}
        
        consolidation = frappe.get_doc("Air Consolidation", self.parent)
        
        # Calculate charges based on consolidation charges and allocation
        individual_charges = {}
        
        for charge in consolidation.consolidation_charges:
            if charge.allocation_method == "Weight-based":
                allocation_factor = self.weight / consolidation.total_weight if consolidation.total_weight > 0 else 0
            elif charge.allocation_method == "Equal":
                total_jobs = len(consolidation.attached_air_freight_jobs)
                allocation_factor = 1 / total_jobs if total_jobs > 0 else 0
            else:
                allocation_factor = self.cost_allocation_percentage / 100
            
            individual_amount = charge.total_amount * allocation_factor
            individual_charges[charge.charge_type] = {
                "amount": individual_amount,
                "allocation_factor": allocation_factor,
                "charge_basis": charge.charge_basis
            }
        
        return individual_charges
    
    @frappe.whitelist()
    def validate_dangerous_goods_compatibility(self):
        """Validate dangerous goods compatibility with other jobs in consolidation"""
        if not self.contains_dangerous_goods:
            return {"compatible": True}
        
        if not self.parent:
            return {"compatible": True}
        
        consolidation = frappe.get_doc("Air Consolidation", self.parent)
        
        # Get DG information for this job
        job_dg_info = frappe.db.get_value("Air Shipment", self.air_freight_job, [
            "dg_class", "un_number", "proper_shipping_name"
        ], as_dict=True)
        
        # Check compatibility with other DG jobs in consolidation
        for attached_job in consolidation.attached_air_freight_jobs:
            if attached_job.air_freight_job != self.air_freight_job and attached_job.contains_dangerous_goods:
                other_dg_info = frappe.db.get_value("Air Shipment", attached_job.air_freight_job, [
                    "dg_class", "un_number", "proper_shipping_name"
                ], as_dict=True)
                
                if not self.is_dg_compatible(job_dg_info, other_dg_info):
                    return {
                        "compatible": False,
                        "conflict_with": attached_job.air_freight_job,
                        "reason": f"Incompatible DG classes: {job_dg_info.dg_class} vs {other_dg_info.dg_class}"
                    }
        
        return {"compatible": True}
    
    def is_dg_compatible(self, dg_info1, dg_info2):
        """Check if two dangerous goods are compatible"""
        if not dg_info1.dg_class or not dg_info2.dg_class:
            return True
        
        # Define incompatible DG class pairs
        incompatible_pairs = [
            ("1", "2"),  # Explosives with gases
            ("3", "5"),  # Flammable liquids with oxidizing substances
            ("4", "5"),  # Flammable solids with oxidizing substances
        ]
        
        for class1, class2 in incompatible_pairs:
            if (dg_info1.dg_class == class1 and dg_info2.dg_class == class2) or \
               (dg_info1.dg_class == class2 and dg_info2.dg_class == class1):
                return False
        
        return True
