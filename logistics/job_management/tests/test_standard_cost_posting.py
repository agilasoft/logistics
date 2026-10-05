# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Internal tariff cost charges post a standard-cost journal instead of a Purchase Invoice."""

from __future__ import unicode_literals

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from logistics.invoice_integration.purchase_invoice_api import (
	CHARGE_CONFIG,
	_get_eligible_consolidation_cost_rows,
	_get_eligible_cost_rows,
)
from logistics.job_management import job_readiness
from logistics.job_management.recognition_engine import RecognitionEngine
from logistics.job_management.standard_cost_posting import (
	is_internal_tariff_cost_charge,
	post_internal_tariff_standard_costs,
)
from logistics.utils.charges_calculation import (
	CHARGE_COST_SIDE_CLEAR_FIELDS,
	CHARGE_ROW_CLIENT_EXPORT_FIELDS,
)
from logistics.utils.get_charges_from_quotation import _SQ_CHARGE_COPY_FIELDS


def _charge(**kwargs):
	data = {
		"doctype": "Sea Shipment Charges",
		"item_code": "HANDLING",
		"item_name": "Handling",
		"charge_type": "Cost",
		"estimated_cost": 100,
		"actual_cost": 0,
		"cost_internal": 0,
		"use_tariff_in_cost": 0,
		"standard_cost_posted": 0,
		"cost_currency": None,
		"purchase_invoice": None,
		"purchase_invoice_status": None,
	}
	data.update(kwargs)
	return SimpleNamespace(**data)


class _Meta:
	def get_field(self, name):
		return True


class _JE:
	def __init__(self):
		self.accounts = []
		self.name = "ACC-JV-2026-00001"
		self.docstatus = 0
		self.inserted = False
		self.submitted = False

	def append(self, field, row):
		self.accounts.append(frappe._dict(row))

	def insert(self, ignore_permissions=True):
		self.inserted = True

	def submit(self):
		self.submitted = True
		self.docstatus = 1


class _Job:
	def __init__(self, charges):
		self.doctype = "Sea Shipment"
		self.name = "SS-1"
		self.company = "Acme Logistics"
		self.cost_center = "Main - AL"
		self.profit_center = "Ops - AL"
		self.branch = "HQ"
		self.job_number = "JN-1"
		self.charges = charges
		self.flags = frappe._dict()
		self.saved = False

	def get(self, key, default=None):
		return getattr(self, key, default)

	def save(self, ignore_permissions=False):
		self.saved = True


class TestInternalTariffQualifier(unittest.TestCase):
	def test_both_flags_qualify(self):
		self.assertTrue(
			is_internal_tariff_cost_charge(_charge(cost_internal=1, use_tariff_in_cost=1))
		)

	def test_tariff_without_internal_does_not_qualify(self):
		self.assertFalse(is_internal_tariff_cost_charge(_charge(use_tariff_in_cost=1)))

	def test_internal_without_tariff_does_not_qualify(self):
		self.assertFalse(is_internal_tariff_cost_charge(_charge(cost_internal=1)))

	def test_disbursement_does_not_qualify(self):
		self.assertFalse(
			is_internal_tariff_cost_charge(
				_charge(charge_type="Disbursement", cost_internal=1, use_tariff_in_cost=1)
			)
		)

	def test_copy_lists_include_cost_internal(self):
		self.assertIn("cost_internal", CHARGE_ROW_CLIENT_EXPORT_FIELDS)
		self.assertIn("cost_internal", CHARGE_COST_SIDE_CLEAR_FIELDS)
		self.assertIn("cost_internal", _SQ_CHARGE_COPY_FIELDS)


class TestPurchaseInvoiceSkipsInternalTariffCost(unittest.TestCase):
	def test_internal_tariff_cost_omitted_and_plain_tariff_kept(self):
		internal = _charge(cost_internal=1, use_tariff_in_cost=1, estimated_cost=80)
		external = _charge(use_tariff_in_cost=1, estimated_cost=40, item_code="FREIGHT")
		job = frappe._dict(doctype="Sea Shipment", charges=[internal, external])
		rows = _get_eligible_cost_rows(job, CHARGE_CONFIG["Sea Shipment"])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0][3], "FREIGHT")

	def test_consolidation_skips_internal_tariff_cost(self):
		internal = frappe._dict(
			item_code="HANDLING",
			charge_item="HANDLING",
			estimated_cost=80,
			actual_cost=0,
			cost_internal=1,
			use_tariff_in_cost=1,
			charge_type="Cost",
			purchase_invoice_status=None,
			purchase_invoice=None,
			allocation_method="Equal",
			pay_to="SUP-1",
		)
		external = frappe._dict(
			item_code="FREIGHT",
			charge_item="FREIGHT",
			estimated_cost=40,
			actual_cost=0,
			cost_internal=0,
			use_tariff_in_cost=1,
			charge_type="Cost",
			purchase_invoice_status=None,
			purchase_invoice=None,
			allocation_method="Equal",
			pay_to="SUP-1",
		)
		doc = frappe._dict(
			doctype="Sea Consolidation",
			consolidation_charges=[internal, external],
			consolidation_packages=[],
			attached_sea_shipments=[
				frappe._dict(sea_shipment="SS-1", value=1, cost_allocation_percentage=0)
			],
		)
		rows = _get_eligible_consolidation_cost_rows(doc)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0][3], "FREIGHT")


