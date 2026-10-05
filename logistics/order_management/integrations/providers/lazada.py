# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lazada Open Platform."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

from logistics.order_management.integrations.base import ChannelAdapter
from logistics.order_management.integrations.common import as_list, blank_order, first, map_status
from logistics.order_management.integrations.registry import register

LAZADA_HOSTS = {
	"vn": "https://api.lazada.vn/rest",
	"th": "https://api.lazada.co.th/rest",
	"id": "https://api.lazada.co.id/rest",
	"my": "https://api.lazada.com.my/rest",
	"ph": "https://api.lazada.com.ph/rest",
	"sg": "https://api.lazada.sg/rest",
}

LAZADA_STATUS = {
	"unpaid": "unpaid",
	"pending": "ready",
	"packed": "ready",
	"repacked": "ready",
	"ready_to_ship": "ready",
	"ready_to_ship_pending": "ready",
	"shipped": "shipped",
	"delivered": "delivered",
	"canceled": "cancelled",
	"cancelled": "cancelled",
	"returned": "return",
	"failed": "return",
	"lost_by_3pl": "return",
	"damaged_by_3pl": "return",
}


LAZADA_AUTH_URL = "https://auth.lazada.com/oauth/authorize"
LAZADA_TOKEN_URL = "https://auth.lazada.com/rest/auth/token/create"


def lazada_authorize_url(app_key, redirect_url) -> str:
	params = {
		"response_type": "code",
		"force_auth": "true",
		"redirect_uri": redirect_url,
		"client_id": app_key,
	}
	return f"{LAZADA_AUTH_URL}?{urlencode(params)}"


def lazada_token_params(app_key, app_secret, code, timestamp_ms) -> dict:
	params = {
		"app_key": app_key,
		"timestamp": str(timestamp_ms),
		"sign_method": "sha256",
		"code": code,
	}
	params["sign"] = lazada_sign("/auth/token/create", params, app_secret)
	return params


def map_lazada_account(credentials, token_payload) -> dict:
	payload = token_payload or {}
	users = payload.get("country_user_info") or payload.get("country_user_info_list") or []
	seller = ""
	country = payload.get("country") or ""
	if users and isinstance(users, list):
		seller = str(users[0].get("seller_id") or users[0].get("user_id") or "")
		country = country or users[0].get("country") or ""
	if not seller:
		account = payload.get("account") or payload.get("seller_id") or ""
		seller = str(account)
	region = str(country or credentials.get("region") or "").lower()
	fields = {
		"platform": "Lazada",
		"app_key": credentials.get("app_key") or "",
		"app_secret": credentials.get("app_secret") or "",
		"access_token": payload.get("access_token") or "",
		"refresh_token": payload.get("refresh_token") or "",
		"shop_id": seller,
		"region": region,
	}
	if region in LAZADA_HOSTS:
		fields["api_url"] = LAZADA_HOSTS[region]
	return {"ok": True, "platform": "Lazada", "fields": fields, "choices": []}


def connect_lazada(credentials, query, http, timestamp_ms=None) -> dict:
	code = (query or {}).get("code")
	if not code:
		raise ValueError("Lazada did not return a login code")
	timestamp_ms = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
	params = lazada_token_params(credentials.get("app_key"), credentials.get("app_secret"), code, timestamp_ms)
	payload = http("POST", LAZADA_TOKEN_URL, data=params)
	if not (payload or {}).get("access_token"):
		raise ValueError("Lazada did not return an access token")
	return map_lazada_account(credentials, payload)


