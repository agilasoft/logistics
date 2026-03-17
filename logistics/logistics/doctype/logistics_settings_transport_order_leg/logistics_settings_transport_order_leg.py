# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class LogisticsSettingsTransportOrderLeg(Document):
	"""Child table for Logistics Settings - defines which routing leg types (direction + leg_type) can create Transport Orders.
	E.g. Import + On-forwarding (company controls delivery from port), Export + Pre-carriage (company controls pickup to port).
	"""

	pass
