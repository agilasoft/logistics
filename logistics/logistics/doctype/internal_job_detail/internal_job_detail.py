# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


class InternalJobDetail(Document):
	"""Child row: internal job link + service parameters (aligned with Sales Quote Charge)."""

	def validate(self):
		st = (self.service_type or "").strip()
		if st:
			expected = default_job_type_for_internal_job_service_type(st)
			if expected:
				self.job_type = expected
