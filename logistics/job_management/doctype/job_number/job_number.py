# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class JobNumber(Document):
	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		cancelled_links = [c for c in cancelled_links if c[0] != "job_no"]
		return invalid_links, cancelled_links
