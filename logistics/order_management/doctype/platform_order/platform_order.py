# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import hashlib

import frappe
from frappe.model.document import Document


class PlatformOrder(Document):
	def validate(self):
		if self.sales_channel and self.external_order_id:
			key = f"{self.sales_channel}::{self.external_order_id}"
			if len(key) > 140:
				key = hashlib.sha256(key.encode("utf-8")).hexdigest()
			self.channel_order_key = key
		if self.sales_channel and self.external_order_id:
			existing = frappe.db.exists(
				"Platform Order",
				{
					"sales_channel": self.sales_channel,
					"external_order_id": self.external_order_id,
					"name": ["!=", self.name],
				},
			)
			if existing:
				frappe.throw(f"Order {self.external_order_id} is already imported on this channel")
