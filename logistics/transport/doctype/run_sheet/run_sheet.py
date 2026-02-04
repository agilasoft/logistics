# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, getdate


class RunSheet(Document):
	def onload(self):
		"""Load Transport Legs dynamically to ensure sync"""
		self.refresh_legs_from_transport_leg()
	
	def validate(self):
		"""Validate Run Sheet data and ensure bidirectional sync"""
		self.validate_vehicle_availability()
		self.validate_capacity()
		self.validate_legs_compatibility()
		self.validate_vehicle_economic_zone_accreditation()
		self.update_legs_missing_data()
		self.sync_legs_to_transport_leg()
	
	def before_save(self):
		"""Update status before saving"""
		# Call update_status() to calculate correct status
		# For submitted documents (docstatus = 1), update_status() will use db_set() 
		# to persist status changes if the status changed
		self.update_status()
	
	def before_submit(self):
		"""Validate required fields before submission and mark as submitting"""
		self.validate_vehicle_required()
		# Set flag to prevent before_save from calling update_status during submission
		self._submitting = True
	
	def after_submit(self):
		"""Set initial status after submission and check leg states"""
		# IMPORTANT: Ensure docstatus is 1 (sometimes it's not set in the object yet)
		# Reload from database to get the actual docstatus
		current_docstatus = frappe.db.get_value(self.doctype, self.name, "docstatus")
		if current_docstatus != 1:
			# If not submitted, something went wrong - log and return
			frappe.log_error(
				f"Run Sheet {self.name} after_submit called but docstatus is {current_docstatus}, not 1",
				"Run Sheet After Submit Error"
			)
			return
		
		# Ensure docstatus is set in the object for update_status to work
		self.docstatus = 1
		
		# Clear submitting flag
		if hasattr(self, '_submitting'):
			delattr(self, '_submitting')
		
		# Set status to "Dispatched" via db_set()
		self.db_set("status", "Dispatched", update_modified=False)
		
		# Call update_status() to calculate correct status based on leg states
		self.update_status()
	
	def on_cancel(self):
		"""Set status to Cancelled when document is cancelled"""
		self.db_set("status", "Cancelled", update_modified=False)
	
	def on_update(self):
		"""Update Transport Leg records after Run Sheet is saved"""
		self.update_transport_leg_assignments()
		self.sync_route_to_legs()
	
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
			order_by="order asc, creation asc"
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
	
	def validate_vehicle_required(self):
		"""Validate that vehicle is required before submission"""
		if not self.vehicle:
			frappe.throw(_("Vehicle is required. Please select a vehicle before submitting the document."))
	
	def validate_vehicle_availability(self):
		"""Validate that the assigned vehicle is not already on another active Run Sheet.
		Checks estimated_return_datetime to ensure vehicle is available for the scheduled date.
		"""
		if not self.vehicle:
			return
		
		# Get the scheduled dispatch datetime for this Run Sheet
		# Prefer estimated_dispatch_datetime, fall back to run_date
		scheduled_dispatch = None
		if hasattr(self, "estimated_dispatch_datetime") and self.estimated_dispatch_datetime:
			scheduled_dispatch = self.estimated_dispatch_datetime
		elif hasattr(self, "run_date") and self.run_date:
			scheduled_dispatch = self.run_date
		
		# Build filters for active Run Sheets
		base_filters = {
			"vehicle": self.vehicle,
			"name": ["!=", self.name],
		}
		
		# Add status filter if status field exists
		if self.meta.has_field("status"):
			base_filters["status"] = ["in", ["Draft", "Dispatched", "In-Progress", "Submitted"]]
		
		# Get all active Run Sheets for this vehicle
		existing_run_sheets = frappe.get_all(
			"Run Sheet",
			filters=base_filters,
			fields=["name", "estimated_return_datetime", "run_date"],
			limit_page_length=100,
		)
		
		if not existing_run_sheets:
			return
		
		# If we have a scheduled dispatch time, check if any existing Run Sheet's
		# estimated_return_datetime is after our scheduled dispatch
		if scheduled_dispatch:
			scheduled_dt = get_datetime(scheduled_dispatch)
			
			for rs in existing_run_sheets:
				# Check estimated_return_datetime if available
				if rs.get("estimated_return_datetime"):
					return_dt = get_datetime(rs["estimated_return_datetime"])
					if return_dt > scheduled_dt:
						frappe.throw(_("Vehicle {0} is already assigned to an active Run Sheet ({1}) "
									  "which has estimated return datetime {2}. "
									  "The vehicle will not be available until after that time.").format(
							self.vehicle, 
							rs["name"],
							frappe.format(rs["estimated_return_datetime"], {"fieldtype": "Datetime"})
						))
				# Fall back to run_date if estimated_return_datetime is not set
				elif rs.get("run_date"):
					run_date_str = str(rs["run_date"])
					if " " in run_date_str:
						run_date_only = run_date_str.split(" ")[0]
					else:
						run_date_only = run_date_str
					# Use end of run_date day as conservative estimate
					run_date_end = f"{run_date_only} 23:59:59"
					run_date_dt = get_datetime(run_date_end)
					if run_date_dt > scheduled_dt:
						frappe.throw(_("Vehicle {0} is already assigned to an active Run Sheet ({1}) "
									  "on {2}. Please set estimated_return_datetime on the existing Run Sheet "
									  "to enable proper scheduling.").format(
							self.vehicle, 
							rs["name"],
							run_date_only
						))
		else:
			# If no scheduled dispatch time is set, use original validation
			# (check if vehicle is assigned to any active Run Sheet)
			if existing_run_sheets:
				existing_rs = existing_run_sheets[0]["name"]
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
		"""
		Validate that all legs are compatible:
		- All legs must share the same transport_vehicle (via vehicle_type)
		- All legs must share the same scheduled/run date
		"""
		if not self.legs or len(self.legs) < 2:
			return
		
		from frappe.utils import getdate
		
		# Collect vehicle types and dates from all legs
		vehicle_types = set()
		leg_run_dates = []
		leg_dates = []
		leg_names = []
		
		for row in self.legs:
			if not row.transport_leg:
				continue
			
			leg_doc = frappe.get_doc("Transport Leg", row.transport_leg)
			leg_names.append(leg_doc.name)
			
			# Collect vehicle types
			if leg_doc.vehicle_type:
				vehicle_types.add(leg_doc.vehicle_type)
			
			# Collect run_date (preferred) or date (fallback) for scheduled/run date validation
			leg_date = None
			if hasattr(leg_doc, "run_date") and leg_doc.run_date:
				leg_date = getdate(leg_doc.run_date)
				leg_run_dates.append((leg_doc.name, leg_date, "run_date"))
			elif hasattr(leg_doc, "date") and leg_doc.date:
				leg_date = getdate(leg_doc.date)
				leg_dates.append((leg_doc.name, leg_date, "date"))
		
		# Validate: All legs must have the same vehicle_type
		if len(vehicle_types) > 1:
			vehicle_types_list = sorted(list(vehicle_types))
			frappe.throw(
				_("Cannot group legs with different vehicle types. "
				  "Legs have the following vehicle types: {0}. "
				  "All legs must share the same vehicle type to be grouped in a Run Sheet.").format(
					", ".join(vehicle_types_list)
				),
				title=_("Vehicle Type Mismatch")
			)
		
		# Validate: All legs must have the same scheduled/run date
		all_dates = leg_run_dates + leg_dates
		if len(all_dates) > 1:
			# Get unique dates
			unique_dates = set(date for _, date, _ in all_dates)
			if len(unique_dates) > 1:
				# Find legs with mismatched dates for error message
				date_groups = {}
				for leg_name, date, date_type in all_dates:
					date_str = str(date)
					if date_str not in date_groups:
						date_groups[date_str] = []
					date_groups[date_str].append((leg_name, date_type))
				
				# Build error message showing which legs have which dates
				date_details = []
				for date_str, legs in sorted(date_groups.items()):
					leg_list = ", ".join([f"{name} ({dt})" for name, dt in legs])
					date_details.append(f"Date {date_str}: {leg_list}")
				
				frappe.throw(
					_("Cannot group legs with different scheduled/run dates. "
					  "All legs must share the same scheduled or run date to be grouped in a Run Sheet.\n\n"
					  "Date mismatches found:\n{0}").format("\n".join(date_details)),
					title=_("Date Mismatch")
				)
		
		# Additional validation: If Run Sheet has a vehicle assigned, verify it matches leg vehicle types
		if self.vehicle and vehicle_types:
			vehicle_doc = frappe.get_doc("Transport Vehicle", self.vehicle)
			vehicle_vehicle_type = getattr(vehicle_doc, "vehicle_type", None)
			
			if vehicle_vehicle_type and vehicle_vehicle_type not in vehicle_types:
				frappe.throw(
					_("The assigned vehicle ({0}) has vehicle type '{1}', but the legs require vehicle type '{2}'. "
					  "Please assign a vehicle with the correct vehicle type or remove legs with incompatible vehicle types.").format(
						self.vehicle,
						vehicle_vehicle_type,
						", ".join(sorted(vehicle_types))
					),
					title=_("Vehicle Type Incompatibility")
				)
	
	def validate_vehicle_economic_zone_accreditation(self):
		"""
		Validate that when a Transport Leg contains an Economic Zone address
		(pick or drop address with Economic Zone set), the Run Sheet's vehicle
		has an accreditation to that Economic Zone.
		"""
		if not self.vehicle or not self.legs:
			return
		
		# Collect all addresses used in legs (pick and drop from Transport Leg)
		address_names = set()
		for row in self.legs:
			if not row.transport_leg:
				continue
			leg = frappe.db.get_value(
				"Transport Leg",
				row.transport_leg,
				["pick_address", "drop_address"],
				as_dict=True
			)
			if leg:
				if leg.get("pick_address"):
					address_names.add(leg.pick_address)
				if leg.get("drop_address"):
					address_names.add(leg.drop_address)
		
		if not address_names:
			return
		
		# Get Economic Zone for each address (custom_economic_zone on Address)
		economic_zones_required = set()
		for address_name in address_names:
			ez = frappe.db.get_value("Address", address_name, "custom_economic_zone")
			if ez:
				economic_zones_required.add(ez)
		
		if not economic_zones_required:
			return
		
		# Get vehicle's accredited Economic Zones (from accreditations child table)
		# Consider accreditation valid if valid_until is empty or >= today
		today = getdate()
		vehicle_doc = frappe.get_doc("Transport Vehicle", self.vehicle)
		accredited_zones = set()
		for acc in getattr(vehicle_doc, "accreditations", []) or []:
			if not acc.get("economic_zone"):
				continue
			valid_until = acc.get("valid_until")
			if valid_until is None or (getdate(valid_until) >= today):
				accredited_zones.add(acc.economic_zone)
		
		# Check every required zone is accredited
		missing = economic_zones_required - accredited_zones
		if missing:
			zone_list = ", ".join(sorted(missing))
			frappe.throw(
				_("Vehicle {0} is not accredited to Economic Zone(s): {1}. "
				  "The Run Sheet contains leg(s) with pick or drop at addresses in these zones. "
				  "Please assign a vehicle that has accreditations for these Economic Zones, "
				  "or use addresses outside these zones.").format(self.vehicle, zone_list),
				title=_("Economic Zone Accreditation Required")
			)
	
	def update_legs_missing_data(self):
		"""Update missing data in legs by fetching from Transport Leg"""
		if not self.legs:
			return
		
		# Fields to fetch from Transport Leg
		fields_to_fetch = [
			"transport_job",
			"facility_type_from",
			"facility_from",
			"pick_mode",
			"pick_address",  # maps to address_from
			"facility_type_to",
			"facility_to",
			"drop_mode",
			"drop_address"  # maps to address_to
		]
		
		for leg in self.legs:
			transport_leg_name = leg.get("transport_leg")
			if not transport_leg_name:
				continue
			
			# Check if any required fields are missing
			has_missing = (
				not leg.get("transport_job") or
				not leg.get("facility_type_from") or
				not leg.get("facility_from") or
				not leg.get("pick_mode") or
				not leg.get("address_from") or
				not leg.get("facility_type_to") or
				not leg.get("facility_to") or
				not leg.get("drop_mode") or
				not leg.get("address_to")
			)
			
			if has_missing:
				try:
					# Fetch data from Transport Leg
					transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
					
					# Update only missing fields
					if not leg.get("transport_job") and transport_leg.get("transport_job"):
						leg.transport_job = transport_leg.transport_job
					
					if not leg.get("facility_type_from") and transport_leg.get("facility_type_from"):
						leg.facility_type_from = transport_leg.facility_type_from
					
					if not leg.get("facility_from") and transport_leg.get("facility_from"):
						leg.facility_from = transport_leg.facility_from
					
					if not leg.get("facility_type_to") and transport_leg.get("facility_type_to"):
						leg.facility_type_to = transport_leg.facility_type_to
					
					if not leg.get("facility_to") and transport_leg.get("facility_to"):
						leg.facility_to = transport_leg.facility_to
					
					if not leg.get("pick_mode") and transport_leg.get("pick_mode"):
						leg.pick_mode = transport_leg.pick_mode
					
					if not leg.get("drop_mode") and transport_leg.get("drop_mode"):
						leg.drop_mode = transport_leg.drop_mode
					
					if not leg.get("address_from") and transport_leg.get("pick_address"):
						leg.address_from = transport_leg.pick_address
					
					if not leg.get("address_to") and transport_leg.get("drop_address"):
						leg.address_to = transport_leg.drop_address
					
					# Fetch customer from transport_job if missing
					if not leg.get("customer") and leg.get("transport_job"):
						try:
							customer = frappe.db.get_value("Transport Job", leg.transport_job, "customer")
							if customer:
								leg.customer = customer
						except Exception:
							pass
					
				except Exception as e:
					frappe.log_error(
						f"Error fetching data from Transport Leg {transport_leg_name}: {str(e)}",
						"Run Sheet Leg Data Fetch Error"
					)
	
	def sync_route_to_legs(self):
		"""Sync route changes from Run Sheet to Transport Legs - clear leg routes when combined route changes"""
		# When Run Sheet route changes, clear individual leg routes so they can be recalculated
		# This ensures leg routes stay in sync with the combined route
		if not hasattr(self, "selected_route_polyline") or not self.selected_route_polyline:
			return
		
		try:
			# Get all Transport Legs in this Run Sheet
			for leg_row in self.legs:
				if not leg_row.transport_leg:
					continue
				
				try:
					leg_doc = frappe.get_doc("Transport Leg", leg_row.transport_leg)
					# Clear leg route so it can be recalculated if needed
					# Note: We don't extract individual segments from combined route (too complex)
					# Instead, leg routes remain independent and can be recalculated separately
					if hasattr(leg_doc, "selected_route_polyline"):
						# Optionally clear leg route, or leave it as-is for independent optimization
						# For now, we'll leave leg routes as-is since extracting from combined route is complex
						pass
				except Exception as e:
					frappe.log_error(f"Error syncing route to Transport Leg {leg_row.transport_leg}: {str(e)}")
		except Exception as e:
			frappe.log_error(f"Error syncing route from Run Sheet {self.name} to legs: {str(e)}")
	
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
	
	def update_status(self):
		"""Update status based on document state and Transport Leg statuses
		
		This method automatically determines the correct status based on:
		- Document state (docstatus 0 = Draft, docstatus 1 = Dispatched/In-Progress/Completed, docstatus 2 = Cancelled)
		- Transport Leg statuses for submitted documents
		- Ensures status always follows docstatus
		"""
		if self.is_new():
			# New documents are always Draft
			self.status = "Draft"
			return
		
		# If cancelled (docstatus = 2), status must be Cancelled
		if self.docstatus == 2:
			self.status = "Cancelled"
			return
		
		# If draft (docstatus = 0), status must be Draft (unless manually set to Hold)
		if self.docstatus == 0:
			# Don't override "Hold" status if manually set
			if not self.status or (self.status != "Hold" and self.status != "Cancelled"):
				self.status = "Draft"
			return
		
		# If submitted (docstatus = 1), check leg statuses to determine Run Sheet status
		# Default to "Dispatched" unless legs indicate "In-Progress" or "Completed"
		if self.docstatus == 1:
			# Don't auto-update if status is manually set to "Hold"
			if self.status == "Hold":
				return
			
			if not self.legs:
				# No legs - status should be Dispatched
				if self.status != "Dispatched":
					self.status = "Dispatched"
				return
			
			# Get all leg statuses directly from database to ensure we have the latest
			# This is important because leg statuses may have changed since the Run Sheet was loaded
			leg_statuses = []
			for leg_row in self.legs:
				transport_leg_name = leg_row.get("transport_leg")
				if transport_leg_name:
					# Always fetch fresh status from database
					leg_status = frappe.db.get_value("Transport Leg", transport_leg_name, "status")
					if leg_status:
						leg_statuses.append(leg_status)
			
			if not leg_statuses:
				# No leg statuses found - default to Dispatched
				if self.status != "Dispatched":
					self.status = "Dispatched"
				return
			
			# Determine Run Sheet status based on leg statuses
			# Map Transport Leg statuses to Run Sheet statuses:
			# - "Completed" or "Billed" → "Completed" (if all legs are completed)
			# - "Started" → "In-Progress" (if any leg is started)
			# - "Assigned" → "Dispatched" (if any leg is assigned but not started)
			# - "Open" → "Dispatched" (if all legs are open)
			# - Submitted document (docstatus = 1) → "Dispatched" by default
			
			old_status = self.status
			
			if all(status in ["Completed", "Billed"] for status in leg_statuses):
				new_status = "Completed"
			elif any(status == "Started" for status in leg_statuses):
				# If any leg is started, status is In-Progress
				new_status = "In-Progress"
			elif any(status == "Assigned" for status in leg_statuses):
				# If any leg is assigned (but not started), status is Dispatched
				new_status = "Dispatched"
			elif all(status == "Open" for status in leg_statuses):
				# If all legs are open, status is Dispatched
				new_status = "Dispatched"
			else:
				# Mixed statuses - prioritize Started > Assigned > Completed
				if any(status == "Started" for status in leg_statuses):
					new_status = "In-Progress"
				elif any(status == "Assigned" for status in leg_statuses):
					new_status = "Dispatched"
				elif any(status in ["Completed", "Billed"] for status in leg_statuses):
					# If some legs are completed but not all, status is In-Progress
					new_status = "In-Progress"
				else:
					# Fallback to Dispatched if we can't determine
					new_status = "Dispatched"
			
			# Update status if it changed
			if new_status != old_status:
				self.status = new_status
				
				# For submitted documents, use db_set to persist the change
				# This prevents validation loops and works with submitted documents
				if self.docstatus == 1:
					self.db_set("status", new_status, update_modified=False)


