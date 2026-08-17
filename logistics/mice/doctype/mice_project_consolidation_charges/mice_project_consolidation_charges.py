# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from logistics.utils.charges_calculation import (
	_apply_tariff_rate_data_cost,
	_charge_reference_is_persistable,
	_copy_tariff_unit_breaks_to_charge,
	_find_tariff_rate_match,
	_resolve_unit_break_rate,
	_tariff_rate_has_unit_breaks,
)


_ALLOWED_CHARGE_TYPES = frozenset({"Margin", "Disbursement", "Revenue", "Cost"})
_CONSOLIDATION_CALC_METHODS = frozenset(
	{
		"Per Unit",
		"Fixed Amount",
		"Flat Rate",
		"Base Plus Additional",
		"First Plus Additional",
		"Percentage",
		"Location-based",
		"Weight Break",
		"Qty Break",
		"Percentage Break",
	}
)


class MICEProjectConsolidationCharges(Document):
	"""Exhibit Consolidation Charges child table.

	Cost-allocation focused charges line for the parent ``Exhibit`` doctype, modeled after
	``Air Consolidation Charges`` / ``Sea Consolidation Charges``. Amounts are recomputed on
	every save and the ``allocated_amount`` is derived from ``total_amount`` × ``allocation_percentage``.
	The actual allocation across targets (Dockets / Exhibit Jobs) is computed by the parent
	``Exhibit`` document via ``allocate_costs``.
	"""

	def validate(self):
		self._apply_cost_tariff_rates_if_needed()
		self.validate_charge_data()
		self.calculate_charge_amount()
		self.calculate_allocated_amount()
		self.update_charge_status()

	def _apply_cost_tariff_rates_if_needed(self):
		"""When Use Tariff in Cost is on, load matching Tariff Charge rates onto unit_rate."""
		if not cint(self.use_tariff_in_cost):
			return
		if not self.cost_tariff or not self.item_code:
			return
		match = _match_cost_tariff_rate(
			self.cost_tariff, self.item_code, getattr(self, "service_type", None)
		)
		if not match:
			return
		rate_data, rate_row, _parentfield = match
		_apply_tariff_rate_data_cost(self, rate_data)
		rate_name = getattr(rate_row, "name", None)
		if not _tariff_rate_has_unit_breaks(rate_name, "Cost"):
			return
		if hasattr(self, "cost_use_unit_breaks"):
			self.cost_use_unit_breaks = 1
		# Prefill unit_rate from tariff tiers before breaks are copied onto this row.
		tier = _pick_unit_break_tier(_cost_unit_breaks_for_tariff_rate(rate_name), flt(self.quantity))
		if tier:
			self.unit_rate = flt(tier.get("unit_rate", 0))
			if tier.get("currency"):
				self.currency = tier.get("currency")

	def validate_charge_data(self):
		if not self.charge_type:
			frappe.throw(_("Charge type is required"))
		if self.charge_type not in _ALLOWED_CHARGE_TYPES:
			frappe.throw(
				_("Charge type must be one of: {0}.").format(", ".join(sorted(_ALLOWED_CHARGE_TYPES))),
				title=_("Invalid charge type"),
			)
		if not self.revenue_calculation_method:
			frappe.throw(_("Calculation method is required"))
		if not self.unit_rate or flt(self.unit_rate) <= 0:
			frappe.throw(_("Rate must be greater than 0"))
		if not self.currency:
			frappe.throw(_("Currency is required"))

	def _apply_cost_unit_break_rate(self):
		"""When Cost Unit Breaks are on, override unit_rate from matching Charge Unit Break tier."""
		if not cint(getattr(self, "cost_use_unit_breaks", 0)):
			return
		if not _charge_reference_is_persistable(self):
			return
		applicable = _resolve_unit_break_rate(
			self,
			flt(self.quantity),
			"Cost",
			unit_type=getattr(self, "unit_type", None),
		)
		if not applicable:
			return
		self.unit_rate = flt(applicable.get("unit_rate", 0))
		if applicable.get("currency"):
			self.currency = applicable.get("currency")

	def calculate_charge_amount(self):
		"""Recalculate base amount, discount amount and total amount from rate, quantity and method."""
		self._apply_cost_unit_break_rate()
		rate = flt(self.unit_rate)
		qty = flt(self.quantity)

		if self.revenue_calculation_method == "Per Unit":
			self.base_amount = rate * qty
		elif self.revenue_calculation_method in ("Flat Rate", "Fixed Amount"):
			self.base_amount = rate
		elif self.revenue_calculation_method == "Percentage":
			self.base_amount = rate * (qty * 0.01) if qty else 0
		else:
			self.base_amount = flt(self.base_amount)

		base = flt(self.base_amount)
		if self.discount_percentage and base:
			self.discount_amount = base * (flt(self.discount_percentage) / 100.0)
		else:
			self.discount_amount = 0

		self.total_amount = (
			flt(self.base_amount)
			- flt(self.discount_amount)
			+ flt(self.surcharge_amount)
		)

	def calculate_allocated_amount(self):
		"""Row-level allocated amount from total × allocation %; parent fills the per-target table."""
		pct = flt(self.allocation_percentage)
		if pct > 0:
			self.allocated_amount = flt(self.total_amount) * (pct / 100.0)
		else:
			self.allocated_amount = 0

	def update_charge_status(self):
		if not self.charge_status or self.charge_status == "Draft":
			if flt(self.total_amount) > 0:
				self.charge_status = "Calculated"


