# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from logistics.pricing_center.api_parts.calculation_engine import get_available_methods
from logistics.pricing_center.doctype.tariff.tariff_rate_rows import (
	tariff_charge_calculation_method,
	tariff_charge_unit_rate,
)
from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage


def _normalize_tariff_api_service_filter(service_type):
	"""Map legacy API labels (e.g. Air Freight) to canonical service keys."""
	if not service_type:
		return None
	s = (service_type if isinstance(service_type, str) else str(service_type)).strip()
	aliases = {
		"Air Freight": "air",
		"Sea Freight": "sea",
		"Transport": "transport",
		"Warehousing": "warehousing",
		"Customs": "custom",
		"Air": "air",
		"Sea": "sea",
	}
	if s in aliases:
		return aliases[s]
	return canonical_charge_service_type_for_storage(s)


class Tariff(Document):
	def validate(self):
		self.validate_tariff_type()
		self.validate_dates()
		self.calculate_total_rates()

	def validate_tariff_type(self):
		"""Validate tariff type and required fields."""
		if self.tariff_type == "Customer" and not self.customer:
			frappe.throw(_("Customer is required for Customer tariff"))

		if self.tariff_type == "Customer Group" and not self.customer_group:
			frappe.throw(_("Customer Group is required for Customer Group tariff"))

		if self.tariff_type == "Territory" and not self.territory:
			frappe.throw(_("Territory is required for Territory tariff"))

		if self.tariff_type == "Specific Customers":
			if not self.customers or len(self.customers) == 0:
				frappe.throw(_("At least one customer is required for Specific Customers tariff"))

		if self.tariff_type == "Agent" and not self.agent:
			frappe.throw(_("Freight Agent is required for Agent tariff"))

	def validate_dates(self):
		"""Validate tariff validity dates."""
		if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
			frappe.throw(_("Valid To date cannot be earlier than Valid From date"))

	def calculate_total_rates(self):
		"""Count unified ``rates`` (Tariff Charge) rows."""
		self.total_rates = len(self.rates) if self.rates else 0

	def get_available_calculators(self, service_type):
		"""Get available calculation methods for a service type."""
		return get_available_methods(service_type)

	def get_rate_summary(self):
		"""Get summary of all rates in this tariff."""
		breakdown = {"air_freight": 0, "sea_freight": 0, "transport": 0, "warehouse": 0, "customs": 0}
		for row in self.rates or []:
			c = canonical_charge_service_type_for_storage(getattr(row, "service_type", "") or "")
			if c == "air":
				breakdown["air_freight"] += 1
			elif c == "sea":
				breakdown["sea_freight"] += 1
			elif c == "transport":
				breakdown["transport"] += 1
			elif c == "warehousing":
				breakdown["warehouse"] += 1
			elif c == "custom":
				breakdown["customs"] += 1
		breakdown["total"] = self.total_rates
		return breakdown


@frappe.whitelist()
def get_tariff_rates(tariff_name, service_type=None):
	"""Get rates from a tariff, optionally filtered by service type (legacy labels supported)."""
	tariff = frappe.get_doc("Tariff", tariff_name)

	if not tariff.is_active:
		frappe.throw(_("Tariff {0} is not active").format(tariff_name))

	want = _normalize_tariff_api_service_filter(service_type)
	out = []
	label_by_canon = {
		"air": "Air Freight",
		"sea": "Sea Freight",
		"transport": "Transport",
		"warehousing": "Warehousing",
		"custom": "Customs",
	}
	for rate in tariff.rates or []:
		row_c = canonical_charge_service_type_for_storage(getattr(rate, "service_type", "") or "")
		if want and row_c != want:
			continue
		api_label = label_by_canon.get(row_c) or (rate.service_type or "")
		out.append(
			{
				"service_type": api_label,
				"rate_name": getattr(rate, "item_name", None) or getattr(rate, "item_code", None),
				"calculation_method": tariff_charge_calculation_method(rate),
				"rate_value": tariff_charge_unit_rate(rate),
				"currency": rate.currency,
				"valid_from": getattr(rate, "tariff_valid_from", None),
				"valid_to": getattr(rate, "tariff_valid_to", None),
			}
		)
	return out


@frappe.whitelist()
def get_available_calculators(service_type):
	"""Get available calculation methods for a service type."""
	return get_available_methods(service_type)


@frappe.whitelist()
def get_tariff_summary(tariff_name):
	"""Get summary of a tariff including rate counts and details."""
	try:
		tariff = frappe.get_doc("Tariff", tariff_name)

		if not tariff.is_active:
			return {"status": "error", "message": "Tariff is not active"}

		def _detail_list(rows):
			return [
				{
					"rate_name": getattr(r, "item_name", None) or getattr(r, "item_code", None),
					"calculation_method": tariff_charge_calculation_method(r),
					"rate_value": tariff_charge_unit_rate(r),
				}
				for r in rows
			]

		air_rows, sea_rows, tr_rows, wh_rows, cu_rows = [], [], [], [], []
		for r in tariff.rates or []:
			c = canonical_charge_service_type_for_storage(getattr(r, "service_type", "") or "")
			if c == "air":
				air_rows.append(r)
			elif c == "sea":
				sea_rows.append(r)
			elif c == "transport":
				tr_rows.append(r)
			elif c == "warehousing":
				wh_rows.append(r)
			elif c == "custom":
				cu_rows.append(r)

		summary = {
			"tariff_name": tariff.tariff_name,
			"tariff_type": tariff.tariff_type,
			"customer": tariff.customer if tariff.tariff_type == "Customer" else None,
			"customer_group": tariff.customer_group if tariff.tariff_type == "Customer Group" else None,
			"territory": tariff.territory if tariff.tariff_type == "Territory" else None,
			"customers": [c.customer for c in tariff.customers]
			if tariff.tariff_type == "Specific Customers" and tariff.customers
			else None,
			"agent": tariff.agent if tariff.tariff_type == "Agent" else None,
			"currency": tariff.currency,
			"valid_from": tariff.valid_from,
			"valid_to": tariff.valid_to,
			"is_active": tariff.is_active,
			"total_rates": tariff.total_rates,
			"rate_breakdown": {
				"air_freight": len(air_rows),
				"sea_freight": len(sea_rows),
				"transport": len(tr_rows),
				"warehouse": len(wh_rows),
				"customs": len(cu_rows),
			},
			"service_details": {
				"air_freight": _detail_list(air_rows),
				"sea_freight": _detail_list(sea_rows),
				"transport": _detail_list(tr_rows),
				"warehouse": _detail_list(wh_rows),
				"customs": _detail_list(cu_rows),
			},
		}

		return {"status": "success", "data": summary}

	except Exception as e:
		frappe.log_error(f"Tariff summary error: {str(e)}")
		return {"status": "error", "message": str(e)}
