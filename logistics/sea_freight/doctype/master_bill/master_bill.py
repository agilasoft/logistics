# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class MasterBill(Document):
	def validate(self):
		"""Validate Master Bill"""
		self.sync_ports_from_cfs()

	def on_update(self):
		"""Called after saving"""
		pass

	def sync_ports_from_cfs(self):
		"""Sync origin/destination port from CFS when CFS is set and port is not"""
		try:
			if self.origin_cfs and not self.origin_port:
				port = frappe.db.get_value("Container Freight Station", self.origin_cfs, "port")
				if port:
					self.origin_port = port

			if self.destination_cfs and not self.destination_port:
				port = frappe.db.get_value("Container Freight Station", self.destination_cfs, "port")
				if port:
					self.destination_port = port
		except Exception as e:
			frappe.log_error(f"Sync ports from CFS error: {str(e)}")


@frappe.whitelist()
def refresh_voyage_status(master_bill_name):
	"""Manually refresh voyage status. Placeholder for future vessel tracking API integration."""
	try:
		doc = frappe.get_doc("Master Bill", master_bill_name)

		# Placeholder: In future, integrate with vessel tracking API (e.g. MarineTraffic, VesselFinder)
		# to fetch real-time position, speed, ETA updates
		# For now, return current document state
		return {
			"success": True,
			"voyage_status": doc.voyage_status,
			"actual_departure": doc.actual_departure,
			"actual_arrival": doc.actual_arrival,
			"last_position_update": doc.last_position_update,
			"message": "Voyage status refreshed. Vessel tracking API integration can be added here."
		}

	except Exception as e:
		frappe.log_error(f"Refresh voyage status error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
