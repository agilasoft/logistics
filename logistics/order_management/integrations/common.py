# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared order/listing shapes used by every platform adapter."""

from __future__ import annotations

from datetime import datetime, timezone


def as_list(value):
	if value is None:
		return []
	if isinstance(value, list):
		return value
	return [value]


def first(data, *keys, default=None):
	if not isinstance(data, dict):
		return default
	for key in keys:
		if data.get(key) not in (None, ""):
			return data.get(key)
	return default


def epoch_to_iso(value):
	if value in (None, ""):
		return None
	try:
		stamp = float(value)
	except (TypeError, ValueError):
		return str(value)
	if stamp > 10_000_000_000:
		stamp = stamp / 1000.0
	return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def blank_order(**overrides) -> dict:
	order = {
		"external_order_id": "",
		"platform_status": "",
		"status": "unpaid",
		"origin_platform": "",
		"buyer_name": "",
		"phone": "",
		"address_line": "",
		"city": "",
		"state": "",
		"country": "",
		"postal_code": "",
		"currency": "",
		"grand_total": 0,
		"payment_method": "",
		"is_cod": 0,
		"ordered_at": None,
		"ship_by": None,
		"tracking_no": "",
		"carrier": "",
		"items": [],
		"raw": {},
	}
	order.update(overrides)
	return order


def map_status(raw, table, default="unpaid") -> str:
	key = str(raw or "").strip().lower().replace(" ", "_")
	return table.get(key, default)
