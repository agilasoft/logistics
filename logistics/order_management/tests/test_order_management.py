# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import hashlib
import hmac
import unittest

from logistics.order_management.connect import authorize_url, finish_connect, pop_state, put_state, result_page
from logistics.order_management.decisions import (
	available_to_sell,
	pancake_should_skip,
	plan_import,
	stock_should_push,
)
from logistics.order_management.integrations.providers.facebook import facebook_stock_batch, parse_facebook_order
from logistics.order_management.integrations.providers.facebook import FacebookAdapter
from logistics.order_management.integrations.providers.lazada import lazada_sign, lazada_stock_payload, parse_lazada_order
from logistics.order_management.integrations.providers.pancake import map_pancake_account, pancake_origin, pancake_stock_body, parse_pancake_order
from logistics.order_management.integrations.providers.shopee import parse_shopee_order, shopee_sign, shopee_stock_body
from logistics.order_management.integrations.providers.shopify import parse_shopify_order, shopify_inventory_body, shopify_shop_host
from logistics.order_management.integrations.providers.tiktok import parse_tiktok_order, tiktok_sign, tiktok_stock_body
from logistics.order_management.integrations.providers.woocommerce import parse_woo_order, woo_stock_body
from logistics.order_management.integrations.registry import get_adapter
from logistics.order_management.integrations.sanitize import sanitize, verify_signature


def _order(status="ready", sku="SKU-1"):
	return {
		"status": status,
		"external_order_id": "EXT-1",
		"items": [{"seller_sku": sku, "qty": 1}],
	}


class TestAvailableToSell(unittest.TestCase):
	def test_subtracts_open_releases_and_safety_stock(self):
		self.assertEqual(available_to_sell(10, 3, 2), 5)

	def test_floors_at_zero(self):
		self.assertEqual(available_to_sell(1, 3, 0), 0)

	def test_on_hand_only(self):
		self.assertEqual(available_to_sell(5, 0, 0), 5)

	def test_stock_push_skips_unchanged_qty(self):
		self.assertFalse(stock_should_push(4, 4))
		self.assertTrue(stock_should_push(4, 5))
		self.assertTrue(stock_should_push(None, 0))


class TestImportPlan(unittest.TestCase):
	def test_second_sync_does_not_create_another_release(self):
		plan = plan_import(
			order=_order(),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={"release_order": "WRO-1", "pick_posted": False},
		)
		self.assertEqual(plan["action"], "update")
		self.assertFalse(plan["create_release"])

	def test_unmapped_sku_holds_and_does_not_release(self):
		plan = plan_import(
			order=_order(),
			import_on_status="Ready to Ship",
			unmapped=["SKU-1"],
			has_contract=True,
			existing={},
		)
		self.assertEqual(plan["action"], "hold")
		self.assertEqual(plan["order_status"], "On Hold")
		self.assertIn("SKU-1", plan["hold_reason"])
		self.assertFalse(plan["create_release"])

	def test_ready_mapped_order_creates_one_release(self):
		plan = plan_import(
			order=_order(),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={},
		)
		self.assertTrue(plan["create_release"])
		self.assertEqual(plan["order_status"], "Released")

	def test_paid_threshold_waits_for_ready_to_ship_only_when_configured(self):
		paid = plan_import(
			order=_order("paid"),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={},
		)
		self.assertFalse(paid["create_release"])
		released = plan_import(
			order=_order("paid"),
			import_on_status="Paid",
			unmapped=[],
			has_contract=True,
			existing={},
		)
		self.assertTrue(released["create_release"])

	def test_return_creates_inbound_once(self):
		first = plan_import(
			order=_order("return"),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={"release_order": "WRO-1"},
		)
		self.assertTrue(first["create_inbound"])
		second = plan_import(
			order=_order("return"),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={"release_order": "WRO-1", "inbound_order": "WIN-1"},
		)
		self.assertFalse(second["create_inbound"])
		self.assertEqual(second["action"], "update")

	def test_cancel_before_pick(self):
		plan = plan_import(
			order=_order("cancelled"),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={"release_order": "WRO-1", "pick_posted": False},
		)
		self.assertTrue(plan["cancel_release"])

	def test_pancake_copy_is_skipped_when_direct_channel_exists(self):
		self.assertTrue(pancake_should_skip("shopee", {"Shopee"}))
		self.assertFalse(pancake_should_skip("pos", {"Shopee"}))
		self.assertFalse(pancake_should_skip("shopee", set()))
		plan = plan_import(
			order=_order(),
			import_on_status="Ready to Ship",
			unmapped=[],
			has_contract=True,
			existing={},
			skip_pancake=True,
		)
		self.assertEqual(plan["action"], "skip")
		self.assertFalse(plan["create_release"])


