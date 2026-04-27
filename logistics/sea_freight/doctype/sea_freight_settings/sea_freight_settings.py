# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SeaFreightSettings(Document):
	def validate(self):
		self.validate_container_deposit_accounts()

	def validate_container_deposit_accounts(self):
		for fname, label in (
			("container_deposit_pending_refund_account", _("CD Pending Refund Request")),
			("container_deposit_ar_shipping_lines_account", _("AR-Shipping Lines")),
		):
			acc = self.get(fname)
			if not acc:
				continue
			if not frappe.db.exists("Account", acc):
				frappe.throw(_("Account {0} does not exist for field {1}.").format(acc, label))
		ar = self.get("container_deposit_ar_shipping_lines_account")
		if ar:
			at = frappe.db.get_value("Account", ar, "account_type")
			if at != "Receivable":
				frappe.throw(
					_("AR-Shipping Lines must be a Receivable account."),
					title=_("Sea Freight Settings"),
				)
