# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SeaFreightSettings(Document):
	def validate(self):
		if not self.company:
			frappe.throw(_("Company is required."), title=_("Sea Freight Settings"))
		self.validate_container_deposit_accounts()

	# Kept separate for tests that call validate_container_deposit_accounts with a stub instance.
	def validate_container_deposit_accounts(self):
		for fname, label in (
			("container_deposit_pending_refund_account", _("Deposits Pending for Refund Request")),
			("container_deposit_ar_shipping_lines_account", _("Container Deposit Receivable Account")),
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
					_("Container Deposit Receivable Account must be a Receivable account."),
					title=_("Sea Freight Settings"),
				)

	def on_update(self):
		frappe.clear_cache()
		frappe.logger().info(
			"Sea Freight Settings updated for company {0} by {1}".format(
				self.company, frappe.session.user
			)
		)

	@staticmethod
	def get_settings(company=None):
		"""Return Sea Freight Settings document for the given company."""
		if not company:
			company = frappe.defaults.get_user_default("Company")
		if not company:
			return None
		try:
			settings_name = frappe.db.get_value("Sea Freight Settings", {"company": company}, "name")
			if settings_name:
				return frappe.get_doc("Sea Freight Settings", settings_name)
		except frappe.DoesNotExistError:
			pass
		return None

	@staticmethod
	def get_default_value(company, fieldname):
		"""Return a single field value from Sea Freight Settings for the company."""
		try:
			settings = SeaFreightSettings.get_settings(company)
			if settings:
				return getattr(settings, fieldname, None)
		except frappe.DoesNotExistError:
			pass
		return None