def lazada_sign(path: str, params: dict, app_secret: str) -> str:
	pieces = "".join(f"{key}{params[key]}" for key in sorted(params) if key != "sign")
	base = f"{path}{pieces}"
	return hmac.new(str(app_secret).encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest().upper()


def parse_lazada_order(raw: dict, items: list | None = None) -> dict:
	address = raw.get("address_shipping") or raw.get("address_billing") or {}
	parsed_items = []
	for row in as_list(items if items is not None else raw.get("order_items")):
		parsed_items.append(
			{
				"seller_sku": first(row, "sku", "shop_sku", "seller_sku", default="") or "",
				"platform_item_id": str(first(row, "order_item_id", "product_id", default="") or ""),
				"variant_id": str(first(row, "sku_id", default="") or ""),
				"item_name": first(row, "name", default="") or "",
				"qty": 1,
				"price": first(row, "paid_price", "item_price", default=0) or 0,
			}
		)
	status = first(raw, "statuses", default="")
	if isinstance(status, list):
		status = status[0] if status else ""
	return blank_order(
		external_order_id=str(first(raw, "order_id", "order_number", default="") or ""),
		platform_status=str(status or ""),
		status=map_status(status, LAZADA_STATUS),
		origin_platform="lazada",
		buyer_name=first(address, "first_name", default="") or first(raw, "customer_first_name", default=""),
		phone=first(address, "phone", "phone2", default="") or "",
		address_line=first(address, "address1", default="") or "",
		city=first(address, "city", default="") or "",
		state=first(address, "address3", default="") or "",
		country=first(address, "country", default="") or "",
		postal_code=str(first(address, "post_code", default="") or ""),
		currency=first(raw, "currency", default="") or "",
		grand_total=first(raw, "price", default=0) or 0,
		payment_method=first(raw, "payment_method", default="") or "",
		is_cod=1 if str(first(raw, "payment_method", default="")).lower() == "cod" else 0,
		ordered_at=first(raw, "created_at", default=None),
		ship_by=first(raw, "promised_shipping_times", default=None),
		tracking_no=first(raw, "tracking_code", default="") or "",
		items=parsed_items,
		raw=raw,
	)


def lazada_stock_payload(updates: list) -> dict:
	skus = []
	for row in updates:
		sku = row.get("seller_sku") or row.get("variant_id")
		if not sku:
			continue
		skus.append({"SellerSku": sku, "Quantity": int(row.get("qty") or 0)})
	return {"Request": {"Product": {"Skus": {"Sku": skus}}}}


@register
class LazadaAdapter(ChannelAdapter):
	platform = "Lazada"

	def host(self) -> str:
		override = self.cred("api_url")
		if override:
			return override.rstrip("/")
		region = str(self.cred("region", "vn")).lower()
		return LAZADA_HOSTS.get(region, LAZADA_HOSTS["vn"])

	def _call(self, path, extra=None, method="GET"):
		params = {
			"app_key": self.cred("app_key"),
			"timestamp": str(int(time.time() * 1000)),
			"sign_method": "sha256",
			"access_token": self.cred("access_token"),
		}
		if extra:
			params.update({key: value for key, value in extra.items() if value is not None})
		params["sign"] = lazada_sign(path, params, self.cred("app_secret"))
		url = f"{self.host()}{path}"
		if method == "GET":
			return self.call("GET", f"{url}?{urlencode(params)}")
		return self.call("POST", url, data=params)

	def fetch_orders(self, since=None) -> list:
		payload = self._call("/orders/get", {"sort_by": "updated_at", "sort_direction": "DESC", "limit": 50, "offset": 0})
		data = payload.get("data") or {}
		orders = []
		for raw in as_list(data.get("orders")):
			detail_items = self._call("/order/items/get", {"order_id": raw.get("order_id")})
			items = (detail_items.get("data") or []) if isinstance(detail_items, dict) else []
			orders.append(parse_lazada_order(raw, items))
		return orders

	def fetch_order(self, external_order_id: str) -> dict | None:
		payload = self._call("/order/get", {"order_id": external_order_id})
		raw = payload.get("data") or {}
		if not raw:
			return None
		detail_items = self._call("/order/items/get", {"order_id": external_order_id})
		return parse_lazada_order(raw, detail_items.get("data") or [])

	def fetch_listings(self) -> list:
		payload = self._call("/products/get", {"filter": "all", "limit": 50, "offset": 0})
		products = as_list((payload.get("data") or {}).get("products"))
		listings = []
		for product in products:
			for sku in as_list(product.get("skus")):
				listings.append(
					{
						"seller_sku": sku.get("SellerSku") or sku.get("seller_sku") or "",
						"platform_item_id": str(product.get("item_id") or ""),
						"variant_id": str(sku.get("SkuId") or sku.get("sku_id") or ""),
						"listing_title": product.get("attributes", {}).get("name") if isinstance(product.get("attributes"), dict) else "",
						"selling_price": sku.get("price"),
						"weight": product.get("attributes", {}).get("package_weight") if isinstance(product.get("attributes"), dict) else None,
						"raw": product,
					}
				)
		return listings

	def push_product(self, item: dict) -> dict:
		if not item.get("platform_item_id") and not item.get("platform_category_id"):
			return {"skipped": "Lazada create requires platform_category_id"}
		return {"skipped": "Lazada listing body is updated through stock and price"}

	def push_stock(self, updates: list) -> dict:
		payload = lazada_stock_payload(updates)
		if not payload["Request"]["Product"]["Skus"]["Sku"]:
			return {"pushed": 0}
		self._call("/product/price_quantity/update", {"payload": __import__("json").dumps(payload)}, method="POST")
		return {"pushed": len(payload["Request"]["Product"]["Skus"]["Sku"])}

	def push_fulfillment(self, order: dict) -> dict:
		self._call(
			"/order/rts",
			{"order_id": order.get("external_order_id"), "tracking_number": order.get("tracking_no") or ""},
			method="POST",
		)
		return {"shipped": True}

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		data = body.get("data") or body
		order_id = data.get("trade_order_id") or data.get("order_id")
		if not order_id:
			return {"orders": []}
		return {"needs_fetch": True, "external_order_id": str(order_id), "platform_status": data.get("order_status") or ""}
