# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors

from unittest.mock import patch

from frappe.tests import UnitTestCase

from logistics.logistics.deposit_processing.container_gl_service import (
	_gl_row_is_container_deposit_charge,
	get_deposit_postings_data,
	get_gl_rows_split,
)


class TestContainerDepositGlFilter(UnitTestCase):
	def test_gl_row_requires_container_deposit_item_when_item_present(self):
		with patch(
			"logistics.logistics.deposit_processing.container_gl_service.item_is_container_deposit",
			side_effect=lambda code: code == "CONDEP",
		):
			self.assertTrue(_gl_row_is_container_deposit_charge({"gl_item_code": "CONDEP"}))
			self.assertFalse(_gl_row_is_container_deposit_charge({"gl_item_code": "FREIGHT"}))

	def test_gl_row_without_item_is_kept_for_refund_je(self):
		self.assertTrue(_gl_row_is_container_deposit_charge({}))

	def test_get_gl_rows_split_excludes_non_deposit_items_on_pending_account(self):
		rows = [
			{
				"account": "PENDING-ACC",
				"company": "Test Co",
				"gl_item_code": "FREIGHT",
				"debit": 400,
			},
			{
				"account": "PENDING-ACC",
				"company": "Test Co",
				"gl_item_code": "CONDEP",
				"debit": 10000,
			},
			{
				"account": "EXP-ACC",
				"company": "Test Co",
				"gl_item_code": "FREIGHT",
				"debit": 400,
			},
		]
		with patch(
			"logistics.logistics.deposit_processing.container_gl_service._container_column",
			return_value="container",
		):
			with patch(
				"logistics.logistics.deposit_processing.container_gl_service._query_gl_for_container",
				return_value=rows,
			):
				with patch(
					"logistics.logistics.deposit_processing.container_gl_service._pending_refund_account_for_company",
					return_value="PENDING-ACC",
				):
					with patch(
						"logistics.logistics.deposit_processing.container_gl_service.item_is_container_deposit",
						side_effect=lambda code: code == "CONDEP",
					):
						with patch(
							"logistics.logistics.deposit_processing.container_gl_service.item_is_container_charge",
							return_value=False,
						):
							deposit_rows, charge_rows = get_gl_rows_split("TEST-CONT")
		self.assertEqual(len(deposit_rows), 1)
		self.assertEqual(deposit_rows[0]["gl_item_code"], "CONDEP")
		self.assertEqual(charge_rows, [])

	def test_get_deposit_postings_data_shapes_rows(self):
		deposit_rows = [
			{
				"posting_date": "2026-05-11",
				"voucher_type": "Purchase Invoice",
				"voucher_no": "PI-1",
				"account": "PENDING-ACC",
				"debit": 10000,
				"credit": 0,
				"gl_item_code": "CONDEP",
				"party_type": "Supplier",
				"party": "SUP-1",
				"company": "Test Co",
			},
			{
				"posting_date": "2026-05-30",
				"voucher_type": "Journal Entry",
				"voucher_no": "JE-1",
				"account": "PENDING-ACC",
				"debit": 0,
				"credit": 5000,
				"gl_item_code": "",
				"party_type": "",
				"party": "",
				"company": "Test Co",
			},
		]
		with patch(
			"logistics.logistics.deposit_processing.container_gl_service._all_pending_refund_accounts",
			return_value=["PENDING-ACC"],
		):
			with patch(
				"logistics.logistics.deposit_processing.container_gl_service.get_gl_rows_split",
				return_value=(deposit_rows, []),
			):
				with patch(
					"logistics.logistics.deposit_processing.container_gl_service._refunded_purchase_invoices_for_container",
					return_value=set(),
				):
					with patch(
						"logistics.logistics.deposit_processing.container_gl_service._account_label",
						side_effect=lambda acc: acc,
					):
						with patch(
							"logistics.logistics.deposit_processing.container_gl_service._party_label",
							return_value="Test Supplier",
						):
							with patch(
								"frappe.db.get_value",
								side_effect=lambda dt, name, field, *a, **k: {
									("Company", "Test Co", "default_currency"): "PHP",
								}.get((dt, name, field if isinstance(field, str) else tuple(field)))
								if dt == "Company"
								else None,
							):
								data = get_deposit_postings_data("TEST-CONT")
		self.assertEqual(len(data["rows"]), 2)
		self.assertEqual(data["rows"][0]["refund_status"], "Open")
		self.assertEqual(data["rows"][1]["refund_status"], "Refunded")
		self.assertEqual(data["items"], ["CONDEP"])

	def test_get_deposit_postings_data_unconfigured(self):
		with patch(
			"logistics.logistics.deposit_processing.container_gl_service._all_pending_refund_accounts",
			return_value=[],
		):
			data = get_deposit_postings_data("TEST-CONT")
		self.assertTrue(data["error"])
		self.assertEqual(data["rows"], [])