class TestAdapters(unittest.TestCase):
	def test_registry_covers_named_platforms(self):
		platforms = ["Shopee", "Lazada", "TikTok Shop", "Pancake", "Facebook", "WooCommerce", "Shopify"]
		for platform in platforms:
			self.assertEqual(get_adapter(platform, {}).platform, platform)

	def test_shopee_order_and_stock(self):
		order = parse_shopee_order(
			{
				"order_sn": "201218V2Y6E59M",
				"order_status": "READY_TO_SHIP",
				"buyer_username": "buyer",
				"recipient_address": {"name": "An", "phone": "090", "full_address": "1 Le Loi", "city": "HCMC"},
				"currency": "VND",
				"total_amount": 100,
				"cod": True,
				"create_time": 1600000000,
				"item_list": [
					{
						"item_id": 11,
						"model_id": 22,
						"model_sku": "SKU-1",
						"item_name": "Shirt",
						"model_quantity_purchased": 2,
						"model_discounted_price": 50,
					}
				],
				"package_list": [{"tracking_number": "SPX1", "shipping_carrier": "SPX"}],
			}
		)
		self.assertEqual(order["status"], "ready")
		self.assertEqual(order["items"][0]["seller_sku"], "SKU-1")
		self.assertEqual(order["tracking_no"], "SPX1")
		body = shopee_stock_body(11, 22, 4)
		self.assertEqual(body["stock_list"][0]["seller_stock"][0]["stock"], 4)
		sign = shopee_sign("1", "/api/v2/order/get_order_list", 1600000000, "token", "99", "secret")
		base = "1/api/v2/order/get_order_list1600000000token99"
		expected = hmac.new(b"secret", base.encode(), hashlib.sha256).hexdigest()
		self.assertEqual(sign, expected)

	def test_lazada_order_and_stock(self):
		order = parse_lazada_order(
			{
				"order_id": 99,
				"statuses": ["ready_to_ship"],
				"address_shipping": {"first_name": "An", "phone": "090", "address1": "1 Le Loi", "city": "HCMC"},
				"price": 20,
			},
			[{"sku": "SKU-1", "name": "Shirt", "paid_price": 20, "sku_id": 5}],
		)
		self.assertEqual(order["status"], "ready")
		self.assertEqual(order["items"][0]["seller_sku"], "SKU-1")
		payload = lazada_stock_payload([{"seller_sku": "SKU-1", "qty": 3}])
		self.assertEqual(payload["Request"]["Product"]["Skus"]["Sku"][0]["Quantity"], 3)
		params = {"app_key": "1", "timestamp": "2"}
		sign = lazada_sign("/orders/get", params, "secret")
		base = "/orders/getapp_key1timestamp2"
		expected = hmac.new(b"secret", base.encode(), hashlib.sha256).hexdigest().upper()
		self.assertEqual(sign, expected)

	def test_tiktok_order_and_stock(self):
		order = parse_tiktok_order(
			{
				"id": "T1",
				"status": "AWAITING_SHIPMENT",
				"recipient_address": {"name": "An", "full_address": "1 Le Loi"},
				"line_items": [{"seller_sku": "SKU-1", "product_id": "p", "sku_id": "s", "product_name": "Shirt", "quantity": 1, "sale_price": 9}],
				"payment": {"total_amount": 9, "currency": "VND"},
			}
		)
		self.assertEqual(order["status"], "ready")
		body = tiktok_stock_body("s", 6)
		self.assertEqual(body["skus"][0]["inventory"][0]["quantity"], 6)
		sign = tiktok_sign("secret", "/order/202309/orders/search", {"app_key": "k", "timestamp": 1}, "")
		pieces = "app_keyktimestamp1"
		base = f"secret/order/202309/orders/search{pieces}secret"
		expected = hmac.new(b"secret", base.encode(), hashlib.sha256).hexdigest()
		self.assertEqual(sign, expected)

	def test_pancake_origin_dedup_and_stock(self):
		order = parse_pancake_order(
			{
				"id": 7,
				"status_name": "confirmed",
				"order_source": {"name": "Shopee"},
				"shipping_address": {"full_name": "An", "phone_number": "090", "address": "1 Le Loi"},
				"items": [{"custom_id": "SKU-1", "product_id": "p", "variation_id": "v", "quantity": 2, "price": 10}],
			}
		)
		self.assertEqual(pancake_origin(order["raw"]), "shopee")
		self.assertEqual(order["status"], "ready")
		self.assertEqual(order["items"][0]["seller_sku"], "SKU-1")
		body = pancake_stock_body("v", 8, "wh")
		self.assertEqual(body["stock"], 8)
		self.assertTrue(pancake_should_skip(order["origin_platform"], {"Shopee"}))

	def test_woocommerce_and_shopify_orders(self):
		woo = parse_woo_order(
			{
				"id": 15,
				"status": "processing",
				"billing": {"phone": "090"},
				"shipping": {"first_name": "An", "address_1": "1 Le Loi", "city": "HCMC"},
				"line_items": [{"sku": "SKU-1", "product_id": 3, "name": "Shirt", "quantity": 1, "price": 12}],
				"total": "12",
			}
		)
		self.assertEqual(woo["status"], "ready")
		self.assertEqual(woo_stock_body(4)["stock_quantity"], 4)
		shop = parse_shopify_order(
			{
				"id": 20,
				"financial_status": "paid",
				"shipping_address": {"name": "An", "address1": "1 Le Loi", "city": "HCMC"},
				"line_items": [{"sku": "SKU-1", "product_id": 8, "variant_id": 9, "name": "Shirt", "quantity": 1, "price": "15"}],
				"total_price": "15",
			}
		)
		self.assertEqual(shop["status"], "ready")
		self.assertEqual(shopify_inventory_body(9, 3, 2)["available"], 2)

	def test_facebook_stock_batch_and_disabled_orders(self):
		batch = facebook_stock_batch([{"seller_sku": "SKU-1", "qty": 4}])
		self.assertEqual(batch["requests"][0]["data"]["quantity_to_sell_on_facebook"], 4)
		order = parse_facebook_order(
			{
				"id": "fb1",
				"order_status": {"state": "CREATED"},
				"shipping_address": {"name": "An", "street1": "1 Le Loi"},
				"items": {"data": [{"retailer_id": "SKU-1", "quantity": 1, "product_name": "Shirt"}]},
			}
		)
		self.assertEqual(order["status"], "ready")
		self.assertEqual(FacebookAdapter({"commerce_orders_enabled": 0}).fetch_orders(), [])

	def test_sanitize_and_signature(self):
		cleaned = sanitize({"access_token": "secret", "order_sn": "1", "nested": {"api_key": "k"}})
		self.assertEqual(cleaned["access_token"], "***REDACTED***")
		self.assertEqual(cleaned["nested"]["api_key"], "***REDACTED***")
		self.assertEqual(cleaned["order_sn"], "1")
		body = b'{"id":1}'
		digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
		self.assertTrue(verify_signature("secret", body, f"sha256={digest}"))
		self.assertFalse(verify_signature("secret", body, "sha256=nope"))
		self.assertFalse(verify_signature("", body, digest))


