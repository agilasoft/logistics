# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Control Tower Organization controller.

Validates dimension-mapping rows and ensures references point at existing
ERPNext accounting dimensions (warning, not error - missing dimensions are
logged so a fresh tenant can still create the org and fill mappings later).
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class ControlTowerOrganization(Document):
	def validate(self):
		seen = set()
		for row in self.mappings or []:
			key = (
				row.company or "",
				row.branch or "",
				row.cost_center or "",
				row.profit_center or "",
			)
			if key in seen:
				frappe.throw(
					_("Duplicate mapping row #{0}: {1}").format(row.idx, " / ".join(x for x in key if x))
				)
			seen.add(key)
			self._warn_if_dimension_missing(row, "company", "Company")
			self._warn_if_dimension_missing(row, "branch", "Branch")
			self._warn_if_dimension_missing(row, "cost_center", "Cost Center")
			self._warn_if_dimension_missing(row, "profit_center", "Profit Center")

	def _warn_if_dimension_missing(self, row, field, doctype):
		value = row.get(field)
		if not value:
			return
		if not frappe.db.exists(doctype, value):
			frappe.msgprint(
				_("Mapping row #{0}: {1} '{2}' does not exist - the dashboard will return no rows for that filter until it is created.").format(
					row.idx, doctype, value
				),
				alert=True,
				indicator="orange",
			)
