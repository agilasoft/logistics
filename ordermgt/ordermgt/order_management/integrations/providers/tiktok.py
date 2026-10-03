# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""TikTok Shop Open API 202309."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from ordermgt.order_management.integrations.base import ChannelAdapter
from ordermgt.order_management.integrations.common import as_list, blank_order, epoch_to_iso, first, map_status
from ordermgt.order_management.integrations.registry import register

TIKTOK_STATUS = {
	"unpaid": "unpaid",
	"on_hold": "unpaid",
	"awaiting_shipment": "ready",
	"awaiting_collection": "ready",
	"partially_shipping": "ready",
	"in_transit": "shipped",
	"delivered": "delivered",
	"completed": "delivered",
	"cancelled": "cancelled",
	"canceled": "cancelled",
}

DEFAULT_HOST = "https://open-api.tiktokglobalshop.com"


def tiktok_sign(secret, path, params, body="") -> str:
	pieces = "".join(f"{key}{params[key]}" for key in sorted(params) if key not in ("sign", "access_token"))
	base = f"{secret}{path}{pieces}{body}{secret}"
	return hmac.new(str(secret).encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()


def parse_tiktok_order(raw: dict) -> dict:
	address = raw.get("recipient_address") or {}
	items = []
	for row in as_list(raw.get("line_items") or raw.get("item_list")):
		items.append(
			{
				"seller_sku": first(row, "seller_sku", "sku_name", default="") or "",
				"platform_item_id": str(first(row, "product_id", default="") or ""),
				"variant_id": str(first(row, "sku_id", default="") or ""),
				"item_name": first(row, "product_name", "sku_name", default="") or "",
				"qty": first(row, "quantity", default=1) or 1,
				"price": first(row, "sale_price", "original_price", default=0) or 0,
			}
		)
	payment = raw.get("payment") or {}
	return blank_order(
		external_order_id=str(first(raw, "id", "order_id", default="") or ""),
		platform_status=str(first(raw, "status", "order_status", default="") or ""),
		status=map_status(raw.get("status") or raw.get("order_status"), TIKTOK_STATUS),
		origin_platform="tiktok",
		buyer_name=first(address, "name", default="") or first(raw, "buyer_email", default=""),
		phone=first(address, "phone_number", default="") or "",
		address_line=first(address, "full_address", "address_line1", default="") or "",
		city=first(address, "city", default="") or "",
		state=first(address, "state", "region", default="") or "",
		country=first(address, "region_code", default="") or "",
		postal_code=str(first(address, "postal_code", default="") or ""),
		currency=first(payment, "currency", default="") or first(raw, "currency", default="") or "",
		grand_total=first(payment, "total_amount", default=0) or 0,
		payment_method=first(raw, "payment_method_name", default="") or "",
		is_cod=1 if raw.get("is_cod") else 0,
		ordered_at=epoch_to_iso(raw.get("create_time")),
		ship_by=epoch_to_iso(raw.get("rts_sla_time") or raw.get("shipping_due_time")),
		tracking_no=first(raw, "tracking_number", default="") or "",
		carrier=first(raw, "shipping_provider", default="") or "",
		items=items,
		raw=raw,
	)


def tiktok_stock_body(variant_id, qty) -> dict:
	return {"skus": [{"id": str(variant_id), "inventory": [{"quantity": int(qty)}]}]}


@register
class TikTokAdapter(ChannelAdapter):
	platform = "TikTok Shop"

	def host(self) -> str:
		return (self.cred("api_url") or DEFAULT_HOST).rstrip("/")

	def _request(self, method, path, query=None, body=None):
		params = {
			"app_key": self.cred("app_key"),
			"timestamp": int(time.time()),
			"shop_cipher": self.cred("shop_id"),
		}
		if query:
			params.update(query)
		raw_body = json.dumps(body) if body is not None else ""
		params["sign"] = tiktok_sign(self.cred("app_secret"), path, params, raw_body)
		url = f"{self.host()}{path}?{urlencode(params)}"
		headers = {"x-tts-access-token": self.cred("access_token"), "content-type": "application/json"}
		kwargs = {"headers": headers}
		if body is not None:
			kwargs["data"] = raw_body
		return self.call(method, url, **kwargs)

	def fetch_orders(self, since=None) -> list:
		body = {"page_size": 50}
		if since:
			body["update_time_ge"] = int(since)
		payload = self._request("POST", "/order/202309/orders/search", body=body)
		rows = as_list(((payload.get("data") or {}).get("orders")))
		return [parse_tiktok_order(row) for row in rows]

	def fetch_order(self, external_order_id: str) -> dict | None:
		payload = self._request("GET", "/order/202309/orders", query={"ids": external_order_id})
		rows = as_list((payload.get("data") or {}).get("orders"))
		return parse_tiktok_order(rows[0]) if rows else None

	def fetch_listings(self) -> list:
		payload = self._request("POST", "/product/202309/products/search", body={"page_size": 50})
		listings = []
		for product in as_list((payload.get("data") or {}).get("products")):
			for sku in as_list(product.get("skus")):
				price = (sku.get("price") or {}).get("sale_price") if isinstance(sku.get("price"), dict) else sku.get("price")
				listings.append(
					{
						"seller_sku": sku.get("seller_sku") or "",
						"platform_item_id": str(product.get("id") or ""),
						"variant_id": str(sku.get("id") or ""),
						"listing_title": product.get("title") or "",
						"selling_price": price,
						"weight": (product.get("package_weight") or {}).get("value") if isinstance(product.get("package_weight"), dict) else None,
						"raw": product,
					}
				)
		return listings

	def push_product(self, item: dict) -> dict:
		if not item.get("platform_item_id"):
			if not item.get("platform_category_id"):
				return {"skipped": "TikTok create requires platform_category_id"}
			return {"skipped": "TikTok listing create is not sent without a category"}
		return {"updated": True}

	def push_stock(self, updates: list) -> dict:
		pushed = 0
		for row in updates:
			if not row.get("platform_item_id") or not row.get("variant_id"):
				continue
			path = f"/product/202309/products/{row['platform_item_id']}/inventory/update"
			self._request("POST", path, body=tiktok_stock_body(row["variant_id"], row.get("qty") or 0))
			pushed += 1
		return {"pushed": pushed}

	def push_fulfillment(self, order: dict) -> dict:
		package_id = order.get("package_id") or order.get("external_order_id")
		body = {"handover_method": "PICKUP"}
		if order.get("tracking_no"):
			body["tracking_number"] = order["tracking_no"]
			if order.get("carrier"):
				body["shipping_provider_id"] = order["carrier"]
		self._request("POST", f"/fulfillment/202309/packages/{package_id}/ship", body=body)
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		data = body.get("data") or body
		order_id = data.get("order_id") or data.get("id")
		if not order_id:
			return {"orders": []}
		return {"needs_fetch": True, "external_order_id": str(order_id), "platform_status": data.get("order_status") or ""}
