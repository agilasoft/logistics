# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import hashlib

import frappe
from frappe.model.document import Document


class ChannelItem(Document):
	def validate(self):
		if self.sales_channel and self.seller_sku:
			key = f"{self.sales_channel}::{self.seller_sku}"
			if len(key) > 140:
				key = hashlib.sha256(key.encode("utf-8")).hexdigest()
			self.channel_sku = key
		if self.sales_channel and self.seller_sku:
			existing = frappe.db.exists(
				"Channel Item",
				{"sales_channel": self.sales_channel, "seller_sku": self.seller_sku, "name": ["!=", self.name]},
			)
			if existing:
				frappe.throw(f"Seller SKU {self.seller_sku} is already mapped on this channel")
