# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SpecialProjectSiteReceipt(Document):
	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		# source_job_no is a historical pointer from posted receipts.
		cancelled_links = [c for c in cancelled_links if c[0] != "source_job_no"]
		return invalid_links, cancelled_links
