# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe

from logistics.invoice_integration.journal_entry_recognition_reversal import (
	collect_journal_entry_recognition_lines,
	reverse_wip_and_accrual_for_journal_entry,
)


def _je(accounts, job_number=None, user_remark=None, flags=None):
	doc = frappe._dict(
		docstatus=1,
		name="JE-0001",
		company="Test Company",
		posting_date="2026-09-29",
		job_number=job_number,
		user_remark=user_remark or "",
		accounts=accounts,
	)
	if flags is not None:
		doc.flags = flags
	return doc


class _Flags(object):
	def __init__(self, skip=False):
		self.skip_logistics_recognition_reversal = skip


class TestCollectJournalEntryRecognitionLines(unittest.TestCase):
	def _policy(self, jcn):
		return {
			"wip_account": "WIP - TC",
			"revenue_liability_account": "Rev Liab - TC",
			"cost_accrual_account": "Cost Accrual - TC",
			"accrued_cost_liability_account": "Accrued Liab - TC",
		}

	def _account(self, name, root_type, account_type=None, job_profit=None):
		return frappe._dict(
			root_type=root_type,
			account_type=account_type,
			job_profit_account_type=job_profit,
		)

	def _run(self, je, accounts):
		def get_value(doctype, name, fields, as_dict=False):
			return accounts.get(name) or {}

		with patch(
			"logistics.invoice_integration.journal_entry_recognition_reversal.get_recognition_policy_for_job",
			side_effect=self._policy,
		), patch(
			"logistics.invoice_integration.journal_entry_recognition_reversal.frappe.db.has_column",
			return_value=True,
		), patch(
			"logistics.invoice_integration.journal_entry_recognition_reversal.frappe.db.get_value",
			side_effect=get_value,
		), patch(
			"logistics.invoice_integration.journal_entry_recognition_reversal.get_item_link_fieldname",
			return_value="item",
		):
			return collect_journal_entry_recognition_lines(je)

	def test_expense_debit_reverses_accrual_not_the_bank_credit(self):
		accounts = {
			"Freight Expense - TC": self._account("Freight Expense - TC", "Expense"),
			"Bank - TC": self._account("Bank - TC", "Asset", "Bank"),
		}
		je = _je(
			[
				frappe._dict(
					account="Freight Expense - TC",
					debit_in_account_currency=150,
					credit_in_account_currency=0,
					job_number="JOB-1",
					item="FREIGHT",
				),
				frappe._dict(
					account="Bank - TC",
					debit_in_account_currency=0,
					credit_in_account_currency=150,
					job_number="JOB-1",
				),
			]
		)
		lines = self._run(je, accounts)
		self.assertEqual(lines["JOB-1"]["accrual"], [(150, "FREIGHT")])
		self.assertEqual(lines["JOB-1"]["wip"], [])

	def test_income_credit_reverses_wip(self):
		accounts = {
			"Freight Income - TC": self._account("Freight Income - TC", "Income"),
			"Debtors - TC": self._account("Debtors - TC", "Asset", "Receivable"),
		}
		je = _je(
			[
				frappe._dict(
					account="Debtors - TC",
					debit=400,
					job_number="JOB-1",
				),
				frappe._dict(
					account="Freight Income - TC",
					credit=400,
					job_number="JOB-1",
					item="FREIGHT",
				),
			]
		)
		lines = self._run(je, accounts)
		self.assertEqual(lines["JOB-1"]["wip"], [(400, "FREIGHT")])
		self.assertFalse(lines["JOB-1"]["accrual"])

	def test_policy_accounts_are_not_treated_as_actual_cost_or_revenue(self):
		accounts = {
			"Cost Accrual - TC": self._account("Cost Accrual - TC", "Expense"),
			"Accrued Liab - TC": self._account("Accrued Liab - TC", "Liability"),
			"WIP - TC": self._account("WIP - TC", "Income"),
			"Rev Liab - TC": self._account("Rev Liab - TC", "Liability"),
		}
		je = _je(
			[
				frappe._dict(account="Cost Accrual - TC", debit=80, job_number="JOB-1"),
				frappe._dict(account="Accrued Liab - TC", credit=80, job_number="JOB-1"),
				frappe._dict(account="Rev Liab - TC", debit=90, job_number="JOB-1"),
				frappe._dict(account="WIP - TC", credit=90, job_number="JOB-1"),
			]
		)
		self.assertEqual(self._run(je, accounts), {})

	def test_header_job_number_fills_blank_rows_only(self):
		accounts = {
			"Expense - TC": self._account("Expense - TC", "Expense"),
			"Income - TC": self._account("Income - TC", "Income"),
		}
		je = _je(
			[
				frappe._dict(account="Expense - TC", debit=10),
				frappe._dict(account="Income - TC", credit=25, job_number="JOB-ROW"),
			],
			job_number="JOB-HEADER",
		)
		lines = self._run(je, accounts)
		self.assertEqual(lines["JOB-HEADER"]["accrual"], [(10, None)])
		self.assertEqual(lines["JOB-HEADER"]["wip"], [])
		self.assertEqual(lines["JOB-ROW"]["wip"], [(25, None)])
		self.assertEqual(lines["JOB-ROW"]["accrual"], [])

	def test_disbursement_account_is_skipped(self):
		accounts = {
			"Duty - TC": self._account("Duty - TC", "Expense", job_profit="Disbursements"),
		}
		je = _je(
			[frappe._dict(account="Duty - TC", debit=30, job_number="JOB-1")]
		)
		self.assertEqual(self._run(je, accounts), {})


class TestSkipJournalEntryReversal(unittest.TestCase):
	def test_skips_reversal_marker(self):
		je = _je(
			[],
			user_remark="Accrual reversal\nCargoNext|RecognitionReversal|Journal Entry Accrual|JE-1|",
		)
		self.assertIsNone(reverse_wip_and_accrual_for_journal_entry(je))

	def test_skips_internal_billing(self):
		je = _je([], user_remark="Internal Billing - Sales Quote SQ-1")
		self.assertIsNone(reverse_wip_and_accrual_for_journal_entry(je))

	def test_skips_flagged_recognition_journal(self):
		je = _je([], flags=_Flags(skip=True))
		self.assertIsNone(reverse_wip_and_accrual_for_journal_entry(je))
