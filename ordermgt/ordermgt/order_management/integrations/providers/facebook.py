# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Meta catalog inventory. Order pull stays off unless commerce orders are enabled."""

from __future__ import annotations

from ordermgt.order_management.integrations.base import ChannelAdapter
from ordermgt.order_management.integrations.common import as_list, blank_order, first, map_status
from ordermgt.order_management.integrations.registry import register

GRAPH = "https://graph.facebook.com/v21.0"

FB_STATUS = {
	"created": "ready",
	"fb_processing": "ready",
	"in_progress": "ready",
	"shipped": "shipped",
	"completed": "delivered",
	"cancelled": "cancelled",
	"refunded": "return",
}


def facebook_stock_batch(updates: list) -> dict:
	requests = []
	for row in updates:
		retailer_id = row.get("seller_sku") or row.get("platform_item_id")
		if not retailer_id:
			continue
		requests.append(
			{
				"method": "UPDATE",
				"data": {
					"id": retailer_id,
					"quantity_to_sell_on_facebook": int(row.get("qty") or 0),
				},
			}
		)
	return {"item_type": "PRODUCT_ITEM", "requests": requests}


def parse_facebook_order(raw: dict) -> dict:
	state = raw.get("order_status") or {}
	if isinstance(state, dict):
		state = state.get("state") or ""
	shipping = raw.get("shipping_address") or {}
	items = []
	item_block = raw.get("items") or {}
	rows = item_block.get("data") if isinstance(item_block, dict) else item_block
	for row in as_list(rows):
		items.append(
			{
				"seller_sku": first(row, "retailer_id", "product_id", default="") or "",
				"platform_item_id": str(first(row, "id", "product_id", default="") or ""),
				"variant_id": "",
				"item_name": first(row, "product_name", "name", default="") or "",
				"qty": first(row, "quantity", default=0) or 0,
				"price": first(row, "price_per_unit", default=0) or 0,
			}
		)
	return blank_order(
		external_order_id=str(raw.get("id") or ""),
		platform_status=str(state or ""),
		status=map_status(state, FB_STATUS),
		origin_platform="facebook",
		buyer_name=first(shipping, "name", default="") or "",
		address_line=first(shipping, "street1", default="") or "",
		city=first(shipping, "city", default="") or "",
		state=first(shipping, "state", default="") or "",
		country=first(shipping, "country", default="") or "",
		postal_code=str(first(shipping, "postal_code", default="") or ""),
		items=items,
		raw=raw,
	)


@register
class FacebookAdapter(ChannelAdapter):
	platform = "Facebook"

	def _token_params(self):
		return {"access_token": self.cred("access_token")}

	def orders_enabled(self) -> bool:
		return bool(self.credentials.get("commerce_orders_enabled"))

	def fetch_orders(self, since=None) -> list:
		if not self.orders_enabled():
			return []
		catalog = self.cred("catalog_id") or self.cred("shop_id")
		payload = self.call(
			"GET",
			f"{GRAPH}/{catalog}/commerce_orders",
			params=self._token_params(),
		)
		return [parse_facebook_order(row) for row in as_list(payload.get("data") if isinstance(payload, dict) else payload)]

	def fetch_order(self, external_order_id: str) -> dict | None:
		if not self.orders_enabled():
			return None
		payload = self.call("GET", f"{GRAPH}/{external_order_id}", params=self._token_params())
		return parse_facebook_order(payload) if isinstance(payload, dict) else None

	def fetch_listings(self) -> list:
		catalog = self.cred("catalog_id") or self.cred("shop_id")
		payload = self.call("GET", f"{GRAPH}/{catalog}/products", params={**self._token_params(), "limit": 50})
		listings = []
		for row in as_list(payload.get("data") if isinstance(payload, dict) else payload):
			listings.append(
				{
					"seller_sku": row.get("retailer_id") or "",
					"platform_item_id": str(row.get("id") or ""),
					"variant_id": "",
					"listing_title": row.get("name") or "",
					"selling_price": row.get("price"),
					"image_url": row.get("image_url") or "",
					"raw": row,
				}
			)
		return listings

	def push_product(self, item: dict) -> dict:
		if not item.get("listing_title") or item.get("selling_price") in (None, ""):
			return {"skipped": "Facebook catalog update requires title and price"}
		batch = {
			"item_type": "PRODUCT_ITEM",
			"requests": [
				{
					"method": "UPDATE",
					"data": {
						"id": item.get("seller_sku"),
						"title": item.get("listing_title"),
						"price": item.get("selling_price"),
						"image_url": item.get("image_url") or "",
					},
				}
			],
		}
		catalog = self.cred("catalog_id") or self.cred("shop_id")
		self.call("POST", f"{GRAPH}/{catalog}/items_batch", params=self._token_params(), json=batch)
		return {"updated": True}

	def push_stock(self, updates: list) -> dict:
		batch = facebook_stock_batch(updates)
		if not batch["requests"]:
			return {"pushed": 0}
		catalog = self.cred("catalog_id") or self.cred("shop_id")
		self.call("POST", f"{GRAPH}/{catalog}/items_batch", params=self._token_params(), json=batch)
		return {"pushed": len(batch["requests"])}

	def push_fulfillment(self, order: dict) -> dict:
		if not self.orders_enabled():
			return {"skipped": "Facebook commerce orders are disabled"}
		body = {"status": "SHIPPED"}
		if order.get("tracking_no"):
			body["tracking_number"] = order["tracking_no"]
		self.call("POST", f"{GRAPH}/{order.get('external_order_id')}/shipments", params=self._token_params(), json=body)
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		if not self.orders_enabled():
			return {"orders": []}
		orders = []
		for entry in as_list(body.get("entry")):
			for change in as_list(entry.get("changes")):
				value = change.get("value") or {}
				if value.get("id"):
					orders.append(parse_facebook_order(value))
		return {"orders": orders}
