# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Log in on a marketplace and return the Sales Channel connection fields.

The dialog never asks for a marketplace password. ``start_connect`` opens the
platform authorize page. The guest callback exchanges the code and posts the
result back to the form. Tokens stay out of the callback URL.
"""

from __future__ import annotations

import json
import secrets
import time
from urllib.parse import urlencode

from logistics.order_management.integrations.providers.facebook import connect_facebook, facebook_authorize_url
from logistics.order_management.integrations.providers.lazada import connect_lazada, lazada_authorize_url
from logistics.order_management.integrations.providers.pancake import DEFAULT_HOST as PANCAKE_HOST
from logistics.order_management.integrations.providers.pancake import map_pancake_account
from logistics.order_management.integrations.providers.shopee import connect_shopee, shopee_authorize_url
from logistics.order_management.integrations.providers.shopify import connect_shopify, shopify_authorize_url
from logistics.order_management.integrations.providers.tiktok import connect_tiktok, tiktok_authorize_url
from logistics.order_management.integrations.providers.woocommerce import map_woo_account, woo_authorize_url

STATE_TTL = 600
CACHE_PREFIX = "order-management-connect|"

REQUIRED_FIELDS = {
	"Shopee": ("partner_id", "app_secret"),
	"Lazada": ("app_key", "app_secret"),
	"TikTok Shop": ("app_key", "app_secret"),
	"Shopify": ("api_url", "app_key", "app_secret"),
	"Facebook": ("app_key", "app_secret"),
	"WooCommerce": ("api_url",),
}

PLATFORMS = tuple(REQUIRED_FIELDS)


def put_state(store, state, data, now, ttl=STATE_TTL):
	store[state] = {"expires": now + ttl, "data": data}


def pop_state(store, state, now):
	"""Return the state payload once. Missing, expired, and reused states are rejected."""
	row = store.get(state)
	if not row:
		return None
	store.pop(state, None)
	if row.get("expires", 0) < now:
		return None
	return row.get("data")


def finish_connect(platform, credentials, query, http, redirect_url="", timestamp=None):
	credentials = credentials or {}
	query = query or {}
	if platform == "Shopee":
		return connect_shopee(credentials, query, http, timestamp=timestamp)
	if platform == "Lazada":
		return connect_lazada(credentials, query, http, timestamp_ms=timestamp)
	if platform == "TikTok Shop":
		return connect_tiktok(credentials, query, http, timestamp=timestamp)
	if platform == "Shopify":
		return connect_shopify(credentials, query, http)
	if platform == "Facebook":
		return connect_facebook(credentials, query, http, redirect_url)
	if platform == "WooCommerce":
		account = map_woo_account(credentials, query)
		if not account["fields"].get("app_key") or not account["fields"].get("app_secret"):
			raise ValueError("WooCommerce did not return an API key")
		return account
	raise ValueError("Unsupported platform")


def authorize_url(platform, credentials, redirect_url, state, timestamp=None):
	credentials = credentials or {}
	if platform == "Shopee":
		return shopee_authorize_url(
			credentials.get("partner_id"),
			credentials.get("app_secret"),
			redirect_url,
			credentials.get("api_url") or "https://partner.shopeemobile.com",
			timestamp,
		)
	if platform == "Lazada":
		return lazada_authorize_url(credentials.get("app_key"), redirect_url)
	if platform == "TikTok Shop":
		return tiktok_authorize_url(credentials.get("app_key"), state)
	if platform == "Shopify":
		return shopify_authorize_url(credentials.get("api_url"), credentials.get("app_key"), redirect_url, state)
	if platform == "Facebook":
		return facebook_authorize_url(credentials.get("app_key"), redirect_url, state)
	if platform == "WooCommerce":
		return woo_authorize_url(
			credentials.get("api_url"),
			_woo_return_url(redirect_url, state),
			_callback_base(redirect_url),
			state,
		)
	raise ValueError("Unsupported platform")


def result_page(payload) -> str:
	safe = json.dumps(payload).replace("<", "\\u003c")
	title = "Connected" if payload.get("ok") else "Connection failed"
	message = payload.get("error") or "You can close this window."
	return f"""<!DOCTYPE html>
