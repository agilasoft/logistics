# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Helpers for Tariff unified ``rates`` (Tariff Charge) rows — used by pricing and legacy call sites."""

from __future__ import annotations

from typing import Any, Dict, Iterator, Optional

from frappe.utils import flt

from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage


def iter_tariff_charges_for_service(
	tariff_doc: Any,
	service_type: Optional[str],
) -> Iterator[Any]:
	"""Yield ``Tariff Charge`` rows whose service_type matches ``service_type`` (any label / canonical)."""
	want = canonical_charge_service_type_for_storage(service_type or "")
	for row in getattr(tariff_doc, "rates", None) or []:
		row_c = canonical_charge_service_type_for_storage(getattr(row, "service_type", None) or "")
		if not want or row_c == want:
			yield row


def tariff_charge_calculation_method(row: Any) -> str:
	return (
		(getattr(row, "revenue_calculation_method", None) or "").strip()
		or (getattr(row, "calculation_method", None) or "").strip()
		or "Per Unit"
	)


def tariff_charge_unit_rate(row: Any) -> float:
	return flt(
		getattr(row, "unit_rate", None)
		or getattr(row, "rate_value", None)
		or 0
	)


def tariff_charge_row_to_engine_dict(row: Any) -> Dict[str, Any]:
	"""Shape used by transport rate engine and similar (calculation_method + rate keys)."""
	d = row.as_dict()
	d["calculation_method"] = tariff_charge_calculation_method(row)
	d["rate"] = tariff_charge_unit_rate(row)
	return d


def tariff_charge_row_to_public_rate_dict(row: Any) -> Dict[str, Any]:
	"""API-friendly dict aligned with legacy transport/sea tariff helpers."""
	return {
		"item_code": getattr(row, "item_code", None),
		"item_name": getattr(row, "item_name", None),
		"calculation_method": tariff_charge_calculation_method(row),
		"rate": tariff_charge_unit_rate(row),
		"unit_type": getattr(row, "unit_type", None),
		"currency": getattr(row, "currency", None),
		"minimum_quantity": flt(getattr(row, "minimum_quantity", None) or 0),
		"minimum_charge": flt(getattr(row, "minimum_charge", None) or 0),
		"maximum_charge": flt(getattr(row, "maximum_charge", None) or 0),
		"base_amount": flt(getattr(row, "base_amount", None) or 0),
		"uom": getattr(row, "uom", None),
	}
