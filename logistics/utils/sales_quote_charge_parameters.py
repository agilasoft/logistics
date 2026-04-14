# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Sales Quote Charge parameter field names and JSON normalization (quote charge rows and routing leg JSON)."""

from __future__ import annotations

import json
from typing import Any

import frappe

# Fields from Sales Quote Charge "parameter" sections (Air / Sea / common / Transport / Customs).
SALES_QUOTE_CHARGE_PARAMETER_FIELDS: tuple[str, ...] = (
	"charge_group",
	"air_house_type",
	"airline",
	"freight_agent",
	"sea_house_type",
	"freight_agent_sea",
	"shipping_line",
	"transport_mode",
	"load_type",
	"direction",
	"origin_port",
	"destination_port",
	"transport_template",
	"vehicle_type",
	"container_type",
	"location_type",
	"location_from",
	"location_to",
	"pick_mode",
	"drop_mode",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
)


def _row_val(row: Any, fieldname: str):
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def extract_sales_quote_charge_parameters(row: Any) -> dict[str, Any]:
	"""Non-empty parameter values from a Sales Quote Charge row (dict or document)."""
	out: dict[str, Any] = {}
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		val = _row_val(row, fn)
		if val is None or val == "":
			continue
		out[fn] = val
	return out


def normalize_quote_parameter_json(value: Any) -> dict[str, Any]:
	if not value:
		return {}
	if isinstance(value, dict):
		return dict(value)
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return dict(parsed) if isinstance(parsed, dict) else {}
		except Exception:
			return {}
	return {}


def lookup_quote_parameters_for_operational_charge(sales_quote: str | None, ch_row: Any) -> dict[str, Any]:
	"""Match Sales Quote Charge by item_code + service_type and return parameter dict."""
	if not sales_quote or not frappe.db.exists("Sales Quote", sales_quote):
		return {}
	item = getattr(ch_row, "item_code", None) or _row_val(ch_row, "item_code")
	st = (getattr(ch_row, "service_type", None) or _row_val(ch_row, "service_type") or "").strip()
	try:
		sq = frappe.get_doc("Sales Quote", sales_quote)
	except Exception:
		return {}
	for r in sq.get("charges") or []:
		if item and r.item_code != item:
			continue
		rst = (r.service_type or "").strip()
		if st and rst != st:
			continue
		return extract_sales_quote_charge_parameters(r)
	return {}
