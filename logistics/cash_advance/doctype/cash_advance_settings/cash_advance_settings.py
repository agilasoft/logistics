# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class CashAdvanceSettings(Document):
	def validate(self):
		if not self.company:
			frappe.throw(_("Company is required."), title=_("Cash Advance Settings"))
		self.validate_ar_employee_account()

	def validate_ar_employee_account(self):
		acc = self.ar_employee_account
		if not acc:
			return
		if not frappe.db.exists("Account", acc):
			frappe.throw(_("Account {0} does not exist.").format(acc))
		acc_company = frappe.db.get_value("Account", acc, "company")
		if acc_company and acc_company != self.company:
			frappe.throw(
				_("A/R Employee account {0} does not belong to company {1}.").format(acc, self.company)
			)

	def on_update(self):
		frappe.clear_cache()

	@staticmethod
	def get_settings(company=None):
		"""Return Cash Advance Settings for the given company."""
		if not company:
			company = frappe.defaults.get_user_default("Company")
		if not company:
			return None
		try:
			settings_name = frappe.db.get_value("Cash Advance Settings", {"company": company}, "name")
			if settings_name:
				return frappe.get_doc("Cash Advance Settings", settings_name)
		except frappe.DoesNotExistError:
			pass
		return None
