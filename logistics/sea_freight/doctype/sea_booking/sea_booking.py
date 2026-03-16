# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, flt
from frappe.contacts.doctype.address.address import get_address_display
from typing import Dict, Any


def _sync_quote_and_sales_quote(doc):
	"""Sync quote_type/quote with sales_quote for backward compatibility."""
	if getattr(doc, "quote_type", None) == "Sales Quote" and getattr(doc, "quote", None):
		doc.sales_quote = doc.quote
	elif getattr(doc, "quote_type", None) == "One-Off Quote":
		doc.sales_quote = None
	elif not getattr(doc, "quote_type", None) and getattr(doc, "sales_quote", None):
		doc.quote_type = "Sales Quote"
		doc.quote = doc.sales_quote


class SeaBooking(Document):
	def before_validate(self):
		"""Normalize legacy house_type values before validation"""
		# Normalize legacy house_type values BEFORE _validate_selects() runs
		if hasattr(self, 'house_type') and self.house_type:
			if self.house_type == "Direct":
				self.house_type = "Standard House"
			elif self.house_type == "Consolidation":
				self.house_type = "Co-load Master"
	
	def validate(self):
		"""Validate Sea Booking data"""
		from logistics.utils.module_integration import set_billing_company_from_sales_quote
		set_billing_company_from_sales_quote(self)
		# Normalize legacy house_type values (backup, in case before_validate didn't run)
		if hasattr(self, 'house_type') and self.house_type:
			if self.house_type == "Direct":
				self.house_type = "Standard House"
			elif self.house_type == "Consolidation":
				self.house_type = "Co-load Master"
		# Preserve quote field value before syncing (to prevent it from being cleared)
		# Get original values from database if document exists
		original_quote = None
		original_quote_type = None
		original_sales_quote = None
		
		if not self.is_new():
			try:
				original_quote = frappe.db.get_value(self.doctype, self.name, 'quote')
				original_quote_type = frappe.db.get_value(self.doctype, self.name, 'quote_type')
				original_sales_quote = frappe.db.get_value(self.doctype, self.name, 'sales_quote')
			except Exception:
				pass
		
		# Use current values if not in database yet
		if not original_quote:
			original_quote = getattr(self, 'quote', None)
		if not original_quote_type:
			original_quote_type = getattr(self, 'quote_type', None)
		if not original_sales_quote:
			original_sales_quote = getattr(self, 'sales_quote', None)
		
		_sync_quote_and_sales_quote(self)
		
		# Ensure quote field is preserved - restore original values if they were cleared
		# This ensures the quote field remains after submission
		if original_quote and not getattr(self, 'quote', None):
			self.quote = original_quote
		if original_quote_type and not getattr(self, 'quote_type', None):
			self.quote_type = original_quote_type
		# Only preserve sales_quote if quote_type is Sales Quote (One-Off Quote clears sales_quote)
		if original_sales_quote and getattr(self, 'quote_type', None) == 'Sales Quote' and not getattr(self, 'sales_quote', None):
			self.sales_quote = original_sales_quote
		
		# Validate One-off Sales Quote not already converted
		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import validate_one_off_quote_not_converted
			validate_one_off_quote_not_converted(self.sales_quote, self.doctype, self.name)
		
		# Validate quote field when quote_type is One-Off Quote (quote might reference Sales Quote)
		if getattr(self, "quote_type", None) == "One-Off Quote" and getattr(self, "quote", None):
			# Check if quote is a Sales Quote (new system) and validate it
			if frappe.db.exists("Sales Quote", self.quote):
				from logistics.pricing_center.doctype.sales_quote.sales_quote import validate_one_off_quote_not_converted
				validate_one_off_quote_not_converted(self.quote, self.doctype, self.name)
		
		# Handle sales_quote field clearing - reset One-off quote if cleared
		if not self.is_new() and original_sales_quote and not self.sales_quote:
			# sales_quote was cleared, check if it was a One-off quote and reset it
			try:
				if frappe.db.exists("Sales Quote", original_sales_quote):
					sq = frappe.get_doc("Sales Quote", original_sales_quote)
					if sq.quotation_type == "One-off":
						from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
						reset_one_off_quote_on_cancel(original_sales_quote)
			except Exception:
				pass
		
		self.validate_required_fields()
		self.validate_dates()
		self.validate_accounts()
		try:
			from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
			apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
		except Exception:
			pass
		if not getattr(self, "override_volume_weight", False):
			self.aggregate_volume_from_packages()
			self.aggregate_weight_from_packages()
		self.calculate_chargeable_weight()
		self._update_packing_summary()
		
		# Warn if accounting fields are missing (needed for conversion to shipment)
		if self.docstatus == 1:  # Only warn if submitted
			warnings = []
			if not self.branch:
				warnings.append(_("Branch"))
			if not self.cost_center:
				warnings.append(_("Cost Center"))
			if not self.profit_center:
				warnings.append(_("Profit Center"))
			
			if warnings:
				frappe.msgprint(
					_("Warning: The following fields are required for conversion to Sea Shipment: {0}").format(", ".join(warnings)),
					indicator="orange",
					title=_("Conversion Requirements")
				)
	
	def aggregate_volume_from_packages(self):
		"""Set header volume from sum of package volumes, converted to m³."""
		if getattr(self, "override_volume_weight", False):
			return
		packages = getattr(self, "packages", []) or []
		if not packages:
			return
		try:
			from logistics.utils.measurements import convert_volume, get_aggregation_volume_uom, get_default_uoms
			target_volume_uom = get_aggregation_volume_uom(company=getattr(self, "company", None))
			if not target_volume_uom:
				return
			defaults = get_default_uoms(company=getattr(self, "company", None))
			target_normalized = str(target_volume_uom).strip().upper()
			total = 0
			for pkg in packages:
				pkg_vol = flt(getattr(pkg, "volume", 0) or 0)
				if pkg_vol <= 0:
					continue
				pkg_volume_uom = getattr(pkg, "volume_uom", None) or defaults.get("volume")
				if not pkg_volume_uom:
					continue
				if str(pkg_volume_uom).strip().upper() == target_normalized:
					total += pkg_vol
				else:
					total += convert_volume(
						pkg_vol,
						from_uom=pkg_volume_uom,
						to_uom=target_volume_uom,
						company=getattr(self, "company", None),
					)
			if total > 0:
				self.total_volume = total
		except Exception:
			pass
	
	def aggregate_weight_from_packages(self):
		"""Set header weight from sum of package weights, converted to base/default weight UOM."""
		if getattr(self, "override_volume_weight", False):
			return
		packages = getattr(self, "packages", []) or []
		if not packages:
			if hasattr(self, "total_weight"):
				self.total_weight = 0
			return
		try:
			from logistics.utils.measurements import convert_weight, get_default_uoms
			defaults = get_default_uoms(company=getattr(self, "company", None))
			target_weight_uom = defaults.get("weight")  # Typically "Kg"
			if not target_weight_uom:
				return
			target_normalized = str(target_weight_uom).strip().upper()
			total = 0
			for pkg in packages:
				pkg_weight = flt(getattr(pkg, "weight", 0) or 0)
				if pkg_weight <= 0:
					continue
				pkg_weight_uom = getattr(pkg, "weight_uom", None) or defaults.get("weight")
				if not pkg_weight_uom:
					continue
				if str(pkg_weight_uom).strip().upper() == target_normalized:
					total += pkg_weight
				else:
					total += convert_weight(
						pkg_weight,
						from_uom=pkg_weight_uom,
						to_uom=target_weight_uom,
						company=getattr(self, "company", None),
					)
			if total > 0:
				self.total_weight = total
			else:
				self.total_weight = 0
		except Exception:
			pass
	
	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on total_volume and total_weight using Sea Freight Settings divisor."""
		if not self.total_volume and not self.total_weight:
			if hasattr(self, "chargeable"):
				self.chargeable = 0
			return
		
		# Get volume to weight divisor from Sea Freight Settings
		divisor = self.get_volume_to_weight_divisor()
		
		# Calculate volume weight
		volume_weight = 0
		if self.total_volume and divisor:
			# Convert volume from m³ to cm³, then divide by divisor
			# Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
			volume_weight = flt(self.total_volume) * (1000000.0 / divisor)
		
		# Calculate chargeable weight (higher of actual weight or volume weight)
		if self.total_weight and volume_weight:
			self.chargeable = max(flt(self.total_weight), volume_weight)
		elif self.total_weight:
			self.chargeable = flt(self.total_weight)
		elif volume_weight:
			self.chargeable = volume_weight
		else:
			self.chargeable = 0
	
	def get_volume_to_weight_divisor(self):
		"""Get the volume to weight divisor from Sea Freight Settings.
		Converts volume_to_weight_factor (kg/m³) to divisor format.
		Formula: divisor = 1,000,000 / factor
		Example: factor = 1000 kg/m³ → divisor = 1000
		"""
		try:
			settings = frappe.get_single("Sea Freight Settings")
			factor = getattr(settings, "volume_to_weight_factor", None)
			if factor:
				# Convert factor (kg/m³) to divisor: divisor = 1,000,000 / factor
				return flt(1000000.0 / flt(factor))
		except Exception:
			pass
		# Default to 1000 (equivalent to 1000 kg/m³ factor, common sea freight standard)
		return 1000.0
	
	def _update_packing_summary(self):
		"""Update total_containers, total_teus, total_packages from child tables. (volume/weight are the main fields.)"""
		containers = getattr(self, "containers", []) or []
		packages = getattr(self, "packages", []) or []
		
		self.total_containers = len(containers)
		
		total_teus = 0
		for c in containers:
			ct = getattr(c, "type", None)
			if ct:
				teu = frappe.db.get_value("Container Type", ct, "teu_count")
				total_teus += flt(teu) or 0
		self.total_teus = total_teus
		
		self.total_packages = sum(flt(getattr(p, "no_of_packs", 0) or 0) for p in packages)
	
	@frappe.whitelist()
	def aggregate_volume_from_packages_api(self):
		"""Whitelisted API method to aggregate volume and weight from packages for client-side calls."""
		if not getattr(self, "override_volume_weight", False):
			self.aggregate_volume_from_packages()
			self.aggregate_weight_from_packages()
		self.calculate_chargeable_weight()
		self._update_packing_summary()
		return {
			"total_volume": getattr(self, "total_volume", 0),
			"total_weight": getattr(self, "total_weight", 0),
			"chargeable": getattr(self, "chargeable", 0),
			"total_containers": getattr(self, "total_containers", 0),
			"total_teus": getattr(self, "total_teus", 0),
			"total_packages": getattr(self, "total_packages", 0),
		}
	
	def validate_container_numbers(self):
		"""Check for duplicate container numbers in submitted Sea Bookings and Sea Shipments."""
		if not hasattr(self, "containers") or not self.containers:
			return
		
		# ISO 6346 validation for each container
		from logistics.utils.container_validation import (
			validate_container_number,
			get_strict_validation_setting,
			normalize_container_number,
		)
		strict = get_strict_validation_setting()
		for i, c in enumerate(self.containers, 1):
			container_no = getattr(c, "container_no", None)
			if container_no and str(container_no).strip():
				valid, err = validate_container_number(container_no, strict=strict)
				if not valid:
					frappe.throw(_("Container {0}: {1}").format(i, err), title=_("Invalid Container Number"))
		
		# In-table duplicate: same container number must not appear on multiple rows
		seen = {}
		for i, c in enumerate(self.containers, 1):
			container_no = getattr(c, "container_no", None)
			if not container_no or not str(container_no).strip():
				continue
			normalized = normalize_container_number(container_no)
			if normalized in seen:
				frappe.throw(
					_("Duplicate container number in this document: {0} appears on row {1} and row {2}.").format(
						container_no, seen[normalized], i
					),
					title=_("Duplicate Container Numbers"),
				)
			seen[normalized] = i
		
		# Get container numbers from current booking (filter out empty values)
		container_numbers = [c.container_no for c in self.containers if getattr(c, "container_no", None) and str(c.container_no).strip()]
		if not container_numbers:
			return
		
		# Check for duplicates in other submitted Sea Bookings (allow reuse when container returned)
		if self.name:
			booking_candidates = frappe.db.sql("""
				SELECT DISTINCT sb.name, sbc.container_no
				FROM `tabSea Booking` sb
				INNER JOIN `tabSea Booking Containers` sbc ON sbc.parent = sb.name
				WHERE sbc.container_no IN %(container_numbers)s
				AND sb.name != %(booking_name)s
				AND sb.docstatus = 1
			""", {
				"container_numbers": container_numbers,
				"booking_name": self.name
			}, as_dict=True)
		else:
			booking_candidates = frappe.db.sql("""
				SELECT DISTINCT sb.name, sbc.container_no
				FROM `tabSea Booking` sb
				INNER JOIN `tabSea Booking Containers` sbc ON sbc.parent = sb.name
				WHERE sbc.container_no IN %(container_numbers)s
				AND sb.docstatus = 1
			""", {
				"container_numbers": container_numbers
			}, as_dict=True)
		existing_bookings = [c for c in booking_candidates if not self._container_returned(c.container_no)]

		# Check for duplicates in submitted Sea Shipments (allow reuse when container returned)
		shipment_candidates = frappe.db.sql("""
			SELECT DISTINCT ss.name, sfc.container_no
			FROM `tabSea Shipment` ss
			INNER JOIN `tabSea Freight Containers` sfc ON sfc.parent = ss.name
			WHERE sfc.container_no IN %(container_numbers)s
			AND ss.docstatus = 1
		""", {
			"container_numbers": container_numbers
		}, as_dict=True)
		existing_shipments = [
			c for c in shipment_candidates
			if not self._container_returned(c.container_no, other_shipment_name=c.name)
		]

		# Build error message if duplicates found
		errors = []
		if existing_bookings:
			container_list = ", ".join(set([c.container_no for c in existing_bookings]))
			booking_list = ", ".join(set([c.name for c in existing_bookings]))
			errors.append(_("Container number(s) {0} are already used in Sea Booking(s): {1}").format(
				container_list, booking_list
			))
		
		if existing_shipments:
			container_list = ", ".join(set([c.container_no for c in existing_shipments]))
			shipment_list = ", ".join(set([c.name for c in existing_shipments]))
			errors.append(_("Container number(s) {0} are already used in Sea Shipment(s): {1}").format(
				container_list, shipment_list
			))
		
		if errors:
			frappe.throw(
				"\n".join(errors),
				title=_("Duplicate Container Numbers")
			)
	
	def _container_returned(self, container_no, other_shipment_name=None):
		"""
		Return True if the container is considered returned so reuse on another booking is allowed.
		When checking another submitted booking/shipment, we allow reuse if the container has been
		returned (Container return_status/status or that shipment's shipping_status indicates returned).
		"""
		if not container_no:
			return False
		# If we have a specific shipment, use its shipping_status first (same as Sea Shipment logic)
		if other_shipment_name:
			shipping_status = frappe.db.get_value("Sea Shipment", other_shipment_name, "shipping_status")
			if shipping_status in ("Empty Container Returned", "Closed"):
				return True
		try:
			from logistics.container_management.api import is_container_management_enabled, get_container_by_number
			if is_container_management_enabled():
				container_name = get_container_by_number(container_no)
				if container_name:
					row = frappe.db.get_value(
						"Container", container_name, ["return_status", "status"], as_dict=True
					)
					if row:
						if row.get("return_status") == "Returned":
							return True
						if row.get("status") in ("Empty Returned", "Closed"):
							return True
		except Exception:
			pass
		return False
	
	def before_submit(self):
		"""Validate quote reference before submitting the Sea Booking."""
		# Ensure quote field values are preserved - sync quote and sales_quote before submission
		_sync_quote_and_sales_quote(self)
		
		# Validate quote reference: either sales_quote (for Sales Quote) or quote (for One-Off Quote) must be set
		quote_type = getattr(self, "quote_type", None)
		if quote_type == "Sales Quote":
			if not self.sales_quote:
				frappe.throw(_("Sales Quote is required. Please select a Sales Quote before submitting the Sea Booking."))
		elif quote_type == "One-Off Quote":
			if not getattr(self, "quote", None):
				frappe.throw(_("One-Off Quote is required. Please select a One-Off Quote before submitting the Sea Booking."))
		else:
			# If quote_type is not set, check if sales_quote is set (backward compatibility)
			if not self.sales_quote:
				frappe.throw(_("Sales Quote is required. Please select a Sales Quote before submitting the Sea Booking."))
		
		# Validate container numbers for duplicates
		self.validate_container_numbers()
	
	def after_submit(self):
		"""Ensure quote field values remain after submission."""
		# Preserve quote field value after submission - ensure it's not cleared
		# Get the quote value from the database to ensure it's preserved
		current_quote = frappe.db.get_value(self.doctype, self.name, 'quote')
		current_quote_type = frappe.db.get_value(self.doctype, self.name, 'quote_type')
		current_sales_quote = frappe.db.get_value(self.doctype, self.name, 'sales_quote')
		
		# If quote was set before submission, ensure it remains set
		# This prevents any code from clearing the quote field after submission
		if current_quote and not getattr(self, 'quote', None):
			self.db_set('quote', current_quote, update_modified=False)
		if current_quote_type and not getattr(self, 'quote_type', None):
			self.db_set('quote_type', current_quote_type, update_modified=False)
		if current_sales_quote and not getattr(self, 'sales_quote', None):
			self.db_set('sales_quote', current_sales_quote, update_modified=False)
		
		# Update One-off Sales Quote status to Converted
		if current_sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import update_one_off_quote_on_submit
			update_one_off_quote_on_submit(current_sales_quote, self.name, self.doctype)
	
	def on_cancel(self):
		"""Reset One-off Sales Quote status when Sea Booking is cancelled."""
		current_sales_quote = frappe.db.get_value(self.doctype, self.name, 'sales_quote')
		if current_sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
			reset_one_off_quote_on_cancel(current_sales_quote)
	
	def validate_required_fields(self):
		"""Validate required fields"""
		if not self.booking_date:
			frappe.throw(_("Booking Date is required"))
		
		if not self.local_customer:
			frappe.throw(_("Local Customer is required"))
		
		if not self.direction:
			frappe.throw(_("Direction is required"))
		
		if not self.shipper:
			frappe.throw(_("Shipper is required"))
		
		if not self.consignee:
			frappe.throw(_("Consignee is required"))
		
		if not self.origin_port:
			frappe.throw(_("Origin Port is required"))
		
		if not self.destination_port:
			frappe.throw(_("Destination Port is required"))
	
	def validate_dates(self):
		"""Validate date logic"""
		from frappe.utils import getdate
		
		# Validate ETD is before ETA
		if self.etd and self.eta:
			if getdate(self.etd) >= getdate(self.eta):
				frappe.throw(_("ETD (Estimated Time of Departure) must be before ETA (Estimated Time of Arrival)"))
	
	def validate_accounts(self):
		"""Validate that cost center, profit center, and branch belong to the company"""
		if not self.company:
			return
		
		if self.cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cost_center_company and cost_center_company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
					self.cost_center, self.company
				))
		
		if self.profit_center:
			# Check if Profit Center doctype has a company field before validating
			# Profit Center may not have a company field in this installation
			try:
				profit_center_meta = frappe.get_meta("Profit Center")
				if profit_center_meta.has_field("company"):
					profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
					if profit_center_company and profit_center_company != self.company:
						frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
							self.profit_center, self.company
						))
			except Exception as e:
				# If Profit Center doesn't have company field in database, skip validation
				# Check if it's a missing column error (1054: Unknown column)
				if hasattr(frappe.db, 'is_missing_column') and frappe.db.is_missing_column(e):
					# Field doesn't exist in database, skip validation
					pass
				elif "Unknown column" in str(e) or "1054" in str(e):
					# Field doesn't exist in database, skip validation
					pass
				else:
					# Re-raise other exceptions
					raise
		
		if self.branch:
			# Check if Branch doctype has a company field before validating
			# Branch may not have a company field in this installation
			try:
				branch_meta = frappe.get_meta("Branch")
				if branch_meta.has_field("company"):
					branch_company = frappe.db.get_value("Branch", self.branch, "company")
					if branch_company and branch_company != self.company:
						frappe.throw(_("Branch {0} does not belong to Company {1}").format(
							self.branch, self.company
						))
			except Exception:
				# If Branch doesn't have company field, skip validation
				pass
	
	def on_change(self):
		"""Handle changes to the document."""
		# Skip if flag is set (e.g., when creating from Sales Quote)
		if getattr(self.flags, 'skip_sales_quote_on_change', False):
			return
		
		# Skip if document name is still temporary (starts with "new-")
		# This prevents errors when the document is being saved for the first time
		if self.name and self.name.startswith("new-"):
			return
			
		if self.has_value_changed("sales_quote"):
			if self.sales_quote:
				self._populate_charges_from_sales_quote_doc()
			else:
				# Clear charges if sales_quote is removed
				self.set("charges", [])
				frappe.msgprint(
					"Charges cleared as Sales Quote was removed",
					title="Charges Updated",
					indicator="blue"
				)
		
		# Handle One-Off Quote changes
		if self.has_value_changed("quote") or self.has_value_changed("quote_type"):
			if getattr(self, "quote_type", None) == "One-Off Quote" and self.quote:
				self._populate_charges_from_one_off_quote()
			elif getattr(self, "quote_type", None) == "One-Off Quote" and not self.quote:
				# Clear charges if One-Off Quote is removed
				self.set("charges", [])
				frappe.msgprint(
					"Charges cleared as One-Off Quote was removed",
					title="Charges Updated",
					indicator="blue"
				)
	
	@frappe.whitelist()
	def fetch_quotations(self):
		"""
		Fetch quotations from Sales Quote and populate Sea Booking fields.
		
		Returns:
			dict: Result with status and message
		"""
		try:
			if not self.sales_quote:
				frappe.throw(_("Please select a Sales Quote first"))
			
			# Set flag to skip on_change handler to prevent it from interfering with charge population
			# This flag prevents on_change from clearing/populating charges when fields are modified
			self.flags.skip_sales_quote_on_change = True
			# Also set a flag to indicate we're fetching quotations (for JavaScript to know not to trigger handlers)
			self.flags.fetching_quotations = True
			
			# Get Sales Quote document
			sales_quote = frappe.get_doc("Sales Quote", self.sales_quote)
			
			# Check if Sales Quote has sea charges (new) or sea freight (legacy)
			sea_charge_exists = frappe.db.exists("Sales Quote Charge", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote",
				"service_type": "Sea"
			})
			sea_freight_exists = frappe.db.exists("Sales Quote Sea Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			}) if frappe.db.table_exists("Sales Quote Sea Freight") else False
			
			if not sea_charge_exists and not sea_freight_exists:
				frappe.msgprint(
					_("No Sea Freight lines found in Sales Quote {0}. Only basic fields will be populated.").format(self.sales_quote),
					indicator="orange"
				)
			
			# Map basic fields from Sales Quote to Sea Booking
			if not self.local_customer:
				self.local_customer = sales_quote.customer
			if not self.shipper:
				self.shipper = getattr(sales_quote, 'shipper', None)
			if not self.consignee:
				self.consignee = getattr(sales_quote, 'consignee', None)
			if not getattr(self, "sending_agent", None):
				self.sending_agent = getattr(sales_quote, "sending_agent", None)
			if not getattr(self, "receiving_agent", None):
				self.receiving_agent = getattr(sales_quote, "receiving_agent", None)
			if not getattr(self, "broker", None):
				self.broker = getattr(sales_quote, "broker", None)
			if not self.origin_port:
				self.origin_port = getattr(sales_quote, 'location_from', None)
			if not self.destination_port:
				self.destination_port = getattr(sales_quote, 'location_to', None)
			if not self.direction:
				self.direction = getattr(sales_quote, 'direction', None)
			if not self.total_weight:
				self.total_weight = getattr(sales_quote, 'total_weight', None) or getattr(sales_quote, 'weight', None)
			if not self.total_volume:
				self.total_volume = getattr(sales_quote, 'total_volume', None) or getattr(sales_quote, 'volume', None)
			if not self.chargeable:
				self.chargeable = getattr(sales_quote, 'chargeable', None)
			if not self.service_level:
				self.service_level = getattr(sales_quote, 'service_level', None)
			if not self.incoterm:
				self.incoterm = getattr(sales_quote, 'incoterm', None)
			if not self.additional_terms:
				self.additional_terms = getattr(sales_quote, 'additional_terms', None)
			if not self.company:
				self.company = sales_quote.company
			if not self.branch:
				self.branch = sales_quote.branch
			if not self.cost_center:
				self.cost_center = sales_quote.cost_center
			if not self.profit_center:
				self.profit_center = sales_quote.profit_center
			if not self.tc_name:
				self.tc_name = getattr(sales_quote, 'tc_name', None)
			if not self.terms:
				self.terms = getattr(sales_quote, 'terms', None)
			
			# Populate charges from Sales Quote Charge (Sea) or Sales Quote Sea Freight (legacy)
			sea_charge_exists = frappe.db.exists("Sales Quote Charge", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote",
				"service_type": "Sea"
			})
			sea_freight_exists = frappe.db.exists("Sales Quote Sea Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			}) if frappe.db.table_exists("Sales Quote Sea Freight") else False
			if sea_charge_exists or sea_freight_exists:
				self._populate_charges_from_sales_quote(sales_quote)
			
			# Save the document to persist the changes (charges and other fields)
			# This ensures charges are saved before the form reloads
			# Keep the flag set during save to prevent on_change from running
			self.save(ignore_permissions=True)
			
			# Clear the flags after charge population and save
			self.flags.skip_sales_quote_on_change = False
			self.flags.fetching_quotations = False
			
			frappe.msgprint(
				_("Quotations fetched successfully from Sales Quote {0}").format(self.sales_quote),
				title=_("Success"),
				indicator="green"
			)
			
			return {
				"success": True,
				"message": _("Quotations fetched successfully")
			}
			
		except Exception as e:
			# Clear the flags even on error
			self.flags.skip_sales_quote_on_change = False
			self.flags.fetching_quotations = False
			frappe.log_error(
				f"Error fetching quotations for Sea Booking {self.name}: {str(e)}",
				"Sea Booking - Fetch Quotations Error"
			)
			frappe.throw(_("Error fetching quotations: {0}").format(str(e)))
	
	def _populate_charges_from_sales_quote_doc(self):
		"""Populate charges based on sales_quote_transport of the filled sales_quote."""
		if not self.sales_quote:
			return

		try:
			# Verify that the sales_quote exists
			if not frappe.db.exists("Sales Quote", self.sales_quote):
				frappe.msgprint(
					f"Sales Quote {self.sales_quote} does not exist",
					title="Error",
					indicator="red"
				)
				return

			# Clear existing charges
			self.set("charges", [])

			# Fetch from Sales Quote Charge (Sea) or Sales Quote Sea Freight (legacy)
			charge_fields = [
				"name", "item_code", "item_name", "calculation_method", "uom", "currency",
				"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue", "charge_type"
			]
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Charge",
				filters={"parent": self.sales_quote, "parenttype": "Sales Quote", "service_type": "Sea"},
				fields=charge_fields,
				order_by="idx"
			)
			if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
				sales_quote_sea_freight_records = frappe.get_all(
					"Sales Quote Sea Freight",
					filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
					fields=charge_fields,
					order_by="idx"
				)

			if not sales_quote_sea_freight_records:
				frappe.msgprint(
					f"No sea freight charges found in Sales Quote: {self.sales_quote}",
					title="No Charges Found",
					indicator="orange"
				)
				return

			# Map and populate charges
			charges_added = 0
			for sqsf_record in sales_quote_sea_freight_records:
				charge_row = self._map_sales_quote_sea_freight_to_charge(sqsf_record)
				if charge_row:
					self.append("charges", charge_row)
					charges_added += 1

			if charges_added > 0:
				frappe.msgprint(
					f"Successfully populated {charges_added} charges from Sales Quote: {self.sales_quote}",
					title="Charges Updated",
					indicator="green"
				)
			else:
				frappe.msgprint(
					f"No valid charges could be mapped from Sales Quote: {self.sales_quote}",
					title="No Valid Charges",
					indicator="orange"
				)

		except Exception as e:
			frappe.log_error(
				f"Error populating charges from sales quote {self.sales_quote}: {str(e)}",
				"Sea Booking Charges Population Error"
			)
			frappe.msgprint(
				f"Error populating charges: {str(e)}",
				title="Error",
				indicator="red"
			)
	
	def _populate_charges_from_sales_quote(self, sales_quote):
		"""Populate charges from Sales Quote Sea Freight records (legacy method for fetch_quotations)"""
		try:
			# Clear existing charges
			self.set("charges", [])
			
			# Get from Sales Quote Charge (Sea) or Sales Quote Sea Freight (legacy)
			charge_fields = [
				"item_code", "item_name", "calculation_method", "uom", "currency",
				"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue", "charge_type"
			]
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Charge",
				filters={"parent": sales_quote.name, "parenttype": "Sales Quote", "service_type": "Sea"},
				fields=charge_fields,
				order_by="idx"
			)
			if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
				sales_quote_sea_freight_records = frappe.get_all(
					"Sales Quote Sea Freight",
					filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
					fields=charge_fields,
					order_by="idx"
				)
			
			if not sales_quote_sea_freight_records:
				frappe.msgprint(
					_("No Sea Freight charges found in Sales Quote. Charges will not be populated."),
					indicator="orange"
				)
				return
			
			# Map and populate charges
			charges_added = 0
			for sqsf_record in sales_quote_sea_freight_records:
				charge_row = self._map_sales_quote_sea_freight_to_charge(sqsf_record)
				if charge_row:
					self.append("charges", charge_row)
					charges_added += 1
			
			if charges_added > 0:
				frappe.msgprint(
					_("Successfully populated {0} charges from Sales Quote").format(charges_added),
					title=_("Charges Updated"),
					indicator="green"
				)
			
		except Exception as e:
			frappe.log_error(
				f"Error populating charges from Sales Quote: {str(e)}",
				"Sea Booking - Charges Population Error"
			)
			# Don't raise - allow booking to be saved even if charges fail
			frappe.msgprint(
				_("Warning: Could not populate all charges from Sales Quote: {0}").format(str(e)),
				indicator="orange"
			)
	
	def _populate_charges_from_one_off_quote(self):
		"""Populate charges based on one_off_quote_sea_freight of the filled one_off_quote."""
		if not self.quote or getattr(self, "quote_type", None) != "One-Off Quote":
			return

		try:
			# Verify that the one_off_quote exists
			if not frappe.db.exists("One-Off Quote", self.quote):
				frappe.msgprint(
					f"One-Off Quote {self.quote} does not exist",
					title="Error",
					indicator="red"
				)
				return

			# Clear existing charges
			self.set("charges", [])

			# Fetch one_off_quote_sea_freight records from the selected one_off_quote
			one_off_quote_sea_freight_records = frappe.get_all(
				"One-Off Quote Sea Freight",
				filters={"parent": self.quote, "parenttype": "One-Off Quote"},
				fields=[
					"name",
					"item_code",
					"item_name",
					"calculation_method",
					"uom",
					"currency",
					"unit_rate",
					"unit_type",
					"minimum_quantity",
					"minimum_charge",
					"maximum_charge",
					"base_amount",
					"estimated_revenue"
				],
				order_by="idx"
			)

			if not one_off_quote_sea_freight_records:
				frappe.msgprint(
					f"No sea freight charges found in One-Off Quote: {self.quote}",
					title="No Charges Found",
					indicator="orange"
				)
				return

			# Map and populate charges (One-Off Quote Sea Freight has same structure as Sales Quote Sea Freight)
			charges_added = 0
			for oqsf_record in one_off_quote_sea_freight_records:
				charge_row = self._map_sales_quote_sea_freight_to_charge(oqsf_record)
				if charge_row:
					self.append("charges", charge_row)
					charges_added += 1

			if charges_added > 0:
				frappe.msgprint(
					f"Successfully populated {charges_added} charges from One-Off Quote: {self.quote}",
					title="Charges Updated",
					indicator="green"
				)
			else:
				frappe.msgprint(
					f"No valid charges could be mapped from One-Off Quote: {self.quote}",
					title="No Valid Charges",
					indicator="orange"
				)

		except Exception as e:
			frappe.log_error(
				f"Error populating charges from one-off quote {self.quote}: {str(e)}",
				"Sea Booking Charges Population Error"
			)
			frappe.msgprint(
				f"Error populating charges: {str(e)}",
				title="Error",
				indicator="red"
			)
	
	def _map_sales_quote_sea_freight_to_charge(self, sqsf_record):
		"""Map sales_quote_sea_freight record to sea_booking_charges format"""
		try:
			# Get the item details
			item_doc = frappe.get_doc("Item", sqsf_record.item_code)
			
			# Get default currency
			default_currency = frappe.get_system_settings("currency") or "USD"
			
			# Map unit_type from Sales Quote to Sea Booking Charges unit_type
			# Sea Booking Charges unit_type options: Distance, Weight, Volume, Package, Piece, Job, Trip, TEU, Operation Time
			unit_type_mapping = {
				"Weight": "Weight",
				"Volume": "Volume",
				"Package": "Package",
				"Piece": "Piece",
				"Container": "TEU",  # Map Container to TEU
				"Shipment": "Job"  # Map Shipment to Job
			}
			mapped_unit_type = unit_type_mapping.get(sqsf_record.unit_type, "Package")
			
			# Get quantity based on unit type
			quantity = 0
			if sqsf_record.unit_type == "Weight":
				quantity = flt(self.total_weight) or 0
			elif sqsf_record.unit_type == "Volume":
				quantity = flt(self.total_volume) or 0
			elif sqsf_record.unit_type == "Package" or sqsf_record.unit_type == "Piece":
				if hasattr(self, 'packages') and self.packages:
					quantity = len(self.packages)
				else:
					quantity = 1
			elif sqsf_record.unit_type == "Container":
				if hasattr(self, 'containers') and self.containers:
					quantity = len(self.containers)
				else:
					quantity = 1
			elif sqsf_record.unit_type == "Shipment":
				quantity = 1
			else:
				quantity = 1
			
			# Calculate selling amount based on calculation method
			selling_amount = 0
			if sqsf_record.calculation_method == "Per Unit":
				selling_amount = (sqsf_record.unit_rate or 0) * quantity
				# Apply minimum/maximum charge
				if sqsf_record.minimum_charge and selling_amount < flt(sqsf_record.minimum_charge):
					selling_amount = flt(sqsf_record.minimum_charge)
				if sqsf_record.maximum_charge and selling_amount > flt(sqsf_record.maximum_charge):
					selling_amount = flt(sqsf_record.maximum_charge)
			elif sqsf_record.calculation_method == "Fixed Amount":
				selling_amount = sqsf_record.unit_rate or 0
			elif sqsf_record.calculation_method == "Base Plus Additional":
				base = flt(sqsf_record.base_amount) or 0
				additional = (sqsf_record.unit_rate or 0) * max(0, quantity - 1)
				selling_amount = base + additional
			elif sqsf_record.calculation_method == "First Plus Additional":
				min_qty = flt(sqsf_record.minimum_quantity) or 1
				if quantity <= min_qty:
					selling_amount = sqsf_record.unit_rate or 0
				else:
					additional = (sqsf_record.unit_rate or 0) * (quantity - min_qty)
					selling_amount = (sqsf_record.unit_rate or 0) + additional
			else:
				selling_amount = sqsf_record.unit_rate or 0
			
			# Determine charge_type: first from Sales Quote Sea Freight record, then from item, then default
			charge_type = "Revenue"
			# First check if charge_type is set in the Sales Quote Sea Freight record
			if hasattr(sqsf_record, 'charge_type') and sqsf_record.charge_type:
				charge_type = sqsf_record.charge_type
			# Fall back to item's custom_charge_type if not set in Sales Quote Sea Freight
			elif hasattr(item_doc, 'custom_charge_type') and item_doc.custom_charge_type:
				charge_type = item_doc.custom_charge_type
			
			# Normalize calculation_method for Sea Booking Charges
			sqsf_calc_method = (sqsf_record.get("calculation_method") or "").strip()
			valid_calc_methods = [
				"Per Unit", "Fixed Amount", "Flat Rate", "Base Plus Additional",
				"First Plus Additional", "Percentage", "Location-based", "Weight Break", "Qty Break"
			]
			
			# Invalid calculation methods that should be converted
			invalid_calc_methods = [
				"Per m³", "Per m3", "Per kg", "Per package", "Per shipment",
				"per m³", "per m3", "per kg", "per package", "per shipment",
				"Per m³", "Per m3", "Per Kg", "Per Package", "Per Shipment",
				"Automatic", "automatic", "Manual", "manual"
			]
			
			# Normalize the calculation_method value (handle case variations and common mistakes)
			sqsf_calc_method_normalized = sqsf_calc_method
			if sqsf_calc_method:
				# First check if it's an invalid method (case-insensitive)
				sqsf_calc_method_lower = sqsf_calc_method.lower()
				sqsf_calc_method_normalized_lower = sqsf_calc_method_normalized.lower()
				
				# Check for invalid methods first
				if sqsf_calc_method_normalized_lower in [m.lower() for m in invalid_calc_methods]:
					# These are invalid - will be converted to "Per Unit" below
					pass
				# Handle case-insensitive matching for valid method variations
				elif sqsf_calc_method_lower in ["per unit", "perunit"]:
					sqsf_calc_method_normalized = "Per Unit"
				elif sqsf_calc_method_lower in ["fixed amount", "fixedamount"]:
					sqsf_calc_method_normalized = "Fixed Amount"
				elif sqsf_calc_method_lower in ["flat rate", "flatrate"]:
					sqsf_calc_method_normalized = "Flat Rate"
				elif sqsf_calc_method_lower in ["base plus additional", "baseplusadditional"]:
					sqsf_calc_method_normalized = "Base Plus Additional"
				elif sqsf_calc_method_lower in ["first plus additional", "firstplusadditional"]:
					sqsf_calc_method_normalized = "First Plus Additional"
				elif sqsf_calc_method_lower in ["percentage"]:
					sqsf_calc_method_normalized = "Percentage"
				elif sqsf_calc_method_lower in ["location-based", "locationbased"]:
					sqsf_calc_method_normalized = "Location-based"
				elif sqsf_calc_method_lower in ["weight break", "weightbreak"]:
					sqsf_calc_method_normalized = "Weight Break"
				elif sqsf_calc_method_lower in ["qty break", "qtybreak", "quantity break", "quantitybreak"]:
					sqsf_calc_method_normalized = "Qty Break"
			
			# If calculation_method is invalid (e.g., "Per m³", "Automatic", empty), convert based on unit_type
			calc_method_final = sqsf_calc_method_normalized
			if not sqsf_calc_method_normalized or sqsf_calc_method_normalized not in valid_calc_methods:
				sqsf_calc_method_normalized_lower = sqsf_calc_method_normalized.lower() if sqsf_calc_method_normalized else ""
				if sqsf_calc_method_normalized_lower in [m.lower() for m in invalid_calc_methods]:
					calc_method_final = "Per Unit"
				elif sqsf_calc_method_normalized_lower in ["fixed amount", "flat rate"]:
					calc_method_final = "Flat Rate"
				else:
					calc_method_final = "Per Unit" if sqsf_record.get("unit_type") else "Flat Rate"
			else:
				calc_method_final = sqsf_calc_method_normalized
			
			if calc_method_final not in valid_calc_methods:
				calc_method_final = "Per Unit" if sqsf_record.get("unit_type") else "Flat Rate"
			
			# Map the fields to Sea Booking Charges structure
			charge_data = {
				"charge_item": sqsf_record.item_code,
				"charge_name": sqsf_record.item_name or item_doc.item_name,
				"charge_type": charge_type,
				"charge_description": sqsf_record.item_name or item_doc.item_name,
				"bill_to": getattr(sqsf_record, "bill_to", None) or (self.local_customer if hasattr(self, 'local_customer') else None),
				"pay_to": getattr(sqsf_record, "pay_to", None),
				"selling_currency": sqsf_record.currency or default_currency,
				"selling_amount": selling_amount,
				"rate": sqsf_record.unit_rate or 0,
				"uom": sqsf_record.uom or None,
				"revenue_calculation_method": calc_method_final,
				"quantity": quantity,
				"currency": sqsf_record.currency or default_currency,
				"unit_type": mapped_unit_type,  # Use mapped unit_type
				"base_amount": sqsf_record.base_amount or 0
			}
			
			# Add minimum/maximum charges and quantities if available
			if sqsf_record.minimum_charge:
				charge_data["minimum_charge"] = sqsf_record.minimum_charge
			if sqsf_record.maximum_charge:
				charge_data["maximum_charge"] = sqsf_record.maximum_charge
			if sqsf_record.minimum_quantity:
				charge_data["minimum_quantity"] = sqsf_record.minimum_quantity
			
			return charge_data
			
		except Exception as e:
			frappe.log_error(
				f"Error mapping sales quote sea freight record: {str(e)}",
				"Sea Booking Mapping Error"
			)
			return None
	
	
	@frappe.whitelist()
	def check_conversion_readiness(self):
		"""
		Check if Sea Booking is ready for conversion to Sea Shipment.
		
		Returns:
			dict: Status with missing_fields list and is_ready boolean
		"""
		missing_fields = []
		
		# Check required accounting fields
		if not self.branch:
			missing_fields.append({
				"field": "branch",
				"label": "Branch",
				"tab": "Accounts",
				"message": "Branch is required for conversion to Sea Shipment"
			})
		
		if not self.cost_center:
			missing_fields.append({
				"field": "cost_center",
				"label": "Cost Center",
				"tab": "Accounts",
				"message": "Cost Center is required for conversion to Sea Shipment"
			})
		
		if not self.profit_center:
			missing_fields.append({
				"field": "profit_center",
				"label": "Profit Center",
				"tab": "Accounts",
				"message": "Profit Center is required for conversion to Sea Shipment"
			})
		
		# Check shipping_line OR master_bill (either one is acceptable)
		if not self.shipping_line and not self.master_bill:
			missing_fields.append({
				"field": "shipping_line",
				"label": "Shipping Line or Master Bill",
				"tab": "Details",
				"message": "Shipping Line or Master Bill is required for conversion to Sea Shipment"
			})
		
		# Validate ports
		if self.origin_port and not frappe.db.exists("UNLOCO", self.origin_port):
			if frappe.db.exists("Location", self.origin_port):
				missing_fields.append({
					"field": "origin_port",
					"label": "Origin Port",
					"tab": "Details",
					"message": "Origin Port must be a UNLOCO code, not a Location"
				})
			else:
				missing_fields.append({
					"field": "origin_port",
					"label": "Origin Port",
					"tab": "Details",
					"message": "Origin Port is not a valid UNLOCO code"
				})
		
		if self.destination_port and not frappe.db.exists("UNLOCO", self.destination_port):
			if frappe.db.exists("Location", self.destination_port):
				missing_fields.append({
					"field": "destination_port",
					"label": "Destination Port",
					"tab": "Details",
					"message": "Destination Port must be a UNLOCO code, not a Location"
				})
			else:
				missing_fields.append({
					"field": "destination_port",
					"label": "Destination Port",
					"tab": "Details",
					"message": "Destination Port is not a valid UNLOCO code"
				})
		
		# Validate link fields
		if self.service_level and not frappe.db.exists("Service Level Agreement", self.service_level):
			missing_fields.append({
				"field": "service_level",
				"label": "Service Level",
				"tab": "Details",
				"message": f"Service Level '{self.service_level}' does not exist"
			})
		
		return {
			"is_ready": len(missing_fields) == 0,
			"missing_fields": missing_fields
		}
	
	@frappe.whitelist()
	def get_dashboard_html(self):
		"""Generate HTML for Dashboard tab: Run Sheet layout with map, milestones."""
		try:
			from logistics.document_management.api import get_document_alerts_html, get_dashboard_alerts_html
			from logistics.document_management.dashboard_layout import (
				build_run_sheet_style_dashboard,
				build_map_segments_from_routing_legs,
				get_dg_dashboard_html,
				get_unloco_coords,
			)

			status = self.get("shipping_status")
			if not status:
				status = "Submitted" if self.docstatus == 1 else "Cancelled" if self.docstatus == 2 else "Draft"
			header_items = [
				("Status", status),
				("ETD", str(self.etd) if self.etd else "—"),
				("ETA", str(self.eta) if self.eta else "—"),
				("Packages", str(len(self.packages or []))),
				("Weight", frappe.format_value(self.total_weight or 0, df=dict(fieldtype="Float"))),
			]
			if self.shipping_line:
				header_items.append(("Shipping Line", self.shipping_line))

			try:
				doc_alerts = get_document_alerts_html("Sea Booking", self.name or "new")
			except Exception:
				doc_alerts = ""

			dg_route_below_html = get_dg_dashboard_html(self)

			milestone_rows = list(self.get("milestones") or [])
			milestone_details = {}
			if milestone_rows:
				names = [m.milestone for m in milestone_rows if m.milestone]
				if names:
					for lm in frappe.get_all("Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]):
						milestone_details[lm.name] = lm.description or lm.name

			cards_html = ""
			for i, m in enumerate(milestone_rows, 1):
				st = (m.status or "Planned").lower().replace(" ", "-")
				desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
				planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
				actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
				cards_html += f"""
				<div class="dash-card {st}">
					<div class="card-header"><h5>{desc}</h5><span class="card-num">#{i}</span></div>
					<div class="card-details">Planned: {planned}<br>Actual: {actual}</div>
					<span class="card-badge {st}">{m.status or "Planned"}</span>
				</div>"""

			map_segments = build_map_segments_from_routing_legs(
				getattr(self, "routing_legs", None) or []
			)
			map_points = []
			if not map_segments:
				o = get_unloco_coords(self.origin_port)
				d = get_unloco_coords(self.destination_port)
				if o:
					map_points.append(o)
				if d and (not map_points or (d.get("lat") != map_points[-1].get("lat")) or (d.get("lon") != map_points[-1].get("lon"))):
					map_points.append(d)

			alerts_html = get_dashboard_alerts_html("Sea Booking", self.name or "new")
			return build_run_sheet_style_dashboard(
				header_title=self.name or "Sea Booking",
				header_subtitle="Sea Booking",
				header_items=header_items,
				cards_html=cards_html or "<div class=\"text-muted\">No milestones. Use Get Milestones in Actions to generate from template.</div>",
				map_points=map_points,
				map_segments=map_segments,
				map_id_prefix="sea-booking-dash-map",
				doc_alerts_html=doc_alerts,
				alerts_html=alerts_html,
				straight_line=True,
				origin_label=self.origin_port or None,
				destination_label=self.destination_port or None,
				route_below_html=dg_route_below_html,
			)
		except Exception as e:
			frappe.log_error(f"Sea Booking get_dashboard_html: {str(e)}", "Sea Booking Dashboard")
			return "<div class='alert alert-warning'>Error loading dashboard.</div>"

	def validate_before_conversion(self):
		"""
		Validate that all required fields are present before conversion to Sea Shipment.
		
		Raises:
			frappe.ValidationError: If required fields are missing
		"""
		# Validate dates before conversion
		self.validate_dates()
		
		# Check if both quote and charges are empty
		quote_type = getattr(self, "quote_type", None)
		has_quote = False
		
		if quote_type == "Sales Quote":
			has_quote = bool(self.sales_quote)
		elif quote_type == "One-Off Quote":
			has_quote = bool(getattr(self, "quote", None))
		else:
			# If quote_type is not set, check sales_quote (backward compatibility)
			has_quote = bool(self.sales_quote)
		
		has_charges = bool(hasattr(self, 'charges') and self.charges and len(self.charges) > 0)
		
		if not has_quote and not has_charges:
			frappe.throw(_("Cannot convert to Sea Shipment. Either a Quote or Charges must be present."))
		
		readiness = self.check_conversion_readiness()
		
		if not readiness["is_ready"]:
			messages = [field["message"] for field in readiness["missing_fields"]]
			frappe.throw(_("Cannot convert to Sea Shipment. Missing or invalid fields:\n{0}").format("\n".join(f"- {msg}" for msg in messages)))
	
	@frappe.whitelist()
	def convert_to_shipment(self):
		"""
		Convert Sea Booking to Sea Shipment.
		
		Enforces 1:1 relationship - one Sea Booking can only have one Sea Shipment.
		
		Returns:
			dict: Result with created Sea Shipment name and status
		"""
		try:
			# Check if Sea Shipment already exists for this Sea Booking (1:1 relationship)
			existing_shipment = frappe.db.get_value("Sea Shipment", {"sea_booking": self.name}, "name")
			if existing_shipment:
				frappe.throw(_(
					"Sea Shipment {0} already exists for this Sea Booking. "
					"One Sea Booking can only have one Sea Shipment."
				).format(existing_shipment))
			
			# Validate before conversion
			self.validate_before_conversion()
			
			# Create new Sea Shipment
			sea_shipment = frappe.new_doc("Sea Shipment")
			
			# Map basic fields from Sea Booking to Sea Shipment
			sea_shipment.local_customer = self.local_customer
			sea_shipment.booking_date = self.booking_date or today()
			sea_shipment.sea_booking = self.name
			sea_shipment.sales_quote = self.sales_quote
			if hasattr(self, "booking_party") and self.booking_party:
				sea_shipment.booking_party = self.booking_party
			if hasattr(self, "controlling_party") and self.controlling_party:
				sea_shipment.controlling_party = self.controlling_party
			sea_shipment.shipper = self.shipper
			sea_shipment.consignee = self.consignee
			sea_shipment.origin_port = self.origin_port
			sea_shipment.destination_port = self.destination_port
			if hasattr(self, "sending_agent") and self.sending_agent:
				sea_shipment.sending_agent = self.sending_agent
			if hasattr(self, "receiving_agent") and self.receiving_agent:
				sea_shipment.receiving_agent = self.receiving_agent
			if hasattr(self, "broker") and self.broker:
				sea_shipment.broker = self.broker
			sea_shipment.direction = self.direction
			sea_shipment.total_weight = self.total_weight
			sea_shipment.total_volume = self.total_volume
			sea_shipment.chargeable = self.chargeable
			# Only copy service_level if it exists as a valid record
			if self.service_level and frappe.db.exists("Logistics Service Level", self.service_level):
				sea_shipment.service_level = self.service_level
			else:
				# Explicitly clear the field if the record doesn't exist
				sea_shipment.service_level = None
			sea_shipment.incoterm = self.incoterm
			sea_shipment.additional_terms = self.additional_terms
			sea_shipment.shipping_line = self.shipping_line
			sea_shipment.freight_agent = self.freight_agent
			sea_shipment.house_type = self.house_type
			# Normalize legacy house_type values
			if sea_shipment.house_type == "Direct":
				sea_shipment.house_type = "Standard House"
			elif sea_shipment.house_type == "Consolidation":
				sea_shipment.house_type = "Co-load Master"
			# Only copy release_type if it exists as a valid record
			if self.release_type and frappe.db.exists("Release Type", self.release_type):
				sea_shipment.release_type = self.release_type
			else:
				# Explicitly clear the field if the record doesn't exist
				sea_shipment.release_type = None
			sea_shipment.entry_type = self.entry_type
			sea_shipment.house_bl = self.house_bl
			sea_shipment.packs = self.packs
			sea_shipment.inner = self.inner
			sea_shipment.goods_value = self.goods_value
			sea_shipment.insurance = self.insurance
			sea_shipment.description = self.description
			sea_shipment.marks_and_nos = self.marks_and_nos
			sea_shipment.etd = self.etd
			sea_shipment.eta = self.eta
			if hasattr(self, "atd") and self.atd:
				sea_shipment.atd = self.atd
			if hasattr(self, "ata") and self.ata:
				sea_shipment.ata = self.ata
			sea_shipment.transport_mode = self.transport_mode
			sea_shipment.company = self.company
			sea_shipment.branch = self.branch
			sea_shipment.cost_center = self.cost_center
			sea_shipment.profit_center = self.profit_center
			# Copy measurement override and costing fields
			if hasattr(self, "override_volume_weight"):
				sea_shipment.override_volume_weight = self.override_volume_weight or 0
			if hasattr(self, "project") and self.project:
				sea_shipment.project = self.project
			if hasattr(self, "job_costing_number") and self.job_costing_number:
				sea_shipment.job_costing_number = self.job_costing_number
			# Copy DG fields
			if hasattr(self, "contains_dangerous_goods"):
				sea_shipment.contains_dangerous_goods = self.contains_dangerous_goods or 0
			if hasattr(self, "dg_declaration_complete"):
				sea_shipment.dg_declaration_complete = self.dg_declaration_complete or 0
			if hasattr(self, "dg_compliance_status"):
				sea_shipment.dg_compliance_status = self.dg_compliance_status
			if hasattr(self, "dg_emergency_contact"):
				sea_shipment.dg_emergency_contact = self.dg_emergency_contact
			if hasattr(self, "dg_emergency_phone"):
				sea_shipment.dg_emergency_phone = self.dg_emergency_phone
			if hasattr(self, "dg_emergency_email"):
				sea_shipment.dg_emergency_email = self.dg_emergency_email
			# Copy notes and terms
			if hasattr(self, "tc_name") and self.tc_name:
				sea_shipment.tc_name = self.tc_name
			if hasattr(self, "terms") and self.terms:
				sea_shipment.terms = self.terms
			if hasattr(self, "internal_notes") and self.internal_notes:
				sea_shipment.internal_notes = self.internal_notes
			if hasattr(self, "client_notes") and self.client_notes:
				sea_shipment.client_notes = self.client_notes
			
			# Copy address and contact from Booking if set
			if hasattr(self, "shipper_address") and self.shipper_address:
				sea_shipment.shipper_address = self.shipper_address
			if hasattr(self, "shipper_address_display") and self.shipper_address_display:
				sea_shipment.shipper_address_display = self.shipper_address_display
			if hasattr(self, "consignee_address") and self.consignee_address:
				sea_shipment.consignee_address = self.consignee_address
			if hasattr(self, "consignee_address_display") and self.consignee_address_display:
				sea_shipment.consignee_address_display = self.consignee_address_display
			if hasattr(self, "shipper_contact") and self.shipper_contact:
				sea_shipment.shipper_contact = self.shipper_contact
			if hasattr(self, "shipper_contact_display") and self.shipper_contact_display:
				sea_shipment.shipper_contact_display = self.shipper_contact_display
			if hasattr(self, "consignee_contact") and self.consignee_contact:
				sea_shipment.consignee_contact = self.consignee_contact
			if hasattr(self, "consignee_contact_display") and self.consignee_contact_display:
				sea_shipment.consignee_contact_display = self.consignee_contact_display
			if hasattr(self, "notify_party") and self.notify_party:
				sea_shipment.notify_party = self.notify_party
			if hasattr(self, "notify_party_address") and self.notify_party_address:
				sea_shipment.notify_party_address = self.notify_party_address
			# Copy Cut-offs from Sea Booking to Sea Shipment
			for field in (
				"cargo_cut_off", "document_cut_off", "vgm_cut_off",
				"gate_in_cut_off", "empty_return_cut_off", "other_cut_off",
			):
				if hasattr(self, field) and getattr(self, field, None):
					setattr(sea_shipment, field, getattr(self, field))
			# Copy CTOs from Sea Booking to Sea Shipment
			if hasattr(self, "origin_cto") and self.origin_cto:
				sea_shipment.origin_cto = self.origin_cto
			if hasattr(self, "destination_cto") and self.destination_cto:
				sea_shipment.destination_cto = self.destination_cto
			# Copy Reference Numbers (child table) from Sea Booking to Sea Shipment
			if hasattr(self, "reference_numbers") and self.reference_numbers:
				for ref in self.reference_numbers:
					sea_shipment.append("reference_numbers", {
						"country_region_of_issue": getattr(ref, "country_region_of_issue", None),
						"reference_type": getattr(ref, "reference_type", None),
						"reference_number": getattr(ref, "reference_number", None),
					})
			# Populate addresses and contacts from Shipper/Consignee primary if not set on Booking
			if self.shipper and (not sea_shipment.shipper_address or not sea_shipment.shipper_contact):
				try:
					shipper_doc = frappe.get_doc("Shipper", self.shipper)
					# Populate shipper address if not already set from Booking
					if not sea_shipment.shipper_address and hasattr(shipper_doc, 'shipper_primary_address') and shipper_doc.shipper_primary_address:
						sea_shipment.shipper_address = shipper_doc.shipper_primary_address
						# Populate display field
						sea_shipment.shipper_address_display = get_address_display(shipper_doc.shipper_primary_address)
					# Populate shipper contact if not already set from Booking
					if not sea_shipment.shipper_contact and hasattr(shipper_doc, 'shipper_primary_contact') and shipper_doc.shipper_primary_contact:
						sea_shipment.shipper_contact = shipper_doc.shipper_primary_contact
						# Populate contact display field
						try:
							contact_doc = frappe.get_doc("Contact", shipper_doc.shipper_primary_contact)
							contact_parts = []
							if contact_doc.first_name or contact_doc.last_name:
								contact_parts.append(" ".join(filter(None, [contact_doc.first_name, contact_doc.last_name])))
							if contact_doc.designation:
								contact_parts.append(contact_doc.designation)
							if contact_doc.phone:
								contact_parts.append(contact_doc.phone)
							if contact_doc.mobile_no:
								contact_parts.append(contact_doc.mobile_no)
							if contact_doc.email_id:
								contact_parts.append(contact_doc.email_id)
							sea_shipment.shipper_contact_display = "\n".join(contact_parts)
						except Exception:
							pass
				except Exception as e:
					frappe.log_error(f"Error fetching shipper address/contact: {str(e)}", "Sea Booking - Convert to Shipment")
			
			if self.consignee and (not sea_shipment.consignee_address or not sea_shipment.consignee_contact):
				try:
					consignee_doc = frappe.get_doc("Consignee", self.consignee)
					# Populate consignee address if not already set from Booking
					if not sea_shipment.consignee_address and hasattr(consignee_doc, 'consignee_primary_address') and consignee_doc.consignee_primary_address:
						sea_shipment.consignee_address = consignee_doc.consignee_primary_address
						# Populate display field
						sea_shipment.consignee_address_display = get_address_display(consignee_doc.consignee_primary_address)
					# Populate consignee contact if not already set from Booking
					if not sea_shipment.consignee_contact and hasattr(consignee_doc, 'consignee_primary_contact') and consignee_doc.consignee_primary_contact:
						sea_shipment.consignee_contact = consignee_doc.consignee_primary_contact
						# Populate contact display field
						try:
							contact_doc = frappe.get_doc("Contact", consignee_doc.consignee_primary_contact)
							contact_parts = []
							if contact_doc.first_name or contact_doc.last_name:
								contact_parts.append(" ".join(filter(None, [contact_doc.first_name, contact_doc.last_name])))
							if contact_doc.designation:
								contact_parts.append(contact_doc.designation)
							if contact_doc.phone:
								contact_parts.append(contact_doc.phone)
							if contact_doc.mobile_no:
								contact_parts.append(contact_doc.mobile_no)
							if contact_doc.email_id:
								contact_parts.append(contact_doc.email_id)
							sea_shipment.consignee_contact_display = "\n".join(contact_parts)
						except Exception:
							pass
				except Exception as e:
					frappe.log_error(f"Error fetching consignee address/contact: {str(e)}", "Sea Booking - Convert to Shipment")
			
			# Copy containers if they exist (from Sea Booking Containers to Sea Freight Containers)
			if hasattr(self, 'containers') and self.containers:
				for container in self.containers:
					sea_shipment.append("containers", {
						"container_no": container.container_no,
						"seal_no": container.seal_no,
						"type": container.type,
						"mode": container.mode,
						"delivery_modes": container.delivery_modes,
						"sealed_by": container.sealed_by,
						"other_references": container.other_references
					})
			
			# Copy packages if they exist (from Sea Booking Packages to Sea Freight Packages)
			if hasattr(self, 'packages') and self.packages:
				for package in self.packages:
					sea_shipment.append("packages", {
						"commodity": package.commodity,
						"hs_code": package.hs_code,
						"reference_no": package.reference_no,
						"container": package.container,
						"goods_description": package.goods_description,
						"no_of_packs": package.no_of_packs,
						"uom": package.uom,
						"weight": package.weight,
						"volume": package.volume,
						"dimension_uom": getattr(package, "dimension_uom", None),
						"length": getattr(package, "length", None),
						"width": getattr(package, "width", None),
						"height": getattr(package, "height", None),
						"volume_uom": getattr(package, "volume_uom", None),
						"weight_uom": getattr(package, "weight_uom", None),
					})
			
			# Copy charges (from Sea Booking Charges to Sea Shipment Charges)
			# Store mapping of old charge names to charge indices for copying weight/qty breaks
			charge_name_mapping = {}
			if hasattr(self, 'charges') and self.charges:
				for idx, charge in enumerate(self.charges):
					old_charge_name = charge.name
					new_charge_row = sea_shipment.append("charges", {})
					
					# Copy basic charge fields
					if hasattr(charge, 'charge_item'):
						new_charge_row.charge_item = charge.charge_item
					if hasattr(charge, 'charge_name'):
						new_charge_row.charge_name = charge.charge_name
					if hasattr(charge, 'charge_type'):
						new_charge_row.charge_type = charge.charge_type
					if hasattr(charge, 'charge_category'):
						new_charge_row.charge_category = charge.charge_category
					if hasattr(charge, 'item_tax_template'):
						new_charge_row.item_tax_template = charge.item_tax_template
					if hasattr(charge, 'invoice_type'):
						new_charge_row.invoice_type = charge.invoice_type
					if hasattr(charge, 'charge_description'):
						new_charge_row.charge_description = charge.charge_description
					if hasattr(charge, 'sales_quote_link'):
						new_charge_row.sales_quote_link = charge.sales_quote_link
					
					# Copy revenue fields
					if hasattr(charge, 'bill_to'):
						new_charge_row.bill_to = charge.bill_to
					if hasattr(charge, 'selling_currency'):
						new_charge_row.selling_currency = charge.selling_currency
					if hasattr(charge, 'selling_amount'):
						new_charge_row.selling_amount = charge.selling_amount
					if hasattr(charge, 'estimated_revenue'):
						new_charge_row.estimated_revenue = charge.estimated_revenue
					if hasattr(charge, 'use_tariff_in_revenue'):
						new_charge_row.use_tariff_in_revenue = charge.use_tariff_in_revenue
					if hasattr(charge, 'revenue_tariff'):
						new_charge_row.revenue_tariff = charge.revenue_tariff
					
					# Copy cost fields
					if hasattr(charge, 'pay_to'):
						new_charge_row.pay_to = charge.pay_to
					if hasattr(charge, 'buying_currency'):
						new_charge_row.buying_currency = charge.buying_currency
					if hasattr(charge, 'buying_amount'):
						new_charge_row.buying_amount = charge.buying_amount
					if hasattr(charge, 'estimated_cost'):
						new_charge_row.estimated_cost = charge.estimated_cost
					if hasattr(charge, 'use_tariff_in_cost'):
						new_charge_row.use_tariff_in_cost = charge.use_tariff_in_cost
					if hasattr(charge, 'cost_tariff'):
						new_charge_row.cost_tariff = charge.cost_tariff
					
					# Copy revenue calculation fields
					if hasattr(charge, 'revenue_calculation_method'):
						new_charge_row.revenue_calculation_method = charge.revenue_calculation_method
					if hasattr(charge, 'quantity'):
						new_charge_row.quantity = charge.quantity
					if hasattr(charge, 'uom'):
						new_charge_row.uom = charge.uom
					if hasattr(charge, 'currency'):
						new_charge_row.currency = charge.currency
					if hasattr(charge, 'rate'):
						new_charge_row.rate = charge.rate
					if hasattr(charge, 'unit_type'):
						new_charge_row.unit_type = charge.unit_type
					if hasattr(charge, 'minimum_quantity'):
						new_charge_row.minimum_quantity = charge.minimum_quantity
					if hasattr(charge, 'minimum_unit_rate'):
						new_charge_row.minimum_unit_rate = charge.minimum_unit_rate
					if hasattr(charge, 'minimum_charge'):
						new_charge_row.minimum_charge = charge.minimum_charge
					if hasattr(charge, 'maximum_charge'):
						new_charge_row.maximum_charge = charge.maximum_charge
					if hasattr(charge, 'base_amount'):
						new_charge_row.base_amount = charge.base_amount
					if hasattr(charge, 'base_quantity'):
						new_charge_row.base_quantity = charge.base_quantity
					
					# Copy cost calculation fields
					if hasattr(charge, 'cost_calculation_method'):
						new_charge_row.cost_calculation_method = charge.cost_calculation_method
					if hasattr(charge, 'cost_quantity'):
						new_charge_row.cost_quantity = charge.cost_quantity
					if hasattr(charge, 'cost_uom'):
						new_charge_row.cost_uom = charge.cost_uom
					if hasattr(charge, 'cost_currency'):
						new_charge_row.cost_currency = charge.cost_currency
					if hasattr(charge, 'unit_cost'):
						new_charge_row.unit_cost = charge.unit_cost
					if hasattr(charge, 'cost_unit_type'):
						new_charge_row.cost_unit_type = charge.cost_unit_type
					if hasattr(charge, 'cost_minimum_quantity'):
						new_charge_row.cost_minimum_quantity = charge.cost_minimum_quantity
					if hasattr(charge, 'cost_minimum_unit_rate'):
						new_charge_row.cost_minimum_unit_rate = charge.cost_minimum_unit_rate
					if hasattr(charge, 'cost_minimum_charge'):
						new_charge_row.cost_minimum_charge = charge.cost_minimum_charge
					if hasattr(charge, 'cost_maximum_charge'):
						new_charge_row.cost_maximum_charge = charge.cost_maximum_charge
					if hasattr(charge, 'cost_base_amount'):
						new_charge_row.cost_base_amount = charge.cost_base_amount
					if hasattr(charge, 'cost_base_quantity'):
						new_charge_row.cost_base_quantity = charge.cost_base_quantity
					
					# Copy calculation notes
					if hasattr(charge, 'revenue_calc_notes'):
						new_charge_row.revenue_calc_notes = charge.revenue_calc_notes
					if hasattr(charge, 'cost_calc_notes'):
						new_charge_row.cost_calc_notes = charge.cost_calc_notes
					
					# Copy other service fields
					if hasattr(charge, 'is_other_service'):
						new_charge_row.is_other_service = charge.is_other_service
					if hasattr(charge, 'other_service_reference'):
						new_charge_row.other_service_reference = charge.other_service_reference
					if hasattr(charge, 'other_service_type'):
						new_charge_row.other_service_type = charge.other_service_type
					if hasattr(charge, 'date_started'):
						new_charge_row.date_started = charge.date_started
					if hasattr(charge, 'date_ended'):
						new_charge_row.date_ended = charge.date_ended
					if hasattr(charge, 'other_service_reference_no'):
						new_charge_row.other_service_reference_no = charge.other_service_reference_no
					if hasattr(charge, 'other_service_notes'):
						new_charge_row.other_service_notes = charge.other_service_notes
					
					# Store mapping for copying weight/qty breaks after insert
					# Use idx+1 because Frappe uses 1-based indexing for child table rows
					if old_charge_name and old_charge_name != "new":
						charge_name_mapping[old_charge_name] = idx + 1
			
			# Copy routing legs (from Sea Booking Routing Leg to Sea Shipment Routing Leg)
			# Note: Order is determined by idx (automatically set by Frappe), not leg_order
			if hasattr(self, 'routing_legs') and self.routing_legs:
				for leg in self.routing_legs:
					sea_shipment.append("routing_legs", {
						"mode": leg.mode,
						"type": leg.type,
						"status": leg.status,
						"charter_route": leg.charter_route,
						"notes": leg.notes,
						"vessel": leg.vessel,
						"voyage_no": leg.voyage_no,
						"shipping_line": getattr(leg, 'shipping_line', None),
						"flight_no": leg.flight_no,
						"airline": getattr(leg, 'airline', None),
						"load_port": leg.load_port,
						"etd": leg.etd,
						"atd": leg.atd,
						"discharge_port": leg.discharge_port,
						"eta": leg.eta,
						"ata": leg.ata
					})
			
			# Copy milestone_template if it exists
			if hasattr(self, 'milestone_template') and self.milestone_template:
				sea_shipment.milestone_template = self.milestone_template
			
			# Copy milestones if they exist (from Sea Booking Milestone to Sea Shipment Milestone)
			if hasattr(self, 'milestones') and self.milestones:
				for milestone in self.milestones:
					sea_shipment.append("milestones", {
						"milestone": milestone.milestone,
						"status": milestone.status,
						"planned_start": milestone.planned_start,
						"planned_end": milestone.planned_end,
						"actual_start": milestone.actual_start,
						"actual_end": milestone.actual_end,
						"source": milestone.source,
						"fetched_at": milestone.fetched_at
					})
			
			# Copy document_list_template and documents (Job Document child table) from Sea Booking to Sea Shipment
			if hasattr(self, 'document_list_template') and self.document_list_template:
				sea_shipment.document_list_template = self.document_list_template
			if hasattr(self, 'documents') and self.documents:
				for doc_row in self.documents:
					sea_shipment.append("documents", {
						"document_type": getattr(doc_row, "document_type", None),
						"document_name": getattr(doc_row, "document_name", None),
						"document_number": getattr(doc_row, "document_number", None),
						"status": getattr(doc_row, "status", None),
						"date_required": getattr(doc_row, "date_required", None),
						"date_received": getattr(doc_row, "date_received", None),
						"date_verified": getattr(doc_row, "date_verified", None),
						"expiry_date": getattr(doc_row, "expiry_date", None),
						"attachment": getattr(doc_row, "attachment", None),
						"is_required": getattr(doc_row, "is_required", 0),
						"is_verified": getattr(doc_row, "is_verified", 0),
						"verified_by": getattr(doc_row, "verified_by", None),
						"issued_by": getattr(doc_row, "issued_by", None),
						"overdue_days": getattr(doc_row, "overdue_days", None),
						"notes": getattr(doc_row, "notes", None),
					})
			
			# Final validation check before insert - ensure all link fields are valid
			# This prevents errors during insert/after_insert hooks
			if hasattr(sea_shipment, 'service_level') and sea_shipment.service_level:
				if not frappe.db.exists("Service Level Agreement", sea_shipment.service_level):
					sea_shipment.service_level = None
			if hasattr(sea_shipment, 'release_type') and sea_shipment.release_type:
				if not frappe.db.exists("Release Type", sea_shipment.release_type):
					sea_shipment.release_type = None
			
			# Insert the Sea Shipment
			try:
				sea_shipment.insert(ignore_permissions=True)
			except (frappe.ValidationError, frappe.LinkValidationError) as e:
				# If validation fails due to invalid link fields, clear them and try again
				if "Could not find" in str(e) or "Invalid link" in str(e) or isinstance(e, frappe.LinkValidationError):
					# Clear potentially invalid link fields
					if hasattr(sea_shipment, 'service_level') and sea_shipment.service_level:
						if not frappe.db.exists("Service Level Agreement", sea_shipment.service_level):
							sea_shipment.service_level = None
					if hasattr(sea_shipment, 'release_type') and sea_shipment.release_type:
						if not frappe.db.exists("Release Type", sea_shipment.release_type):
							sea_shipment.release_type = None
					# Try insert again
					sea_shipment.insert(ignore_permissions=True)
				else:
					raise
			
			# Reload the document to sync the timestamp after insert
			# This prevents timestamp mismatch errors when saving again
			sea_shipment.reload()
			
			# Save the Sea Shipment (after_insert may have already saved it, but we save again to be sure)
			try:
				sea_shipment.save(ignore_permissions=True)
			except (frappe.ValidationError, frappe.LinkValidationError) as e:
				# If validation fails due to invalid link fields, clear them and try again
				if "Could not find" in str(e) or "Invalid link" in str(e) or isinstance(e, frappe.LinkValidationError):
					# Clear potentially invalid link fields
					if hasattr(sea_shipment, 'service_level') and sea_shipment.service_level:
						if not frappe.db.exists("Service Level Agreement", sea_shipment.service_level):
							sea_shipment.service_level = None
					if hasattr(sea_shipment, 'release_type') and sea_shipment.release_type:
						if not frappe.db.exists("Release Type", sea_shipment.release_type):
							sea_shipment.release_type = None
					# Try save again
					sea_shipment.save(ignore_permissions=True)
				else:
					raise
			
			# Copy weight breaks and quantity breaks from Sea Booking Charges to Sea Shipment Charges
			# This must be done after the shipment is saved so charge names are available
			if charge_name_mapping:
				sea_shipment.reload()  # Reload to get saved charge names
				for old_charge_name, charge_idx in charge_name_mapping.items():
					if not old_charge_name or old_charge_name == "new":
						continue
					
					# Get the new charge name after save by matching idx
					new_charge_name = None
					if sea_shipment.charges:
						for ch in sea_shipment.charges:
							if hasattr(ch, 'idx') and ch.idx == charge_idx:
								new_charge_name = ch.name
								break
					
					if not new_charge_name:
						continue
					
					# Copy weight breaks (Selling)
					old_weight_breaks = frappe.get_all(
						"Sales Quote Weight Break",
						filters={
							"reference_doctype": "Sea Booking Charges",
							"reference_no": old_charge_name,
							"type": "Selling"
						},
						fields=["rate_type", "weight_break", "unit_rate", "currency"]
					)
					for wb in old_weight_breaks:
						new_wb = frappe.new_doc("Sales Quote Weight Break")
						new_wb.reference_doctype = "Sea Shipment Charges"
						new_wb.reference_no = new_charge_name
						new_wb.type = "Selling"
						new_wb.rate_type = wb.get("rate_type") or "N (Normal)"
						new_wb.weight_break = wb.get("weight_break", 0)
						new_wb.unit_rate = wb.get("unit_rate", 0)
						new_wb.currency = wb.get("currency") or "USD"
						new_wb.insert(ignore_permissions=True)
					
					# Copy weight breaks (Cost)
					old_cost_weight_breaks = frappe.get_all(
						"Sales Quote Weight Break",
						filters={
							"reference_doctype": "Sea Booking Charges",
							"reference_no": old_charge_name,
							"type": "Cost"
						},
						fields=["rate_type", "weight_break", "unit_rate", "currency"]
					)
					for wb in old_cost_weight_breaks:
						new_wb = frappe.new_doc("Sales Quote Weight Break")
						new_wb.reference_doctype = "Sea Shipment Charges"
						new_wb.reference_no = new_charge_name
						new_wb.type = "Cost"
						new_wb.rate_type = wb.get("rate_type") or "N (Normal)"
						new_wb.weight_break = wb.get("weight_break", 0)
						new_wb.unit_rate = wb.get("unit_rate", 0)
						new_wb.currency = wb.get("currency") or "USD"
						new_wb.insert(ignore_permissions=True)
					
					# Copy quantity breaks (Selling)
					old_qty_breaks = frappe.get_all(
						"Sales Quote Qty Break",
						filters={
							"reference_doctype": "Sea Booking Charges",
							"reference_no": old_charge_name,
							"type": "Selling"
						},
						fields=["qty_break", "unit_rate", "currency"]
					)
					for qb in old_qty_breaks:
						new_qb = frappe.new_doc("Sales Quote Qty Break")
						new_qb.reference_doctype = "Sea Shipment Charges"
						new_qb.reference_no = new_charge_name
						new_qb.type = "Selling"
						new_qb.qty_break = qb.get("qty_break", 0)
						new_qb.unit_rate = qb.get("unit_rate", 0)
						new_qb.currency = qb.get("currency") or "USD"
						new_qb.insert(ignore_permissions=True)
					
					# Copy quantity breaks (Cost)
					old_cost_qty_breaks = frappe.get_all(
						"Sales Quote Qty Break",
						filters={
							"reference_doctype": "Sea Booking Charges",
							"reference_no": old_charge_name,
							"type": "Cost"
						},
						fields=["qty_break", "unit_rate", "currency"]
					)
					for qb in old_cost_qty_breaks:
						new_qb = frappe.new_doc("Sales Quote Qty Break")
						new_qb.reference_doctype = "Sea Shipment Charges"
						new_qb.reference_no = new_charge_name
						new_qb.type = "Cost"
						new_qb.qty_break = qb.get("qty_break", 0)
						new_qb.unit_rate = qb.get("unit_rate", 0)
						new_qb.currency = qb.get("currency") or "USD"
						new_qb.insert(ignore_permissions=True)
			
			# Ensure commit before client navigates to the new doc (avoids "not found" on form load)
			frappe.db.commit()
			
			frappe.msgprint(
				_("Sea Shipment {0} created successfully from Sea Booking {1}").format(sea_shipment.name, self.name),
				title=_("Sea Shipment Created"),
				indicator="green"
			)
			
			return {
				"success": True,
				"message": _("Sea Shipment {0} created successfully").format(sea_shipment.name),
				"sea_shipment": sea_shipment.name
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error converting Sea Booking {self.name} to Sea Shipment: {str(e)}",
				"Sea Booking - Convert to Shipment Error"
			)
			frappe.throw(_("Error converting to shipment: {0}").format(str(e)))


@frappe.whitelist()
def recalculate_all_charges(docname):
	"""Recalculate all charges based on current Sea Booking data."""
	booking = frappe.get_doc("Sea Booking", docname)
	if not booking.charges:
		return {"success": False, "message": _("No charges found to recalculate")}
	try:
		charges_recalculated = 0
		for charge in booking.charges:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=booking)
				charges_recalculated += 1
		booking.save()
		return {
			"success": True,
			"message": _("Successfully recalculated {0} charges").format(charges_recalculated),
			"charges_recalculated": charges_recalculated,
		}
	except Exception as e:
		frappe.log_error(str(e), "Sea Booking - Recalculate Charges Error")
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


@frappe.whitelist()
def get_available_one_off_quotes(sea_booking_name: str = None) -> Dict[str, Any]:
	"""Get list of One-Off Quotes that are not yet linked to a Sea Booking and not converted.
	
	Excludes One-Off Quotes that are:
	1. Already linked to another Sea Booking
	2. Already converted (status = "Converted" or converted_to_doc is set)
	
	This prevents users from selecting quotes that have already been converted or used.
	"""
	try:
		# Get all One-Off Quotes already linked to Sea Bookings (excluding current booking)
		used_quotes = frappe.get_all(
			"Sea Booking",
			filters={
				"quote_type": "One-Off Quote",
				"quote": ["is", "set"],
				"name": ["!=", sea_booking_name or ""]
			},
			pluck="quote"
		)
		
		# Get all converted One-Off Quotes (status = "Converted" or converted_to_doc is set)
		converted_quotes = frappe.get_all(
			"One-Off Quote",
			filters={
				"status": "Converted"
			},
			pluck="name"
		)
		
		# Also get quotes with converted_to_doc set (in case status wasn't updated)
		quotes_with_conversion = frappe.get_all(
			"One-Off Quote",
			filters={
				"converted_to_doc": ["is", "set"]
			},
			pluck="name"
		)
		
		# Combine all excluded quotes
		excluded_quotes = list(set(used_quotes + converted_quotes + quotes_with_conversion))
		
		# Return filter to exclude used and converted quotes
		filters = {}
		if excluded_quotes:
			filters["name"] = ["not in", excluded_quotes]
		
		# Also filter to only show Sales Quotes that have sea enabled
		def _has_field(doctype: str, fieldname: str) -> bool:
			try:
				return frappe.get_meta(doctype).has_field(fieldname)
			except Exception:
				return False

		if _has_field("Sales Quote", "main_service"):
			filters["main_service"] = "Sea"
		
		return {"filters": filters}
	except Exception as e:
		frappe.log_error(
			f"Error getting available One-Off Quotes: {str(e)}",
			"Sea Booking Quote Query Error"
		)
		return {"filters": {}}


@frappe.whitelist()
def populate_charges_from_sales_quote(docname: str = None, sales_quote: str = None):
	"""Populate charges from sales_quote. Called from frontend when sales_quote field changes.
	
	Returns charge data that can be populated in the frontend.
	"""
	if not sales_quote:
		return {"charges": []}
	
	try:
		# Verify that the sales_quote exists
		if not frappe.db.exists("Sales Quote", sales_quote):
			return {
				"error": f"Sales Quote {sales_quote} does not exist",
				"charges": []
			}
		
		# Get the document if it exists (for getting weight/volume/containers/packages)
		doc = None
		if docname:
			try:
				doc = frappe.get_doc("Sea Booking", docname)
			except Exception:
				pass
		
		# Fetch sales_quote_sea_freight records from the selected sales_quote
		sales_quote_sea_freight_records = frappe.get_all(
			"Sales Quote Sea Freight",
			filters={"parent": sales_quote, "parenttype": "Sales Quote"},
			fields=[
				"name",
				"item_code",
				"item_name",
				"calculation_method",
				"uom",
				"currency",
				"unit_rate",
				"unit_type",
				"minimum_quantity",
				"minimum_charge",
				"maximum_charge",
				"base_amount",
				"estimated_revenue",
				"charge_type"
			],
			order_by="idx"
		)
		
		if not sales_quote_sea_freight_records:
			return {
				"charges": [],
				"message": f"No sea freight charges found in Sales Quote: {sales_quote}"
			}
		
		# Map and populate charges
		charges = []
		for sqsf_record in sales_quote_sea_freight_records:
			# Create a temporary document instance for mapping
			temp_doc = doc if doc else frappe.new_doc("Sea Booking")
			if doc:
				# Copy relevant fields from the document
				temp_doc.total_weight = doc.total_weight
				temp_doc.total_volume = doc.total_volume
				temp_doc.local_customer = doc.local_customer
				if hasattr(doc, 'packages'):
					temp_doc.packages = doc.packages
				if hasattr(doc, 'containers'):
					temp_doc.containers = doc.containers
			
			charge_row = temp_doc._map_sales_quote_sea_freight_to_charge(sqsf_record)
			if charge_row:
				charges.append(charge_row)
		
		# Note: We do NOT save the document here to avoid "document has been modified" errors.
		# The client-side JavaScript will handle updating the form with the charges data.
		
		return {
			"charges": charges,
			"charges_count": len(charges)
		}
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from sales quote {sales_quote}: {str(e)}",
			"Sea Booking Charges Population Error"
		)
		return {
			"error": f"Error populating charges: {str(e)}",
			"charges": []
		}


@frappe.whitelist()
def populate_charges_from_one_off_quote(docname: str = None, one_off_quote: str = None):
	"""Populate charges from one_off_quote. Called from frontend when one_off_quote field changes.
	
	Returns charge data that can be populated in the frontend.
	"""
	if not one_off_quote:
		return {"charges": []}
	
	try:
		# Verify that the one_off_quote exists
		if not frappe.db.exists("One-Off Quote", one_off_quote):
			return {
				"error": f"One-Off Quote {one_off_quote} does not exist",
				"charges": []
			}
		
		# Get the document if it exists (for getting weight/volume/containers/packages)
		doc = None
		if docname:
			try:
				doc = frappe.get_doc("Sea Booking", docname)
			except Exception:
				pass
		
		# Fetch one_off_quote_sea_freight records from the selected one_off_quote
		one_off_quote_sea_freight_records = frappe.get_all(
			"One-Off Quote Sea Freight",
			filters={"parent": one_off_quote, "parenttype": "One-Off Quote"},
			fields=[
				"name",
				"item_code",
				"item_name",
				"calculation_method",
				"uom",
				"currency",
				"unit_rate",
				"unit_type",
				"minimum_quantity",
				"minimum_charge",
				"maximum_charge",
				"base_amount",
				"estimated_revenue"
			],
			order_by="idx"
		)
		
		if not one_off_quote_sea_freight_records:
			return {
				"charges": [],
				"message": f"No sea freight charges found in One-Off Quote: {one_off_quote}"
			}
		
		# Map and populate charges (One-Off Quote Sea Freight has same structure as Sales Quote Sea Freight)
		charges = []
		for oqsf_record in one_off_quote_sea_freight_records:
			# Create a temporary document instance for mapping
			temp_doc = doc if doc else frappe.new_doc("Sea Booking")
			if doc:
				# Copy relevant fields from the document
				temp_doc.total_weight = doc.total_weight
				temp_doc.total_volume = doc.total_volume
				temp_doc.local_customer = doc.local_customer
				if hasattr(doc, 'packages'):
					temp_doc.packages = doc.packages
				if hasattr(doc, 'containers'):
					temp_doc.containers = doc.containers
			
			charge_row = temp_doc._map_sales_quote_sea_freight_to_charge(oqsf_record)
			if charge_row:
				charges.append(charge_row)
		
		# Note: We do NOT save the document here to avoid "document has been modified" errors.
		# The client-side JavaScript will handle updating the form with the charges data.
		
		return {
			"charges": charges,
			"charges_count": len(charges)
		}
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from one-off quote {one_off_quote}: {str(e)}",
			"Sea Booking Charges Population Error"
		)
		return {
			"error": f"Error populating charges: {str(e)}",
			"charges": []
		}