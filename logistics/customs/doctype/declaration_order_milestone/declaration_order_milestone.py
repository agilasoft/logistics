# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class DeclarationOrderMilestone(Document):
	"""Child table for milestones on Declaration Order."""

	def before_save(self):
		if not self.get("created_at"):
			self.created_at = frappe.utils.now()
		from logistics.utils.milestone_status_utils import update_milestone_status
		update_milestone_status(self)
