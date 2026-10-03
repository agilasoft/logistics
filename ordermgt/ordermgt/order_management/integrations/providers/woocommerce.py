# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""WooCommerce REST API wc/v3."""

from __future__ import annotations

from urllib.parse import urlencode

from ordermgt.order_management.integrations.base import ChannelAdapter
from ordermgt.order_management.integrations.common import as_list, blank_order, first, map_status
from ordermgt.order_management.integrations.registry import register

WOO_STATUS = {
	"pending": "unpaid",
	"on-hold": "unpaid",
	"failed": "cancelled",
	"processing": "ready",
	"completed": "delivered",
	"cancelled": "cancelled",
	"refunded": "return",
}


def parse_woo_order(raw: dict) -> dict:
	shipping = raw.get("shipping") or {}
	billing = raw.get("billing") or {}
	items = []
	for row in as_list(raw.get("line_items")):
		items.append(
			{
				"seller_sku": first(row, "sku", default="") or "",
				"platform_item_id": str(first(row, "product_id", default="") or ""),
				"variant_id": str(first(row, "variation_id", default="") or ""),
				"item_name": first(row, "name", default="") or "",
				"qty": first(row, "quantity", default=0) or 0,
				"price": first(row, "price", default=0) or 0,
			}
		)
	meta_tracking = ""
	for meta in as_list(raw.get("meta_data")):
		if meta.get("key") in ("_tracking_number", "tracking_number"):
			meta_tracking = str(meta.get("value") or "")
	return blank_order(
		external_order_id=str(raw.get("id") or ""),
		platform_status=str(raw.get("status") or ""),
		status=map_status(raw.get("status"), WOO_STATUS),
		origin_platform="woocommerce",
		buyer_name=" ".join(part for part in [shipping.get("first_name"), shipping.get("last_name")] if part) or billing.get("first_name") or "",
		phone=billing.get("phone") or "",
		address_line=" ".join(part for part in [shipping.get("address_1"), shipping.get("address_2")] if part),
		city=shipping.get("city") or "",
		state=shipping.get("state") or "",
		country=shipping.get("country") or "",
		postal_code=shipping.get("postcode") or "",
		currency=raw.get("currency") or "",
		grand_total=raw.get("total") or 0,
		payment_method=raw.get("payment_method_title") or raw.get("payment_method") or "",
		is_cod=1 if str(raw.get("payment_method") or "").lower() == "cod" else 0,
		ordered_at=raw.get("date_created"),
		tracking_no=meta_tracking,
		items=items,
		raw=raw,
	)


def parse_woo_orders(payload) -> list:
	return [parse_woo_order(row) for row in as_list(payload) if isinstance(row, dict)]


def woo_stock_body(qty) -> dict:
	return {"manage_stock": True, "stock_quantity": int(qty)}


@register
class WooCommerceAdapter(ChannelAdapter):
	platform = "WooCommerce"

	def _url(self, path, extra=None) -> str:
		base = self.cred("api_url").rstrip("/")
		params = {
			"consumer_key": self.cred("app_key") or self.cred("api_key"),
			"consumer_secret": self.cred("app_secret"),
		}
		if extra:
			params.update(extra)
		return f"{base}/wp-json/wc/v3{path}?{urlencode(params)}"

	def fetch_orders(self, since=None) -> list:
		extra = {"per_page": 50, "orderby": "modified", "order": "desc"}
		if since:
			extra["modified_after"] = since
		return parse_woo_orders(self.call("GET", self._url("/orders", extra)))

	def fetch_order(self, external_order_id: str) -> dict | None:
		payload = self.call("GET", self._url(f"/orders/{external_order_id}"))
		return parse_woo_order(payload) if isinstance(payload, dict) else None

	def fetch_listings(self) -> list:
		products = as_list(self.call("GET", self._url("/products", {"per_page": 50})))
		listings = []
		for product in products:
			variations = as_list(product.get("variations"))
			if variations and product.get("type") == "variable":
				for variation_id in variations:
					if isinstance(variation_id, dict):
						row = variation_id
					else:
						row = {"id": variation_id, "sku": product.get("sku")}
					listings.append(_woo_listing(product, row))
			else:
				listings.append(_woo_listing(product, product))
		return listings

	def push_product(self, item: dict) -> dict:
		body = {
			"name": item.get("listing_title"),
			"sku": item.get("seller_sku"),
			"regular_price": str(item.get("selling_price") or ""),
			"weight": str(item.get("weight") or ""),
			"manage_stock": True,
		}
		if item.get("image_url"):
			body["images"] = [{"src": item["image_url"]}]
		if item.get("platform_item_id"):
			self.call("PUT", self._url(f"/products/{item['platform_item_id']}"), json=body)
			return {"updated": True}
		if not item.get("listing_title") or item.get("selling_price") in (None, "") or not item.get("weight"):
			return {"skipped": "WooCommerce create requires title, price, and weight"}
		self.call("POST", self._url("/products"), json=body)
		return {"created": True}

	def push_stock(self, updates: list) -> dict:
		pushed = 0
		for row in updates:
			target = row.get("variant_id") if row.get("variant_id") not in (None, "", "0", 0) else row.get("platform_item_id")
			if not target:
				continue
			path = f"/products/{row.get('platform_item_id')}/variations/{row['variant_id']}" if row.get("variant_id") not in (None, "", "0", 0) else f"/products/{target}"
			self.call("PUT", self._url(path), json=woo_stock_body(row.get("qty") or 0))
			pushed += 1
		return {"pushed": pushed}

	def push_fulfillment(self, order: dict) -> dict:
		self.call("PUT", self._url(f"/orders/{order.get('external_order_id')}"), json={"status": "completed"})
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		if not isinstance(body, dict) or not body.get("id"):
			return {"orders": []}
		return {"orders": [parse_woo_order(body)]}


def _woo_listing(product, row) -> dict:
	images = as_list(product.get("images"))
	return {
		"seller_sku": row.get("sku") or product.get("sku") or "",
		"platform_item_id": str(product.get("id") or ""),
		"variant_id": str(row.get("id") or "") if row is not product else "",
		"listing_title": product.get("name") or "",
		"selling_price": row.get("regular_price") or row.get("price") or product.get("regular_price"),
		"weight": row.get("weight") or product.get("weight"),
		"image_url": (images[0] or {}).get("src") if images else "",
		"raw": product,
	}
