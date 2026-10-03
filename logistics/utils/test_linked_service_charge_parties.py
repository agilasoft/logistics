# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

from logistics.utils.linked_service_charge_parties import (
	apply_linked_service_charge_parties,
	on_before_save_linked_service_charge_parties,
)


class _Row:
	def __init__(self, **values):
		self.__dict__.update(values)


class _Doc:
	def __init__(self, **values):
		self.__dict__.update(values)
		self.doctype = values.get("doctype") or "Air Booking"

	def get(self, fieldname):
		return getattr(self, fieldname, None)


def _linked_booking(**overrides):
	values = {
		"doctype": "Air Booking",
		"service_role": "Linked",
		"main_service_type": "Sea Shipment",
		"main_service": "SEA-1",
		"company": "Op Co",
		"charges": [],
	}
	values.update(overrides)
	return _Doc(**values)


def _db_get_value(doctype, filters, fieldname, **kwargs):
	if doctype == "Sea Shipment":
		return "Main Co"
	if doctype == "Customer":
		if isinstance(filters, dict) and filters.get("represents_company") == "Main Co":
			return "CUST-MAIN"
		return None
	if doctype == "Supplier":
		if isinstance(filters, dict) and filters.get("represents_company") == "Op Co":
			return "SUP-LS"
		return None
	return None


class TestLinkedServiceChargeParties(unittest.TestCase):
	def test_rewrites_bill_to_and_fills_empty_pay_to(self):
		kept = _Row(charge_type="Margin", bill_to="END-CUST", pay_to="SUP-MAIN")
		empty_pay = _Row(charge_type="Disbursement", bill_to="END-CUST", pay_to="")
		cost = _Row(charge_type="Cost", bill_to="END-CUST", pay_to="")
		revenue = _Row(charge_type="Revenue", bill_to="END-CUST", pay_to="")
		doc = _linked_booking(charges=[kept, empty_pay, cost, revenue])

		with patch(
			"logistics.utils.linked_service_charge_parties.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.utils.linked_service_charge_parties.frappe.db.get_value",
			side_effect=_db_get_value,
		):
			apply_linked_service_charge_parties(doc)

		self.assertEqual(kept.bill_to, "CUST-MAIN")
		self.assertEqual(kept.pay_to, "SUP-MAIN")
		self.assertEqual(empty_pay.bill_to, "CUST-MAIN")
		self.assertEqual(empty_pay.pay_to, "SUP-LS")
		self.assertEqual(cost.bill_to, "END-CUST")
		self.assertEqual(cost.pay_to, "SUP-LS")
		self.assertEqual(revenue.bill_to, "CUST-MAIN")
		self.assertEqual(revenue.pay_to, "")

	def test_missing_customer_keeps_copied_bill_to(self):
		row = _Row(charge_type="Margin", bill_to="END-CUST", pay_to="SUP-MAIN")
		doc = _linked_booking(charges=[row])

		def get_value(doctype, filters, fieldname, **kwargs):
			if doctype == "Sea Shipment":
				return "Main Co"
			return None

		with patch(
			"logistics.utils.linked_service_charge_parties.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.utils.linked_service_charge_parties.frappe.db.get_value",
			side_effect=get_value,
		):
			apply_linked_service_charge_parties(doc)

		self.assertEqual(row.bill_to, "END-CUST")
		self.assertEqual(row.pay_to, "SUP-MAIN")

	def test_standalone_document_is_unchanged(self):
		row = _Row(charge_type="Margin", bill_to="END-CUST", pay_to="")
		doc = _Doc(
			doctype="Air Booking",
			service_role="Standalone",
			company="Op Co",
			charges=[row],
		)
		apply_linked_service_charge_parties(doc)
		self.assertEqual(row.bill_to, "END-CUST")
		self.assertEqual(row.pay_to, "")

	def test_before_save_runs_only_on_first_save(self):
		row = _Row(charge_type="Margin", bill_to="END-CUST", pay_to="")
		doc = _linked_booking(charges=[row])
		doc.is_new = lambda: False
		on_before_save_linked_service_charge_parties(doc)
		self.assertEqual(row.bill_to, "END-CUST")
		self.assertEqual(row.pay_to, "")

		doc.is_new = lambda: True
		with patch(
			"logistics.utils.linked_service_charge_parties.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.utils.linked_service_charge_parties.frappe.db.get_value",
			side_effect=_db_get_value,
		):
			on_before_save_linked_service_charge_parties(doc)
		self.assertEqual(row.bill_to, "CUST-MAIN")
		self.assertEqual(row.pay_to, "SUP-LS")
