# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FlightScheduleSettings(Document):
	def validate(self):
		"""Validate Flight Schedule Settings"""
		if not self.default_provider:
			frappe.throw("Please select a default flight data provider")
		
		# Validate OpenSky
		if self.opensky_enabled and not self.opensky_endpoint:
			frappe.throw("OpenSky API Endpoint is required when OpenSky is enabled")
		
		# Validate AviationStack
		if self.aviationstack_enabled and not self.aviationstack_api_key:
			frappe.throw("AviationStack API Key is required when AviationStack is enabled")
		
		if self.aviationstack_enabled and not self.aviationstack_endpoint:
			frappe.throw("AviationStack Endpoint is required when AviationStack is enabled")
		
		# Validate Aviation Edge
		if self.aviation_edge_enabled and not self.aviation_edge_api_key:
			frappe.throw("Aviation Edge API Key is required when Aviation Edge is enabled")
		
		if self.aviation_edge_enabled and not self.aviation_edge_endpoint:
			frappe.throw("Aviation Edge Endpoint is required when Aviation Edge is enabled")
		
		# Validate FlightAware
		if self.flightaware_enabled and not self.flightaware_api_key:
			frappe.throw("FlightAware API Key is required when FlightAware is enabled")
		
		if self.flightaware_enabled and not self.flightaware_endpoint:
			frappe.throw("FlightAware Endpoint is required when FlightAware is enabled")
		
		# Validate at least one provider is enabled
		if not any([
			self.opensky_enabled,
			self.aviationstack_enabled,
			self.aviation_edge_enabled,
			self.flightaware_enabled
		]):
			frappe.throw("At least one flight data provider must be enabled")

	def on_update(self):
		"""Called after saving"""
		frappe.msgprint("Flight Schedule Settings updated successfully")
		
		# Clear cache to ensure changes take effect
		frappe.clear_cache()
		
		# Log the update
		frappe.log_error(
			title="Flight Schedule Settings Updated",
			message=f"Settings updated by {frappe.session.user}"
		)


