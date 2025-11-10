# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RunSheet(Document):
	def onload(self):
		"""Load Transport Legs dynamically to ensure sync"""
		self.refresh_legs_from_transport_leg()
	
	def validate(self):
		"""Validate Run Sheet data and ensure bidirectional sync"""
		self.validate_vehicle_availability()
		self.validate_capacity()
		self.validate_legs_compatibility()
		self.sync_legs_to_transport_leg()
	
	def on_update(self):
		"""Update Transport Leg records after Run Sheet is saved"""
		self.update_transport_leg_assignments()
	
	def on_trash(self):
		"""Clear run_sheet field on Transport Legs when Run Sheet is deleted"""
		self.clear_transport_leg_assignments()
	
	def refresh_legs_from_transport_leg(self):
		"""
		Refresh child table from Transport Leg records.
		This ensures the child table reflects the latest Transport Leg data.
		"""
		if not self.name:
			return
		
		# Get all Transport Legs assigned to this Run Sheet, ordered by their order field
		transport_legs = frappe.get_all(
			"Transport Leg",
			filters={"run_sheet": self.name},
			fields=["name", "transport_job", "facility_from", "facility_to", 
			        "facility_type_from", "facility_type_to", "pick_mode", 
			        "drop_mode", "status", "order"],
			order_by="`order` asc, creation asc"
		)
		
		# Get existing leg links from child table
		existing_leg_links = {row.transport_leg for row in self.get("legs", [])}
		
		# Get leg links from Transport Leg query
		queried_leg_links = {leg.name for leg in transport_legs}
		
		# Remove legs that no longer exist in Transport Leg
		for row in list(self.get("legs", [])):
			if row.transport_leg and row.transport_leg not in queried_leg_links:
				self.remove(row)
		
		# Add new legs that exist in Transport Leg but not in child table
		for leg in transport_legs:
			if leg.name not in existing_leg_links:
				self.append("legs", {
					"transport_leg": leg.name,
					# Other fields will be auto-fetched via fetch_from
				})
	
	def sync_legs_to_transport_leg(self):
		"""
		Sync child table idx to Transport Leg order field.
		This ensures the order in Transport Leg matches the arrangement in child table.
		Note: Only updates order field using db.set_value for performance, 
		as order changes don't affect status.
		"""
		if not self.legs:
			return
		
		# Sync idx from child table to Transport Leg order field
		for idx, row in enumerate(self.legs, start=1):
			if not row.transport_leg:
				continue
			
			# Validate Transport Leg exists
			if not frappe.db.exists("Transport Leg", row.transport_leg):
				frappe.throw(f"Transport Leg {row.transport_leg} does not exist")
			
			# Update order field in Transport Leg to match child table idx
			# Using db.set_value here is OK since order field doesn't affect status
			frappe.db.set_value(
				"Transport Leg",
				row.transport_leg,
				"order",
				idx,
				update_modified=False
			)
	
	def update_transport_leg_assignments(self):
		"""
		Update the run_sheet field on Transport Leg records.
		This ensures Transport Leg knows which Run Sheet it belongs to.
		Also properly updates the status field by triggering document hooks.
		"""
		if not self.legs:
			return
		
		# Collect all transport_leg links from the child table
		current_leg_links = {row.transport_leg for row in self.legs if row.transport_leg}
		
		# Update run_sheet field on all Transport Legs in the child table
		# Use proper document update to trigger status update hooks
		for leg_link in current_leg_links:
			try:
				leg_doc = frappe.get_doc("Transport Leg", leg_link)
				if leg_doc.run_sheet != self.name:
					leg_doc.run_sheet = self.name
					leg_doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error updating Transport Leg {leg_link} run_sheet assignment: {str(e)}")
		
		# Find Transport Legs that were previously assigned but are now removed
		previously_assigned = frappe.get_all(
			"Transport Leg",
			filters={"run_sheet": self.name},
			pluck="name"
		)
		
		removed_legs = set(previously_assigned) - current_leg_links
		
		# Clear run_sheet field for removed legs
		# Use proper document update to trigger status update hooks
		for leg_name in removed_legs:
			try:
				leg_doc = frappe.get_doc("Transport Leg", leg_name)
				if leg_doc.run_sheet:
					leg_doc.run_sheet = None
					leg_doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error clearing Transport Leg {leg_name} run_sheet assignment: {str(e)}")
	
	def validate_vehicle_availability(self):
		"""Validate that the assigned vehicle is not already on another active Run Sheet"""
		if not self.vehicle:
			return
		
		if self.is_new():
			# Check if vehicle is already on an active Run Sheet
			existing_rs = frappe.db.exists("Run Sheet", {
				"vehicle": self.vehicle,
				"status": ["in", ["Draft", "Submitted", "In Progress"]],
				"name": ["!=", self.name]
			})
			
			if existing_rs:
				frappe.throw(_("Vehicle {0} is already assigned to an active Run Sheet ({1})").format(
					self.vehicle, existing_rs
				))
		else:
			# For existing documents, check if vehicle changed
			old_vehicle = frappe.db.get_value("Run Sheet", self.name, "vehicle")
			if old_vehicle != self.vehicle:
				# Check if new vehicle is available
				existing_rs = frappe.db.exists("Run Sheet", {
					"vehicle": self.vehicle,
					"status": ["in", ["Draft", "Submitted", "In Progress"]],
					"name": ["!=", self.name]
				})
				
				if existing_rs:
					frappe.throw(_("Vehicle {0} is already assigned to an active Run Sheet ({1})").format(
						self.vehicle, existing_rs
					))
	
	def validate_capacity(self):
		"""Validate that the vehicle has sufficient capacity for all legs"""
		if not self.vehicle or not self.legs:
			return
		
		# Get vehicle capacity
		vehicle_doc = frappe.get_doc("Transport Vehicle", self.vehicle)
		vehicle_capacity_weight = flt(getattr(vehicle_doc, "max_weight_kg", 0))
		vehicle_capacity_volume = flt(getattr(vehicle_doc, "max_volume_m3", 0))
		vehicle_capacity_pallets = flt(getattr(vehicle_doc, "max_pallets", 0))
		
		# Calculate total requirements from legs
		total_weight = 0
		total_volume = 0
		total_pallets = 0
		
		for row in self.legs:
			if not row.transport_leg:
				continue
			
			leg_doc = frappe.get_doc("Transport Leg", row.transport_leg)
			total_weight += flt(getattr(leg_doc, "weight_kg", 0))
			total_volume += flt(getattr(leg_doc, "volume_m3", 0))
			total_pallets += flt(getattr(leg_doc, "pallets", 0))
		
		# Validate capacity
		if vehicle_capacity_weight > 0 and total_weight > vehicle_capacity_weight:
			frappe.throw(_("Total weight ({0} kg) exceeds vehicle capacity ({1} kg)").format(
				total_weight, vehicle_capacity_weight
			))
		
		if vehicle_capacity_volume > 0 and total_volume > vehicle_capacity_volume:
			frappe.throw(_("Total volume ({0} m³) exceeds vehicle capacity ({1} m³)").format(
				total_volume, vehicle_capacity_volume
			))
		
		if vehicle_capacity_pallets > 0 and total_pallets > vehicle_capacity_pallets:
			frappe.throw(_("Total pallets ({0}) exceeds vehicle capacity ({1})").format(
				total_pallets, vehicle_capacity_pallets
			))
	
	def validate_legs_compatibility(self):
		"""Validate that all legs are compatible (same vehicle type, reasonable date range)"""
		if not self.legs or len(self.legs) < 2:
			return
		
		# Get vehicle types from all legs
		vehicle_types = set()
		leg_dates = []
		
		for row in self.legs:
			if not row.transport_leg:
				continue
			
			leg_doc = frappe.get_doc("Transport Leg", row.transport_leg)
			if leg_doc.vehicle_type:
				vehicle_types.add(leg_doc.vehicle_type)
			
			# Collect dates for range check
			if hasattr(leg_doc, "pick_window_start") and leg_doc.pick_window_start:
				from frappe.utils import getdate
				leg_dates.append(getdate(leg_doc.pick_window_start))
			if hasattr(leg_doc, "drop_window_end") and leg_doc.drop_window_end:
				from frappe.utils import getdate
				leg_dates.append(getdate(leg_doc.drop_window_end))
		
		# Warn if legs have different vehicle types
		if len(vehicle_types) > 1:
			frappe.msgprint(_("Warning: Legs have different vehicle types ({0}). This may cause issues.").format(
				", ".join(vehicle_types)
			), indicator="orange")
		
		# Warn if legs span more than 7 days
		if leg_dates:
			from frappe.utils import getdate
			min_date = min(leg_dates)
			max_date = max(leg_dates)
			days_span = (max_date - min_date).days
			
			if days_span > 7:
				frappe.msgprint(_("Warning: Legs span {0} days. This may indicate a scheduling issue.").format(
					days_span
				), indicator="orange")
	
	def clear_transport_leg_assignments(self):
		"""Clear run_sheet field on all Transport Legs when Run Sheet is deleted
		Uses proper document update to trigger status update hooks."""
		# Find all Transport Legs assigned to this Run Sheet
		assigned_legs = frappe.get_all(
			"Transport Leg",
			filters={"run_sheet": self.name},
			pluck="name"
		)
		
		# Clear the run_sheet field using proper document update
		for leg_name in assigned_legs:
			try:
				leg_doc = frappe.get_doc("Transport Leg", leg_name)
				if leg_doc.run_sheet:
					leg_doc.run_sheet = None
					leg_doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Error clearing Transport Leg {leg_name} run_sheet assignment on Run Sheet deletion: {str(e)}")


