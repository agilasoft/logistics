# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Pancake POS (https://pos.pages.fm/api/v1).

Auth is the ``api_key`` query parameter. Social inbox orders (Facebook,
Instagram, Zalo) arrive here. ``origin_platform`` is taken from the order
source so a shop that is also connected directly is not released twice.
"""

from __future__ import annotations

from urllib.parse import urlencode

from logistics.order_management.integrations.base import ChannelAdapter
from logistics.order_management.integrations.common import as_list, blank_order, first, map_status
from logistics.order_management.integrations.registry import register

PANCAKE_STATUS = {
	"new": "paid",
	"0": "paid",
	"confirmed": "ready",
	"1": "ready",
	"shipping": "shipped",
	"shipped": "shipped",
	"2": "shipped",
	"done": "delivered",
	"delivered": "delivered",
	"3": "delivered",
	"cancelled": "cancelled",
	"canceled": "cancelled",
	"4": "cancelled",
	"returned": "return",
	"return": "return",
	"5": "return",
}

DEFAULT_HOST = "https://pos.pages.fm/api/v1"

ORIGIN_WORDS = (
	("shopee", "shopee"),
	("lazada", "lazada"),
	("tiktok", "tiktok"),
	("facebook", "facebook"),
	("instagram", "facebook"),
	("zalo", "pos"),
	("woocommerce", "woocommerce"),
	("shopify", "shopify"),
)


def pancake_origin(raw: dict) -> str:
	source = raw.get("order_source") or raw.get("source") or raw.get("marketplace") or {}
	if isinstance(source, dict):
		text = " ".join(str(source.get(key) or "") for key in ("name", "code", "platform", "type"))
	else:
		text = str(source or raw.get("source_name") or "")
	lower = text.lower()
	for needle, origin in ORIGIN_WORDS:
		if needle in lower:
			return origin
	return "pos"


def parse_pancake_order(raw: dict) -> dict:
	address = raw.get("shipping_address") or raw.get("address") or {}
	if isinstance(address, str):
		address = {"address": address}
	items = []
	for row in as_list(raw.get("items") or raw.get("line_items")):
		items.append(
			{
				"seller_sku": str(first(row, "sku", "custom_id", "variation_id", "product_id", default="") or ""),
				"platform_item_id": str(first(row, "product_id", default="") or ""),
				"variant_id": str(first(row, "variation_id", default="") or ""),
				"item_name": first(row, "name", "product_name", default="") or "",
				"qty": first(row, "quantity", "qty", default=0) or 0,
				"price": first(row, "price", "retail_price", default=0) or 0,
			}
		)
	status_name = first(raw, "status_name", "status", default="")
	return blank_order(
		external_order_id=str(first(raw, "id", "order_id", default="") or ""),
		platform_status=str(status_name or ""),
		status=map_status(status_name, PANCAKE_STATUS, default="unpaid"),
		origin_platform=pancake_origin(raw),
		buyer_name=first(address, "full_name", "name", default="") or first(raw, "customer_name", default="") or "",
		phone=first(address, "phone_number", "phone", default="") or first(raw, "customer_phone", default="") or "",
		address_line=first(address, "address", "full_address", default="") or "",
		city=first(address, "province", "city", default="") or "",
		state=first(address, "district", default="") or "",
		country="VN",
		postal_code=str(first(address, "commune", default="") or ""),
		grand_total=first(raw, "total", "total_price", default=0) or 0,
		payment_method=str(first(raw, "payment_method", default="") or ""),
		is_cod=1 if raw.get("cod") or raw.get("customer_pay_fee") else 0,
		ordered_at=first(raw, "inserted_at", "created_at", default=None),
		tracking_no=first(raw, "tracking_number", "tracking_no", default="") or "",
		carrier=first(raw, "partner_name", "shipping_partner", default="") or "",
		items=items,
		raw=raw,
	)


def parse_pancake_orders(payload) -> list:
	if isinstance(payload, list):
		rows = payload
	else:
		rows = as_list((payload or {}).get("data") or (payload or {}).get("orders") or payload)
	return [parse_pancake_order(row) for row in rows if isinstance(row, dict)]


def pancake_stock_body(variant_id, qty, warehouse_id=None) -> dict:
	body = {"variation_id": variant_id, "stock": int(qty)}
	if warehouse_id:
		body["warehouse_id"] = warehouse_id
	return body


@register
class PancakeAdapter(ChannelAdapter):
	platform = "Pancake"

	def host(self) -> str:
		return (self.cred("api_url") or DEFAULT_HOST).rstrip("/")

	def _params(self, extra=None):
		params = {"api_key": self.cred("api_key") or self.cred("access_token")}
		if extra:
			params.update(extra)
		return params

	def _url(self, path, extra=None) -> str:
		return f"{self.host()}{path}?{urlencode(self._params(extra))}"

	def fetch_orders(self, since=None) -> list:
		extra = {"page": 1, "page_size": 50}
		if since:
			extra["from_date"] = since
		payload = self.call("GET", self._url(f"/shops/{self.cred('shop_id')}/orders", extra))
		return parse_pancake_orders(payload)

	def fetch_order(self, external_order_id: str) -> dict | None:
		payload = self.call("GET", self._url(f"/shops/{self.cred('shop_id')}/orders/{external_order_id}"))
		data = payload.get("data") if isinstance(payload, dict) else payload
		if isinstance(data, dict):
			return parse_pancake_order(data)
		return None

	def fetch_listings(self) -> list:
		payload = self.call("GET", self._url(f"/shops/{self.cred('shop_id')}/products", {"page": 1, "page_size": 50}))
		rows = payload.get("data") if isinstance(payload, dict) else payload
		listings = []
		for product in as_list(rows):
			variations = as_list(product.get("variations")) or [product]
			for variation in variations:
				listings.append(
					{
						"seller_sku": str(first(variation, "custom_id", "sku", "id", default="") or first(product, "custom_id", default="") or ""),
						"platform_item_id": str(product.get("id") or ""),
						"variant_id": str(variation.get("id") or ""),
						"listing_title": product.get("name") or "",
						"selling_price": variation.get("retail_price") or product.get("price"),
						"weight": product.get("weight"),
						"image_url": (as_list(product.get("images")) or [None])[0],
						"raw": product,
					}
				)
		return listings

	def push_product(self, item: dict) -> dict:
		if item.get("platform_item_id"):
			return {"updated": True}
		if not item.get("listing_title") or item.get("selling_price") in (None, "") or not item.get("weight"):
			return {"skipped": "Pancake create requires title, price, and weight"}
		body = {
			"name": item["listing_title"],
			"weight": item["weight"],
			"custom_id": item.get("seller_sku"),
			"variations": [
				{
					"custom_id": item.get("seller_sku"),
					"retail_price": item["selling_price"],
				}
			],
		}
		if item.get("image_url"):
			body["images"] = [item["image_url"]]
		created = self.call("POST", self._url(f"/shops/{self.cred('shop_id')}/products"), json=body)
		return {"created": True, "response": created}

	def push_stock(self, updates: list) -> dict:
		pushed = 0
		warehouse_id = self.cred("location_id")
		for row in updates:
			variant_id = row.get("variant_id")
			product_id = row.get("platform_item_id")
			if not variant_id or not product_id:
				continue
			body = pancake_stock_body(variant_id, row.get("qty") or 0, warehouse_id)
			self.call(
				"PUT",
				self._url(f"/shops/{self.cred('shop_id')}/products/{product_id}/update_stock"),
				json=body,
			)
			pushed += 1
		return {"pushed": pushed}

	def push_fulfillment(self, order: dict) -> dict:
		body = {"status": "shipping"}
		if order.get("tracking_no"):
			body["tracking_number"] = order["tracking_no"]
		self.call(
			"PUT",
			self._url(f"/shops/{self.cred('shop_id')}/orders/{order.get('external_order_id')}"),
			json=body,
		)
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		raw = body.get("data") or body.get("order") or body
		if not isinstance(raw, dict) or not (raw.get("id") or raw.get("order_id")):
			return {"orders": []}
		return {"orders": [parse_pancake_order(raw)]}
