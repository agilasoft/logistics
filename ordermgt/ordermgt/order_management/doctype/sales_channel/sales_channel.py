# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url


class SalesChannel(Document):
	def validate(self):
		if self.platform == "Facebook" and self.sync_orders and not self.commerce_orders_enabled:
			frappe.throw(
				_(
					"Facebook order pull stays off unless Commerce orders are enabled. "
					"Use Pancake for Facebook, Instagram, and Zalo orders, or enable Commerce orders."
				)
			)
		if self.auto_create_warehouse_job and not self.auto_submit_release_order:
			frappe.throw(_("Create Warehouse Job requires Submit Release Order."))
		if self.name and not self.name.startswith("new-"):
			slug = (self.platform or "").lower().replace(" ", "")
			self.webhook_url = get_url(
				f"/api/method/ordermgt.order_management.webhook.handle?platform={slug}&channel={self.name}"
			)
