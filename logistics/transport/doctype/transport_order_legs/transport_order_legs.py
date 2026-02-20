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
def get_addresses_for_facility(facility_type: str, facility_name: str):
	"""Get all addresses linked to a facility - used for frontend query filters
	This fetches addresses that appear in the facility's address_html field.
	Addresses are linked via Dynamic Links where link_doctype=facility_type and link_name=facility_name
	"""
	if not facility_type or not facility_name:
		return []
	
	try:
		# Get addresses linked to this facility via Dynamic Links
		# This is the same way frappe.contacts.render_address_and_contact works
		# The address_html field shows all addresses linked this way
		addresses = frappe.get_all("Dynamic Link",
			filters={
				"link_doctype": facility_type,
				"link_name": facility_name,
				"parenttype": "Address"
			},
			fields=["parent"],
			order_by="creation ASC"
		)
		
		if addresses:
			# Extract address names
			address_names = [addr.parent for addr in addresses]
			
			# Get full address details with proper ordering
			address_details = frappe.get_all("Address",
				filters={"name": ["in", address_names]},
				fields=["name", "address_title", "is_primary_address", "is_shipping_address"],
				order_by="is_primary_address DESC, is_shipping_address DESC, creation ASC"
			)
			
			if address_details:
				address_list = [addr.name for addr in address_details]
				debug_info = [f"{a.name} ({a.address_title or 'no title'})" for a in address_details]
				frappe.log_error(f"Found {len(address_list)} addresses for {facility_type} {facility_name}: {debug_info}", "get_addresses_for_facility_debug")
				return address_list
		
		# Log if no addresses found
		facility_exists = frappe.db.exists(facility_type, facility_name)
		frappe.log_error(f"No addresses found for {facility_type} {facility_name}. Facility exists: {facility_exists}", "get_addresses_for_facility_debug")
		
	except Exception as e:
		import traceback
		frappe.log_error(f"Error getting addresses for {facility_type} {facility_name}: {str(e)}\n{traceback.format_exc()}", "get_addresses_for_facility")
	
	return []


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
