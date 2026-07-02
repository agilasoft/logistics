# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from logistics.pricing_center.utils.opportunity_scopes import get_scope_ytd_profitability


class OpportunityServiceScope(Document):
	@property
	def actual_revenue(self) -> float:
		return flt(self._scope_profitability().get("revenue"))

	@property
	def actual_profit(self) -> float:
		return flt(self._scope_profitability().get("gross_profit"))

	def _scope_profitability(self) -> dict[str, Any]:
		cache_key = "_logistics_scope_profitability"
		if not hasattr(self, cache_key):
			setattr(self, cache_key, self._compute_scope_profitability())
		return getattr(self, cache_key)

	def _compute_scope_profitability(self) -> dict[str, Any]:
		opportunity_doc = self._get_parent_opportunity()
		return get_scope_ytd_profitability(self, opportunity_doc)

	def _get_parent_opportunity(self) -> Document | None:
		if not self.parent or self.parenttype != "Opportunity" or self.parent.startswith("new-"):
			return None
		try:
			return frappe.get_doc(self.parenttype, self.parent)
		except frappe.DoesNotExistError:
			return None
