# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, flt


class PeriodicBilling(Document):
	def validate(self):
		"""Validate periodic billing document."""
		self.validate_contract_setup()
		self.validate_date_range()
	
	def before_submit(self):
		"""Validate before submitting periodic billing document."""
		self.validate_total_amount()
	
	def validate_total_amount(self):
		"""Validate that no charge items have zero amount."""
		if not self.charges:
			frappe.throw(_("Cannot submit Periodic Billing with no charges. Please add charges first."))
		
		# Check each charge item for zero amount
		zero_amount_items = []
		for idx, charge in enumerate(self.charges, start=1):
			charge_total = flt(charge.get("total", 0) or 0)
			if charge_total == 0:
				item_name = charge.get("item_name") or charge.get("item") or _("Item {0}").format(idx)
				zero_amount_items.append(item_name)
		
		if zero_amount_items:
			items_list = ", ".join(zero_amount_items)
			frappe.throw(_("Cannot submit Periodic Billing with zero amount items: {0}. Please ensure all charge items have a non-zero amount.").format(items_list))
	
	def after_insert(self):
		"""Create Job Costing Number after document is inserted"""
		self.create_job_costing_number_if_needed()
		# Save the document to persist the job_costing_number field
		if self.job_costing_number:
			self.db_set("job_costing_number", self.job_costing_number, commit=False)
			frappe.db.commit()
	
	def validate_contract_setup(self):
		"""Validate that contract setup is properly configured."""
		if self.warehouse_contract:
			contract = frappe.get_doc("Warehouse Contract", self.warehouse_contract)
			if contract.docstatus != 1:
				frappe.throw(_("Warehouse Contract {0} is not submitted. Please submit the contract first.").format(self.warehouse_contract))
			
			# Check if contract has valid items
			if not contract.items:
				frappe.throw(_("Warehouse Contract {0} has no contract items. Please add contract items first.").format(self.warehouse_contract))
			
			# Check if contract is valid for the billing period
			if contract.valid_until and self.date_to and contract.valid_until < getdate(self.date_to):
				frappe.msgprint(_("Warning: Contract {0} expires on {1}, which is before the billing period ends on {2}.").format(
					self.warehouse_contract, contract.valid_until, self.date_to
				))
	
	def validate_date_range(self):
		"""Validate date range."""
		if self.date_from and self.date_to and getdate(self.date_from) > getdate(self.date_to):
			frappe.throw(_("Date From cannot be later than Date To."))
	
	def get_contract_setup_summary(self):
		"""Get summary of contract setup for this periodic billing."""
		if not self.warehouse_contract:
			return None
		
		contract = frappe.get_doc("Warehouse Contract", self.warehouse_contract)
		summary = {
			"contract_name": self.warehouse_contract,
			"customer": contract.customer,
			"valid_until": contract.valid_until,
			"total_items": len(contract.items),
			"storage_charges": len([item for item in contract.items if item.storage_charge]),
			"inbound_charges": len([item for item in contract.items if item.inbound_charge]),
			"outbound_charges": len([item for item in contract.items if item.outbound_charge]),
			"transfer_charges": len([item for item in contract.items if item.transfer_charge]),
			"vas_charges": len([item for item in contract.items if item.vas_charge]),
			"stocktake_charges": len([item for item in contract.items if item.stocktake_charge]),
		}
		return summary
	
	@frappe.whitelist()
	def get_contract_setup_summary_api(self):
		"""Get contract setup summary for frontend."""
		return self.get_contract_setup_summary()
	
	def create_job_costing_number_if_needed(self):
		"""Create Job Costing Number when document is first saved"""
		# Only create if job_costing_number is not set
		if not self.job_costing_number:
			# Check if this is the first save (no existing Job Costing Number)
			existing_job_ref = frappe.db.get_value("Job Costing Number", {
				"job_type": "Periodic Billing",
				"job_no": self.name
			})
			
			if not existing_job_ref:
				# Create Job Costing Number
				job_ref = frappe.new_doc("Job Costing Number")
				job_ref.job_type = "Periodic Billing"
				job_ref.job_no = self.name
				job_ref.company = self.company
				job_ref.branch = self.branch
				job_ref.cost_center = self.cost_center
				job_ref.profit_center = self.profit_center
				# Use periodic billing's date_from as job_open_date
				job_ref.job_open_date = self.date_from
				job_ref.insert(ignore_permissions=True)
				
				# Set the job_costing_number field
				self.job_costing_number = job_ref.name
				
				frappe.msgprint(_("Job Costing Number {0} created successfully").format(job_ref.name))