<html><head><title>{title}</title></head>
<body><p>{_escape(message if not payload.get("ok") else "Connected. You can close this window.")}</p>
<script>
var payload = {safe};
if (window.opener) {{
  window.opener.postMessage({{source: "order-management-connect", payload: payload}}, window.location.origin);
}}
window.close();
</script></body></html>"""


def _escape(value) -> str:
	return (
		str(value)
		.replace("&", "&amp;")
		.replace("<", "&lt;")
		.replace(">", "&gt;")
	)


def _callback_base(redirect_url: str) -> str:
	base = redirect_url.split("?", 1)[0]
	return base


def _woo_return_url(redirect_url: str, state: str) -> str:
	return _callback_base(redirect_url) + "?" + urlencode({"woo_return": 1, "state": state})


def _require_login():
	import frappe

	if frappe.session.user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)


def _cache_key(state: str) -> str:
	return CACHE_PREFIX + state


def _cache_put(state, data, now=None):
	import frappe

	now = time.time() if now is None else now
	record = {"expires": now + STATE_TTL, "data": data}
	frappe.cache.set_value(_cache_key(state), record, expires_in_sec=STATE_TTL)


def _cache_get(state):
	import frappe

	record = frappe.cache.get_value(_cache_key(state))
	if not record:
		return None
	if record.get("expires", 0) < time.time():
		frappe.cache.delete_value(_cache_key(state))
		return None
	return record


def _cache_pop(state):
	import frappe

	record = _cache_get(state)
	frappe.cache.delete_value(_cache_key(state))
	if not record:
		return None
	return record.get("data")


def _loads(value):
	if isinstance(value, str) and value:
		try:
			return json.loads(value)
		except Exception:
			return {}
	return value or {}


def _redirect_for(state: str) -> str:
	from frappe.utils import get_url

	return get_url("/api/method/logistics.order_management.connect.callback") + "?" + urlencode({"state": state})


def _html_response(html: str):
	import frappe

	frappe.response["type"] = "download"
	frappe.response["filename"] = "connect.html"
	frappe.response["filecontent"] = html.encode("utf-8")
	frappe.response["content_type"] = "text/html"
	frappe.response["display_content_as"] = "inline"


def _missing_fields(platform, credentials) -> list:
	required = REQUIRED_FIELDS.get(platform) or ()
	return [field for field in required if not credentials.get(field)]


def start_connect(platform, credentials=None):
	import frappe

	_require_login()
	credentials = _loads(credentials)
	if platform not in PLATFORMS:
		frappe.throw("Choose a platform")
	missing = _missing_fields(platform, credentials)
	if missing:
		frappe.throw("Enter " + ", ".join(missing))
	state = secrets.token_urlsafe(24)
	kept = {field: credentials.get(field) for field in REQUIRED_FIELDS[platform]}
	if credentials.get("api_url") and "api_url" not in kept:
		kept["api_url"] = credentials.get("api_url")
	if credentials.get("region"):
		kept["region"] = credentials.get("region")
	_cache_put(
		state,
		{"platform": platform, "credentials": kept, "user": frappe.session.user},
	)
	redirect_url = _redirect_for(state)
	return {
		"state": state,
		"authorize_url": authorize_url(platform, kept, redirect_url, state),
	}


def connect_result(state):
	import frappe

	_require_login()
	record = _cache_get(state)
	if not record:
		return {"ok": False, "error": "This connection expired. Start again."}
	data = record.get("data") or {}
	if data.get("user") and data.get("user") != frappe.session.user:
		frappe.throw("Login required", frappe.PermissionError)
	if not data.get("result"):
		return {"ok": False, "pending": True, "state": state}
	frappe.cache.delete_value(_cache_key(state))
	return data["result"]


def list_pancake_shops(api_key, api_url=None):
	from logistics.order_management.integrations.http import request

	_require_login()
	if not api_key:
		import frappe

		frappe.throw("Enter api_key")
	host = str(api_url or PANCAKE_HOST).rstrip("/")
	try:
		payload = request("GET", f"{host}/shops", params={"api_key": api_key})
	except Exception as exc:
		import frappe

		frappe.throw(f"Pancake did not return shops: {exc}")
	return map_pancake_account(api_key, payload)


def callback():
	import frappe

	form = _merged_form()
	if frappe.request and frappe.request.method == "POST":
		_accept_woo_keys(form)
		return
	state = form.get("state") or form.get("user_id")
	if form.get("woo_return"):
		_html_response(_woo_return_page(state))
		return
	data = _cache_pop(state) if state else None
	if not data or data.get("result"):
		_html_response(result_page({"ok": False, "error": "This connection expired. Start again."}))
		return
	redirect_url = _redirect_for(state)
	try:
		from logistics.order_management.integrations.http import request

		payload = finish_connect(data["platform"], data["credentials"], form, request, redirect_url)
	except ValueError as exc:
		_html_response(result_page({"ok": False, "error": str(exc)}))
		return
	except Exception:
		frappe.log_error(title="Order Management connect")
		_html_response(result_page({"ok": False, "error": "Could not finish the platform login."}))
		return
	_html_response(result_page(payload))


def _merged_form():
	import frappe

	form = {key: frappe.form_dict.get(key) for key in frappe.form_dict.keys()}
	request = getattr(frappe, "request", None)
	if request is not None:
		try:
			body = request.get_json(silent=True) or {}
		except Exception:
			body = {}
		if isinstance(body, dict):
			form.update(body)
	return form


def _accept_woo_keys(form):
	import frappe

	state = form.get("user_id") or form.get("state")
	record = _cache_get(state)
	if not record:
		frappe.response["message"] = {"ok": False}
		return
	data = record.get("data") or {}
	if data.get("platform") != "WooCommerce":
		frappe.response["message"] = {"ok": False}
		return
	result = map_woo_account(data.get("credentials") or {}, form)
	if not result["fields"].get("app_key") or not result["fields"].get("app_secret"):
		frappe.response["message"] = {"ok": False}
		return
	data["result"] = result
	_cache_put(state, data)
	frappe.response["message"] = {"ok": True}


def _woo_return_page(state):
	record = _cache_get(state) if state else None
	data = (record or {}).get("data") or {}
	if data.get("result"):
		_cache_pop(state)
		return result_page(data["result"])
	return result_page({"ok": False, "pending": True, "state": state or ""})


# Whitelist after the functions exist. Importing frappe stays inside the calls above
# so unit tests can import the URL and state helpers without a site.
def _whitelist():
	import frappe

	globals()["start_connect"] = frappe.whitelist()(start_connect)
	globals()["connect_result"] = frappe.whitelist()(connect_result)
	globals()["list_pancake_shops"] = frappe.whitelist()(list_pancake_shops)
	globals()["callback"] = frappe.whitelist(allow_guest=True, methods=["GET", "POST"])(callback)


try:
	_whitelist()
except ImportError:
	pass
