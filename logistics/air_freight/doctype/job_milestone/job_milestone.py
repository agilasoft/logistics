# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class JobMilestone(Document):
	def validate(self):
		"""Auto-update status based on actual dates"""
		# If actual_start is set and status is not already started/completed, set to Started
		if self.actual_start and self.status.lower() not in ['started', 'completed', 'finished', 'done']:
			self.status = "Started"
		
		# If actual_end is set, set status to Completed
		if self.actual_end and self.status.lower() not in ['completed', 'finished', 'done']:
			self.status = "Completed"
	
	@frappe.whitelist()
	def capture_actual_start(self):
		"""Capture actual start time for this milestone"""
		if not self.actual_start:
			self.actual_start = frappe.utils.now_datetime()
			self.status = "Started"
			self.save()
			frappe.db.commit()
			return True
		return False
	
	@frappe.whitelist()
	def capture_actual_end(self):
		"""Capture actual end time for this milestone"""
		if not self.actual_end:
			self.actual_end = frappe.utils.now_datetime()
			self.status = "Completed"
			self.save()
			frappe.db.commit()
			return True
		return False
