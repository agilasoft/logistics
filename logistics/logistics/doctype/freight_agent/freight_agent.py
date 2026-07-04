# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.utils.party_code import maybe_set_party_code
from logistics.utils.service_mode_flags import MODULE_FLAG_FIELDS


class FreightAgent(Document):
	def validate(self):
		maybe_set_party_code(
			self,
			name_field="freight_agent_name",
			unloco_field="default_unloco",
			code_fieldname="code",
		)
		self.validate_applicable_service_types()

	def validate_applicable_service_types(self):
		if any(getattr(self, field, 0) for field in MODULE_FLAG_FIELDS):
			return
		frappe.throw(
			_("Select at least one Applicable Service Type (Air, Sea, Transport, Customs, or Warehousing)."),
			title=_("Applicable Service Types Required"),
		)
