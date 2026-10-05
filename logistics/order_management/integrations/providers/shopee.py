# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shopee Open API v2."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

from logistics.order_management.integrations.base import ChannelAdapter
from logistics.order_management.integrations.common import as_list, blank_order, epoch_to_iso, first, map_status
from logistics.order_management.integrations.registry import register

SHOPEE_STATUS = {
	"unpaid": "unpaid",
	"invoice_pending": "unpaid",
	"ready_to_ship": "ready",
	"processed": "ready",
	"retry_ship": "ready",
	"shipped": "shipped",
	"to_confirm_receive": "shipped",
	"completed": "delivered",
	"in_cancel": "cancelled",
	"cancelled": "cancelled",
	"to_return": "return",
}

DEFAULT_HOST = "https://partner.shopeemobile.com"


def shopee_sign(partner_id, path, timestamp, access_token, shop_id, partner_key) -> str:
	base = f"{partner_id}{path}{timestamp}{access_token}{shop_id}"
	return hmac.new(str(partner_key).encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()


def shopee_auth_sign(partner_id, path, timestamp, partner_key) -> str:
	base = f"{partner_id}{path}{timestamp}"
	return hmac.new(str(partner_key).encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()


def shopee_authorize_url(partner_id, partner_key, redirect_url, host=DEFAULT_HOST, timestamp=None) -> str:
	timestamp = int(time.time()) if timestamp is None else int(timestamp)
	path = "/api/v2/shop/auth_partner"
	params = {
		"partner_id": partner_id,
		"timestamp": timestamp,
		"sign": shopee_auth_sign(partner_id, path, timestamp, partner_key),
		"redirect": redirect_url,
	}
	return f"{str(host).rstrip('/')}{path}?{urlencode(params)}"


def shopee_token_url(partner_id, partner_key, host=DEFAULT_HOST, timestamp=None) -> str:
	timestamp = int(time.time()) if timestamp is None else int(timestamp)
	path = "/api/v2/auth/token/get"
	params = {
		"partner_id": partner_id,
		"timestamp": timestamp,
		"sign": shopee_auth_sign(partner_id, path, timestamp, partner_key),
	}
	return f"{str(host).rstrip('/')}{path}?{urlencode(params)}"


def shopee_shop_info_url(partner_id, partner_key, access_token, shop_id, host=DEFAULT_HOST, timestamp=None) -> str:
	timestamp = int(time.time()) if timestamp is None else int(timestamp)
	path = "/api/v2/shop/get_shop_info"
	params = {
		"partner_id": partner_id,
		"timestamp": timestamp,
		"access_token": access_token,
		"shop_id": shop_id,
		"sign": shopee_sign(partner_id, path, timestamp, access_token, shop_id, partner_key),
	}
	return f"{str(host).rstrip('/')}{path}?{urlencode(params)}"


def map_shopee_account(credentials, token_payload, shop_info, shop_id) -> dict:
	response = (token_payload or {}).get("response") or token_payload or {}
	info = (shop_info or {}).get("response") or shop_info or {}
	region = str(info.get("region") or credentials.get("region") or "").lower()
	fields = {
		"platform": "Shopee",
		"partner_id": credentials.get("partner_id") or "",
		"app_secret": credentials.get("app_secret") or "",
		"shop_id": str(shop_id or info.get("shop_id") or ""),
		"region": region,
		"access_token": response.get("access_token") or "",
		"refresh_token": response.get("refresh_token") or "",
	}
	if info.get("shop_name"):
		fields["channel_name"] = info.get("shop_name")
	return {"ok": True, "platform": "Shopee", "fields": fields, "choices": []}


def connect_shopee(credentials, query, http, timestamp=None) -> dict:
	code = (query or {}).get("code")
	shop_id = (query or {}).get("shop_id")
	if not code or not shop_id:
		raise ValueError("Shopee did not return a shop")
	partner_id = credentials.get("partner_id")
	partner_key = credentials.get("app_secret")
	host = credentials.get("api_url") or DEFAULT_HOST
	token_payload = http(
		"POST",
		shopee_token_url(partner_id, partner_key, host, timestamp),
		json={
			"code": code,
			"shop_id": int(shop_id) if str(shop_id).isdigit() else shop_id,
			"partner_id": int(partner_id) if str(partner_id).isdigit() else partner_id,
		},
	)
	response = (token_payload or {}).get("response") or {}
	access_token = response.get("access_token")
	if not access_token:
		raise ValueError("Shopee did not return an access token")
	shop_info = http(
		"GET",
		shopee_shop_info_url(partner_id, partner_key, access_token, shop_id, host, timestamp),
	)
	return map_shopee_account(credentials, token_payload, shop_info, shop_id)


def parse_shopee_order(raw: dict) -> dict:
	address = raw.get("recipient_address") or {}
	items = []
	for row in as_list(raw.get("item_list")):
		sku = first(row, "model_sku", "item_sku", default="")
		items.append(
			{
				"seller_sku": sku,
				"platform_item_id": str(first(row, "item_id", default="") or ""),
				"variant_id": str(first(row, "model_id", default="") or ""),
				"item_name": first(row, "item_name", "model_name", default=""),
				"qty": first(row, "model_quantity_purchased", "quantity", default=0) or 0,
				"price": first(row, "model_discounted_price", "model_original_price", default=0) or 0,
			}
		)
	package = (as_list(raw.get("package_list")) or [{}])[0]
	payment = str(first(raw, "payment_method", default="") or "")
	return blank_order(
		external_order_id=str(first(raw, "order_sn", default="") or ""),
		platform_status=str(first(raw, "order_status", default="") or ""),
		status=map_status(raw.get("order_status"), SHOPEE_STATUS),
		origin_platform="shopee",
		buyer_name=first(address, "name", default="") or first(raw, "buyer_username", default=""),
		phone=first(address, "phone", default="") or "",
		address_line=first(address, "full_address", default="") or "",
		city=first(address, "city", default="") or "",
		state=first(address, "state", default="") or "",
		country=first(address, "region", default="") or "",
		postal_code=str(first(address, "zipcode", default="") or ""),
		currency=first(raw, "currency", default="") or "",
		grand_total=first(raw, "total_amount", default=0) or 0,
		payment_method=payment,
		is_cod=1 if raw.get("cod") or payment.upper() == "COD" else 0,
		ordered_at=epoch_to_iso(raw.get("create_time")),
		ship_by=epoch_to_iso(raw.get("ship_by_date")),
		tracking_no=first(package, "tracking_number", default="") or "",
		carrier=first(package, "shipping_carrier", default="") or "",
		items=items,
		raw=raw,
	)


def shopee_stock_body(item_id, model_id, qty) -> dict:
	row = {"seller_stock": [{"stock": int(qty)}]}
	if model_id not in (None, "", 0, "0"):
		row["model_id"] = int(model_id)
	return {"item_id": int(item_id), "stock_list": [row]}


@register
class ShopeeAdapter(ChannelAdapter):
	platform = "Shopee"

	def host(self) -> str:
		return (self.cred("api_url") or DEFAULT_HOST).rstrip("/")

	def _signed(self, path, extra=None):
		timestamp = int(time.time())
		partner_id = self.cred("partner_id")
		shop_id = self.cred("shop_id")
		token = self.cred("access_token")
		sign = shopee_sign(partner_id, path, timestamp, token, shop_id, self.cred("app_secret"))
		params = {
			"partner_id": partner_id,
			"timestamp": timestamp,
			"access_token": token,
			"shop_id": shop_id,
			"sign": sign,
		}
		if extra:
			params.update(extra)
		return f"{self.host()}{path}?{urlencode(params)}"

	def fetch_orders(self, since=None) -> list:
		time_from = int(since) if since else int(time.time()) - 2 * 86400
		cursor = ""
		sns = []
		for _ in range(10):
			url = self._signed(
				"/api/v2/order/get_order_list",
				{
					"time_range_field": "update_time",
					"time_from": time_from,
					"time_to": int(time.time()),
					"page_size": 50,
					"cursor": cursor,
					"response_optional_fields": "order_status",
				},
			)
			payload = self.call("GET", url)
			response = payload.get("response") or {}
			for row in as_list(response.get("order_list")):
				if row.get("order_sn"):
					sns.append(row["order_sn"])
			if not response.get("more"):
				break
			cursor = response.get("next_cursor") or ""
			if not cursor:
				break
		orders = []
		for index in range(0, len(sns), 50):
			chunk = sns[index : index + 50]
			detail = self.call(
				"GET",
				self._signed(
					"/api/v2/order/get_order_detail",
					{
						"order_sn_list": ",".join(chunk),
						"response_optional_fields": "item_list,recipient_address,total_amount,payment_method,package_list",
					},
				),
			)
			for raw in as_list((detail.get("response") or {}).get("order_list")):
				orders.append(parse_shopee_order(raw))
		return orders

	def fetch_order(self, external_order_id: str) -> dict | None:
		detail = self.call(
			"GET",
			self._signed(
				"/api/v2/order/get_order_detail",
				{
					"order_sn_list": external_order_id,
					"response_optional_fields": "item_list,recipient_address,total_amount,payment_method,package_list",
				},
			),
		)
		rows = as_list((detail.get("response") or {}).get("order_list"))
		return parse_shopee_order(rows[0]) if rows else None

	def fetch_listings(self) -> list:
		url = self._signed("/api/v2/product/get_item_list", {"offset": 0, "page_size": 50, "item_status": "NORMAL"})
		payload = self.call("GET", url)
		ids = [row.get("item_id") for row in as_list((payload.get("response") or {}).get("item") or (payload.get("response") or {}).get("item_list")) if row.get("item_id")]
		if not ids:
			return []
		info = self.call("GET", self._signed("/api/v2/product/get_item_base_info", {"item_id_list": ",".join(str(i) for i in ids)}))
		listings = []
		for item in as_list((info.get("response") or {}).get("item_list")):
			models = as_list(item.get("model") or item.get("models"))
			if not models:
				models = [{"model_sku": item.get("item_sku"), "model_id": 0, "price_info": item.get("price_info")}]
			for model in models:
				price_info = as_list(model.get("price_info") or item.get("price_info"))
				price = (price_info[0] or {}).get("current_price") if price_info else None
				listings.append(
					{
						"seller_sku": first(model, "model_sku", default="") or first(item, "item_sku", default=""),
						"platform_item_id": str(item.get("item_id") or ""),
						"variant_id": str(model.get("model_id") or ""),
						"listing_title": item.get("item_name") or "",
						"selling_price": price,
						"weight": item.get("weight"),
						"raw": item,
					}
				)
		return listings

	def push_product(self, item: dict) -> dict:
		if not item.get("platform_category_id") and not item.get("platform_item_id"):
			return {"skipped": "Shopee create requires platform_category_id"}
		if item.get("platform_item_id"):
			body = shopee_stock_body(item["platform_item_id"], item.get("variant_id"), item.get("qty") or 0)
			return {"updated": True, "stock": body}
		return {"skipped": "Shopee listing create needs an existing item id or category"}

	def push_stock(self, updates: list) -> dict:
		sent = []
		for row in updates:
			if not row.get("platform_item_id"):
				continue
			body = shopee_stock_body(row["platform_item_id"], row.get("variant_id"), row.get("qty") or 0)
			self.call("POST", self._signed("/api/v2/product/update_stock"), json=body)
			sent.append(body)
		return {"pushed": len(sent)}

	def push_fulfillment(self, order: dict) -> dict:
		body = {"order_sn": order.get("external_order_id")}
		if order.get("tracking_no"):
			body["tracking_number"] = order["tracking_no"]
		self.call("POST", self._signed("/api/v2/logistics/ship_order"), json=body)
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		data = body.get("data") or body
		order_sn = data.get("ordersn") or data.get("order_sn")
		if not order_sn:
			return {"orders": []}
		return {
			"needs_fetch": True,
			"external_order_id": order_sn,
			"platform_status": data.get("status") or "",
		}
