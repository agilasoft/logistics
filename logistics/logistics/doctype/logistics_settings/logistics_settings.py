# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LogisticsSettings(Document):
	def validate(self):
		"""Validate temperature limits configuration"""
		self.validate_temperature_limits()
		self.validate_credit_control_rules()
		self.validate_container_deposit_accounts()
	
	def validate_temperature_limits(self):
		"""Validate that min_temp < max_temp if both are set"""
		min_temp = flt(getattr(self, "min_temp", None)) if hasattr(self, "min_temp") else None
		max_temp = flt(getattr(self, "max_temp", None)) if hasattr(self, "max_temp") else None
		
		if min_temp is not None and max_temp is not None:
			if min_temp >= max_temp:
				frappe.throw(
					_("Minimum temperature ({0}°C) must be less than maximum temperature ({1}°C).").format(
						min_temp, max_temp
					),
					title=_("Temperature Limits Validation Error")
				)

	def validate_credit_control_rules(self):
		rows = self.get("credit_control_rules") or []
		seen = set()
		for row in rows:
			dt = row.get("controlled_doctype")
			if not dt:
				continue
			if dt in seen:
				frappe.throw(_("Duplicate credit rule for DocType {0}.").format(dt))
			seen.add(dt)

	def validate_container_deposit_accounts(self):
		for fname, label in (
			("container_deposit_clearing_account", _("Deposit clearing account")),
			("container_deposit_customer_liability_account", _("Customer deposit liability account")),
			("container_deposit_forfeiture_account", _("Deposit forfeiture expense account")),
		):
			acc = self.get(fname)
			if not acc:
				continue
			if not frappe.db.exists("Account", acc):
				frappe.throw(_("Account {0} does not exist for field {1}.").format(acc, label))
		debt = self.get("container_deposit_debtors_account")
		if debt and not frappe.db.exists("Account", debt):
			frappe.throw(_("Debtors override account does not exist."))