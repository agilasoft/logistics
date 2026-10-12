# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Warehouse Stock Ledger must build its chart without a missing translation helper."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch


def _install_frappe_stub() -> None:
	frappe = types.ModuleType("frappe")

	class _dict(dict):
		def __getattr__(self, key):
			try:
				return self[key]
			except KeyError as exc:
				raise AttributeError(key) from exc

	frappe._dict = _dict
	frappe._ = lambda text: text
	frappe.db = types.SimpleNamespace(sql=lambda *args, **kwargs: [])

	utils = types.ModuleType("frappe.utils")
	utils.getdate = lambda value: value
	utils.flt = lambda value, precision=None: float(value or 0)
	utils.cint = lambda value: int(value or 0)
	frappe.utils = utils

	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = utils


try:
	import frappe  # noqa: F401
except ModuleNotFoundError:
	_install_frappe_stub()


class TestWarehouseStockLedgerReport(unittest.TestCase):
	def test_execute_builds_movements_chart(self):
		from logistics.warehousing.report.warehouse_stock_ledger.warehouse_stock_ledger import (
			execute,
		)

		rows = [{"item": "ITEM-1"}]
		with patch(
			"logistics.warehousing.report.warehouse_stock_ledger.warehouse_stock_ledger.frappe.db.sql",
			return_value=rows,
		):
			columns, data, _message, chart, summary = execute({"date_to": "2026-10-12"})

		self.assertTrue(columns)
		self.assertEqual(data, rows)
		self.assertEqual(chart["data"]["datasets"][0]["name"], "Movements")
		self.assertEqual(chart["data"]["labels"], ["ITEM-1"])
		self.assertEqual(chart["type"], "bar")
		self.assertEqual(summary, [])


if __name__ == "__main__":
	unittest.main()
