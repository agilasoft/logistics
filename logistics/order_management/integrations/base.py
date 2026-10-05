# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from logistics.order_management.integrations.http import request


class ChannelError(Exception):
	pass


class ChannelAdapter:
	platform = ""

	def __init__(self, credentials: dict | None = None):
		self.credentials = credentials or {}

	def cred(self, field, default=""):
		value = self.credentials.get(field)
		return default if value in (None, "") else value

	def fetch_orders(self, since=None) -> list:
		raise NotImplementedError

	def fetch_order(self, external_order_id: str) -> dict | None:
		raise NotImplementedError

	def fetch_listings(self) -> list:
		raise NotImplementedError

	def push_product(self, item: dict) -> dict:
		raise NotImplementedError

	def push_stock(self, updates: list) -> dict:
		raise NotImplementedError

	def push_fulfillment(self, order: dict) -> dict:
		raise NotImplementedError

	def parse_webhook(self, headers: dict, body: dict) -> dict:
		raise NotImplementedError

	def call(self, method, url, **kwargs):
		try:
			return request(method, url, **kwargs)
		except Exception as exc:
			raise ChannelError(f"{self.platform} request failed: {exc}") from exc
