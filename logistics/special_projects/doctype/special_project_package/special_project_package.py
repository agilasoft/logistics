# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SpecialProjectPackage(Document):
	def before_insert(self):
		"""Set default dimension/volume/weight UOM from Logistics Settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions (Dimension Volume UOM Conversion)."""
		self._apply_default_uoms()
		self.calculate_volume()

	def _apply_default_uoms(self):
		"""Apply default dimension_uom, volume_uom and weight_uom from Logistics Settings if not set."""
		from logistics.utils.measurements import get_default_uoms

		company = self._get_parent_company()
		defaults = get_default_uoms(company=company)
		if not getattr(self, "dimension_uom", None) and defaults.get("dimension"):
			self.dimension_uom = defaults["dimension"]
		if not getattr(self, "volume_uom", None) and defaults.get("volume"):
			self.volume_uom = defaults["volume"]
		if not getattr(self, "weight_uom", None) and defaults.get("weight"):
			self.weight_uom = defaults["weight"]

	def _get_parent_company(self):
		"""Get company from parent Special Project."""
		if self.get("parenttype") == "Special Project" and self.get("parent"):
			if self.parent and self.parent.startswith("new-"):
				return None
			if not frappe.db.exists("Special Project", self.parent):
				return None
			return frappe.db.get_value("Special Project", self.parent, "company")
		return None

	def calculate_volume(self):
		"""Calculate volume from length, width, height using Dimension Volume UOM Conversion."""
		if not self.length or not self.width or not self.height:
			if getattr(self, "volume", None) is None:
				self.volume = 0
			return
		from logistics.utils.measurements import (
			calculate_volume_from_dimensions,
			get_default_uoms,
			get_package_line_volume_multiplier,
		)

		dimension_uom = getattr(self, "dimension_uom", None)
		volume_uom = getattr(self, "volume_uom", None)
		company = self._get_parent_company()
		if not dimension_uom or not volume_uom:
			defaults = get_default_uoms(company=company)
			dimension_uom = dimension_uom or defaults.get("dimension")
			volume_uom = volume_uom or defaults.get("volume")
		base = calculate_volume_from_dimensions(
			length=self.length,
			width=self.width,
			height=self.height,
			dimension_uom=dimension_uom,
			volume_uom=volume_uom,
			company=company,
		)
		self.volume = base * get_package_line_volume_multiplier(self)
