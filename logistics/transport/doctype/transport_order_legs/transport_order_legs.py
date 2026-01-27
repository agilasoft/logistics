# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TransportOrderLegs(Document):
	def validate(self):
		"""Auto-fill pick_address and drop_address from facility primary addresses"""
		self.auto_fill_addresses()
	
	def auto_fill_addresses(self):
		"""Auto-fill pick_address and drop_address based on facility primary addresses"""
		# Auto-fill pick_address if not already set
		if not self.pick_address and self.facility_type_from and self.facility_from:
			primary_address = self._get_primary_address(self.facility_type_from, self.facility_from)
			if primary_address:
				self.pick_address = primary_address
		
		# Auto-fill drop_address if not already set
		if not self.drop_address and self.facility_type_to and self.facility_to:
			primary_address = self._get_primary_address(self.facility_type_to, self.facility_to)
			if primary_address:
				self.drop_address = primary_address
	
	def _get_primary_address(self, facility_type, facility_name):
		"""Get the primary address for a facility"""
		try:
			# Map facility types to their primary address field names
			primary_address_fields = {
				"Shipper": "shipper_primary_address",
				"Consignee": "consignee_primary_address", 
				"Container Yard": "containeryard_primary_address",
				"Container Depot": "containerdepot_primary_address",
				"Container Freight Station": "cfs_primary_address",
				"Transport Terminal": "transportterminal_primary_address"
			}
			
			# Get the primary address field name for this facility type
			primary_address_field = primary_address_fields.get(facility_type)
			
			if primary_address_field:
				# Get the facility document and its primary address
				facility_doc = frappe.get_doc(facility_type, facility_name)
				primary_address = getattr(facility_doc, primary_address_field, None)
				
				if primary_address:
					return primary_address
			
			# Fallback: For facility types without primary address fields (Storage Facility, Truck Park, Sorting Hub, Terminal)
			# or if primary address is not set, get addresses linked to this facility
			addresses = frappe.get_all("Address",
				filters={
					"link_doctype": facility_type,
					"link_name": facility_name
				},
				fields=["name", "is_primary_address", "is_shipping_address"],
				order_by="is_primary_address DESC, is_shipping_address DESC, creation ASC"
			)
			
			if addresses:
				# Return the primary address, or shipping address, or first address
				for address in addresses:
					if address.is_primary_address or address.is_shipping_address:
						return address.name
				return addresses[0].name
			
		except Exception as e:
			frappe.log_error(f"Error getting primary address for {facility_type} {facility_name}: {str(e)}")
		
		return None


@frappe.whitelist()
def get_primary_address(facility_type: str, facility_name: str):
	"""Get the primary address for a facility"""
	if not facility_type or not facility_name:
		return None
	
	try:
		# Map facility types to their primary address field names
		primary_address_fields = {
			"Shipper": "shipper_primary_address",
			"Consignee": "consignee_primary_address", 
			"Container Yard": "containeryard_primary_address",
			"Container Depot": "containerdepot_primary_address",
			"Container Freight Station": "cfs_primary_address",
			"Transport Terminal": "transportterminal_primary_address"
		}
		
		# Get the primary address field name for this facility type
		primary_address_field = primary_address_fields.get(facility_type)
		
		if primary_address_field:
			# Get the facility document and its primary address
			facility_doc = frappe.get_doc(facility_type, facility_name)
			primary_address = getattr(facility_doc, primary_address_field, None)
			
			if primary_address:
				return primary_address
		
		# Fallback: For facility types without primary address fields (Storage Facility, Truck Park, Sorting Hub, Terminal)
		# or if primary address is not set, get addresses linked to this facility
		addresses = frappe.get_all("Address",
			filters={
				"link_doctype": facility_type,
				"link_name": facility_name
			},
			fields=["name", "is_primary_address", "is_shipping_address"],
			order_by="is_primary_address DESC, is_shipping_address DESC, creation ASC"
		)
		
		if addresses:
			# Return the primary address, or shipping address, or first address
			for address in addresses:
				if address.is_primary_address or address.is_shipping_address:
					return address.name
			return addresses[0].name
		
	except Exception as e:
		frappe.log_error(f"Error getting primary address for {facility_type} {facility_name}: {str(e)}")
	
	return None
