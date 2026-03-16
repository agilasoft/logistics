# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AirBookingPackages(Document):
	def before_insert(self):
		"""Set default dimension/volume/weight UOM from settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions. Chargeable weight is computed on parent Air Booking."""
		self._apply_default_uoms()
		self.calculate_volume()

	def _apply_default_uoms(self):
		"""Apply default dimension_uom, volume_uom and weight_uom from Logistics Settings if not set."""
		company = self._get_parent_company()
		defaults = self._get_safe_default_uoms(company=company)
		if not getattr(self, "dimension_uom", None) and defaults.get("dimension"):
			self.dimension_uom = defaults["dimension"]
		if not getattr(self, "volume_uom", None) and defaults.get("volume"):
			self.volume_uom = defaults["volume"]
		if not getattr(self, "weight_uom", None) and defaults.get("weight"):
			self.weight_uom = defaults["weight"]
	
	def _get_safe_default_uoms(self, company=None):
		"""Get default UOMs with fallbacks - never throws, always returns a dict."""
		from logistics.utils.measurements import get_default_uoms
		try:
			return get_default_uoms(company=company)
		except Exception as e:
			# If Logistics Settings are not configured, return empty dict
			# Callers should handle missing UOMs gracefully
			frappe.log_error(
				f"Could not get default UOMs (company={company}): {str(e)}. "
				"Please configure Logistics Settings with default UOMs.",
				"Air Booking Package - Default UOM Warning"
			)
			return {"dimension": None, "volume": None, "weight": None}

	def _get_parent_company(self):
		"""Get company from parent Air Booking. Works with both saved and unsaved parents."""
		if self.get("parenttype") == "Air Booking" and self.get("parent"):
			# Skip if parent name is still temporary (starts with "new-")
			# This can happen during document creation before the parent is fully saved
			if self.parent and self.parent.startswith("new-"):
				# Fallback to user default company
				try:
					return frappe.defaults.get_user_default("Company")
				except Exception:
					return None
			# Check if parent exists before trying to get value
			if frappe.db.exists("Air Booking", self.parent):
				try:
					company = frappe.db.get_value("Air Booking", self.parent, "company")
					if company:
						return company
				except Exception:
					pass
		# Fallback: try to get company from user defaults
		try:
			return frappe.defaults.get_user_default("Company")
		except Exception:
			return None

	def calculate_volume(self):
		"""Calculate volume from length, width, height using Dimension Volume UOM Conversion. No fallbacks; conversion required."""
		if not self.length or not self.width or not self.height:
			if getattr(self, "volume", None) is None:
				self.volume = 0
			return
		from logistics.utils.measurements import (
			calculate_volume_from_dimensions,
			get_default_uoms,
		)
		dimension_uom = getattr(self, "dimension_uom", None)
		volume_uom = getattr(self, "volume_uom", None)
		company = self._get_parent_company()
		if not dimension_uom or not volume_uom:
			defaults = get_default_uoms(company=company)
			dimension_uom = dimension_uom or defaults.get("dimension")
			volume_uom = volume_uom or defaults.get("volume")
		self.volume = calculate_volume_from_dimensions(
			length=self.length,
			width=self.width,
			height=self.height,
			dimension_uom=dimension_uom,
			volume_uom=volume_uom,
			company=company,
		)
