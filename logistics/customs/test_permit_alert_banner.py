# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Permit warning banner must follow the open form, not a name-only permission check."""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _install_frappe_stub():
	frappe = sys.modules.get("frappe")
	if frappe is None or not hasattr(frappe, "whitelist"):
		frappe = types.ModuleType("frappe")
		sys.modules["frappe"] = frappe

	class DoesNotExistError(Exception):
		pass

	class PermissionError(Exception):
		pass

	def whitelist(*args, **kwargs):
		if args and callable(args[0]) and not kwargs:
			return args[0]

		def decorator(fn):
			return fn

		return decorator

	frappe.DoesNotExistError = getattr(frappe, "DoesNotExistError", DoesNotExistError)
	frappe.PermissionError = getattr(frappe, "PermissionError", PermissionError)
	frappe._ = lambda message, *args, **kwargs: message
	frappe.whitelist = whitelist
	frappe.throw = MagicMock(side_effect=AssertionError("permit banner must not raise"))
	frappe.db = getattr(frappe, "db", MagicMock())
	frappe.get_doc = getattr(frappe, "get_doc", MagicMock())
	utils = sys.modules.get("frappe.utils") or types.ModuleType("frappe.utils")
	utils.cint = getattr(utils, "cint", lambda value: int(value or 0))
	utils.date_diff = getattr(utils, "date_diff", lambda *args, **kwargs: 0)
	utils.getdate = getattr(utils, "getdate", lambda value: value)
	utils.today = getattr(utils, "today", lambda: "2026-10-19")
	frappe.utils = utils
	sys.modules["frappe.utils"] = utils
	return frappe


class TestPermitAlertBanner(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.frappe = _install_frappe_stub()
		from logistics.customs.permit_matching import get_permit_alerts_html

		cls.get_permit_alerts_html = staticmethod(get_permit_alerts_html)

	@classmethod
	def tearDownClass(cls):
		for name in list(sys.modules):
			if name == "frappe" or name.startswith("frappe."):
				del sys.modules[name]
			elif name == "logistics.customs.permit_matching":
				del sys.modules[name]

	def test_unsaved_quote_has_no_banner(self):
		self.assertEqual(self.get_permit_alerts_html("Sales Quote", "new"), "")
		self.assertEqual(self.get_permit_alerts_html("Sales Quote", ""), "")

	def test_missing_quote_has_no_banner(self):
		self.frappe.db.exists.return_value = None
		self.assertEqual(self.get_permit_alerts_html("Sales Quote", "SQU000000120"), "")

	def test_sales_user_who_can_read_the_open_quote_gets_the_banner(self):
		"""Name-only permission can say no while the open quote says yes."""
		doc = MagicMock()
		doc.has_permission.return_value = True
		self.frappe.db.exists.return_value = "SQU000000120"
		self.frappe.get_doc.return_value = doc
		self.frappe.has_permission = MagicMock(return_value=False)
		alerts = [{"level": "warning", "msg": "Import permit expires soon"}]
		with patch("logistics.customs.permit_matching.visible_permit_alerts", return_value=alerts):
			html = self.get_permit_alerts_html("Sales Quote", "SQU000000120")
		self.assertIn("Import permit expires soon", html)
		self.assertIn("alert-warning", html)
		doc.has_permission.assert_called_once_with("read")
		self.frappe.has_permission.assert_not_called()
		self.frappe.throw.assert_not_called()

	def test_user_who_cannot_read_the_quote_gets_an_empty_banner(self):
		doc = MagicMock()
		doc.has_permission.return_value = False
		self.frappe.db.exists.return_value = "SQU000000120"
		self.frappe.get_doc.return_value = doc
		with patch("logistics.customs.permit_matching.visible_permit_alerts") as alerts:
			html = self.get_permit_alerts_html("Sales Quote", "SQU000000120")
		self.assertEqual(html, "")
		alerts.assert_not_called()
		self.frappe.throw.assert_not_called()


if __name__ == "__main__":
	unittest.main()
