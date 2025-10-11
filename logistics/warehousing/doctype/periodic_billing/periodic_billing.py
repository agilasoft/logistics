# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate


class PeriodicBilling(Document):
	def validate(self):
		"""Validate periodic billing document."""
		self.validate_contract_setup()
		self.validate_date_range()
	
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
