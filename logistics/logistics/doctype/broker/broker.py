# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from logistics.utils.party_code import maybe_set_party_code


class Broker(Document):
	def validate(self):
		maybe_set_party_code(
			self,
			name_field="broker_name",
			unloco_field="default_unloco",
			code_fieldname="code",
		)
