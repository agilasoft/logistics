# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TransportJobPackage(Document):
	def before_insert(self):
		"""Set default weight/volume UOM from Transport Settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions"""
		self.calculate_volume()

	def _apply_default_uoms(self):
		"""Apply default weight_uom and volume_uom from Transport Settings if not set."""
		try:
			from logistics.utils.default_uom import get_default_uoms_for_domain
			defaults = get_default_uoms_for_domain("transport")
			if not self.weight_uom and defaults.get("weight_uom"):
				self.weight_uom = defaults["weight_uom"]
			if not self.volume_uom and defaults.get("volume_uom"):
				self.volume_uom = defaults["volume_uom"]
		except Exception:
			pass

	def calculate_volume(self):
		"""Calculate volume from length, width, and height"""
		if self.length and self.widht and self.height:
			# Calculate volume in cubic meters
			# Assuming dimensions are in meters
			self.volume = self.length * self.widht * self.height
		else:
			self.volume = 0