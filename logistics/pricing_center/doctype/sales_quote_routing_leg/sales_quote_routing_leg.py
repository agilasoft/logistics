# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SalesQuoteRoutingLeg(Document):
	"""Child table for multimodal routing details. Validation handled by parent Sales Quote."""

	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		cancelled_links = [c for c in cancelled_links if c[0] != "job_no"]
		return invalid_links, cancelled_links
