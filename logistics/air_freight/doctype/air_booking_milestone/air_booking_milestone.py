# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class AirBookingMilestone(Document):
	"""Child table for milestones on Air Booking.

	Parent save runs Date Based sync in logistics.document_management.milestone_sync
	(via doc_events on Air Booking). User-entered actual_end is preserved unless the
	template uses sync direction "Parent to Milestone only" with an empty parent date.
	"""

	def before_save(self):
		if not self.get("created_at"):
			self.created_at = frappe.utils.now()
		from logistics.utils.milestone_status_utils import update_milestone_status
		update_milestone_status(self)
