# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import base64
import hashlib
import hmac

SENSITIVE = (
	"password",
	"secret",
	"token",
	"api_key",
	"authorization",
	"app_secret",
	"access_token",
	"refresh_token",
	"webhook_secret",
	"consumer_secret",
)


def sanitize(value):
	if isinstance(value, dict):
		cleaned = {}
		for key, item in value.items():
			if any(part in str(key).lower() for part in SENSITIVE):
				cleaned[key] = "***REDACTED***"
			else:
				cleaned[key] = sanitize(item)
		return cleaned
	if isinstance(value, list):
		return [sanitize(item) for item in value]
	return value


def verify_signature(secret: str, body: bytes, header_value: str, encoding: str = "hex") -> bool:
	if not secret or not header_value:
		return False
	digest = hmac.new(secret.encode("utf-8"), body or b"", hashlib.sha256)
	if encoding == "base64":
		expected = base64.b64encode(digest.digest()).decode("utf-8")
		got = header_value.strip()
	else:
		expected = digest.hexdigest()
		got = header_value.strip()
		if "=" in got:
			got = got.split("=", 1)[1]
	try:
		return hmac.compare_digest(expected, got)
	except Exception:
		return False
