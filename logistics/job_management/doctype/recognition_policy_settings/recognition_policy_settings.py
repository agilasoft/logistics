# Copyright (c) 2024, Logistics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RecognitionPolicySettings(Document):
	def validate(self):
		self.validate_parameters_or_legacy()
		for row in self.recognition_parameters or []:
			self.validate_parameter_accounts(row)

	def before_insert(self):
		if frappe.db.exists("Recognition Policy Settings", {"company": self.company}):
			frappe.throw(
				_("There is already Revenue Recognition Policy Settings for this company. Open that document instead."),
				title=_("One policy per company"),
			)

	def validate_parameters_or_legacy(self):
		has_rows = bool(self.recognition_parameters)
		legacy_ok = bool(
			self.wip_account
			and self.revenue_liability_account
			and self.cost_accrual_account
			and self.accrued_cost_liability_account
		)
		if not has_rows and not legacy_ok:
			frappe.throw(
				_(
					"Add at least one row in Recognition Parameters with all four accounts, "
					"or keep legacy account fields populated until migration completes."
				)
			)

	def validate_parameter_accounts(self, row):
		fields = [
			("wip_account", "WIP Account"),
			("revenue_liability_account", "Revenue Liability Account"),
			("cost_accrual_account", "Cost Accrual Account"),
			("accrued_cost_liability_account", "Accrued Cost Liability Account"),
		]
		for fieldname, label in fields:
			acc = row.get(fieldname)
			if not acc:
				frappe.throw(_("{0} is required on each parameter row").format(_(label)))
			ac = frappe.db.get_value(
				"Account",
				acc,
				["company", "account_type", "root_type", "is_group", "job_profit_account_type"],
				as_dict=True,
			)
			if not ac or ac.company != self.company:
				frappe.throw(_("Account {0} must belong to company {1}").format(acc, self.company))
			if ac.is_group:
				frappe.throw(_("Account {0} cannot be a group account").format(acc))
			self._check_account_role(fieldname, ac)

	def _check_account_role(self, fieldname, ac):
		at = (ac.account_type or "").strip()
		jpt = (ac.job_profit_account_type or "").strip()
		if fieldname == "wip_account":
			if at != "Income Account":
				frappe.throw(_("WIP Account must be an Income Account with Job Profit Account Type **WIP**."))
			if jpt != "WIP":
				frappe.throw(_("WIP Account: Job Profit Account Type must be **WIP**."))
		elif fieldname == "revenue_liability_account":
			if ac.root_type != "Asset":
				frappe.throw(_("Revenue Liability Account must be an Asset account."))
		elif fieldname == "cost_accrual_account":
			if at != "Expense Account" and ac.root_type != "Expense":
				frappe.throw(_("Cost Accrual Account must be an Expense Account."))
			if jpt != "Accrual":
				frappe.throw(_("Cost Accrual Account: Job Profit Account Type must be **Accrual**."))
		elif fieldname == "accrued_cost_liability_account":
			if ac.root_type != "Liability":
				frappe.throw(_("Accrued Cost Liability Account must be a Liability account."))
