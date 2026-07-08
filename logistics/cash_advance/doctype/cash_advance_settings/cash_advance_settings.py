# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


DEFAULT_LIQUIDATION_DUE_DATE_OFFSET_DAYS = 30
DEFAULT_MAX_DUE_DATE_EXTENSION_DAYS = 30


class CashAdvanceSettings(Document):
	def validate(self):
		if not self.company:
			frappe.throw(_("Company is required."), title=_("Cash Advance Settings"))
		self.validate_ar_employee_account()
		self.validate_due_date_settings()

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

	def validate_due_date_settings(self):
		if cint(self.liquidation_due_date_offset_days) < 0:
			frappe.throw(_("Default Due Date Offset (Days) cannot be negative."))
		if cint(self.max_due_date_extension_days) < 0:
			frappe.throw(_("Maximum Due Date Extension (Days) cannot be negative."))

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


def get_liquidation_due_date_offset_days(company: str | None = None) -> int:
	"""Return default liquidation due date offset in days for the company."""
	if not company:
		return DEFAULT_LIQUIDATION_DUE_DATE_OFFSET_DAYS
	try:
		value = frappe.db.get_value(
			"Cash Advance Settings",
			{"company": company},
			"liquidation_due_date_offset_days",
		)
		return cint(value) if value is not None else DEFAULT_LIQUIDATION_DUE_DATE_OFFSET_DAYS
	except Exception:
		return DEFAULT_LIQUIDATION_DUE_DATE_OFFSET_DAYS


def get_max_due_date_extension_days(company: str | None = None) -> int:
	"""Return maximum due date extension days allowed in one extension."""
	if not company:
		return DEFAULT_MAX_DUE_DATE_EXTENSION_DAYS
	try:
		value = frappe.db.get_value(
			"Cash Advance Settings",
			{"company": company},
			"max_due_date_extension_days",
		)
		return cint(value) if value is not None else DEFAULT_MAX_DUE_DATE_EXTENSION_DAYS
	except Exception:
		return DEFAULT_MAX_DUE_DATE_EXTENSION_DAYS


@frappe.whitelist()
def get_due_date_settings(company: str | None = None) -> dict:
	"""Desk helper for liquidation due date defaults and extension limits."""
	return {
		"liquidation_due_date_offset_days": get_liquidation_due_date_offset_days(company),
		"max_due_date_extension_days": get_max_due_date_extension_days(company),
	}
