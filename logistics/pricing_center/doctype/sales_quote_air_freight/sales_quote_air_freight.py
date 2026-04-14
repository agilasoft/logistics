# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Sales Quote Air Freight child table controller.
Calculation methods and unit types (including Container, Item Count) aligned with
TransportRateCalculationEngine and charges_calculation.
"""

import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from typing import Optional, Any

from logistics.pricing_center.api_parts.transport_rate_calculation_engine import (
	TransportRateCalculationEngine,
)


class SalesQuoteAirFreight(Document):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.calculator = TransportRateCalculationEngine()
	def _calculate_per_unit_quantity(self, parent_doc: Any) -> float:
		"""Calculate quantity for Per Unit method from parent (Sales Quote) or line."""
		if not self.unit_type:
			return 1.0
		if self.unit_type == "Distance":
			return flt(parent_doc.get("total_distance", 0))
		if self.unit_type == "Weight":
			return flt(parent_doc.get("weight", 0) or parent_doc.get("total_weight", 0))
		if self.unit_type == "Chargeable Weight":
			return flt(parent_doc.get("chargeable", 0) or parent_doc.get("chargeable_weight", 0))
		if self.unit_type == "Volume":
			return flt(parent_doc.get("volume", 0) or parent_doc.get("total_volume", 0))
		if self.unit_type in ("Package", "Piece"):
			return flt(parent_doc.get("total_pieces", 0))
		if self.unit_type == "TEU":
			return flt(parent_doc.get("total_teu", 0))
		if self.unit_type == "Container":
			return flt(
				parent_doc.get("total_containers", 0)
				or parent_doc.get("total_teu", 0)
				or self.quantity
				or 0
			)
		if self.unit_type == "Item Count":
			products = getattr(parent_doc, "project_products", None) or getattr(
				parent_doc, "products", None
			) or []
			return flt(len(products)) if products else flt(self.quantity or 0)
		if self.unit_type == "Operation Time":
			return flt(parent_doc.get("total_operation_time", 0))
		return flt(self.quantity or 1)

	def _get_actual_data_from_parent(self) -> dict:
		"""Get actual data from parent (Sales Quote) for charge calculation."""
		parent_doc = self.get_parent_doc()
		line_quantity = flt(self.quantity or 0)
		actual_data = {
			"actual_quantity": line_quantity,
			"actual_weight": line_quantity if self.unit_type == "Weight" else 0,
			"actual_chargeable_weight": line_quantity if self.unit_type == "Chargeable Weight" else 0,
			"actual_volume": line_quantity if self.unit_type == "Volume" else 0,
			"actual_distance": line_quantity if self.unit_type == "Distance" else 0,
			"actual_pieces": line_quantity if self.unit_type in ("Package", "Piece") else 0,
			"actual_teu": line_quantity if self.unit_type == "TEU" else 0,
			"actual_containers": line_quantity if self.unit_type == "Container" else 0,
			"actual_item_count": line_quantity if self.unit_type == "Item Count" else 0,
			"actual_operation_time": line_quantity if self.unit_type == "Operation Time" else 0,
		}
		if parent_doc:
			products = getattr(parent_doc, "project_products", None) or getattr(
				parent_doc, "products", None
			) or []
			item_count = len(products) if products else 0
			# Use air-specific fields (air_weight, air_volume) when available
			weight = flt(
				parent_doc.get("air_weight", 0) or parent_doc.get("weight", 0)
				or parent_doc.get("total_weight", actual_data["actual_weight"])
			)
			volume = flt(
				parent_doc.get("air_volume", 0) or parent_doc.get("volume", 0)
				or parent_doc.get("total_volume", actual_data["actual_volume"])
			)
			chargeable_weight = flt(
				parent_doc.get("chargeable", 0) or parent_doc.get("chargeable_weight", 0)
			)
			actual_data.update({
				"actual_weight": weight,
				"actual_chargeable_weight": chargeable_weight,
				"actual_volume": volume,
				"actual_distance": flt(parent_doc.get("total_distance", actual_data["actual_distance"])),
				"actual_pieces": flt(parent_doc.get("total_pieces", actual_data["actual_pieces"])),
				"actual_teu": flt(parent_doc.get("total_teu", actual_data["actual_teu"])),
				"actual_containers": flt(
					parent_doc.get("total_containers", actual_data.get("actual_containers", 0))
					or flt(parent_doc.get("total_teu", 0))
				),
				"actual_item_count": item_count or actual_data.get("actual_item_count", 0),
				"actual_operation_time": flt(
					parent_doc.get("total_operation_time", actual_data["actual_operation_time"])
				),
			})
			# Ensure actual_quantity reflects the calculated quantity for engine
			qty = self._calculate_per_unit_quantity(parent_doc)
			actual_data["actual_quantity"] = qty
		return actual_data

	def get_parent_doc(self) -> Optional[Any]:
		"""Return parent Sales Quote document."""
		if getattr(self, "parent", None) and getattr(self, "parenttype", None):
			try:
				return frappe.get_doc(self.parenttype, self.parent)
			except Exception:
				pass
		return None

	def handle_tariff_data(self):
		"""Handle tariff data. Uses revenue_tariff for revenue fields, cost_tariff for cost fields (fallback: tariff)."""
		rev_tariff = getattr(self, "revenue_tariff", None) or getattr(self, "tariff", None)
		cost_tariff = getattr(self, "cost_tariff", None) or getattr(self, "tariff", None)
		if not (self.use_tariff_in_revenue or self.use_tariff_in_cost):
			return
		if not rev_tariff and not cost_tariff:
			return
		try:
			if self.use_tariff_in_revenue and rev_tariff:
				tariff_doc = frappe.get_doc("Tariff", rev_tariff)
				if tariff_doc and tariff_doc.transport_rates:
					for rate in tariff_doc.transport_rates:
						if rate.item_code == self.item_code:
							self.calculation_method = rate.calculation_method or "Per Unit"
							self.unit_rate = rate.rate or 0
							self.unit_type = rate.unit_type
							self.currency = rate.currency or "USD"
							self.minimum_quantity = rate.minimum_quantity or 0
							self.minimum_charge = rate.minimum_charge or 0
							self.maximum_charge = rate.maximum_charge or 0
							self.base_amount = rate.base_amount or 0
							break
			if self.use_tariff_in_cost and cost_tariff:
				tariff_doc = frappe.get_doc("Tariff", cost_tariff)
				if tariff_doc and tariff_doc.transport_rates:
					for rate in tariff_doc.transport_rates:
						if rate.item_code == self.item_code:
							self.cost_calculation_method = rate.calculation_method or "Per Unit"
							self.unit_cost = rate.rate or 0
							self.cost_unit_type = rate.unit_type
							self.cost_minimum_quantity = rate.minimum_quantity or 0
							self.cost_minimum_charge = rate.minimum_charge or 0
							self.cost_maximum_charge = rate.maximum_charge or 0
							self.cost_base_amount = rate.base_amount or 0
							break
		except Exception as e:
			frappe.log_error(f"Error fetching tariff data: {str(e)}")

	def calculate_quantities(self):
		"""Calculate quantity based on calculation method."""
		if not self.calculation_method:
			return
		parent_doc = self.get_parent_doc()
		if not parent_doc:
			if not self.quantity or self.quantity == 0:
				self.quantity = 1
			return
		if self.calculation_method == "Per Unit":
			self.quantity = self._calculate_per_unit_quantity(parent_doc)
		elif self.calculation_method == "Fixed Amount":
			if not self.quantity or self.quantity == 0:
				self.quantity = 1
		elif self.calculation_method == "Base Plus Additional":
			base_qty = flt(getattr(self, "base_quantity", None) or 1)
			total_qty = self._calculate_per_unit_quantity(parent_doc)
			self.quantity = max(0, total_qty - base_qty)
		elif self.calculation_method == "First Plus Additional":
			min_qty = flt(self.minimum_quantity or 0)
			total_qty = self._calculate_per_unit_quantity(parent_doc)
			self.quantity = max(0, total_qty - min_qty)
		elif self.calculation_method == "Percentage":
			self.quantity = 1
		else:
			self.quantity = flt(self.quantity or 1)

	def _prepare_revenue_rate_data(self) -> dict:
		"""Prepare rate data for revenue calculation."""
		return {
			"calculation_method": self.calculation_method,
			"rate": flt(self.unit_rate or 0),
			"unit_type": self.unit_type,
			"minimum_quantity": flt(self.minimum_quantity or 0),
			"minimum_unit_rate": flt(getattr(self, "minimum_unit_rate", None) or 0),
			"minimum_charge": flt(self.minimum_charge or 0),
			"maximum_charge": flt(self.maximum_charge or 0),
			"base_amount": flt(self.base_amount or 0),
			"base_quantity": flt(getattr(self, "base_quantity", None) or 1),
			"currency": self.currency or "USD",
			"item_code": self.item_code,
			"item_name": self.item_name,
		}

	def _prepare_cost_rate_data(self) -> dict:
		"""Prepare rate data for cost calculation."""
		return {
			"calculation_method": self.cost_calculation_method,
			"rate": flt(self.unit_cost or 0),
			"unit_type": self.cost_unit_type,
			"minimum_quantity": flt(self.cost_minimum_quantity or 0),
			"minimum_unit_rate": flt(getattr(self, "cost_minimum_unit_rate", None) or 0),
			"minimum_charge": flt(self.cost_minimum_charge or 0),
			"maximum_charge": flt(self.cost_maximum_charge or 0),
			"base_amount": flt(self.cost_base_amount or 0),
			"base_quantity": flt(getattr(self, "cost_base_quantity", None) or 1),
			"currency": getattr(self, "cost_currency", None) or "USD",
			"item_code": self.item_code,
			"item_name": self.item_name,
		}

	def _get_cost_actual_data(self) -> dict:
		"""Get actual data for cost calculation."""
		parent_doc = self.get_parent_doc()
		if not parent_doc:
			cq = flt(self.cost_quantity or 0)
			return {
				"actual_quantity": cq,
				"actual_weight": cq if self.cost_unit_type == "Weight" else 0,
				"actual_chargeable_weight": cq if self.cost_unit_type == "Chargeable Weight" else 0,
				"actual_volume": cq if self.cost_unit_type == "Volume" else 0,
				"actual_distance": cq if self.cost_unit_type == "Distance" else 0,
				"actual_pieces": cq if self.cost_unit_type in ("Package", "Piece") else 0,
				"actual_teu": cq if self.cost_unit_type == "TEU" else 0,
				"actual_containers": cq if self.cost_unit_type == "Container" else 0,
				"actual_item_count": cq if self.cost_unit_type == "Item Count" else 0,
				"actual_operation_time": cq if self.cost_unit_type == "Operation Time" else 0,
			}
		weight = flt(
			parent_doc.get("air_weight", 0) or parent_doc.get("weight", 0)
			or parent_doc.get("total_weight", 0)
		)
		volume = flt(
			parent_doc.get("air_volume", 0) or parent_doc.get("volume", 0)
			or parent_doc.get("total_volume", 0)
		)
		return {
			"actual_quantity": flt(self.cost_quantity or 0),
			"actual_weight": weight,
			"actual_chargeable_weight": flt(
				parent_doc.get("chargeable", 0) or parent_doc.get("chargeable_weight", 0)
			),
			"actual_volume": volume,
			"actual_distance": flt(parent_doc.get("total_distance", 0)),
			"actual_pieces": flt(parent_doc.get("total_pieces", 0)),
			"actual_teu": flt(parent_doc.get("total_teu", 0)),
			"actual_containers": flt(parent_doc.get("total_containers", 0) or parent_doc.get("total_teu", 0)),
			"actual_item_count": len(getattr(parent_doc, "project_products", None) or getattr(parent_doc, "products", None) or []),
			"actual_operation_time": flt(parent_doc.get("total_operation_time", 0)),
		}

	def calculate_estimated_revenue(self):
		"""Calculate estimated revenue based on calculation method."""
		if not self.calculation_method:
			self.estimated_revenue = 0
			self.revenue_calc_notes = "No calculation method specified"
			return
		if not self.unit_rate or self.unit_rate == 0:
			self.estimated_revenue = 0
			self.revenue_calc_notes = "No unit rate specified"
			return
		if self.calculation_method == "Percentage" and (not self.base_amount or self.base_amount == 0):
			self.estimated_revenue = 0
			self.revenue_calc_notes = "Base Amount is required for Percentage calculation"
			return
		try:
			rate_data = self._prepare_revenue_rate_data()
			actual_data = self._get_actual_data_from_parent()
			result = self.calculator.calculate_transport_rate(rate_data=rate_data, **actual_data)
			if result.get("success"):
				self.estimated_revenue = result.get("amount", 0)
				self.revenue_calc_notes = result.get("calculation_details", "")
			else:
				self.estimated_revenue = 0
				self.revenue_calc_notes = f"Calculation failed: {result.get('error', 'Unknown error')}"
		except Exception as e:
			frappe.log_error(f"Revenue calculation error: {str(e)}")
			self.estimated_revenue = 0
			self.revenue_calc_notes = f"Error: {str(e)}"

	def calculate_estimated_cost(self):
		"""Calculate estimated cost based on cost calculation method."""
		if not self.cost_calculation_method:
			self.estimated_cost = 0
			self.cost_calc_notes = "No cost calculation method specified"
			return
		if not self.unit_cost or self.unit_cost == 0:
			self.estimated_cost = 0
			self.cost_calc_notes = "No unit cost specified"
			return
		if self.cost_calculation_method == "Percentage" and (not self.cost_base_amount or self.cost_base_amount == 0):
			self.estimated_cost = 0
			self.cost_calc_notes = "Cost Base Amount is required for Percentage calculation"
			return
		try:
			cost_rate_data = self._prepare_cost_rate_data()
			actual_data = self._get_cost_actual_data()
			result = self.calculator.calculate_transport_rate(rate_data=cost_rate_data, **actual_data)
			if result.get("success"):
				self.estimated_cost = result.get("amount", 0)
				self.cost_calc_notes = result.get("calculation_details", "")
			else:
				self.estimated_cost = 0
				self.cost_calc_notes = f"Cost calculation failed: {result.get('error', 'Unknown error')}"
		except Exception as e:
			frappe.log_error(f"Cost calculation error: {str(e)}")
			self.estimated_cost = 0
			self.cost_calc_notes = f"Error: {str(e)}"

	def trigger_calculations(self) -> bool:
		"""Trigger all calculations - can be called from client-side."""
		try:
			self.handle_tariff_data()
			self.calculate_quantities()
			self.calculate_estimated_revenue()
			self.calculate_estimated_cost()
			return True
		except Exception as e:
			frappe.log_error(f"Error in trigger_calculations: {str(e)}")
			return False


@frappe.whitelist()
def trigger_air_freight_calculations_for_line(line_data):
	"""
	Trigger calculations for a specific air freight line.
	Called from client-side when user changes rate, calculation method, etc.

	Args:
		line_data: JSON string of line data

	Returns:
		dict with success, estimated_revenue, estimated_cost, revenue_calc_notes, cost_calc_notes
	"""
	try:
		if isinstance(line_data, str):
			line_dict = json.loads(line_data)
		else:
			line_dict = line_data

		temp_doc = frappe.new_doc("Sales Quote Air Freight")
		temp_doc.update(line_dict)

		success = temp_doc.trigger_calculations()

		if success:
			return {
				"success": True,
				"estimated_revenue": flt(temp_doc.estimated_revenue or 0),
				"estimated_cost": flt(temp_doc.estimated_cost or 0),
				"revenue_calc_notes": temp_doc.revenue_calc_notes or "",
				"cost_calc_notes": temp_doc.cost_calc_notes or "",
			}
		return {
			"success": False,
			"error": "Calculation failed",
		}
	except Exception as e:
		frappe.log_error(f"Air freight line calculation error: {str(e)}")
		return {
			"success": False,
			"error": str(e),
		}
