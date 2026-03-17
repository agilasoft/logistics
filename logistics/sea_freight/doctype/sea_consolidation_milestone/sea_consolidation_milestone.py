# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SeaConsolidationMilestone(Document):
	"""Child table for milestones on Sea Consolidation."""

	def before_save(self):
		if not self.get("created_at"):
			self.created_at = frappe.utils.now()
		from logistics.utils.milestone_status_utils import update_milestone_status
		update_milestone_status(self)