def _match_cost_tariff_rate(tariff_name, item_code, service_type=None):
	"""Find cost tariff rate; prefer service_type match, then fall back to item-only."""
	if not tariff_name or not item_code:
		return None
	match = _find_tariff_rate_match(tariff_name, item_code, service_type, is_revenue=False)
	if not match and service_type:
		match = _find_tariff_rate_match(tariff_name, item_code, None, is_revenue=False)
	return match


def _normalize_consolidation_rate_data(rate_data):
	"""Drop calculation_method values this child table does not support."""
	method = (rate_data.get("calculation_method") or "Per Unit") or ""
	if method not in _CONSOLIDATION_CALC_METHODS:
		rate_data = dict(rate_data)
		rate_data["calculation_method"] = None
	return rate_data


def _cost_unit_breaks_for_tariff_rate(tariff_rate_name):
	"""Return Cost Charge Unit Break rows for a Tariff Charge line."""
	if not tariff_rate_name or not frappe.db.exists("DocType", "Charge Unit Break"):
		return []
	return frappe.get_all(
		"Charge Unit Break",
		filters={
			"reference_doctype": "Tariff Charge",
			"reference_no": tariff_rate_name,
			"type": "Cost",
		},
		fields=["unit_type", "unit_break", "unit_rate", "currency"],
		order_by="unit_break asc",
	) or []


def _pick_unit_break_tier(unit_breaks, comparison_qty):
	"""Pick highest Cost/Selling unit-break tier whose threshold ≤ comparison_qty."""
	if not unit_breaks:
		return None
	sorted_desc = sorted(unit_breaks, key=lambda x: flt(x.get("unit_break", 0)), reverse=True)
	for row in sorted_desc:
		if flt(comparison_qty) >= flt(row.get("unit_break", 0)):
			return row
	return sorted(unit_breaks, key=lambda x: flt(x.get("unit_break", 0)))[0]


def sync_tariff_cost_unit_breaks_on_consolidation_charges(parent_doc):
	"""Copy Cost Unit Breaks from Cost Tariff onto saved consolidation charge rows."""
	for ch in parent_doc.get("consolidation_charges") or []:
		if not cint(getattr(ch, "use_tariff_in_cost", 0)):
			continue
		if not getattr(ch, "cost_tariff", None) or not getattr(ch, "item_code", None):
			continue
		match = _match_cost_tariff_rate(
			ch.cost_tariff, ch.item_code, getattr(ch, "service_type", None)
		)
		if not match:
			continue
		_rate_data, rate_row, _parentfield = match
		_copy_tariff_unit_breaks_to_charge(ch, rate_row, "Cost")


@frappe.whitelist()
def fetch_cost_tariff_rate(tariff_name, item_code, service_type=None):
	"""Return normalized cost tariff rate_data for a consolidation charge row, or None."""
	match = _match_cost_tariff_rate(tariff_name, item_code, service_type)
	if not match:
		return None
	rate_data, rate_row, _parentfield = match
	out = _normalize_consolidation_rate_data(dict(rate_data or {}))
	rate_name = getattr(rate_row, "name", None)
	out["tariff_rate_name"] = rate_name
	has_breaks = _tariff_rate_has_unit_breaks(rate_name, "Cost")
	out["has_cost_unit_breaks"] = 1 if has_breaks else 0
	out["unit_breaks"] = _cost_unit_breaks_for_tariff_rate(rate_name) if has_breaks else []
	return out
