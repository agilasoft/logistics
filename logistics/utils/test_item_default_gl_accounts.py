# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

"""Item Default / Item Group resolution for WIP, accrual, and standard-cost accounts."""

from __future__ import unicode_literals

import sys
import types
import unittest
from unittest.mock import patch


def _ensure_frappe():
	try:
		import frappe  # noqa: F401
		return
	except ModuleNotFoundError:
		pass

	frappe = types.ModuleType("frappe")

	def _gettext(message, *args, **kwargs):
		return message

	class _Throw(Exception):
		pass

	def _throw(message, *args, **kwargs):
		raise _Throw(message)

	def _whitelist(*args, **kwargs):
		def decorator(fn):
			return fn

		return decorator

	frappe._ = _gettext
	frappe.throw = _throw
	frappe.whitelist = _whitelist
	frappe.new_doc = lambda *args, **kwargs: None
	frappe.db = types.SimpleNamespace(set_value=lambda *args, **kwargs: None)
	frappe.get_meta = lambda doctype: None
	utils = types.ModuleType("frappe.utils")

	def flt(value, precision=None):
		try:
			return float(value or 0)
		except (TypeError, ValueError):
			return 0.0

	utils.flt = flt
	utils.getdate = lambda value: value
	utils.today = lambda: "2026-10-16"
	utils.nowdate = lambda: "2026-10-16"
	utils.cint = lambda value: int(value or 0)
	frappe.utils = utils
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = utils


_ensure_frappe()

import frappe

from logistics.utils.item_accounts import (
	accounts_by_company,
	apply_gl_accounts_to_items,
	copy_company_accounts,
	get_cost_accrual_account_for_item,
	get_standard_cost_accounts_for_item,
	get_wip_account_for_item,
	item_default_gl_fields,
	item_default_rows,
	validate_item_default_accounts,
)


class _Row(dict):
	def get(self, key, default=None):
		return super().get(key, default)


