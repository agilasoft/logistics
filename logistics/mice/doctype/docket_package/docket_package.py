# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DocketPackage(Document):
	def before_insert(self):
		self._apply_default_uoms()

	def validate(self):
		self.calculate_volume()
		self.validate_temperature()

	def _apply_default_uoms(self):
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
		if self.get("parenttype") == "Docket" and self.get("parent"):
			if self.parent and self.parent.startswith("new-"):
				return None
			if not frappe.db.exists("Docket", self.parent):
				return None
			return frappe.db.get_value("Docket", self.parent, "company")
		return None

	def calculate_volume(self):
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

	def validate_temperature(self):
		if not self.temp_controlled:
			return
		from logistics.utils.temperature_validation import validate_temperature_range

		if self.min_temperature is not None or self.max_temperature is not None:
			validate_temperature_range(
				min_temperature=self.min_temperature,
				max_temperature=self.max_temperature,
				min_field_label="Minimum Temperature",
				max_field_label="Maximum Temperature",
				raise_exception=True,
			)