# Whitelisted methods for client-side calls

@frappe.whitelist()
def refresh_legs(run_sheet_name):
	"""
	API method to refresh legs from Transport Leg doctype.
	Called from client-side button.
	"""
	try:
		rs = frappe.get_doc("Run Sheet", run_sheet_name)
		rs.refresh_legs_from_transport_leg()
		rs.save(ignore_permissions=True)
		
		return {
			"status": "success",
			"message": f"Refreshed {len(rs.legs)} legs from Transport Leg"
		}
	except Exception as e:
		frappe.log_error(f"Error refreshing legs for Run Sheet {run_sheet_name}: {str(e)}")
		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist()
def sync_legs_to_transport(run_sheet_name):
	"""
	API method to sync Run Sheet Leg changes to Transport Leg doctype.
	Called from client-side button.
	"""
	try:
		rs = frappe.get_doc("Run Sheet", run_sheet_name)
		rs.sync_legs_to_transport_leg()
		rs.update_transport_leg_assignments()
		
		return {
			"status": "success",
			"message": f"Synced {len(rs.legs)} legs to Transport Leg"
		}
	except Exception as e:
		frappe.log_error(f"Error syncing legs for Run Sheet {run_sheet_name}: {str(e)}")
		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist()
def update_leg_order(run_sheet_name, leg_order):
	"""
	Update the order of Transport Legs based on drag-and-drop reordering.
	Saves child table idx to Transport Leg order field.
	
	Args:
		run_sheet_name: Name of the Run Sheet
		leg_order: List of dicts with transport_leg names in desired order
	"""
	import json
	
	if isinstance(leg_order, str):
		leg_order = json.loads(leg_order)
	
	try:
		frappe.logger().info(f"🔄 update_leg_order called for {run_sheet_name}")
		frappe.logger().info(f"   Received order: {leg_order}")
		
		# Get the Run Sheet
		rs = frappe.get_doc("Run Sheet", run_sheet_name)
		frappe.logger().info(f"   Current legs count: {len(rs.legs)}")
		
		# Create a map of transport_leg to desired position
		position_map = {item["transport_leg"]: idx for idx, item in enumerate(leg_order, 1)}
		frappe.logger().info(f"   Position map: {position_map}")
		
		# Clear and rebuild the child table in the correct order
		old_legs = list(rs.legs)
		rs.legs = []
		
		# Add legs back in the new order
		for item in leg_order:
			leg_name = item["transport_leg"]
			# Find the original leg row
			for old_leg in old_legs:
				if old_leg.transport_leg == leg_name:
					rs.append("legs", {
						"transport_leg": old_leg.transport_leg,
						"transport_job": old_leg.transport_job,
						"customer": old_leg.customer,
						"facility_type_from": old_leg.facility_type_from,
						"facility_from": old_leg.facility_from,
						"facility_type_to": old_leg.facility_type_to,
						"facility_to": old_leg.facility_to,
						"pick_mode": old_leg.pick_mode,
						"drop_mode": old_leg.drop_mode
					})
					break
		
		frappe.logger().info(f"   Rebuilt child table with {len(rs.legs)} legs")
		
		# Save the Run Sheet (Frappe will automatically update idx fields)
		rs.flags.ignore_validate = True
		rs.flags.ignore_permissions = True
		rs.save(ignore_permissions=True)
		frappe.logger().info("   ✅ Run Sheet saved")
		
		# Now sync the idx to Transport Leg order field
		updated_legs = []
		for idx, row in enumerate(rs.legs, start=1):
			if row.transport_leg:
				frappe.logger().info(f"   Setting {row.transport_leg}.order = {idx}")
				frappe.db.set_value(
					"Transport Leg",
					row.transport_leg,
					"order",
					idx,
					update_modified=False
				)
				updated_legs.append(f"{row.transport_leg}={idx}")
		
		frappe.db.commit()
		frappe.logger().info(f"   ✅ Committed to database")
		
		return {
			"status": "success",
			"message": f"Reordered {len(leg_order)} legs",
			"count": len(leg_order),
			"updated": updated_legs
		}
	except Exception as e:
		import traceback
		error_msg = f"Error reordering legs: {str(e)}\n{traceback.format_exc()}"
		frappe.logger().error(error_msg)
		frappe.log_error(error_msg, "Run Sheet Order Update Failed")
		frappe.db.rollback()
		return {
			"status": "error",
			"message": str(e)
		}
