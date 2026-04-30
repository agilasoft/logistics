# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, flt, cint
from frappe.contacts.doctype.address.address import get_address_display
from typing import Dict, Any

from logistics.utils.module_integration import copy_sales_quote_fields_to_target
from logistics.utils.charge_service_type import (
	filter_sales_quote_charge_rows_for_operational_doc,
	operational_booking_charge_service_type_label,
	sales_quote_charge_filters,
	throw_if_missing_destination_service_charge,
)
from logistics.utils.document_date_validation import throw_if_left_date_after_right
from logistics.utils.dg_fields import update_parent_dg_compliance_status
from logistics.utils.internal_job_charge_copy import (
	build_internal_job_sea_booking_charge_dicts,
	populate_internal_job_charges_from_main_service,
	should_apply_internal_job_main_charge_overlay,
)
from logistics.utils.sales_quote_charge_parameters import filter_fields_existing_in_doctype
from logistics.utils.sales_quote_routing import (
	apply_sales_quote_routing_to_booking,
	routing_legs_for_api_response,
)
from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings


def _sync_quote_and_sales_quote(doc):
    """Sync quote_type/quote with sales_quote for backward compatibility."""
    if getattr(doc, "quote_type", None) == "Sales Quote" and getattr(doc, "quote", None):
        doc.sales_quote = doc.quote
    elif getattr(doc, "quote_type", None) == "One-Off Quote":
        q = getattr(doc, "quote", None)
        if q and frappe.db.exists("Sales Quote", q):
            doc.sales_quote = q
        else:
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
		from logistics.utils.charges_calculation import (
			clear_charge_resolution_parent,
			register_charge_resolution_parent,
		)

		register_charge_resolution_parent(self)
		try:
			from logistics.utils.internal_job_main_link import validate_internal_job_main_link_unchanged

			validate_internal_job_main_link_unchanged(self)
			from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

			apply_shipper_consignee_defaults(self)
			if self.is_new():
				from logistics.sea_freight.sea_freight_settings_defaults import (
					apply_accounting_defaults_from_sea_freight_settings,
				)

				apply_accounting_defaults_from_sea_freight_settings(self)
			# Normalize legacy house_type values (backup, in case before_validate didn't run)
			if hasattr(self, 'house_type') and self.house_type:
				if self.house_type == "Direct":
					self.house_type = "Standard House"
				elif self.house_type == "Consolidation":
					self.house_type = "Co-load Master"
			update_parent_dg_compliance_status(self)
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
			# Restore sales_quote if something cleared it while quote still points at the same Sales Quote
			qt = getattr(self, "quote_type", None)
			if original_sales_quote and not getattr(self, "sales_quote", None):
				if qt == "Sales Quote" or (
					qt == "One-Off Quote"
					and getattr(self, "quote", None)
					and original_sales_quote == getattr(self, "quote", None)
				):
					self.sales_quote = original_sales_quote
		
			# Validate One-off Sales Quote not already converted (internal satellite bookings may share the main leg's quote)
			_quote_is_sales_quote = (
				getattr(self, "quote_type", None) == "One-Off Quote"
				and getattr(self, "quote", None)
				and frappe.db.exists("Sales Quote", self.quote)
			)
			if self.sales_quote or _quote_is_sales_quote:
				from frappe.utils import cint

				from logistics.pricing_center.doctype.sales_quote.sales_quote import (
					resolve_allow_linked_freight_bookings_for_internal_job,
					validate_one_off_quote_not_converted,
				)

				allow_sea, allow_air = resolve_allow_linked_freight_bookings_for_internal_job(self)
				_allow_main_with_do = cint(getattr(self, "is_main_service", 0)) == 1
				if self.sales_quote:
					validate_one_off_quote_not_converted(
						self.sales_quote,
						self.doctype,
						self.name,
						allow_linked_sea_booking=allow_sea,
						allow_linked_air_booking=allow_air,
						allow_main_transport_if_converted_to_declaration_order=_allow_main_with_do,
					)
				if _quote_is_sales_quote:
					validate_one_off_quote_not_converted(
						self.quote,
						self.doctype,
						self.name,
						allow_linked_sea_booking=allow_sea,
						allow_linked_air_booking=allow_air,
						allow_main_transport_if_converted_to_declaration_order=_allow_main_with_do,
					)
		
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

			from logistics.utils.get_charges_from_quotation import assert_one_off_sales_quote_job_rules

			assert_one_off_sales_quote_job_rules(self)
		
			self.validate_dates()
			self.validate_accounts()
			self.validate_main_routing_legs_by_entry_type()
			self._prepare_header_totals_for_charge_calculation()
			self._sync_charges_with_parent_actuals()
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

			from logistics.utils.sales_quote_validity import msgprint_sales_quote_validity_warnings

			msgprint_sales_quote_validity_warnings(self)

		finally:
			clear_charge_resolution_parent(self)

	def _prepare_header_totals_for_charge_calculation(self):
		"""Refresh header weight/volume/chargeable from packages (same basis as validate, before charge math)."""
		try:
			from logistics.utils.measurements import apply_measurement_uom_conversion_to_children

			apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
		except Exception:
			pass
		if not getattr(self, "override_volume_weight", False):
			self.aggregate_volume_from_packages()
			self.aggregate_weight_from_packages()
		self.calculate_chargeable_weight()

	def _sync_charges_with_parent_actuals(self):
		"""Recalculate each charge row from header actuals (overwrites Sales Quote copy)."""
		if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
			return
		if getattr(self.flags, "ignore_charges_sync", False):
			return
		for charge in self.get("charges") or []:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=self)

	def _apply_actuals_to_charge_dicts(self, charge_dicts):
		"""Recompute charge row dicts for API responses (populate from Sales Quote without save)."""
		if not charge_dicts:
			return
		self._prepare_header_totals_for_charge_calculation()
		for row_dict in charge_dicts:
			row = frappe.new_doc("Sea Booking Charges")
			row.update(row_dict)
			row.calculate_charge_amount(parent_doc=self)
			row_dict["quantity"] = row.quantity
			row_dict["cost_quantity"] = row.cost_quantity
			row_dict["estimated_revenue"] = row.estimated_revenue
			row_dict["estimated_cost"] = row.estimated_cost
			if hasattr(row, "revenue_calc_notes"):
				row_dict["revenue_calc_notes"] = row.revenue_calc_notes
			if hasattr(row, "cost_calc_notes"):
				row_dict["cost_calc_notes"] = row.cost_calc_notes
			if hasattr(row, "rate"):
				row_dict["rate"] = row.rate

	def validate_main_routing_legs_by_entry_type(self):
		"""Allow additional Main leg for Transit/Transshipment while keeping Direct capped at one."""
		entry_type = (getattr(self, "entry_type", "") or "").strip()
		if not entry_type:
			return

		main_leg_count = sum(
			1
			for leg in (getattr(self, "routing_legs", None) or [])
			if (getattr(leg, "type", "") or "").strip() == "Main"
		)

		if entry_type in {"Transit", "Transshipment"} and main_leg_count > 2:
			frappe.throw(
				_("For {0}, you can define at most two Main routing legs.").format(entry_type),
				title=_("Invalid Routing Legs"),
			)

		if entry_type == "Direct" and main_leg_count > 1:
			frappe.throw(
				_("For Direct entry type, only one Main routing leg is allowed."),
				title=_("Invalid Routing Legs"),
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
		"""Calculate chargeable weight using Sea Freight Settings divisor and chargeable_weight_calculation."""
		if not self.total_volume and not self.total_weight:
			self.chargeable = 0
			return

		divisor = self.get_volume_to_weight_divisor()
		calculation_method = self.get_chargeable_weight_calculation_method()

		volume_weight = 0
		if self.total_volume and divisor:
			volume_weight = flt(self.total_volume) * (1000000.0 / divisor)

		actual_weight = flt(self.total_weight) or 0

		if calculation_method == "Actual Weight":
			self.chargeable = actual_weight
		elif calculation_method == "Volume Weight":
			self.chargeable = volume_weight
		else:
			if actual_weight > 0 and volume_weight > 0:
				self.chargeable = max(actual_weight, volume_weight)
			elif actual_weight > 0:
				self.chargeable = actual_weight
			elif volume_weight > 0:
				self.chargeable = volume_weight
			else:
				self.chargeable = 0

	def get_chargeable_weight_calculation_method(self):
		"""Sea Freight Settings: 'Actual Weight', 'Volume Weight', or 'Higher of Both' (default)."""
		try:
			settings = SeaFreightSettings.get_settings(self.company)
			method = getattr(settings, "chargeable_weight_calculation", None) if settings else None
			if method in ("Actual Weight", "Volume Weight", "Higher of Both"):
				return method
		except Exception:
			pass
		return "Higher of Both"

	def get_volume_to_weight_divisor(self):
		"""Get the volume to weight divisor from Sea Freight Settings.
		Converts volume_to_weight_factor (kg/m³) to divisor format.
		Formula: divisor = 1,000,000 / factor
		Example: factor = 1000 kg/m³ → divisor = 1000
		"""
		try:
			settings = SeaFreightSettings.get_settings(self.company)
			factor = getattr(settings, "volume_to_weight_factor", None) if settings else None
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
		from logistics.sea_freight.container_row_metrics import sync_sea_freight_container_child_rows

		sync_sea_freight_container_child_rows(self)
	
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
		)
		from logistics.container_management.api import (
			expand_sea_container_no_for_sql_in,
			sea_container_row_field_to_equipment_number,
		)

		strict = get_strict_validation_setting()
		for i, c in enumerate(self.containers, 1):
			container_no = getattr(c, "container_no", None)
			if container_no and str(container_no).strip():
				equip = sea_container_row_field_to_equipment_number(container_no)
				valid, err = validate_container_number(equip, strict=strict)
				if not valid:
					frappe.throw(_("Container {0}: {1}").format(i, err), title=_("Invalid Container Number"))
		
		# In-table duplicate: same container number must not appear on multiple rows
		seen = {}
		for i, c in enumerate(self.containers, 1):
			container_no = getattr(c, "container_no", None)
			if not container_no or not str(container_no).strip():
				continue
			equip = sea_container_row_field_to_equipment_number(container_no)
			if equip in seen:
				frappe.throw(
					_("Duplicate container number in this document: {0} appears on row {1} and row {2}.").format(
						equip, seen[equip], i
					),
					title=_("Duplicate Container Numbers"),
				)
			seen[equip] = i
		
		# Get container numbers from current booking (filter out empty values)
		container_numbers = []
		for c in self.containers:
			cn = getattr(c, "container_no", None)
			if cn and str(cn).strip():
				container_numbers.extend(expand_sea_container_no_for_sql_in(cn))
		container_numbers = list(set(container_numbers))
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
		existing_bookings = [
			c
			for c in booking_candidates
			if not self._container_returned(c.container_no, other_booking_name=c.name)
		]

		# Same rules as Sea Shipment.validate_duplicates: any non-cancelled shipment; draft always
		# blocks reuse; submitted blocks unless the container is considered returned.
		shipment_candidates = frappe.db.sql("""
			SELECT DISTINCT ss.name, ss.docstatus, sfc.container_no
			FROM `tabSea Shipment` ss
			INNER JOIN `tabSea Freight Containers` sfc ON sfc.parent = ss.name
			WHERE sfc.container_no IN %(container_numbers)s
			AND ss.docstatus != 2
		""", {
			"container_numbers": container_numbers
		}, as_dict=True)
		existing_shipments = [
			c for c in shipment_candidates
			if c.docstatus == 0 or not self._container_returned(c.container_no, other_shipment_name=c.name)
		]

		# Build error message if duplicates found
		errors = []
		if existing_bookings:
			container_list = ", ".join(
				sorted(
					set(
						sea_container_row_field_to_equipment_number(x.container_no)
						for x in existing_bookings
						if x.container_no
					)
				)
			)
			booking_list = ", ".join(set([c.name for c in existing_bookings]))
			errors.append(_("Container number(s) {0} are already used in Sea Booking(s): {1}").format(
				container_list, booking_list
			))
		
		if existing_shipments:
			container_list = ", ".join(
				sorted(
					set(
						sea_container_row_field_to_equipment_number(x.container_no)
						for x in existing_shipments
						if x.container_no
					)
				)
			)
			shipment_list = ", ".join(set([c.name for c in existing_shipments]))
			errors.append(_("Container number(s) {0} are already used in Sea Shipment(s): {1}").format(
				container_list, shipment_list
			))
		
		if errors:
			frappe.throw(
				"\n".join(errors),
				title=_("Duplicate Container Numbers")
			)

	def _container_returned(
		self, container_no, other_shipment_name=None, other_booking_name=None
	):
		"""
		Return True if the container is considered returned so reuse on another booking is allowed.
		When checking another submitted booking/shipment, we allow reuse if the container has been
		returned (Container return_status/status), the other Sea Booking is terminal (Delivered/Cancelled),
		or the other Sea Shipment is finished (job completed/closed, empty returned, etc.).
		"""
		if not container_no:
			return False
		# Resolve by equipment number to the active Container (avoids stale child-row links to inactive rows)
		try:
			from logistics.container_management.api import (
				container_row_indicates_empty_returned,
				is_container_management_enabled,
			)
			if is_container_management_enabled() and container_row_indicates_empty_returned(container_no):
				return True
		except Exception:
			pass
		if other_booking_name:
			other_sb_status = frappe.db.get_value("Sea Booking", other_booking_name, "shipping_status")
			if other_sb_status in ("Delivered", "Cancelled"):
				return True
			# Booking may still be Confirmed / In Transit while a linked Sea Shipment job is finished.
			from logistics.container_management.api import expand_sea_container_no_for_sql_in

			variants = list(expand_sea_container_no_for_sql_in(container_no))
			if variants and frappe.db.sql(
				"""
				SELECT 1
				FROM `tabSea Shipment` ss
				INNER JOIN `tabSea Freight Containers` sfc ON sfc.parent = ss.name
				WHERE ss.sea_booking = %(bk)s
				AND sfc.container_no IN %(cns)s
				AND ss.docstatus = 1
				AND IFNULL(ss.job_status, '') IN ('Completed', 'Closed', 'Cancelled')
				LIMIT 1
				""",
				{"bk": other_booking_name, "cns": variants},
			):
				return True
		if other_shipment_name:
			row = frappe.db.get_value(
				"Sea Shipment",
				other_shipment_name,
				["shipping_status", "job_status"],
				as_dict=True,
			)
			if not row:
				return False
			if (row.get("job_status") or "") in ("Completed", "Closed", "Cancelled"):
				return True
			if row.get("shipping_status") in ("Empty Container Returned", "Closed"):
				return True
		return False
	
	def validate_ready_for_sea_shipment_on_submit(self):
		"""Enforce the same accounting and detail rules as Sea Shipment conversion at submit time."""
		readiness = self.check_conversion_readiness()
		if not readiness["is_ready"]:
			messages = [field["message"] for field in readiness["missing_fields"]]
			frappe.throw(
				_("Cannot submit Sea Booking. Missing or invalid fields:\n{0}").format(
					"\n".join(f"- {msg}" for msg in messages)
				)
			)

	def before_submit(self):
		"""Validate quote reference before submitting the Sea Booking."""
		self.validate_required_fields_for_submit()
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

		throw_if_missing_destination_service_charge(self)

		self.validate_ready_for_sea_shipment_on_submit()
		
		# Duplicate container checks when numbers are entered (FCL Container No enforced on Sea Shipment submit)
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
	
	def validate_required_fields_for_submit(self):
		"""Enforce header party/routing fields when submitting (draft saves may omit them)."""
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
		from logistics.utils.validation_user_messages import (
			atd_ata_freight_invalid_message,
			atd_ata_freight_title,
			etd_eta_freight_invalid_message,
			etd_eta_freight_title,
		)

		throw_if_left_date_after_right(
			self.etd, self.eta, etd_eta_freight_invalid_message, etd_eta_freight_title
		)
		throw_if_left_date_after_right(
			self.atd, self.ata, atd_ata_freight_invalid_message, atd_ata_freight_title
		)
	
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
				sq = frappe.get_doc("Sales Quote", self.sales_quote)
				apply_sales_quote_routing_to_booking(self, sq)
				self._populate_charges_from_sales_quote_doc()
			else:
				# Clear charges if sales_quote is removed
				self.set("charges", [])
				self.set("routing_legs", [])
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

			apply_sales_quote_routing_to_booking(self, sales_quote)
			
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
			if (
				sea_charge_exists
				or sea_freight_exists
				or (
					cint(getattr(self, "is_internal_job", 0))
					and should_apply_internal_job_main_charge_overlay(self)
				)
			):
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
		overlay_populated = False
		if cint(getattr(self, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(self):
			try:
				n, st = populate_internal_job_charges_from_main_service(self)
				if n:
					frappe.msgprint(
						_("Populated {0} charge rows from Main Job (Service Type: {1}).").format(n, st),
						title=_("Charges Updated"),
						indicator="green",
					)
					overlay_populated = True
				else:
					frappe.msgprint(
						_("No Sea charge lines on the Main Job; loading charges from Sales Quote if available."),
						title=_("Charges"),
						indicator="orange",
					)
			except Exception as e:
				frappe.log_error(
					f"Error populating Sea Booking charges from Main Job: {str(e)}",
					"Sea Booking Charges From Main Job Error",
				)
				frappe.msgprint(str(e), title=_("Error"), indicator="red")
		if overlay_populated:
			return

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

			sales_quote_doc = frappe.get_doc("Sales Quote", self.sales_quote)
			filters = sales_quote_charge_filters(self, sales_quote_doc)

			# Fetch from Sales Quote Charge (filtered) or Sales Quote Sea Freight (legacy)
			charge_fields = [
				"name", "item_code", "item_name", "revenue_calculation_method", "calculation_method", "uom", "currency",
				"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue", "charge_type", "charge_category",
				"apply_95_5_rule", "taxable_freight_item", "taxable_freight_item_tax_template",
				"bill_to", "pay_to", "service_type",
				"origin_port", "destination_port",
				# Cost fields (only include fields that exist in Sales Quote Charge)
				"cost_calculation_method", "unit_cost", "cost_unit_type", "cost_currency",
				"cost_quantity", "cost_minimum_quantity", "cost_minimum_charge",
				"cost_maximum_charge", "cost_base_amount", "cost_uom", "estimated_cost",
				"use_tariff_in_revenue", "use_tariff_in_cost", "tariff", "revenue_tariff", "cost_tariff",
				"bill_to_exchange_rate",
				"pay_to_exchange_rate",
				"bill_to_exchange_rate_source",
				"pay_to_exchange_rate_source",
			]
			sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Charge",
				filters=filters,
				fields=sqc_fields,
				order_by="idx"
			)
			if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
				legacy_fields = filter_fields_existing_in_doctype("Sales Quote Sea Freight", charge_fields)
				sales_quote_sea_freight_records = frappe.get_all(
					"Sales Quote Sea Freight",
					filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
					fields=legacy_fields,
					order_by="idx"
				)
			sales_quote_sea_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
				self, sales_quote_sea_freight_records
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

			from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

			sync_operational_exchange_rates_from_charge_rows(self, self.charges)

			# Don't show success message here - it's called automatically during validation
			# The frontend will show a user-friendly message when the user explicitly selects a quote
			if charges_added == 0:
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
		overlay_populated = False
		if cint(getattr(self, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(self):
			try:
				n, st = populate_internal_job_charges_from_main_service(self)
				if n:
					overlay_populated = True
				else:
					frappe.msgprint(
						_("No Sea charge lines on the Main Job; loading charges from Sales Quote if available."),
						title=_("Charges"),
						indicator="orange",
					)
			except Exception as e:
				frappe.log_error(
					f"Error populating Sea Booking charges from Main Job: {str(e)}",
					"Sea Booking Charges From Main Job Error",
				)
				frappe.msgprint(str(e), title=_("Error"), indicator="red")
		if overlay_populated:
			return

		try:
			# Clear existing charges
			self.set("charges", [])
			
			sq_doc = sales_quote if getattr(sales_quote, "doctype", None) == "Sales Quote" else frappe.get_doc("Sales Quote", sales_quote)
			filters = sales_quote_charge_filters(self, sq_doc)

			# Get from Sales Quote Charge (filtered) or Sales Quote Sea Freight (legacy)
			charge_fields = [
				"item_code", "item_name", "revenue_calculation_method", "calculation_method", "uom", "currency",
				"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue", "charge_type", "charge_category",
				"apply_95_5_rule", "taxable_freight_item", "taxable_freight_item_tax_template",
				"bill_to", "pay_to", "service_type",
				"origin_port", "destination_port",
				# Cost fields (only include fields that exist in Sales Quote Charge)
				"cost_calculation_method", "unit_cost", "cost_unit_type", "cost_currency",
				"cost_quantity", "cost_minimum_quantity", "cost_minimum_charge",
				"cost_maximum_charge", "cost_base_amount", "cost_uom", "estimated_cost",
				"use_tariff_in_revenue", "use_tariff_in_cost", "tariff", "revenue_tariff", "cost_tariff",
				"bill_to_exchange_rate",
				"pay_to_exchange_rate",
				"bill_to_exchange_rate_source",
				"pay_to_exchange_rate_source",
			]
			sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Charge",
				filters=filters,
				fields=sqc_fields,
				order_by="idx"
			)
			if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
				legacy_fields = filter_fields_existing_in_doctype("Sales Quote Sea Freight", charge_fields)
				sales_quote_sea_freight_records = frappe.get_all(
					"Sales Quote Sea Freight",
					filters={"parent": sq_doc.name, "parenttype": "Sales Quote"},
					fields=legacy_fields,
					order_by="idx"
				)
			sales_quote_sea_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
				self, sales_quote_sea_freight_records
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

			from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

			sync_operational_exchange_rates_from_charge_rows(self, self.charges)
			
			# Don't show success message here - it's called automatically during validation
			# The frontend will show a user-friendly message when the user explicitly selects a quote
			
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

			from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

			sync_operational_exchange_rates_from_charge_rows(self, self.charges)

			# Don't show success message here - it's called automatically during validation
			# The frontend will show a user-friendly message when the user explicitly selects a quote
			if charges_added == 0:
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
			# Support both dict (from get_all) and document-like records
			def _get(key, default=None):
				return sqsf_record.get(key, default) if isinstance(sqsf_record, dict) else getattr(sqsf_record, key, default)

			def _quote_rev_method():
				v = _get("revenue_calculation_method") or _get("calculation_method")
				return (str(v).strip() if v is not None and v != "" else "")

			# Get the item details
			item_doc = frappe.get_doc("Item", _get("item_code"))
			
			# Get default currency
			default_currency = frappe.get_system_settings("currency") or "USD"

			quote_unit_type = (_get("unit_type") or "").strip() or None

			# Map Sales Quote Charge unit_type → Sea Booking Charge (same options + a few renames).
			# The old small dict defaulted unknown quote values to "Package", so TEU/Job/Trip/etc. never copied.
			_sea_booking_charge_unit_types = frozenset(
				{
					"Distance",
					"Weight",
					"Chargeable Weight",
					"Volume",
					"Package",
					"Piece",
					"Job",
					"Trip",
					"TEU",
					"Container",
					"Operation Time",
				}
			)
			_quote_only_unit_type_map = {
				"Shipment": "Job",  # legacy Sales Quote Sea Freight
				"Item Count": "Piece",
				"Handling Unit": "Package",
			}

			def _map_quote_unit_type_to_sea_booking_charge(raw):
				if not raw:
					return "Package"
				if raw in _sea_booking_charge_unit_types:
					return raw
				return _quote_only_unit_type_map.get(raw, "Package")

			mapped_unit_type = _map_quote_unit_type_to_sea_booking_charge(quote_unit_type)

			# Get quantity based on unit type (use quote row value, not only mapped label)
			quantity = 0
			if quote_unit_type == "Chargeable Weight":
				chargeable_qty = getattr(self, "chargeable", None)
				if chargeable_qty in (None, ""):
					chargeable_qty = getattr(self, "chargeable_weight", None)
				quantity = flt(chargeable_qty or 0)
			elif quote_unit_type == "Weight":
				quantity = flt(self.total_weight) or 0
			elif quote_unit_type == "Volume":
				quantity = flt(self.total_volume) or 0
			elif quote_unit_type in ("Package", "Piece", "Handling Unit"):
				if hasattr(self, "packages") and self.packages:
					quantity = len(self.packages)
				else:
					quantity = 1
			elif quote_unit_type == "Item Count":
				if hasattr(self, "packages") and self.packages:
					quantity = len(self.packages)
				else:
					quantity = 1
			elif quote_unit_type in ("Container", "TEU"):
				if hasattr(self, "containers") and self.containers:
					quantity = len(self.containers)
				else:
					quantity = 1
			elif quote_unit_type in ("Shipment", "Job", "Trip", "Distance", "Operation Time"):
				quantity = 1
			else:
				quantity = 1
			
			# Calculate selling amount based on calculation method (quote row uses revenue_calculation_method on Sales Quote Charge)
			_sq_rev_method = _quote_rev_method()
			_sq_unit_rate = flt(_get("unit_rate")) or 0
			selling_amount = 0
			if _sq_rev_method == "Per Unit":
				selling_amount = _sq_unit_rate * quantity
				# Apply minimum/maximum charge
				_sq_min_ch = _get("minimum_charge")
				_sq_max_ch = _get("maximum_charge")
				if _sq_min_ch and selling_amount < flt(_sq_min_ch):
					selling_amount = flt(_sq_min_ch)
				if _sq_max_ch and selling_amount > flt(_sq_max_ch):
					selling_amount = flt(_sq_max_ch)
			elif _sq_rev_method == "Fixed Amount":
				selling_amount = _sq_unit_rate
			elif _sq_rev_method == "Base Plus Additional":
				base = flt(_get("base_amount")) or 0
				additional = _sq_unit_rate * max(0, quantity - 1)
				selling_amount = base + additional
			elif _sq_rev_method == "First Plus Additional":
				min_qty = flt(_get("minimum_quantity")) or 1
				if quantity <= min_qty:
					selling_amount = _sq_unit_rate
				else:
					additional = _sq_unit_rate * (quantity - min_qty)
					selling_amount = _sq_unit_rate + additional
			else:
				selling_amount = _sq_unit_rate
			
			charge_type = _get("charge_type") or (
				item_doc.custom_charge_type if hasattr(item_doc, "custom_charge_type") and item_doc.custom_charge_type else None
			) or "Revenue"
			
			# Normalize calculation_method for Sea Booking Charges
			sqsf_calc_method = _quote_rev_method()
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
					calc_method_final = "Per Unit" if quote_unit_type else "Flat Rate"
			else:
				calc_method_final = sqsf_calc_method_normalized
			
			if calc_method_final not in valid_calc_methods:
				calc_method_final = "Per Unit" if quote_unit_type else "Flat Rate"
			
			charge_category = _get("charge_category") or (
				item_doc.custom_charge_category if hasattr(item_doc, "custom_charge_category") and item_doc.custom_charge_category else None
			) or "Other"
			
			# Get description from item or use item_name as fallback
			description = None
			if hasattr(item_doc, 'description') and item_doc.description:
				description = item_doc.description
			else:
				description = _get("item_name") or item_doc.item_name
			
			# Get item_tax_template and invoice_type from item if available
			item_tax_template = None
			if hasattr(item_doc, 'item_tax_template'):
				item_tax_template = item_doc.item_tax_template
			
			invoice_type = None
			if hasattr(item_doc, 'invoice_type'):
				invoice_type = item_doc.invoice_type
			
			# Map the fields to Sea Booking Charges structure
			charge_data = {
				"service_type": operational_booking_charge_service_type_label(
					_get("service_type"), default="Sea"
				),
				"item_code": _get("item_code"),
				"item_name": _get("item_name") or item_doc.item_name,
				"charge_type": charge_type,
				"charge_category": charge_category,  # Added: charge_category
				"description": description,  # Added: description from item
				"item_tax_template": item_tax_template,  # Added: item_tax_template from item
				"invoice_type": invoice_type,  # Added: invoice_type from item
				"charge_description": _get("item_name") or item_doc.item_name,
				"bill_to": _get("bill_to") or (self.local_customer if hasattr(self, 'local_customer') else None),
				"pay_to": _get("pay_to"),
				"selling_currency": _get("currency") or default_currency,
				"selling_amount": selling_amount,
				"rate": _get("unit_rate") or 0,
				"uom": _get("uom") or None,
				"revenue_calculation_method": calc_method_final,
				"quantity": quantity,
				"currency": _get("currency") or default_currency,
				"unit_type": mapped_unit_type,  # Use mapped unit_type
				"base_amount": _get("base_amount") or 0,
				"sales_quote_link": self.sales_quote if hasattr(self, 'sales_quote') and self.sales_quote else None,
			}
			# Copy estimated revenue from quote so booking shows correct revenue
			est_rev = _get("estimated_revenue")
			if est_rev is not None:
				charge_data["estimated_revenue"] = flt(est_rev)
			
			# Add minimum/maximum charges and quantities if available
			if _get("minimum_charge"):
				charge_data["minimum_charge"] = _get("minimum_charge")
			if _get("maximum_charge"):
				charge_data["maximum_charge"] = _get("maximum_charge")
			if _get("minimum_quantity"):
				charge_data["minimum_quantity"] = _get("minimum_quantity")

			if _get("apply_95_5_rule") is not None:
				charge_data["apply_95_5_rule"] = cint(_get("apply_95_5_rule"))
			if _get("taxable_freight_item"):
				charge_data["taxable_freight_item"] = _get("taxable_freight_item")
			if _get("taxable_freight_item_tax_template"):
				charge_data["taxable_freight_item_tax_template"] = _get("taxable_freight_item_tax_template")
			
			# Add cost fields if available
			if hasattr(sqsf_record, "cost_calculation_method") and sqsf_record.cost_calculation_method:
				charge_data["cost_calculation_method"] = sqsf_record.cost_calculation_method
			if hasattr(sqsf_record, "unit_cost") and sqsf_record.unit_cost is not None:
				charge_data["unit_cost"] = sqsf_record.unit_cost
			cost_unit_type = _get("cost_unit_type")
			if cost_unit_type:
				charge_data["cost_unit_type"] = cost_unit_type
			if hasattr(sqsf_record, "cost_currency") and sqsf_record.cost_currency:
				charge_data["cost_currency"] = sqsf_record.cost_currency
			if hasattr(sqsf_record, "cost_quantity") and sqsf_record.cost_quantity is not None:
				charge_data["cost_quantity"] = sqsf_record.cost_quantity
			if hasattr(sqsf_record, "cost_minimum_quantity") and sqsf_record.cost_minimum_quantity is not None:
				charge_data["cost_minimum_quantity"] = sqsf_record.cost_minimum_quantity
			if hasattr(sqsf_record, "cost_minimum_unit_rate") and sqsf_record.cost_minimum_unit_rate is not None:
				charge_data["cost_minimum_unit_rate"] = sqsf_record.cost_minimum_unit_rate
			if hasattr(sqsf_record, "cost_minimum_charge") and sqsf_record.cost_minimum_charge is not None:
				charge_data["cost_minimum_charge"] = sqsf_record.cost_minimum_charge
			if hasattr(sqsf_record, "cost_maximum_charge") and sqsf_record.cost_maximum_charge is not None:
				charge_data["cost_maximum_charge"] = sqsf_record.cost_maximum_charge
			if hasattr(sqsf_record, "cost_base_amount") and sqsf_record.cost_base_amount is not None:
				charge_data["cost_base_amount"] = sqsf_record.cost_base_amount
			if hasattr(sqsf_record, "cost_base_quantity") and sqsf_record.cost_base_quantity is not None:
				charge_data["cost_base_quantity"] = sqsf_record.cost_base_quantity
			if hasattr(sqsf_record, "cost_uom") and sqsf_record.cost_uom:
				charge_data["cost_uom"] = sqsf_record.cost_uom
			if hasattr(sqsf_record, "estimated_cost") and sqsf_record.estimated_cost is not None:
				charge_data["estimated_cost"] = sqsf_record.estimated_cost
			if hasattr(sqsf_record, "use_tariff_in_revenue"):
				charge_data["use_tariff_in_revenue"] = getattr(sqsf_record, "use_tariff_in_revenue", False)
			if hasattr(sqsf_record, "use_tariff_in_cost"):
				charge_data["use_tariff_in_cost"] = getattr(sqsf_record, "use_tariff_in_cost", False)
			if hasattr(sqsf_record, "tariff") and sqsf_record.tariff:
				charge_data["tariff"] = sqsf_record.tariff
			if hasattr(sqsf_record, "revenue_tariff") and sqsf_record.revenue_tariff:
				charge_data["revenue_tariff"] = sqsf_record.revenue_tariff
			if hasattr(sqsf_record, "cost_tariff") and sqsf_record.cost_tariff:
				charge_data["cost_tariff"] = sqsf_record.cost_tariff
			bxr = _get("bill_to_exchange_rate")
			if bxr is not None:
				charge_data["bill_to_exchange_rate"] = bxr
			pxr = _get("pay_to_exchange_rate")
			if pxr is not None:
				charge_data["pay_to_exchange_rate"] = pxr
			b_src = _get("bill_to_exchange_rate_source")
			if b_src:
				charge_data["bill_to_exchange_rate_source"] = b_src
			p_src = _get("pay_to_exchange_rate_source")
			if p_src:
				charge_data["pay_to_exchange_rate_source"] = p_src
			
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
		if self.service_level and not frappe.db.exists("Logistics Service Level", self.service_level):
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
		"""Generate HTML for Dashboard tab: tabbed layout with map, milestones, alerts."""
		try:
			from logistics.document_management.logistics_form_dashboard import (
				build_sea_booking_dashboard_config,
				render_logistics_form_dashboard_html,
			)
			from logistics.utils.sales_quote_validity import get_sales_quote_validity_dashboard_html

			dash = render_logistics_form_dashboard_html(
				self, build_sea_booking_dashboard_config(self)
			)
			return get_sales_quote_validity_dashboard_html(self) + dash
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
		self.validate_required_fields_for_submit()
		
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

		self.validate_container_numbers()

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
			copy_sales_quote_fields_to_target(self, sea_shipment)
			if hasattr(sea_shipment, "is_main_service") and hasattr(self, "is_main_service"):
				sea_shipment.is_main_service = self.is_main_service
			if hasattr(sea_shipment, "is_internal_job") and hasattr(self, "is_internal_job"):
				sea_shipment.is_internal_job = self.is_internal_job
			if hasattr(sea_shipment, "main_job_type") and hasattr(self, "main_job_type"):
				sea_shipment.main_job_type = self.main_job_type
			if hasattr(sea_shipment, "main_job") and hasattr(self, "main_job"):
				sea_shipment.main_job = self.main_job
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
			sea_shipment.freight_consolidator = frappe.db.get_value(
				"Sea Booking", self.name, "freight_consolidator"
			)
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
			if getattr(self, "load_type", None):
				sea_shipment.load_type = self.load_type
			sea_shipment.company = self.company
			sea_shipment.branch = self.branch
			sea_shipment.cost_center = self.cost_center
			sea_shipment.profit_center = self.profit_center
			# Copy measurement override and costing fields
			if hasattr(self, "override_volume_weight"):
				sea_shipment.override_volume_weight = self.override_volume_weight or 0
			if hasattr(self, "project") and self.project:
				sea_shipment.project = self.project
			if hasattr(self, "job_number") and self.job_number:
				sea_shipment.job_number = self.job_number
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
						"other_references": container.other_references,
						"size": getattr(container, "size", None),
						"packages_in_container": getattr(container, "packages_in_container", None),
						"weight_in_container": getattr(container, "weight_in_container", None),
						"volume_in_container": getattr(container, "volume_in_container", None),
						"max_weight": getattr(container, "max_weight", None),
						"max_volume": getattr(container, "max_volume", None),
						"utilization_percentage": getattr(container, "utilization_percentage", None),
					})
			
			# Copy packages if they exist (from Sea Booking Packages to Sea Freight Packages)
			if hasattr(self, 'packages') and self.packages:
				for package in self.packages:
					sea_shipment.append("packages", {
						"commodity": package.commodity,
						"warehouse_item": getattr(package, "warehouse_item", None),
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
			
			# Fetch charges from Sales Quote or One-Off Quote if Sea Booking has quote but no charges
			if not hasattr(self, 'charges') or not self.charges:
				if self.sales_quote:
					self._populate_charges_from_sales_quote_doc()
				elif cint(getattr(self, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(
					self
				):
					self._populate_charges_from_sales_quote_doc()
				elif getattr(self, "quote_type", None) == "One-Off Quote" and getattr(self, "quote", None):
					self._populate_charges_from_one_off_quote()

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
					if hasattr(charge, 'item_code'):
						new_charge_row.item_code = charge.item_code
					if hasattr(charge, 'item_name'):
						new_charge_row.item_name = charge.item_name
					if hasattr(charge, 'charge_name'):
						new_charge_row.charge_name = charge.charge_name
					if hasattr(charge, 'charge_type'):
						new_charge_row.charge_type = charge.charge_type
					if hasattr(charge, 'charge_category'):
						new_charge_row.charge_category = charge.charge_category
					if hasattr(charge, 'apply_95_5_rule'):
						new_charge_row.apply_95_5_rule = charge.apply_95_5_rule
					if hasattr(charge, 'taxable_freight_item'):
						new_charge_row.taxable_freight_item = charge.taxable_freight_item
					if hasattr(charge, 'taxable_freight_item_tax_template'):
						new_charge_row.taxable_freight_item_tax_template = charge.taxable_freight_item_tax_template
					if hasattr(charge, 'service_type') and charge.service_type:
						new_charge_row.service_type = charge.service_type
					if hasattr(charge, 'item_tax_template'):
						new_charge_row.item_tax_template = charge.item_tax_template
					if hasattr(charge, 'invoice_type'):
						new_charge_row.invoice_type = charge.invoice_type
					if hasattr(charge, 'charge_description'):
						new_charge_row.charge_description = charge.charge_description
					new_charge_row.sales_quote_link = getattr(charge, 'sales_quote_link', None) or self.sales_quote
					
					# Copy revenue fields
					if hasattr(charge, 'bill_to'):
						new_charge_row.bill_to = charge.bill_to
					if hasattr(charge, 'bill_to_exchange_rate'):
						new_charge_row.bill_to_exchange_rate = charge.bill_to_exchange_rate
					if hasattr(charge, 'bill_to_exchange_rate_source'):
						new_charge_row.bill_to_exchange_rate_source = charge.bill_to_exchange_rate_source
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
					if hasattr(charge, 'pay_to_exchange_rate'):
						new_charge_row.pay_to_exchange_rate = charge.pay_to_exchange_rate
					if hasattr(charge, 'pay_to_exchange_rate_source'):
						new_charge_row.pay_to_exchange_rate_source = charge.pay_to_exchange_rate_source
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

			if getattr(self, "operational_exchange_rates", None):
				for ox in self.operational_exchange_rates:
					sea_shipment.append(
						"operational_exchange_rates",
						{
							"entity_type": ox.entity_type,
							"entity": ox.entity,
							"exchange_rate_source": ox.exchange_rate_source,
							"currency": ox.currency,
							"rate": ox.rate,
							"alternate_currency": getattr(ox, "alternate_currency", None),
							"alternate_rate": getattr(ox, "alternate_rate", None),
						},
					)
			
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

			from logistics.utils.internal_job_detail_copy import copy_internal_job_details_to_doc

			copy_internal_job_details_to_doc(self, sea_shipment)
			
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
				if not frappe.db.exists("Logistics Service Level", sea_shipment.service_level):
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
						if not frappe.db.exists("Logistics Service Level", sea_shipment.service_level):
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
						if not frappe.db.exists("Logistics Service Level", sea_shipment.service_level):
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
			# Provide user-friendly error messages
			error_msg = str(e)
			if "Could not find Job No" in error_msg or isinstance(e, frappe.LinkValidationError):
				# Extract the job number from the error if possible
				match = re.search(r'Job No:?\s*([A-Z0-9]+)', error_msg)
				if match:
					job_no = match.group(1)
					frappe.throw(
						_("Unable to create shipment: The system tried to create a Job Number but the shipment document '{0}' was not yet saved. Please try again or contact support if the issue persists.").format(job_no),
						title=_("Conversion Error")
					)
				else:
					frappe.throw(
						_("Unable to create shipment: There was an issue creating the Job Number. The shipment document may not have been fully saved. Please try again or contact support if the issue persists."),
						title=_("Conversion Error")
					)
			else:
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
		frappe.log_error(title="Sea Booking - Recalculate Charges Error", message=str(e))
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


@frappe.whitelist()
def get_available_one_off_quotes(sea_booking_name: str = None) -> Dict[str, Any]:
	"""Get Link filters for One-off Sales Quotes usable on Sea Booking (single-use rules preserved).

	Eligible quotes must have **Sea** charge lines (unified or legacy), not only ``main_service`` = Sea,
	so a multi-service one-off can be selected here when sea is priced.

	Excludes quotes already linked to another Sea Booking or already converted.
	"""
	try:
		from logistics.utils.sales_quote_service_eligibility import (
			converted_one_off_sales_quote_names,
			one_off_sales_quote_link_filters_for_service,
		)

		used_rows = frappe.get_all(
			"Sea Booking",
			filters={
				"quote_type": "One-Off Quote",
				"name": ["!=", sea_booking_name or ""],
				"docstatus": ["!=", 2],
				"is_main_service": 1,
				"sales_quote": ["is", "set"],
			},
			fields=["sales_quote"],
		)
		used_quotes = []
		for row in used_rows:
			ref = (row.get("sales_quote") or "").strip()
			if ref:
				used_quotes.append(ref)

		converted_legacy: list[str] = []
		if frappe.db.exists("DocType", "One-Off Quote"):
			try:
				converted_legacy = frappe.get_all(
					"One-Off Quote",
					filters={"status": "Converted"},
					pluck="name",
				) + frappe.get_all(
					"One-Off Quote",
					filters={"converted_to_doc": ["is", "set"]},
					pluck="name",
				)
			except Exception:
				converted_legacy = []

		excluded_quotes = list(
			set(used_quotes + converted_legacy + converted_one_off_sales_quote_names())
		)

		filters = one_off_sales_quote_link_filters_for_service("Sea", excluded_quotes)
		return {"filters": filters}
	except Exception as e:
		frappe.log_error(
			f"Error getting available One-Off Quotes: {str(e)}",
			"Sea Booking Quote Query Error"
		)
		return {"filters": {}}


@frappe.whitelist()
def populate_charges_from_sales_quote(
	docname: str = None,
	sales_quote: str = None,
	is_internal_job: int = None,
	main_job_type: str = None,
	main_job: str = None,
):
	"""Populate charges from sales_quote. Called from frontend when sales_quote field changes.
	
	Returns charge data that can be populated in the frontend.
	"""
	try:
		doc = None
		if docname:
			try:
				doc = frappe.get_doc("Sea Booking", docname)
			except Exception:
				pass

		parent = doc if doc else frappe._dict(
			doctype="Sea Booking", name=docname, is_internal_job=0, is_main_service=0
		)
		if is_internal_job is not None:
			parent.is_internal_job = cint(is_internal_job)
		if main_job_type is not None:
			parent.main_job_type = main_job_type
		if main_job is not None:
			parent.main_job = main_job

		if should_apply_internal_job_main_charge_overlay(parent):
			charges = build_internal_job_sea_booking_charge_dicts(parent)
			ij_detail_payload = []
			if sales_quote and frappe.db.exists("Sales Quote", sales_quote):
				sq_doc = frappe.get_doc("Sales Quote", sales_quote)
				from logistics.utils.sync_internal_job_details_from_sales_quote import (
					build_internal_job_details_payload_for_quote_response,
				)

				ij_detail_payload = build_internal_job_details_payload_for_quote_response(
					"Sea Booking", doc, sq_doc
				)
			if doc and charges:
				doc._apply_actuals_to_charge_dicts(charges)
			return {
				"charges": charges,
				"charges_count": len(charges),
				"internal_job_charge_overlay_applied": True,
				"source": "main_service",
				"routing_legs": routing_legs_for_api_response(sales_quote, doc) if sales_quote else [],
				"internal_job_details": ij_detail_payload,
			}

		if not sales_quote:
			return {"charges": []}

		# Temporary names (unsaved documents) cannot be fetched
		if sales_quote.startswith("new-"):
			return {
				"error": _("Please save the Sales Quote first before selecting it here."),
				"charges": []
			}
		# Verify that the sales_quote exists
		if not frappe.db.exists("Sales Quote", sales_quote):
			return {
				"error": f"Sales Quote {sales_quote} does not exist",
				"charges": []
			}

		sales_quote_doc = frappe.get_doc("Sales Quote", sales_quote)
		from logistics.utils.sync_internal_job_details_from_sales_quote import (
			build_internal_job_details_payload_for_quote_response,
		)

		ij_detail_payload = build_internal_job_details_payload_for_quote_response(
			"Sea Booking", doc, sales_quote_doc
		)
		filters = sales_quote_charge_filters(parent, sales_quote_doc)

		# Fetch from Sales Quote Charge (filtered) or Sales Quote Sea Freight (legacy)
		charge_fields = [
			"name",
			"item_code",
			"item_name",
			"revenue_calculation_method",
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
			"charge_type",
			"charge_category",  # Include charge_category
			"apply_95_5_rule",
			"taxable_freight_item",
			"taxable_freight_item_tax_template",
			"bill_to",  # Include bill_to
			"pay_to",  # Include pay_to
			"service_type",  # Include service_type to identify charge types
			"origin_port",
			"destination_port",
			# Cost fields (only include fields that exist in Sales Quote Charge)
			"cost_calculation_method",
			"unit_cost",
			"cost_unit_type",
			"cost_currency",
			"cost_quantity",
			"cost_minimum_quantity",
			"cost_minimum_charge",
			"cost_maximum_charge",
			"cost_base_amount",
			"cost_uom",
			"estimated_cost",
			"use_tariff_in_revenue",
			"use_tariff_in_cost",
			"tariff",
			"revenue_tariff",
			"cost_tariff",
			"bill_to_exchange_rate",
			"pay_to_exchange_rate",
			"bill_to_exchange_rate_source",
			"pay_to_exchange_rate_source",
		]
		sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
		sales_quote_sea_freight_records = frappe.get_all(
			"Sales Quote Charge",
			filters=filters,
			fields=sqc_fields,
			order_by="idx"
		)
		if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
			legacy_fields = filter_fields_existing_in_doctype("Sales Quote Sea Freight", charge_fields)
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Sea Freight",
				filters={"parent": sales_quote, "parenttype": "Sales Quote"},
				fields=legacy_fields,
				order_by="idx"
			)
		filter_parent = doc if doc else parent
		sales_quote_sea_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
			filter_parent, sales_quote_sea_freight_records
		)
		
		if not sales_quote_sea_freight_records:
			return {
				"charges": [],
				"message": f"No sea freight charges found in Sales Quote: {sales_quote}",
				"customer": sales_quote_doc.customer,
				"routing_legs": routing_legs_for_api_response(sales_quote, doc),
				"internal_job_details": ij_detail_payload,
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

		if doc and charges:
			doc._apply_actuals_to_charge_dicts(charges)
		
		# Note: We do NOT save the document here to avoid "document has been modified" errors.
		# The client-side JavaScript will handle updating the form with the charges data.
		
		return {
			"charges": charges,
			"charges_count": len(charges),
			"customer": sales_quote_doc.customer,
			"routing_legs": routing_legs_for_api_response(sales_quote, doc),
			"internal_job_details": ij_detail_payload,
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
		# Temporary names (unsaved documents) cannot be fetched
		if one_off_quote.startswith("new-"):
			return {
				"error": _("Please save the One-Off Quote first before selecting it here."),
				"charges": []
			}
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