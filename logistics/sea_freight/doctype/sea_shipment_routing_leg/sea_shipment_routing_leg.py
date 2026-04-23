# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from logistics.utils.transport_mode_flags import sync_flags_to_routing_leg


class SeaShipmentRoutingLeg(Document):
	"""Child table for routing legs. Order is determined by idx."""

	def validate(self):
		sync_flags_to_routing_leg(self)
