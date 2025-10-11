# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FlightRoute(Document):
	def validate(self):
		"""Validate Flight Route"""
		if self.origin_airport == self.destination_airport:
			frappe.throw("Origin and Destination airports cannot be the same")
		
		# Generate route name if not provided
		if not self.route_name:
			self.route_name = f"{self.origin_airport} to {self.destination_airport}"