class TestItemDefaultAccountResolution(unittest.TestCase):
	def _defaults(self, parent, parenttype, company, **fields):
		row = {"parent": parent, "parenttype": parenttype, "company": company}
		row.update(fields)
		return row

	def _db(self, rows, item_group="Forwarding", header=None):
		header = header or {}

		def has_column(doctype, field):
			return True

		def sql(query, params, as_dict=False):
			matched = [
				row
				for row in rows
				if row["parent"] == params["parent"]
				and row["parenttype"] == params["parenttype"]
				and row["company"] == params["company"]
			]
			return matched[:1]

		def get_value(doctype, name, field, as_dict=False):
			if doctype == "Item" and field == "item_group":
				return item_group
			if doctype == "Item" and as_dict:
				return header
			return None

		return (
			patch.object(frappe.db, "has_column", has_column, create=True),
			patch.object(frappe.db, "sql", sql, create=True),
			patch.object(frappe.db, "get_value", get_value, create=True),
		)

	def test_item_default_wins_over_item_group_and_policy(self):
		patches = self._db(
			[
				self._defaults(
					"HANDLING",
					"Item",
					"ASL",
					custom_wip_account="WIP Item - ASL",
					custom_cost_accrual_account="Accrual Item - ASL",
					custom_standard_cost_account="Std Item - ASL",
					custom_applied_standard_cost_account="Applied Item - ASL",
				),
				self._defaults(
					"Forwarding",
					"Item Group",
					"ASL",
					custom_wip_account="WIP Group - ASL",
					custom_cost_accrual_account="Accrual Group - ASL",
					custom_standard_cost_account="Std Group - ASL",
					custom_applied_standard_cost_account="Applied Group - ASL",
				),
			],
			header={
				"custom_standard_cost_account": "Std Header - ASL",
				"custom_applied_standard_cost_account": "Applied Header - ASL",
			},
		)
		with patches[0], patches[1], patches[2]:
			self.assertEqual(get_wip_account_for_item("HANDLING", "ASL", "WIP Policy - ASL"), "WIP Item - ASL")
			self.assertEqual(
				get_cost_accrual_account_for_item("HANDLING", "ASL", "Accrual Policy - ASL"),
				"Accrual Item - ASL",
			)
			self.assertEqual(
				get_standard_cost_accounts_for_item("HANDLING", "ASL"),
				("Std Item - ASL", "Applied Item - ASL"),
			)

	def test_item_group_wins_over_policy_and_item_header(self):
		patches = self._db(
			[
				self._defaults("HANDLING", "Item", "ASL"),
				self._defaults(
					"Forwarding",
					"Item Group",
					"ASL",
					custom_wip_account="WIP Group - ASL",
					custom_cost_accrual_account="Accrual Group - ASL",
					custom_standard_cost_account="Std Group - ASL",
					custom_applied_standard_cost_account="Applied Group - ASL",
				),
			]
		)
		with patches[0], patches[1], patches[2]:
			self.assertEqual(get_wip_account_for_item("HANDLING", "ASL", "WIP Policy - ASL"), "WIP Group - ASL")
			self.assertEqual(
				get_cost_accrual_account_for_item("HANDLING", "ASL", "Accrual Policy - ASL"),
				"Accrual Group - ASL",
			)
			self.assertEqual(
				get_standard_cost_accounts_for_item("HANDLING", "ASL"),
				("Std Group - ASL", "Applied Group - ASL"),
			)

	def test_policy_and_item_header_are_the_fallback(self):
		patches = self._db(
			[],
			header={
				"custom_standard_cost_account": "Std Header - ASL",
				"custom_applied_standard_cost_account": "Applied Header - ASL",
			},
		)
		with patches[0], patches[1], patches[2]:
			self.assertEqual(get_wip_account_for_item("HANDLING", "ASL", "WIP Policy - ASL"), "WIP Policy - ASL")
			self.assertEqual(
				get_cost_accrual_account_for_item(None, "ASL", "Accrual Policy - ASL"),
				"Accrual Policy - ASL",
			)
			self.assertEqual(
				get_standard_cost_accounts_for_item("HANDLING", "ASL"),
				("Std Header - ASL", "Applied Header - ASL"),
			)

	def test_header_standard_cost_wins_over_item_group(self):
		patches = self._db(
			[
				self._defaults(
					"Forwarding",
					"Item Group",
					"ASL",
					custom_standard_cost_account="Std Group - ASL",
					custom_applied_standard_cost_account="Applied Group - ASL",
				)
			],
			header={
				"custom_standard_cost_account": "Std Header - ASL",
				"custom_applied_standard_cost_account": "Applied Header - ASL",
			},
		)
		with patches[0], patches[1], patches[2]:
			self.assertEqual(
				get_standard_cost_accounts_for_item("HANDLING", "ASL"),
				("Std Header - ASL", "Applied Header - ASL"),
			)

	def test_wip_account_must_be_income_tagged_wip(self):
		class _Meta:
			def get_field(self, name):
				return True

		doc = _Row(
			item_defaults=[
				_Row(company="ASL", custom_wip_account="Accrual Group - ASL"),
			]
		)
		with patch.object(frappe, "get_meta", lambda doctype: _Meta(), create=True), patch.object(
			frappe.db, "has_column", lambda doctype, field: True, create=True
		), patch.object(
			frappe.db,
			"get_value",
			lambda doctype, name, fields, as_dict=False: {
				"company": "ASL",
				"account_type": "Expense Account",
				"is_group": 0,
				"job_profit_account_type": "Accrual",
			},
			create=True,
		):
			with self.assertRaises(Exception) as raised:
				validate_item_default_accounts(doc)
		self.assertIn("WIP Account", str(raised.exception))

	def test_item_group_validation_reads_item_group_defaults(self):
		class _Meta:
			def get_field(self, name):
				return True

		clean_group = _Row(
			doctype="Item Group",
			item_defaults=[_Row(company="ASL", custom_wip_account="Accrual Group - ASL")],
			item_group_defaults=[_Row(company="ASL", income_account="Income - ASL")],
		)
		bad_group = _Row(
			doctype="Item Group",
			item_defaults=[_Row(company="ASL", income_account="Income - ASL")],
			item_group_defaults=[_Row(company="ASL", custom_wip_account="Accrual Group - ASL")],
		)
		with patch.object(frappe, "get_meta", lambda doctype: _Meta(), create=True), patch.object(
			frappe.db, "has_column", lambda doctype, field: True, create=True
		), patch.object(
			frappe.db,
			"get_value",
			lambda doctype, name, fields, as_dict=False: {
				"company": "ASL",
				"account_type": "Expense Account",
				"is_group": 0,
				"job_profit_account_type": "Accrual",
			},
			create=True,
		):
			validate_item_default_accounts(clean_group)
			with self.assertRaises(Exception) as raised:
				validate_item_default_accounts(bad_group)
		self.assertIn("WIP Account", str(raised.exception))