class TestStandardCostJournal(unittest.TestCase):
	def _item(self, debit="5100 - Standard Cost - AL", credit="5200 - Applied Cost - AL"):
		return frappe._dict(
			custom_standard_cost_account=debit,
			custom_applied_standard_cost_account=credit,
		)

	def _post(self, job, item):
		je = _JE()

		def _get_doc(doctype, name):
			self.assertEqual(doctype, "Item")
			return item

		with patch("logistics.utils.menu_permission.assert_perm"), patch(
			"logistics.job_management.standard_cost_posting.today", return_value="2026-10-05"
		), patch(
			"logistics.job_management.standard_cost_posting.now", return_value="2026-10-05 01:00:00"
		), patch("frappe.get_meta", return_value=_Meta()), patch(
			"frappe.get_cached_value", return_value="PHP"
		), patch("frappe.get_doc", side_effect=_get_doc), patch(
			"frappe.new_doc", return_value=je
		), patch("frappe.db.commit"):
			result = post_internal_tariff_standard_costs(job)
		return result, je

	def test_posts_balanced_journal_for_tariff_cost(self):
		charge = _charge(cost_internal=1, use_tariff_in_cost=1, estimated_cost=125)
		job = _Job([charge])
		result, je = self._post(job, self._item())
		self.assertTrue(result["ok"])
		self.assertEqual(result["journal_entry"], je.name)
		self.assertEqual(result["charges_posted"], 1)
		self.assertEqual(result["total_amount"], 125)
		self.assertTrue(je.inserted and je.submitted)
		debits = [row for row in je.accounts if row.debit_in_account_currency]
		credits = [row for row in je.accounts if row.credit_in_account_currency]
		self.assertEqual(len(debits), 1)
		self.assertEqual(len(credits), 1)
		self.assertEqual(debits[0].account, "5100 - Standard Cost - AL")
		self.assertEqual(debits[0].debit_in_account_currency, 125)
		self.assertEqual(credits[0].account, "5200 - Applied Cost - AL")
		self.assertEqual(credits[0].credit_in_account_currency, 125)
		self.assertEqual(debits[0].job_number, "JN-1")
		self.assertEqual(charge.standard_cost_posted, 1)
		self.assertEqual(charge.journal_entry_reference, je.name)
		self.assertTrue(job.saved)

	def test_converts_cost_currency_into_company_currency(self):
		charge = _charge(
			cost_internal=1,
			use_tariff_in_cost=1,
			estimated_cost=10,
			cost_currency="USD",
		)
		job = _Job([charge])
		with patch(
			"logistics.invoice_integration.billing_currency.charge_to_company_rate_buying",
			return_value=2,
		):
			result, je = self._post(job, self._item())
		self.assertTrue(result["ok"])
		self.assertEqual(je.accounts[0].debit_in_account_currency, 20)
		self.assertEqual(je.accounts[1].credit_in_account_currency, 20)

	def test_missing_item_accounts_are_not_posted(self):
		charge = _charge(cost_internal=1, use_tariff_in_cost=1, estimated_cost=50)
		job = _Job([charge])
		result, je = self._post(job, self._item(debit=None, credit=None))
		self.assertFalse(result["ok"])
		self.assertFalse(je.inserted)
		self.assertEqual(charge.standard_cost_posted, 0)
		self.assertIn("Standard Cost Account", result["message"])

	def test_second_post_does_not_create_another_journal(self):
		charge = _charge(
			cost_internal=1,
			use_tariff_in_cost=1,
			estimated_cost=50,
			standard_cost_posted=1,
			journal_entry_reference="ACC-JV-EXISTING",
		)
		job = _Job([charge])
		with patch("logistics.utils.menu_permission.assert_perm"), patch(
			"frappe.new_doc"
		) as new_doc:
			result = post_internal_tariff_standard_costs(job)
		new_doc.assert_not_called()
		self.assertFalse(result["ok"])


class TestReadinessAndAccrual(unittest.TestCase):
	def _doc(self, charges):
		doc = SimpleNamespace(
			doctype="Sea Shipment",
			name="SS-1",
			company="Acme Logistics",
			docstatus=1,
			charges=charges,
		)
		doc.get = lambda key, default=None: getattr(doc, key, default)
		return doc

	@patch("logistics.job_management.job_readiness._invoice_submitted", return_value=True)
	def test_submitted_standard_cost_journal_satisfies_readiness(self, _mock_sub):
		doc = self._doc(
			[
				_charge(
					cost_internal=1,
					use_tariff_in_cost=1,
					journal_entry_reference="ACC-JV-1",
					standard_cost_posted=1,
				)
			]
		)
		self.assertEqual(job_readiness.check_charges_posted(doc), [])

	def test_unposted_internal_tariff_cost_is_not_a_purchase_invoice_gap(self):
		doc = self._doc([_charge(cost_internal=1, use_tariff_in_cost=1)])
		issues = job_readiness.check_charges_posted(doc)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["code"], "charge_not_posted_standard_cost")

	def test_accrual_skips_internal_tariff_cost(self):
		internal = _charge(cost_internal=1, use_tariff_in_cost=1, estimated_cost=40)
		external = _charge(item_code="FREIGHT", estimated_cost=20, use_tariff_in_cost=1)
		job = self._doc([internal, external])
		job.estimated_costs = 60
		job.accrual_amount = 0
		lines = RecognitionEngine(job)._get_unrecognized_accrual_lines()
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0]["amount"], 20)
		self.assertEqual(lines[0]["item_code"], "FREIGHT")

	def test_accrual_does_not_fall_back_to_header_for_internal_only_cost(self):
		job = self._doc([_charge(cost_internal=1, use_tariff_in_cost=1, estimated_cost=40)])
		job.estimated_costs = 40
		job.accrual_amount = 0
		self.assertEqual(RecognitionEngine(job)._get_unrecognized_accrual_lines(), [])
