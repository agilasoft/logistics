# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import unittest

from logistics.utils.module_integration import propagate_from_warehouse_contract


class TestWarehouseContractAccounts(unittest.TestCase):
	def test_propagate_from_warehouse_contract_fills_empty_account_fields(self):
		order = SimpleNamespace(
			doctype="Inbound Order",
			contract="WC-001",
			company=None,
			branch="",
			cost_center=None,
			profit_center=None,
		)
		contract = SimpleNamespace(
			company="Demo Co",
			branch="Manila",
			cost_center="CC-1",
			profit_center="PC-1",
		)
		with patch(
			"logistics.utils.module_integration.frappe.get_cached_doc",
			return_value=contract,
		):
			propagate_from_warehouse_contract(order)

		self.assertEqual(order.company, "Demo Co")
		self.assertEqual(order.branch, "Manila")
		self.assertEqual(order.cost_center, "CC-1")
		self.assertEqual(order.profit_center, "PC-1")

	def test_propagate_from_warehouse_contract_does_not_overwrite_existing_company(self):
		order = SimpleNamespace(
			doctype="Release Order",
			contract="WC-001",
			company="Existing Co",
			branch="Existing Branch",
			cost_center="CC-OLD",
			profit_center="PC-OLD",
		)
		contract = SimpleNamespace(
			company="Demo Co",
			branch="Manila",
			cost_center="CC-1",
			profit_center="PC-1",
		)
		with patch(
			"logistics.utils.module_integration.frappe.get_cached_doc",
			return_value=contract,
		):
			propagate_from_warehouse_contract(order)

		self.assertEqual(order.company, "Existing Co")
		self.assertEqual(order.branch, "Existing Branch")
		self.assertEqual(order.cost_center, "CC-OLD")
		self.assertEqual(order.profit_center, "PC-OLD")