class _Charge:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)


class _Job:
	def __init__(self, charges):
		self.doctype = "Sea Shipment"
		self.name = "SS-1"
		self.company = "ASL"
		self.charges = charges

	def get(self, key, default=None):
		return getattr(self, key, default)


class _JE:
	def __init__(self):
		self.accounts = []
		self.name = "ACC-JV-1"
		self.flags = types.SimpleNamespace()

	def append(self, field, row):
		self.accounts.append(dict(row))

	def insert(self, ignore_permissions=True):
		self.inserted = True

	def submit(self):
		self.submitted = True


class TestRecognitionUsesItemGroupAccounts(unittest.TestCase):
	def _engine(self, charges):
		from logistics.job_management.recognition_engine import RecognitionEngine

		job = _Job(charges)
		engine = RecognitionEngine(job)
		engine.get_settings = lambda: {
			"wip_account": "WIP Policy - ASL",
			"revenue_liability_account": "WIP Liability - ASL",
			"cost_accrual_account": "Accrual Policy - ASL",
			"accrued_cost_liability_account": "Accrued Liability - ASL",
		}
		engine._je_dimension_fields_for_job = lambda: {}
		engine._item_dimension_je_row = lambda item_code: {}
		engine._insert_and_submit_je = lambda je: None
		engine._je_account_reference_fields = lambda: {}
		return engine

	def _accounts_for(self, item_code, company, fallback):
		if item_code == "HANDLING":
			if "WIP" in (fallback or "") or fallback == "WIP Policy - ASL":
				return "WIP Group - ASL"
			return "Accrual Group - ASL"
		return fallback

	def test_wip_and_accrual_journals_use_item_group_then_policy(self):
		from logistics.job_management import recognition_engine as engine_mod

		charge = _Charge(item_code="HANDLING", charge_type="Revenue", estimated_revenue=40, estimated_cost=25)
		engine = self._engine([charge])
		je = _JE()
		with patch.object(engine_mod, "get_wip_account_for_item", side_effect=self._accounts_for), patch.object(
			engine_mod, "get_cost_accrual_account_for_item", side_effect=self._accounts_for
		), patch.object(engine_mod.frappe, "new_doc", return_value=je), patch.object(
			engine_mod, "apply_journal_entry_posting_header_from_job"
		):
			engine.create_wip_recognition_je_multi(
				"2026-10-16",
				[{"amount": 40, "item_code": "HANDLING"}, {"amount": 10, "item_code": None}],
			)
		credits = [row for row in je.accounts if row["credit_in_account_currency"]]
		self.assertEqual(credits[0]["account"], "WIP Group - ASL")
		self.assertEqual(credits[1]["account"], "WIP Policy - ASL")
		debits = [row for row in je.accounts if row["debit_in_account_currency"]]
		self.assertEqual({row["account"] for row in debits}, {"WIP Liability - ASL"})

		je = _JE()
		with patch.object(engine_mod, "get_wip_account_for_item", side_effect=self._accounts_for), patch.object(
			engine_mod, "get_cost_accrual_account_for_item", side_effect=self._accounts_for
		), patch.object(engine_mod.frappe, "new_doc", return_value=je), patch.object(
			engine_mod, "apply_journal_entry_posting_header_from_job"
		):
			engine.create_accrual_recognition_je(
				"2026-10-16",
				[{"amount": 25, "item_code": "HANDLING"}, {"amount": 5, "item_code": None}],
			)
		accrual_debits = [row for row in je.accounts if row["debit_in_account_currency"]]
		self.assertEqual(accrual_debits[0]["account"], "Accrual Group - ASL")
		self.assertEqual(accrual_debits[1]["account"], "Accrual Policy - ASL")

	def test_adjustment_reverses_the_account_that_was_posted(self):
		from logistics.job_management import recognition_engine as engine_mod

		charge = _Charge(
			item_code="HANDLING",
			charge_type="Revenue",
			estimated_revenue=80,
			estimated_cost=30,
			wip_recognition_journal_entry="JE-WIP",
			accrual_recognition_journal_entry="JE-ACC",
		)
		engine = self._engine([charge])
		je = _JE()
		with patch.object(engine_mod, "get_wip_account_for_item", side_effect=self._accounts_for), patch.object(
			engine_mod, "get_cost_accrual_account_for_item", side_effect=self._accounts_for
		), patch.object(engine_mod.frappe, "new_doc", return_value=je), patch.object(
			engine_mod, "apply_journal_entry_posting_header_from_job"
		):
			engine.create_wip_adjustment_je(100, "2026-10-16")
		wip_debits = [row for row in je.accounts if row["debit_in_account_currency"]]
		self.assertEqual(wip_debits[0]["account"], "WIP Group - ASL")
		self.assertEqual(wip_debits[0]["debit_in_account_currency"], 80)
		self.assertEqual(wip_debits[1]["account"], "WIP Policy - ASL")
		self.assertEqual(wip_debits[1]["debit_in_account_currency"], 20)

	def test_sales_invoice_reversal_posts_the_same_wip_account(self):
		from logistics.invoice_integration import wip_reversal

		je = _JE()
		job = _Job([])
		job.job_number = "JN-1"
		job.cost_center = None
		job.profit_center = None
		job.wip_amount = 40
		job.recognized_revenue = 0

		def _wip(item_code, company, fallback):
			self.assertEqual(fallback, "WIP Policy - ASL")
			return "WIP Group - ASL" if item_code == "HANDLING" else fallback

		with patch.object(wip_reversal, "get_wip_account_for_item", side_effect=_wip), patch.object(
			wip_reversal, "resolve_policy_row_for_job", return_value=(None, {
				"wip_account": "WIP Policy - ASL",
				"revenue_liability_account": "WIP Liability - ASL",
			})
		), patch.object(wip_reversal.frappe, "new_doc", return_value=je), patch.object(
			wip_reversal, "apply_journal_entry_posting_header_from_job"
		), patch.object(wip_reversal, "item_row_dict", return_value={}), patch.object(
			wip_reversal.frappe.db, "set_value"
		), patch.object(wip_reversal, "set_wip_adjustment_je_on_charges"):
			name = wip_reversal.post_wip_reversal_journal_multi(
				[(job, [(40, "HANDLING")])],
				"2026-10-16",
				"ASL",
				"reversal",
			)
		self.assertEqual(name, "ACC-JV-1")
		self.assertEqual(je.accounts[0]["account"], "WIP Group - ASL")
		self.assertEqual(je.accounts[1]["account"], "WIP Liability - ASL")


