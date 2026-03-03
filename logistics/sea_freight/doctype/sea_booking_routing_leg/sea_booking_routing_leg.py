# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SeaBookingRoutingLeg(Document):
	"""Child table for routing legs. Order is determined by idx."""
