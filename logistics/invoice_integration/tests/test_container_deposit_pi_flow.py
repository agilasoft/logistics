# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.container_deposit_pi import apply_container_deposit_expense_account
from logistics.invoice_integration.container_deposit_sync import (
	clear_container_deposits_on_purchase_invoice_cancel,
)
from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings


class TestContainerDepositPIFlow(UnitTestCase):
	def test_sea_freight_settings_rejects_non_receivable_ar_account(self):
		class _S:
			def get(self, k, default=None):
				return {
					"container_deposit_pending_refund_account": "PEND-1",
					"container_deposit_ar_shipping_lines_account": "AR-1",
				}.get(k, default)

		with patch("frappe.db.exists", return_value=True):
			with patch("frappe.db.get_value", return_value="Bank"):
				with self.assertRaises(frappe.ValidationError):
					SeaFreightSettings.validate_container_deposit_accounts(_S())

	def test_apply_container_deposit_expense_account_on_pi_item(self):
		class _Item:
			def __init__(self):
				self.item_code = "TEST-ITEM"
				self.reference_doctype = "Sea Shipment"
				self.reference_name = "SS-1"
				self.expense_account = None

			def get(self, k, default=None):
				return getattr(self, k, default)

		class _PI:
			doctype = "Purchase Invoice"
			docstatus = 0
			reference_doctype = ""
			reference_name = ""

			def __init__(self):
				self.items = [_Item()]

			def get(self, k, default=None):
				return getattr(self, k, default)

		pi = _PI()
		with patch(
			"logistics.invoice_integration.container_deposit_pi._pending_refund_account",
			return_value="PENDING-CD-ACC",
		):
			with patch(
				"logistics.invoice_integration.container_deposit_pi.item_is_container_deposit",
				return_value=True,
			):
				with patch("frappe.db.exists", return_value=True):
					apply_container_deposit_expense_account(pi)
		self.assertEqual(pi.items[0].expense_account, "PENDING-CD-ACC")

	def test_clear_pi_cancel_blocked_when_refund_request_je_on_line(self):
		class _PI:
			doctype = "Purchase Invoice"
			name = "PI-CD-TEST"

		with patch.object(
			frappe,
			"get_all",
			return_value=[
				{
					"name": "cdrow1",
					"refund_request_journal_entry": "JE-CD-1",
					"parent": "CONT-1",
				}
			],
		):
			with self.assertRaises(frappe.ValidationError):
				clear_container_deposits_on_purchase_invoice_cancel(_PI())
