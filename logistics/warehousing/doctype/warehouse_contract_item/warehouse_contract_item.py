# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class WarehouseContractItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item_charge: DF.Link
		description: DF.Text | None
		rate: DF.Currency
		currency: DF.Link
		handling_uom: DF.Link | None
		time_uom: DF.Link | None
		storage_uom: DF.Link | None
		storage_charge: DF.Check
		inbound_charge: DF.Check
		outbound_charge: DF.Check
		transfer_charge: DF.Check
		vas_charge: DF.Check
		stocktake_charge: DF.Check
		billing_method: DF.Literal["Per Volume", "Per Weight", "Per Piece", "Per Container", "Per Hour", "Per Handling Unit", "High Water Mark"]
		volume_uom: DF.Link | None
		volume_calculation_method: DF.Literal["Daily Volume", "Peak Volume", "Average Volume", "End Volume"]
		handling_unit_type: DF.Link | None
		storage_type: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		"""Apply default UOMs when creating new contract item."""
		self.apply_default_uoms()
	
	def on_update(self):
		"""Handle updates to contract item."""
		pass
	
	def apply_default_uoms(self):
		"""Apply default UOMs from warehouse settings."""
		try:
			# Get default UOMs from warehouse settings
			default_uoms = frappe.call(
				"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.get_default_uoms"
			)
			
			if not default_uoms:
				return
			
			# Apply defaults based on billing method
			if self.billing_method == "Per Volume" and default_uoms.get("volume"):
				self.volume_uom = default_uoms["volume"]
			elif self.billing_method == "Per Weight" and default_uoms.get("weight"):
				self.uom = default_uoms["weight"]
			elif self.billing_method == "Per Piece" and default_uoms.get("piece"):
				self.uom = default_uoms["piece"]
			elif self.billing_method == "Per Container" and default_uoms.get("container"):
				self.uom = default_uoms["container"]
			elif self.billing_method == "Per Hour" and default_uoms.get("hour"):
				self.uom = default_uoms["hour"]
			elif self.billing_method == "Per Handling Unit" and default_uoms.get("handling_unit"):
				self.uom = default_uoms["handling_unit"]
					
		except Exception as e:
			frappe.log_error(f"Error applying default UOMs: {str(e)}")
	
	def validate_billing_methods(self):
		"""Validate billing methods for each charge type."""
		try:
			# Validate billing method for any active charge type
			if (self.storage_charge or self.inbound_charge or self.outbound_charge or 
				self.transfer_charge or self.vas_charge or self.stocktake_charge) and self.billing_method:
				self.validate_billing_method("general", self.billing_method)
			
				
		except Exception as e:
			frappe.log_error(f"Error validating billing methods: {str(e)}")
	
	def validate_billing_method(self, charge_type: str, billing_method: str):
		"""Validate a specific billing method for a charge type."""
		try:
			result = frappe.call(
				"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.validate_uom_for_billing_method",
				billing_method=billing_method,
				uom=self.volume_uom or ""
			)
			
			if result and not result.get("valid", True):
				frappe.throw(_(result.get("message", f"Invalid billing method for {charge_type}")))
				
		except Exception as e:
			frappe.log_error(f"Error validating billing method: {str(e)}")


# =============================================================================
# API Functions
# =============================================================================

@frappe.whitelist()
def apply_default_uoms(contract_item_name: str):
	"""
	Apply default UOMs to a contract item.
	
	Args:
		contract_item_name: Name of the Warehouse Contract Item
	
	Returns:
		Dict with success status
	"""
	try:
		return frappe.call(
			"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.apply_default_uoms_to_contract_item",
			contract_item_name=contract_item_name
		)
	except Exception as e:
		frappe.log_error(f"Error applying default UOMs: {str(e)}")
		return {"error": str(e)}


@frappe.whitelist()
def get_default_uom_for_billing_method(billing_method: str):
	"""
	Get default UOM for a billing method.
	
	Args:
		billing_method: Billing method name
	
	Returns:
		Default UOM for the billing method
	"""
	try:
		return frappe.call(
			"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.get_default_uom_for_billing_method",
			billing_method=billing_method
		)
	except Exception as e:
		frappe.log_error(f"Error getting default UOM for billing method: {str(e)}")
		return None


@frappe.whitelist()
def validate_uom_for_billing_method(billing_method: str, uom: str):
	"""
	Validate a UOM for a billing method.
	
	Args:
		billing_method: Billing method name
		uom: UOM to validate
	
	Returns:
		Dict with validation result
	"""
	try:
		return frappe.call(
			"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.validate_uom_for_billing_method",
			billing_method=billing_method,
			uom=uom
		)
	except Exception as e:
		frappe.log_error(f"Error validating UOM for billing method: {str(e)}")
		return {"valid": False, "error": str(e)}


@frappe.whitelist()
def get_volume_billing_settings():
	"""
	Get volume billing settings.
	
	Returns:
		Dict with volume billing settings
	"""
	try:
		return frappe.call(
			"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.get_volume_billing_settings"
		)
	except Exception as e:
		frappe.log_error(f"Error getting volume billing settings: {str(e)}")
		return None


@frappe.whitelist()
def reset_to_defaults(contract_item_name: str):
	"""
	Reset contract item UOMs to defaults.
	
	Args:
		contract_item_name: Name of the Warehouse Contract Item
	
	Returns:
		Dict with success status
	"""
	try:
		return frappe.call(
			"logistics.warehousing.doctype.warehouse_settings.warehouse_settings.apply_default_uoms_to_contract_item",
			contract_item_name=contract_item_name
		)
	except Exception as e:
		frappe.log_error(f"Error resetting to defaults: {str(e)}")
		return {"error": str(e)}