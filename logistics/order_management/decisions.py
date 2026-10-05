# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Pure decisions for marketplace import, dedup, and available-to-sell."""

from __future__ import annotations

DIRECT_ORIGINS = {
	"shopee": "Shopee",
	"lazada": "Lazada",
	"tiktok": "TikTok Shop",
	"tiktok shop": "TikTok Shop",
	"facebook": "Facebook",
	"instagram": "Facebook",
	"meta": "Facebook",
	"woocommerce": "WooCommerce",
	"woo": "WooCommerce",
	"shopify": "Shopify",
}

RELEASE_STATUSES = {
	"Ready to Ship": {"ready"},
	"Paid": {"paid", "ready"},
}

ORDER_LABELS = {
	"unpaid": "New",
	"paid": "New",
	"ready": "Released",
	"shipped": "Shipped",
	"delivered": "Delivered",
	"cancelled": "Cancelled",
	"return": "Returned",
}


def available_to_sell(on_hand, allocated, safety) -> float:
	"""On-hand minus open releases minus channel safety stock, floored at zero."""
	qty = float(on_hand or 0) - float(allocated or 0) - float(safety or 0)
	if qty < 0:
		return 0.0
	return qty


def stock_should_push(previous, new) -> bool:
	if previous is None or previous == "":
		return True
	return abs(float(previous) - float(new)) > 0.0001


def pancake_should_skip(origin, direct_platforms) -> bool:
	"""Skip a Pancake copy when the customer already syncs that marketplace directly."""
	mapped = DIRECT_ORIGINS.get((origin or "").strip().lower())
	if not mapped:
		return False
	return mapped in set(direct_platforms or [])


def ship_to_summary(order: dict) -> str:
	parts = [
		order.get("buyer_name"),
		order.get("phone"),
		order.get("address_line"),
		order.get("city"),
		order.get("state"),
		order.get("postal_code"),
		order.get("country"),
	]
	return "\n".join(str(part).strip() for part in parts if part)


def cust_reference(platform: str, external_order_id: str, prefix: str = "") -> str:
	ref = f"{prefix}{platform}:{external_order_id}"
	return ref[:140]


def line_mappings(items, sku_to_item: dict):
	lines = []
	unmapped = []
	for item in items or []:
		sku = (item.get("seller_sku") or "").strip()
		warehouse_item = sku_to_item.get(sku) if sku else None
		lines.append({**item, "seller_sku": sku, "warehouse_item": warehouse_item, "mapped": bool(warehouse_item)})
		if not warehouse_item:
			unmapped.append(sku or item.get("item_name") or "?")
	return lines, unmapped


def plan_import(
	*,
	order: dict,
	import_on_status: str,
	unmapped: list,
	has_contract: bool,
	existing: dict | None = None,
	skip_pancake: bool = False,
) -> dict:
	"""Decide what an incoming marketplace order should do to warehouse documents.

	``existing`` may include ``release_order``, ``inbound_order``, and ``pick_posted``.
	A second sync of the same order never sets ``create_release`` when a release exists.
	"""
	existing = existing or {}
	status = (order.get("status") or "").strip().lower()
	release_order = existing.get("release_order")
	inbound_order = existing.get("inbound_order")
	pick_posted = bool(existing.get("pick_posted"))

	result = {
		"action": "record",
		"order_status": ORDER_LABELS.get(status, "New"),
		"hold_reason": None,
		"create_release": False,
		"create_inbound": False,
		"cancel_release": False,
	}

	if skip_pancake:
		result["action"] = "skip"
		return result

	if status == "cancelled":
		result["order_status"] = "Cancelled"
		if release_order and not pick_posted:
			result["action"] = "cancel"
			result["cancel_release"] = True
		elif release_order and pick_posted:
			result["action"] = "hold"
			result["order_status"] = "On Hold"
			result["hold_reason"] = "Already picked"
		return result

	if status == "return":
		result["order_status"] = "Returned"
		if unmapped or not has_contract:
			return _hold(result, unmapped, has_contract)
		if inbound_order:
			result["action"] = "update"
			return result
		result["action"] = "inbound"
		result["create_inbound"] = True
		return result

	if status in ("shipped", "delivered"):
		result["order_status"] = ORDER_LABELS[status]
		result["action"] = "update" if release_order else "record"
		return result

	allowed = RELEASE_STATUSES.get(import_on_status or "Ready to Ship", RELEASE_STATUSES["Ready to Ship"])
	if status not in allowed:
		result["order_status"] = "New"
		result["action"] = "record"
		return result

	if release_order:
		result["action"] = "update"
		result["order_status"] = "Released"
		return result

	if unmapped or not has_contract:
		return _hold(result, unmapped, has_contract)

	result["action"] = "release"
	result["order_status"] = "Released"
	result["create_release"] = True
	return result


def _hold(result: dict, unmapped: list, has_contract: bool) -> dict:
	result["action"] = "hold"
	result["order_status"] = "On Hold"
	result["create_release"] = False
	result["create_inbound"] = False
	if not has_contract:
		result["hold_reason"] = "Missing warehouse contract"
	else:
		skus = ", ".join(unmapped) if unmapped else "?"
		result["hold_reason"] = f"Unmapped SKU: {skus}"
	return result