class TestConnect(unittest.TestCase):
	def test_authorize_urls_hide_the_app_secret(self):
		redirect = "https://erp.example/api/method/logistics.order_management.connect.callback?state=abc"
		shopee = authorize_url(
			"Shopee",
			{"partner_id": "10", "app_secret": "partner-key-secret"},
			redirect,
			"abc",
			timestamp=1,
		)
		self.assertIn("partner_id=10", shopee)
		self.assertIn("redirect=", shopee)
		self.assertNotIn("partner-key-secret", shopee)
		sign = hmac.new(b"partner-key-secret", b"10/api/v2/shop/auth_partner1", hashlib.sha256).hexdigest()
		self.assertIn(f"sign={sign}", shopee)

		lazada = authorize_url("Lazada", {"app_key": "lk", "app_secret": "lazada-secret"}, redirect, "abc")
		self.assertIn("client_id=lk", lazada)
		self.assertNotIn("lazada-secret", lazada)

		tiktok = authorize_url("TikTok Shop", {"app_key": "tk", "app_secret": "tiktok-secret"}, redirect, "abc")
		self.assertIn("state=abc", tiktok)
		self.assertNotIn("tiktok-secret", tiktok)

		shopify = authorize_url(
			"Shopify",
			{"api_url": "my-store", "app_key": "cid", "app_secret": "shopify-secret"},
			redirect,
			"abc",
		)
		self.assertTrue(shopify.startswith("https://my-store.myshopify.com/admin/oauth/authorize?"))
		self.assertIn("state=abc", shopify)
		self.assertNotIn("shopify-secret", shopify)
		self.assertEqual(shopify_shop_host("https://my-store.myshopify.com/admin"), "https://my-store.myshopify.com")

		facebook = authorize_url("Facebook", {"app_key": "fb-app", "app_secret": "fb-secret"}, redirect, "abc")
		self.assertIn("client_id=fb-app", facebook)
		self.assertNotIn("fb-secret", facebook)

		woo = authorize_url("WooCommerce", {"api_url": "shop.example"}, redirect, "abc")
		self.assertIn("https://shop.example/wc-auth/v1/authorize?", woo)
		self.assertIn("user_id=abc", woo)
		self.assertIn("callback_url=", woo)
		self.assertNotIn("consumer_secret", woo)

	def test_state_is_single_use_and_rejects_expired(self):
		store = {}
		put_state(store, "live", {"platform": "Shopee"}, now=100, ttl=10)
		self.assertEqual(pop_state(store, "missing", 100), None)
		self.assertEqual(pop_state(store, "live", 100)["platform"], "Shopee")
		self.assertIsNone(pop_state(store, "live", 100))
		put_state(store, "old", {"platform": "Lazada"}, now=100, ttl=10)
		self.assertIsNone(pop_state(store, "old", 111))

	def test_mocked_account_payloads_map_onto_channel_fields(self):
		def http(method, url, **kwargs):
			http.calls.append((method, url, kwargs))
			if "token/get" in url and "shopee" not in url and "auth.tiktok" not in url:
				pass
			if "/api/v2/auth/token/get" in url:
				return {"response": {"access_token": "shopee-token", "refresh_token": "shopee-refresh"}}
			if "/api/v2/shop/get_shop_info" in url:
				return {"response": {"shop_name": "An Shop", "region": "VN"}}
			if "auth.lazada.com" in url:
				return {
					"access_token": "lz-token",
					"refresh_token": "lz-refresh",
					"country": "vn",
					"country_user_info": [{"seller_id": "555"}],
				}
			if "auth.tiktok-shops.com" in url:
				return {"data": {"access_token": "tt-token", "refresh_token": "tt-refresh"}}
			if "/authorization/202309/shops" in url:
				return {
					"data": {
						"shops": [
							{"cipher": "cipher-a", "name": "Alpha", "region": "VN"},
							{"cipher": "cipher-b", "name": "Beta", "region": "TH"},
						]
					}
				}
			if url.endswith("/access_token"):
				return {"access_token": "shop-token"}
			if url.endswith("/locations.json"):
				return {"locations": [{"id": 3, "name": "Main"}, {"id": 4, "name": "Overflow"}]}
			if url.endswith("/shop.json"):
				return {"shop": {"name": "My Store"}}
			if url.endswith("/oauth/access_token"):
				return {"access_token": "fb-token"}
			if "assigned_product_catalogs" in url:
				return {"data": [{"id": "cat-1", "name": "Catalog"}]}
			raise AssertionError(url)

		http.calls = []
		shopee = finish_connect(
			"Shopee",
			{"partner_id": "10", "app_secret": "secret"},
			{"code": "code-1", "shop_id": "99"},
			http,
			timestamp=1,
		)
		self.assertEqual(shopee["fields"]["shop_id"], "99")
		self.assertEqual(shopee["fields"]["access_token"], "shopee-token")
		self.assertEqual(shopee["fields"]["region"], "vn")
		self.assertEqual(shopee["fields"]["channel_name"], "An Shop")
		self.assertFalse(shopee["choices"])

		lazada = finish_connect(
			"Lazada",
			{"app_key": "lk", "app_secret": "secret"},
			{"code": "code-2"},
			http,
			timestamp=1000,
		)
		self.assertEqual(lazada["fields"]["shop_id"], "555")
		self.assertEqual(lazada["fields"]["api_url"], "https://api.lazada.vn/rest")
		self.assertEqual(lazada["fields"]["access_token"], "lz-token")

		tiktok = finish_connect(
			"TikTok Shop",
			{"app_key": "tk", "app_secret": "secret"},
			{"code": "code-3"},
			http,
			timestamp=1,
		)
		self.assertEqual(tiktok["fields"]["access_token"], "tt-token")
		self.assertNotIn("shop_id", tiktok["fields"])
		self.assertEqual([choice["id"] for choice in tiktok["choices"]], ["cipher-a", "cipher-b"])

		shopify = finish_connect(
			"Shopify",
			{"api_url": "my-store", "app_key": "cid", "app_secret": "secret"},
			{"code": "code-4"},
			http,
		)
		self.assertEqual(shopify["fields"]["api_url"], "https://my-store.myshopify.com")
		self.assertEqual(shopify["fields"]["access_token"], "shop-token")
		self.assertEqual(shopify["fields"]["channel_name"], "My Store")
		self.assertEqual(len(shopify["choices"]), 2)
		self.assertNotIn("location_id", shopify["fields"])

		facebook = finish_connect(
			"Facebook",
			{"app_key": "fb-app", "app_secret": "secret"},
			{"code": "code-5"},
			http,
			redirect_url="https://erp.example/callback?state=abc",
		)
		self.assertEqual(facebook["fields"]["catalog_id"], "cat-1")
		self.assertEqual(facebook["fields"]["commerce_orders_enabled"], 0)
		self.assertFalse(facebook["choices"])

		woo = finish_connect(
			"WooCommerce",
			{"api_url": "shop.example"},
			{"consumer_key": "ck_1", "consumer_secret": "cs_1"},
			http,
		)
		self.assertEqual(woo["fields"]["app_key"], "ck_1")
		self.assertEqual(woo["fields"]["app_secret"], "cs_1")
		self.assertEqual(woo["fields"]["api_url"], "https://shop.example")

		pancake = map_pancake_account("pos-key", {"shops": [{"id": 7, "name": "Pos Shop"}, {"id": 8, "name": "Other"}]})
		self.assertEqual(pancake["fields"]["api_key"], "pos-key")
		self.assertEqual(len(pancake["choices"]), 2)
		single = map_pancake_account("pos-key", {"data": [{"id": 7, "name": "Pos Shop"}]})
		self.assertEqual(single["fields"]["shop_id"], "7")
		self.assertFalse(single["choices"])

		page = result_page({"ok": True, "fields": {"access_token": "secret-token"}})
		self.assertIn("secret-token", page)
		self.assertNotIn("secret-token=", page)
		self.assertIn("order-management-connect", page)


if __name__ == "__main__":
	unittest.main()
