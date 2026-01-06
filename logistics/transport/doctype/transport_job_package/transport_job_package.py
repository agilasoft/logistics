# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TransportJobPackage(Document):
	def validate(self):
		"""Calculate volume from dimensions"""
		self.calculate_volume()
	
	def calculate_volume(self):
		"""Calculate volume from length, width, and height"""
		if self.length and self.widht and self.height:
			# Calculate volume in cubic meters
			# Assuming dimensions are in meters
			self.volume = self.length * self.widht * self.height
		else:
			self.volume = 0