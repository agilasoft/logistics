# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shopify Admin REST."""

from __future__ import annotations

from logistics.order_management.integrations.base import ChannelAdapter
from logistics.order_management.integrations.common import as_list, blank_order, first
from logistics.order_management.integrations.registry import register

API_VERSION = "2024-10"


def shopify_status(raw: dict) -> str:
	if raw.get("cancelled_at"):
		return "cancelled"
	financial = str(raw.get("financial_status") or "").lower()
	fulfillment = str(raw.get("fulfillment_status") or "").lower()
	if financial in ("refunded", "partially_refunded"):
		return "return"
	if fulfillment == "fulfilled":
		return "shipped"
	if financial in ("paid", "partially_paid"):
		return "ready"
	if financial == "pending":
		return "unpaid"
	return "unpaid"


def parse_shopify_order(raw: dict) -> dict:
	shipping = raw.get("shipping_address") or raw.get("billing_address") or {}
	fulfillment = (as_list(raw.get("fulfillments")) or [{}])[0]
	items = []
	for row in as_list(raw.get("line_items")):
		items.append(
			{
				"seller_sku": first(row, "sku", default="") or "",
				"platform_item_id": str(first(row, "product_id", default="") or ""),
				"variant_id": str(first(row, "variant_id", default="") or ""),
				"item_name": first(row, "name", "title", default="") or "",
				"qty": first(row, "quantity", default=0) or 0,
				"price": first(row, "price", default=0) or 0,
			}
		)
	return blank_order(
		external_order_id=str(raw.get("id") or raw.get("name") or ""),
		platform_status=str(raw.get("financial_status") or ""),
		status=shopify_status(raw),
		origin_platform="shopify",
		buyer_name=first(shipping, "name", default="") or "",
		phone=first(shipping, "phone", default="") or "",
		address_line=" ".join(part for part in [shipping.get("address1"), shipping.get("address2")] if part),
		city=shipping.get("city") or "",
		state=shipping.get("province") or "",
		country=shipping.get("country") or "",
		postal_code=shipping.get("zip") or "",
		currency=raw.get("currency") or "",
		grand_total=raw.get("total_price") or 0,
		payment_method=str((as_list(raw.get("payment_gateway_names")) or [""])[0] or ""),
		is_cod=1 if "cod" in str((as_list(raw.get("payment_gateway_names")) or [""])[0] or "").lower() else 0,
		ordered_at=raw.get("created_at"),
		tracking_no=first(fulfillment, "tracking_number", default="") or "",
		carrier=first(fulfillment, "tracking_company", default="") or "",
		items=items,
		raw=raw,
	)


def parse_shopify_orders(payload) -> list:
	rows = payload.get("orders") if isinstance(payload, dict) else payload
	return [parse_shopify_order(row) for row in as_list(rows) if isinstance(row, dict)]


def shopify_inventory_body(inventory_item_id, location_id, qty) -> dict:
	return {
		"location_id": location_id,
		"inventory_item_id": inventory_item_id,
		"available": int(qty),
	}


@register
class ShopifyAdapter(ChannelAdapter):
	platform = "Shopify"

	def _headers(self):
		return {"X-Shopify-Access-Token": self.cred("access_token"), "Content-Type": "application/json"}

	def _url(self, path) -> str:
		base = self.cred("api_url").rstrip("/")
		return f"{base}/admin/api/{API_VERSION}{path}"

	def fetch_orders(self, since=None) -> list:
		params = {"status": "any", "limit": 50}
		if since:
			params["updated_at_min"] = since
		return parse_shopify_orders(self.call("GET", self._url("/orders.json"), headers=self._headers(), params=params))

	def fetch_order(self, external_order_id: str) -> dict | None:
		payload = self.call("GET", self._url(f"/orders/{external_order_id}.json"), headers=self._headers())
		raw = payload.get("order") if isinstance(payload, dict) else None
		return parse_shopify_order(raw) if raw else None

	def fetch_listings(self) -> list:
		payload = self.call("GET", self._url("/products.json"), headers=self._headers(), params={"limit": 50})
		listings = []
		for product in as_list(payload.get("products") if isinstance(payload, dict) else payload):
			image = (as_list(product.get("images")) or [{}])[0]
			for variant in as_list(product.get("variants")) or [{}]:
				listings.append(
					{
						"seller_sku": variant.get("sku") or "",
						"platform_item_id": str(variant.get("inventory_item_id") or product.get("id") or ""),
						"variant_id": str(variant.get("id") or ""),
						"listing_title": product.get("title") or "",
						"selling_price": variant.get("price"),
						"weight": variant.get("weight"),
						"barcode": variant.get("barcode") or "",
						"image_url": image.get("src") or "",
						"raw": product,
					}
				)
		return listings

	def push_product(self, item: dict) -> dict:
		variant = {
			"sku": item.get("seller_sku"),
			"price": str(item.get("selling_price") or ""),
			"weight": item.get("weight"),
			"inventory_management": "shopify",
		}
		if item.get("barcode"):
			variant["barcode"] = item["barcode"]
		body = {"product": {"title": item.get("listing_title"), "variants": [variant]}}
		if item.get("image_url"):
			body["product"]["images"] = [{"src": item["image_url"]}]
		if item.get("variant_id"):
			self.call(
				"PUT",
				self._url(f"/variants/{item['variant_id']}.json"),
				headers=self._headers(),
				json={"variant": variant},
			)
			return {"updated": True}
		if not item.get("listing_title") or item.get("selling_price") in (None, "") or not item.get("weight"):
			return {"skipped": "Shopify create requires title, price, and weight"}
		self.call("POST", self._url("/products.json"), headers=self._headers(), json=body)
		return {"created": True}

	def push_stock(self, updates: list) -> dict:
		location_id = self.cred("location_id")
		pushed = 0
		for row in updates:
			inventory_item_id = row.get("platform_item_id")
			if not inventory_item_id or not location_id:
				continue
			self.call(
				"POST",
				self._url("/inventory_levels/set.json"),
				headers=self._headers(),
				json=shopify_inventory_body(inventory_item_id, location_id, row.get("qty") or 0),
			)
			pushed += 1
		return {"pushed": pushed}

	def push_fulfillment(self, order: dict) -> dict:
		body = {
			"fulfillment": {
				"notify_customer": False,
				"tracking_info": {
					"number": order.get("tracking_no") or "",
					"company": order.get("carrier") or "",
				},
			}
		}
		self.call(
			"POST",
			self._url(f"/orders/{order.get('external_order_id')}/fulfillments.json"),
			headers=self._headers(),
			json=body,
		)
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		if not isinstance(body, dict) or not body.get("id"):
			return {"orders": []}
		return {"orders": [parse_shopify_order(body)]}
