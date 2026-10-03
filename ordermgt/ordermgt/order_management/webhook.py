# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe

from ordermgt.order_management.integrations.registry import get_adapter
from ordermgt.order_management.integrations.sanitize import verify_signature
from ordermgt.order_management.sync import credentials_from_channel, import_normalized_order

BASE64_HEADERS = ("x-shopify-hmac-sha256", "x-wc-webhook-signature")
SIGNATURE_HEADERS = BASE64_HEADERS + ("x-hub-signature-256", "x-shopee-signature", "authorization")


@frappe.whitelist(allow_guest=True)
def handle(platform=None, channel=None):
	channel_name = channel or frappe.form_dict.get("channel")
	if not channel_name:
		frappe.throw("Sales Channel is required")
	doc = frappe.get_doc("Sales Channel", channel_name)
	if not doc.enabled:
		frappe.throw("Sales Channel is disabled")

	raw = frappe.request.get_data() or b""
	headers = {key.lower(): value for key, value in (frappe.request.headers or {}).items()}
	secret = ""
	for field in ("webhook_secret", "app_secret"):
		try:
			secret = doc.get_password(field, raise_exception=False) or ""
		except Exception:
			secret = ""
		if secret:
			break
	header_name = next((name for name in SIGNATURE_HEADERS if headers.get(name)), "")
	header_value = headers.get(header_name, "")
	encoding = "base64" if header_name in BASE64_HEADERS else "hex"
	if not verify_signature(secret, raw, header_value, encoding):
		frappe.throw("Invalid webhook signature", frappe.AuthenticationError)

	body = frappe.parse_json(raw) if raw else {}
	adapter = get_adapter(doc.platform, credentials_from_channel(doc))
	parsed = adapter.parse_webhook(headers, body if isinstance(body, dict) else {})
	orders = list(parsed.get("orders") or [])
	if parsed.get("needs_fetch") and parsed.get("external_order_id"):
		fetched = adapter.fetch_order(parsed["external_order_id"])
		if fetched:
			orders.append(fetched)

	results = []
	for order in orders:
		results.append(import_normalized_order(doc, order))
	return {"received": len(results), "results": results}