# Whitelisted methods for client-side calls


@frappe.whitelist()
def has_economic_zone_address(run_sheet_name):
	"""
	Return whether the Run Sheet has any Transport Leg with a pick or drop
	address that is tagged with an Economic Zone (Address.custom_economic_zone).
	Used by the form to show a red reminder when Economic Zone addresses are present.
	"""
	if not run_sheet_name:
		return {"has_ez_address": False}
	legs = frappe.get_all(
		"Transport Leg",
		filters={"run_sheet": run_sheet_name},
		fields=["pick_address", "drop_address"]
	)
	address_names = set()
	for leg in legs:
		if leg.get("pick_address"):
			address_names.add(leg.pick_address)
		if leg.get("drop_address"):
			address_names.add(leg.drop_address)
	if not address_names:
		return {"has_ez_address": False}
	for address_name in address_names:
		ez = frappe.db.get_value("Address", address_name, "custom_economic_zone")
		if ez:
			return {"has_ez_address": True}
	return {"has_ez_address": False}


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


@frappe.whitelist()
def fetch_missing_leg_data(run_sheet_name):
	"""
	Fetch and update missing data from Transport Leg for all legs in a Run Sheet.
	This method works even for submitted documents by using db_set.
	
	Args:
		run_sheet_name: Name of the Run Sheet
		
	Returns:
		Dict with status and count of updated legs
	"""
	if not run_sheet_name:
		frappe.throw(_("Run Sheet name is required"))
	
	rs = frappe.get_doc("Run Sheet", run_sheet_name)
	
	if not rs.legs:
		return {"ok": True, "updated_count": 0, "message": _("No legs found in this Run Sheet")}
	
	updated_count = 0
	
	for leg in rs.legs:
		transport_leg_name = leg.get("transport_leg")
		if not transport_leg_name:
			continue
		
		# Check if any required fields are missing
		has_missing = (
			not leg.get("transport_job") or
			not leg.get("facility_type_from") or
			not leg.get("facility_from") or
			not leg.get("pick_mode") or
			not leg.get("address_from") or
			not leg.get("facility_type_to") or
			not leg.get("facility_to") or
			not leg.get("drop_mode") or
			not leg.get("address_to")
		)
		
		if has_missing:
			try:
				# Fetch data from Transport Leg
				transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
				
				# Track if we updated anything
				updated_this_leg = False
				
				# Update missing fields using db_set to work with submitted documents
				if not leg.get("transport_job") and transport_leg.get("transport_job"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "transport_job",
									   transport_leg.transport_job, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("facility_type_from") and transport_leg.get("facility_type_from"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "facility_type_from",
									   transport_leg.facility_type_from, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("facility_from") and transport_leg.get("facility_from"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "facility_from",
									   transport_leg.facility_from, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("facility_type_to") and transport_leg.get("facility_type_to"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "facility_type_to",
									   transport_leg.facility_type_to, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("facility_to") and transport_leg.get("facility_to"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "facility_to",
									   transport_leg.facility_to, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("pick_mode") and transport_leg.get("pick_mode"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "pick_mode",
									   transport_leg.pick_mode, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("drop_mode") and transport_leg.get("drop_mode"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "drop_mode",
									   transport_leg.drop_mode, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("address_from") and transport_leg.get("pick_address"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "address_from",
									   transport_leg.pick_address, update_modified=False)
					updated_this_leg = True
				
				if not leg.get("address_to") and transport_leg.get("drop_address"):
					frappe.db.set_value("Run Sheet Leg", leg.name, "address_to",
									   transport_leg.drop_address, update_modified=False)
					updated_this_leg = True
				
				# Fetch customer from transport_job if missing
				if not leg.get("customer") and leg.get("transport_job"):
					try:
						customer = frappe.db.get_value("Transport Job", leg.transport_job, "customer")
						if customer:
							frappe.db.set_value("Run Sheet Leg", leg.name, "customer",
											   customer, update_modified=False)
							updated_this_leg = True
					except Exception:
						pass
				
				if updated_this_leg:
					updated_count += 1
					
			except Exception as e:
				frappe.log_error(
					f"Error fetching data from Transport Leg {transport_leg_name}: {str(e)}",
					"Fetch Missing Leg Data Error"
				)
	
	# Commit the changes
	frappe.db.commit()
	
	return {
		"ok": True,
		"updated_count": updated_count,
		"message": _("Updated {0} leg(s) with missing data").format(updated_count)
	}


def _get_primary_address(facility_type, facility_name):
	"""Get the primary address for a facility or terminal"""
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
		
		# Fallback: Get addresses linked to this facility/terminal
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
def update_status_from_client(run_sheet_name):
	"""
	Update Run Sheet status from client-side JavaScript.
	This method recalculates the status based on current leg statuses
	and returns the updated status.
	
	Args:
		run_sheet_name: Name of the Run Sheet
		
	Returns:
		Dict with status and success flag
	"""
	if not run_sheet_name:
		return {
			"success": False,
			"error": "Run Sheet name is required"
		}
	
	try:
		rs = frappe.get_doc("Run Sheet", run_sheet_name)
		
		# Only update status for submitted documents
		if rs.docstatus != 1:
			return {
				"success": True,
				"status": rs.status,
				"message": "Status update only applies to submitted documents"
			}
		
		# Don't update if status is manually set to "Hold"
		if rs.status == "Hold":
			return {
				"success": True,
				"status": rs.status,
				"message": "Status is set to Hold and will not be auto-updated"
			}
		
		# Store old status from database (may be different from in-memory)
		db_status = frappe.db.get_value("Run Sheet", run_sheet_name, "status")
		old_status = db_status or rs.status
		
		# Call update_status() to recalculate based on current leg statuses
		rs.update_status()
		
		# Get the new status (may have been updated by update_status)
		new_status = rs.status
		
		# Always persist to database if different from current DB value
		# This ensures the database is always up-to-date
		if new_status != db_status:
			rs.db_set("status", new_status, update_modified=False)
			frappe.db.commit()
			frappe.logger().info(f"Run Sheet {run_sheet_name} status updated: {db_status} → {new_status}")
		
		return {
			"success": True,
			"status": new_status,
			"old_status": old_status,
			"db_status": db_status,
			"changed": new_status != old_status
		}
	except Exception as e:
		frappe.log_error(f"Error updating Run Sheet status for {run_sheet_name}: {str(e)}", "Run Sheet Status Update Error")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def create_support_legs(run_sheet_name):
	"""
	Create support legs for a Run Sheet:
	- Dispatch Leg: From Dispatch Terminal to First Pickup
	- Connecting Legs: From each Drop Location to Next Pickup
	- Return Leg: From Last Drop to Return Terminal
	"""
	if not run_sheet_name:
		frappe.throw(_("Run Sheet name is required"))
	
	try:
		rs = frappe.get_doc("Run Sheet", run_sheet_name)
		
		# Validate required fields
		if not rs.dispatch_terminal:
			frappe.throw(_("Dispatch Terminal is required to create support legs"))
		
		if not rs.return_terminal:
			frappe.throw(_("Return Terminal is required to create support legs"))
		
		if not rs.legs or len(rs.legs) == 0:
			frappe.throw(_("No legs found in this Run Sheet. Please add legs first."))
		
		created_legs = []
		
		# Get all legs with their Transport Leg details
		legs_data = []
		for leg_row in rs.legs:
			if not leg_row.transport_leg:
				continue
			
			leg_doc = frappe.get_doc("Transport Leg", leg_row.transport_leg)
			legs_data.append({
				"transport_leg": leg_row.transport_leg,
				"transport_job": leg_doc.transport_job,
				"facility_type_from": leg_doc.facility_type_from,
				"facility_from": leg_doc.facility_from,
				"pick_address": leg_doc.pick_address,
				"facility_type_to": leg_doc.facility_type_to,
				"facility_to": leg_doc.facility_to,
				"drop_address": leg_doc.drop_address,
				"vehicle_type": leg_doc.vehicle_type,
				"run_date": leg_doc.run_date or rs.run_date,
				"order": leg_doc.order or len(legs_data) + 1
			})
		
		if not legs_data:
			frappe.throw(_("No valid legs found in this Run Sheet"))
		
		# Sort legs by order
		legs_data.sort(key=lambda x: x.get("order", 999))
		
		first_leg = legs_data[0]
		last_leg = legs_data[-1]
		
		# 1. Create Dispatch Leg: From Dispatch Terminal to First Pickup
		if first_leg.get("facility_type_from") and first_leg.get("facility_from"):
			dispatch_leg = frappe.new_doc("Transport Leg")
			dispatch_leg.leg_type = "Dispatch"
			dispatch_leg.run_sheet = rs.name
			dispatch_leg.transport_job = first_leg.get("transport_job")
			dispatch_leg.run_date = first_leg.get("run_date")
			dispatch_leg.vehicle_type = first_leg.get("vehicle_type") or rs.vehicle_type
			
			# Set from dispatch terminal
			dispatch_leg.facility_type_from = "Transport Terminal"
			dispatch_leg.facility_from = rs.dispatch_terminal
			dispatch_address = _get_primary_address("Transport Terminal", rs.dispatch_terminal)
			if dispatch_address:
				dispatch_leg.pick_address = dispatch_address
			
			# Set to first pickup location
			dispatch_leg.facility_type_to = first_leg.get("facility_type_from")
			dispatch_leg.facility_to = first_leg.get("facility_from")
			if first_leg.get("pick_address"):
				dispatch_leg.drop_address = first_leg.get("pick_address")
			
			# Set order to be before the first leg
			dispatch_leg.order = (first_leg.get("order", 1) or 1) - 1
			
			dispatch_leg.insert(ignore_permissions=True)
			created_legs.append({"type": "Dispatch", "name": dispatch_leg.name})
		
		# 2. Create Connecting Legs: From each Drop Location to Next Pickup
		# Collect connecting legs to create, then insert them in reverse order to avoid order conflicts
		connecting_legs_to_create = []
		for i in range(len(legs_data) - 1):
			current_leg = legs_data[i]
			next_leg = legs_data[i + 1]
			
			# Only create connecting leg if drop and next pickup are different locations
			if (current_leg.get("facility_type_to") and current_leg.get("facility_to") and
				next_leg.get("facility_type_from") and next_leg.get("facility_from") and
				(current_leg.get("facility_to") != next_leg.get("facility_from") or
				 current_leg.get("facility_type_to") != next_leg.get("facility_type_from"))):
				
				connecting_legs_to_create.append({
					"current_leg": current_leg,
					"next_leg": next_leg,
					"index": i
				})
		
		# Create connecting legs in reverse order and shift subsequent leg orders
		for conn_info in reversed(connecting_legs_to_create):
			current_leg = conn_info["current_leg"]
			next_leg = conn_info["next_leg"]
			i = conn_info["index"]
			
			# Shift all subsequent legs' orders by 1
			for j in range(i + 1, len(legs_data)):
				subsequent_leg_name = legs_data[j].get("transport_leg")
				if subsequent_leg_name:
					current_order = legs_data[j].get("order", j + 1) or (j + 1)
					frappe.db.set_value("Transport Leg", subsequent_leg_name, "order", current_order + 1, update_modified=False)
					legs_data[j]["order"] = current_order + 1
			
			# Create connecting leg
			connecting_leg = frappe.new_doc("Transport Leg")
			connecting_leg.leg_type = "Connecting"
			connecting_leg.run_sheet = rs.name
			connecting_leg.transport_job = next_leg.get("transport_job")
			connecting_leg.run_date = next_leg.get("run_date")
			connecting_leg.vehicle_type = next_leg.get("vehicle_type") or rs.vehicle_type
			
			# Set from current leg's drop location
			connecting_leg.facility_type_from = current_leg.get("facility_type_to")
			connecting_leg.facility_from = current_leg.get("facility_to")
			if current_leg.get("drop_address"):
				connecting_leg.pick_address = current_leg.get("drop_address")
			
			# Set to next leg's pickup location
			connecting_leg.facility_type_to = next_leg.get("facility_type_from")
			connecting_leg.facility_to = next_leg.get("facility_from")
			if next_leg.get("pick_address"):
				connecting_leg.drop_address = next_leg.get("pick_address")
			
			# Set order between current and next leg
			current_order = current_leg.get("order", i + 1) or (i + 1)
			connecting_leg.order = current_order + 1
			
			connecting_leg.insert(ignore_permissions=True)
			created_legs.append({"type": "Connecting", "name": connecting_leg.name})
		
		# 3. Create Return Leg: From Last Drop to Return Terminal
		if last_leg.get("facility_type_to") and last_leg.get("facility_to"):
			return_leg = frappe.new_doc("Transport Leg")
			return_leg.leg_type = "Return"
			return_leg.run_sheet = rs.name
			return_leg.transport_job = last_leg.get("transport_job")
			return_leg.run_date = last_leg.get("run_date")
			return_leg.vehicle_type = last_leg.get("vehicle_type") or rs.vehicle_type
			
			# Set from last drop location
			return_leg.facility_type_from = last_leg.get("facility_type_to")
			return_leg.facility_to = last_leg.get("facility_to")
			if last_leg.get("drop_address"):
				return_leg.pick_address = last_leg.get("drop_address")
			
			# Set to return terminal
			return_leg.facility_type_to = "Transport Terminal"
			return_leg.facility_to = rs.return_terminal
			return_address = _get_primary_address("Transport Terminal", rs.return_terminal)
			if return_address:
				return_leg.drop_address = return_address
			
			# Set order to be after the last leg
			return_leg.order = (last_leg.get("order", len(legs_data)) or len(legs_data)) + 1
			
			return_leg.insert(ignore_permissions=True)
			created_legs.append({"type": "Return", "name": return_leg.name})
		
		# Add created legs to Run Sheet's legs child table
		for leg_info in created_legs:
			leg_name = leg_info["name"]
			# Check if leg already exists in child table
			exists = False
			for row in rs.legs:
				if row.transport_leg == leg_name:
					exists = True
					break
			
			if not exists:
				rs.append("legs", {
					"transport_leg": leg_name,
					# Other fields will be auto-fetched via fetch_from
				})
		
		# Save Run Sheet to persist the new legs in child table
		rs.save(ignore_permissions=True)
		
		# Commit changes
		frappe.db.commit()
		
		# Refresh the Run Sheet to show new legs
		rs.reload()
		
		return {
			"status": "success",
			"message": _("Created {0} support leg(s)").format(len(created_legs)),
			"legs_created": len(created_legs),
			"legs": created_legs
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating support legs for Run Sheet {run_sheet_name}: {str(e)}")
		frappe.db.rollback()
		return {
			"status": "error",
			"message": str(e)
		}
