# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ActivityCode(Document):
	def validate(self):
		if not self.for_exhibits and not self.for_special_project:
			frappe.throw(_("Select Exhibits and/or Special Project for this activity code."))
		if self.lifecycle_stage:
			stage = frappe.db.get_value(
				"Lifecycle Stage",
				self.lifecycle_stage,
				["for_exhibits", "for_special_project"],
				as_dict=True,
			)
			if not stage:
				return
			if self.for_exhibits and not stage.for_exhibits:
				frappe.throw(
					_("Lifecycle Stage {0} is not enabled for Exhibits.").format(self.lifecycle_stage)
				)
			if self.for_special_project and not stage.for_special_project:
				frappe.throw(
					_("Lifecycle Stage {0} is not enabled for Special Project.").format(
						self.lifecycle_stage
					)
				)