class _Child(dict):
	def set(self, key, value):
		self[key] = value


class _ItemDoc:
	def __init__(self, defaults, doctype="Item", child_field="item_defaults"):
		self.doctype = doctype
		self._children = {child_field: [_Child(dict(row)) for row in defaults]}
		self.saved = 0

	def get(self, key, default=None):
		if key == "doctype":
			return self.doctype
		if key in ("item_defaults", "item_group_defaults"):
			return self._children.get(key) or []
		return default

	def append(self, key, payload):
		child = _Child(dict(payload))
		self._children.setdefault(key, []).append(child)
		return child

	@property
	def item_defaults(self):
		return self._children.setdefault("item_defaults", [])

	def save(self):
		self.saved += 1


class TestApplyGlAccountsToItems(unittest.TestCase):
	def test_blank_group_accounts_do_not_clear_item_accounts(self):
		item = _ItemDoc(
			[{"company": "ASL", "income_account": "Old Income", "expense_account": "Keep Expense"}]
		)
		changed = copy_company_accounts(
			item,
			{"ASL": {"income_account": "Group Income", "custom_wip_account": "WIP - ASL"}},
		)
		self.assertTrue(changed)
		row = item.item_defaults[0]
		self.assertEqual(row["income_account"], "Group Income")
		self.assertEqual(row["expense_account"], "Keep Expense")
		self.assertEqual(row["custom_wip_account"], "WIP - ASL")

	def test_missing_company_row_is_created_and_unchanged_rows_stay(self):
		item = _ItemDoc([{"company": "ASL", "income_account": "Income - ASL"}])
		changed = copy_company_accounts(item, {"ASL": {"income_account": "Income - ASL"}})
		self.assertFalse(changed)
		changed = copy_company_accounts(item, {"BCO": {"expense_account": "Expense - BCO"}})
		self.assertTrue(changed)
		self.assertEqual(item.item_defaults[1]["company"], "BCO")
		self.assertEqual(item.item_defaults[1]["expense_account"], "Expense - BCO")

	def test_accounts_by_company_skips_empty_rows(self):
		rows = [
			{"company": "", "income_account": "Skip"},
			{"company": "ASL", "income_account": "", "expense_account": "Expense - ASL"},
			{"company": "ASL", "custom_wip_account": "WIP - ASL"},
		]
		self.assertEqual(
			accounts_by_company(rows, ["income_account", "expense_account", "custom_wip_account"]),
			{"ASL": {"expense_account": "Expense - ASL", "custom_wip_account": "WIP - ASL"}},
		)

	def test_gl_fields_follow_account_links(self):
		meta = types.SimpleNamespace(
			fields=[
				{"fieldname": "income_account", "fieldtype": "Link", "options": "Account"},
				{"fieldname": "default_warehouse", "fieldtype": "Link", "options": "Warehouse"},
				{"fieldname": "custom_wip_account", "fieldtype": "Link", "options": "Account"},
			]
		)
		with patch.object(frappe, "get_meta", return_value=meta), patch.object(
			frappe.db, "has_column", return_value=True, create=True
		):
			self.assertEqual(
				item_default_gl_fields(),
				["income_account", "custom_wip_account", "purchase_expense_account"],
			)

	def test_item_group_rows_come_from_item_group_defaults(self):
		group = _ItemDoc(
			[{"company": "ASL", "income_account": "Income - ASL"}],
			doctype="Item Group",
			child_field="item_group_defaults",
		)
		group._children["item_defaults"] = [_Child({"company": "ASL", "income_account": "Wrong Table"})]
		self.assertEqual(item_default_rows(group)[0]["income_account"], "Income - ASL")
		item = _ItemDoc([{"company": "ASL", "income_account": "Item Income"}])
		self.assertEqual(item_default_rows(item)[0]["income_account"], "Item Income")

	def test_apply_updates_items_in_child_groups(self):
		group = _ItemDoc(
			[
				{
					"company": "ASL",
					"income_account": "Income - ASL",
					"expense_account": "",
					"custom_wip_account": "WIP - ASL",
				},
				{"company": "BCO", "expense_account": "Expense - BCO"},
			],
			doctype="Item Group",
			child_field="item_group_defaults",
		)
		handling = _ItemDoc(
			[{"company": "ASL", "income_account": "Old", "expense_account": "Keep", "custom_wip_account": ""}]
		)
		air_fee = _ItemDoc(
			[
				{"company": "ASL", "income_account": "Income - ASL", "custom_wip_account": "WIP - ASL"},
				{"company": "BCO", "expense_account": "Expense - BCO"},
			]
		)
		docs = {("Item Group", "Forwarding"): group, ("Item", "HANDLING"): handling, ("Item", "AIR-FEE"): air_fee}

		def get_doc(doctype, name):
			return docs[(doctype, name)]

		def get_value(doctype, name, fields, as_dict=False):
			return {"lft": 2, "rgt": 7}

		def sql(query, params):
			return [("Forwarding",), ("Air",)]

		with patch.object(frappe.db, "exists", return_value=True, create=True), patch.object(
			frappe, "has_permission", return_value=True, create=True
		), patch.object(frappe, "get_doc", side_effect=get_doc, create=True), patch.object(
			frappe, "get_all", return_value=[{"name": "HANDLING"}, {"name": "AIR-FEE"}], create=True
		), patch.object(
			frappe.db, "get_value", side_effect=get_value, create=True
		), patch.object(frappe.db, "sql", side_effect=sql, create=True), patch.object(
			frappe.db, "has_column", return_value=True, create=True
		), patch.object(
			frappe,
			"get_meta",
			return_value=types.SimpleNamespace(
				fields=[
					{"fieldname": "income_account", "fieldtype": "Link", "options": "Account"},
					{"fieldname": "expense_account", "fieldtype": "Link", "options": "Account"},
					{"fieldname": "custom_wip_account", "fieldtype": "Link", "options": "Account"},
				]
			),
		):
			result = apply_gl_accounts_to_items("Forwarding")

		self.assertEqual(result["items"], 2)
		self.assertEqual(result["updated"], 1)
		self.assertEqual(result["companies"], ["ASL", "BCO"])
		self.assertEqual(handling.saved, 1)
		self.assertEqual(air_fee.saved, 0)
		self.assertEqual(handling.item_defaults[0]["income_account"], "Income - ASL")
		self.assertEqual(handling.item_defaults[0]["expense_account"], "Keep")
		self.assertEqual(handling.item_defaults[0]["custom_wip_account"], "WIP - ASL")
		self.assertEqual(handling.item_defaults[1]["company"], "BCO")
		self.assertEqual(handling.item_defaults[1]["expense_account"], "Expense - BCO")

	def test_apply_ignores_accounts_stored_on_item_defaults(self):
		group = _ItemDoc(
			[{"company": "ASL", "income_account": "Income - ASL"}],
			doctype="Item Group",
			child_field="item_defaults",
		)
		with patch.object(frappe.db, "exists", return_value=True, create=True), patch.object(
			frappe, "has_permission", return_value=True, create=True
		), patch.object(frappe, "get_doc", return_value=group, create=True), patch.object(
			frappe.db, "has_column", return_value=True, create=True
		), patch.object(frappe, "get_meta", return_value=types.SimpleNamespace(fields=[])):
			with self.assertRaises(Exception) as raised:
				apply_gl_accounts_to_items("Forwarding")
		self.assertIn("Set GL accounts", str(raised.exception))

	def test_apply_requires_a_company_account(self):
		group = _ItemDoc(
			[{"company": "ASL", "income_account": ""}],
			doctype="Item Group",
			child_field="item_group_defaults",
		)
		with patch.object(frappe.db, "exists", return_value=True, create=True), patch.object(
			frappe, "has_permission", return_value=True, create=True
		), patch.object(frappe, "get_doc", return_value=group, create=True), patch.object(
			frappe.db, "has_column", return_value=True, create=True
		), patch.object(frappe, "get_meta", return_value=types.SimpleNamespace(fields=[])):
			with self.assertRaises(Exception) as raised:
				apply_gl_accounts_to_items("Forwarding")
		self.assertIn("Set GL accounts", str(raised.exception))


if __name__ == "__main__":
	unittest.main()
