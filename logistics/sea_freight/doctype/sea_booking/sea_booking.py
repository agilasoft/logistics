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
	def validate(self):
		"""Validate Sea Booking data"""
		# Normalize legacy house_type values
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
				self.volume = total
		except Exception:
			pass
	
	def aggregate_weight_from_packages(self):
		"""Set header weight from sum of package weights, converted to base/default weight UOM."""
		if getattr(self, "override_volume_weight", False):
			return
		packages = getattr(self, "packages", []) or []
		if not packages:
			if hasattr(self, "weight"):
				self.weight = 0
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
				self.weight = total
			else:
				self.weight = 0
		except Exception:
			pass
	
	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on volume and weight using Sea Freight Settings divisor."""
		if not self.volume and not self.weight:
			if hasattr(self, "chargeable"):
				self.chargeable = 0
			return
		
		# Get volume to weight divisor from Sea Freight Settings
		divisor = self.get_volume_to_weight_divisor()
		
		# Calculate volume weight
		volume_weight = 0
		if self.volume and divisor:
			# Convert volume from m³ to cm³, then divide by divisor
			# Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
			volume_weight = flt(self.volume) * (1000000.0 / divisor)
		
		# Calculate chargeable weight (higher of actual weight or volume weight)
		if self.weight and volume_weight:
			self.chargeable = max(flt(self.weight), volume_weight)
		elif self.weight:
			self.chargeable = flt(self.weight)
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
	
	@frappe.whitelist()
	def aggregate_volume_from_packages_api(self):
		"""Whitelisted API method to aggregate volume and weight from packages for client-side calls."""
		if not getattr(self, "override_volume_weight", False):
			self.aggregate_volume_from_packages()
			self.aggregate_weight_from_packages()
		self.calculate_chargeable_weight()
		return {
			"volume": getattr(self, "volume", 0),
			"weight": getattr(self, "weight", 0),
			"chargeable": getattr(self, "chargeable", 0)
		}
	
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
			
			# Get Sales Quote document
			sales_quote = frappe.get_doc("Sales Quote", self.sales_quote)
			
			# Check if Sales Quote has sea freight details
			# Note: Sales Quote Sea Freight child table may not exist yet
			# If it doesn't exist, we'll still populate basic fields
			sea_freight_exists = frappe.db.exists("Sales Quote Sea Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			})
			
			if not sea_freight_exists:
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
			if not self.origin_port:
				self.origin_port = getattr(sales_quote, 'location_from', None)
			if not self.destination_port:
				self.destination_port = getattr(sales_quote, 'location_to', None)
			if not self.direction:
				self.direction = getattr(sales_quote, 'direction', None)
			if not self.weight:
				self.weight = getattr(sales_quote, 'weight', None)
			if not self.volume:
				self.volume = getattr(sales_quote, 'volume', None)
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
			
			# Populate charges from Sales Quote Sea Freight (if child table exists)
			sea_freight_exists = frappe.db.exists("Sales Quote Sea Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			})
			if sea_freight_exists:
				self._populate_charges_from_sales_quote(sales_quote)
			
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

			# Fetch sales_quote_sea_freight records from the selected sales_quote
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Sea Freight",
				filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
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
			
			# Get Sales Quote Sea Freight records
			# Note: Adjust the child table name if it's different
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Sea Freight",
				filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
				fields=[
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
			
			# If Sales Quote Sea Freight doesn't exist, return early
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
			
			# Map unit_type to unit (for Sea Booking Charges)
			unit_type_to_unit = {
				"Weight": "Weight",
				"Volume": "Volume",
				"Package": "House Bill",
				"Piece": "House Bill",
				"Shipment": "House Bill",
				"Container": "Container Count"
			}
			unit = unit_type_to_unit.get(sqsf_record.unit_type, "House Bill")
			
			# Get quantity based on unit type
			quantity = 0
			if sqsf_record.unit_type == "Weight":
				quantity = flt(self.weight) or 0
			elif sqsf_record.unit_type == "Volume":
				quantity = flt(self.volume) or 0
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
			
			# Determine charge_type from item or use default
			charge_type = "Revenue"
			if hasattr(item_doc, 'custom_charge_type'):
				charge_type = item_doc.custom_charge_type or "Revenue"
			
			# Map revenue_calc_type from calculation_method
			calc_method_to_revenue_calc_type = {
				"Per Unit": "Base plus per Unit",
				"Fixed Amount": "Fixed",
				"Base Plus Additional": "Base plus per Unit",
				"First Plus Additional": "Base plus per Unit"
			}
			revenue_calc_type = calc_method_to_revenue_calc_type.get(sqsf_record.calculation_method, "Fixed")
			
			# Map the fields to Sea Booking Charges structure
			charge_data = {
				"charge_item": sqsf_record.item_code,
				"charge_name": sqsf_record.item_name or item_doc.item_name,
				"charge_type": charge_type,
				"charge_description": sqsf_record.item_name or item_doc.item_name,
				"bill_to": self.local_customer if hasattr(self, 'local_customer') else None,
				"selling_currency": sqsf_record.currency or default_currency,
				"selling_amount": selling_amount,
				"per_unit_rate": sqsf_record.unit_rate or 0,
				"unit": unit,
				"revenue_calc_type": revenue_calc_type,
				"base_amount": sqsf_record.base_amount or 0
			}
			
			# Add minimum charge if available
			if sqsf_record.minimum_charge:
				charge_data["minimum"] = sqsf_record.minimum_charge
			
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
			sea_shipment.shipper = self.shipper
			sea_shipment.consignee = self.consignee
			sea_shipment.origin_port = self.origin_port
			sea_shipment.destination_port = self.destination_port
			sea_shipment.direction = self.direction
			sea_shipment.weight = self.weight
			sea_shipment.volume = self.volume
			sea_shipment.chargeable = self.chargeable
			# Only copy service_level if it exists as a valid record
			if self.service_level and frappe.db.exists("Service Level Agreement", self.service_level):
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
			sea_shipment.good_value = self.good_value
			sea_shipment.insurance = self.insurance
			sea_shipment.description = self.description
			sea_shipment.marks_and_nos = self.marks_and_nos
			sea_shipment.etd = self.etd
			sea_shipment.eta = self.eta
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
			if hasattr(self, "notify_to_party") and self.notify_to_party:
				sea_shipment.notify_to_party = self.notify_to_party
			if hasattr(self, "notify_to_address") and self.notify_to_address:
				sea_shipment.notify_to_address = self.notify_to_address
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
			
			# Copy services if they exist (from Sea Booking Services to Sea Freight Services)
			if hasattr(self, 'services') and self.services:
				for svc in self.services:
					sea_shipment.append("services", {
						"type": svc.type,
						"date_booked": svc.date_booked,
						"date_completed": svc.date_completed,
						"service_provider": svc.service_provider,
						"reference": svc.reference,
						"currency": svc.currency,
						"rate": svc.rate,
						"tax_category": svc.tax_category,
						"notes": getattr(svc, "notes", None),
					})
			
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
						"chargeable_weight": getattr(package, "chargeable_weight", None),
						"chargeable_weight_uom": getattr(package, "chargeable_weight_uom", None),
					})
			
			# Copy charges (from Sea Booking Charges to Sea Freight Charges)
			if hasattr(self, 'charges') and self.charges:
				for charge in self.charges:
					sea_shipment.append("charges", {
						"charge_item": charge.charge_item,
						"charge_name": charge.charge_name,
						"charge_type": charge.charge_type,
						"item_tax_template": charge.item_tax_template,
						"invoice_type": charge.invoice_type,
						"charge_description": charge.charge_description,
						"bill_to": charge.bill_to,
						"selling_currency": charge.selling_currency,
						"selling_amount": charge.selling_amount,
						"pay_to": charge.pay_to,
						"buying_currency": charge.buying_currency,
						"buying_amount": charge.buying_amount,
						"revenue_calc_type": charge.revenue_calc_type,
						"base_amount": charge.base_amount,
						"per_unit_rate": charge.per_unit_rate,
						"unit": charge.unit,
						"minimum": charge.minimum,
						"cost_calc_type": charge.cost_calc_type
					})
			
			# Copy routing legs (from Sea Booking Routing Leg to Sea Shipment Routing Leg)
			if hasattr(self, 'routing_legs') and self.routing_legs:
				for leg in self.routing_legs:
					sea_shipment.append("routing_legs", {
						"leg_order": leg.leg_order,
						"mode": leg.mode,
						"type": leg.type,
						"status": leg.status,
						"charter_route": leg.charter_route,
						"notes": leg.notes,
						"vessel": leg.vessel,
						"voyage_no": leg.voyage_no,
						"flight_no": leg.flight_no,
						"carrier_type": leg.carrier_type,
						"carrier": leg.carrier,
						"load_port": leg.load_port,
						"etd": leg.etd,
						"atd": leg.atd,
						"discharge_port": leg.discharge_port,
						"eta": leg.eta,
						"ata": leg.ata
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
		
		# Also filter to only show One-Off Quotes that have sea enabled
		# Check if One-Off Quote has is_sea field
		def _has_field(doctype: str, fieldname: str) -> bool:
			try:
				return frappe.get_meta(doctype).has_field(fieldname)
			except Exception:
				return False
		
		if _has_field("One-Off Quote", "is_sea"):
			filters["is_sea"] = 1
		
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
				"estimated_revenue"
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
				temp_doc.weight = doc.weight
				temp_doc.volume = doc.volume
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
				temp_doc.weight = doc.weight
				temp_doc.volume = doc.volume
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
