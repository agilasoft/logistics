# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_from_source import (
	_linked_charge_groups_for_create,
	resolve_internal_job_detail_row_for_create,
)


class TestLinkedChargeInternalJobCreate(FrappeTestCase):
	def _make_shipment(self, charges=None):
		doc = MagicMock(doctype="Air Shipment", name="ASP-TEST")
		doc.charges = charges or []
		return doc

	def test_groups_linked_scoped_charges_by_service_and_link(self):
		shipment = self._make_shipment(
			[
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="LS-TR-1",
					location_from="A",
					location_to="B",
				),
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="LS-TR-1",
					item_code="DUP",
				),
				frappe._dict(
					service_type="Warehousing",
					charge_scope="Linked",
					internal_job="LS-WH-1",
				),
				frappe._dict(service_type="Air", charge_scope="Main", item_code="MAIN"),
			]
		)

		groups = _linked_charge_groups_for_create(shipment)

		self.assertEqual(len(groups), 2)
		self.assertEqual(groups[0][1].service_type, "Transport")
		self.assertEqual(groups[0][1].linked_service, "LS-TR-1")
		self.assertEqual(groups[1][1].service_type, "Warehousing")
		self.assertEqual(groups[1][1].internal_job, "LS-WH-1")

	@patch(
		"logistics.utils.internal_job_from_source._job_no_for_linked_charge_row",
		return_value="",
	)
	def test_resolve_linked_charge_row_by_index(self, _mock_job_no):
		shipment = self._make_shipment(
			[
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="LS-TR-1",
				)
			]
		)

		row, idx = resolve_internal_job_detail_row_for_create(
			shipment, "Transport Order", 1
		)

		self.assertEqual(idx, 1)
		self.assertEqual(row.service_type, "Transport")
		self.assertEqual(row.job_type, "Transport Order")

	@patch("logistics.utils.internal_job_from_source._linked_service_doc_for_row")
	@patch("logistics.utils.internal_job_from_source.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_from_source.frappe.get_doc")
	def test_choices_from_linked_charges_not_internal_job_details(
		self, mock_get_doc, _mock_exists, mock_ls_doc
	):
		from logistics.utils.internal_job_from_source import get_internal_job_creation_choices

		doc = MagicMock(
			doctype="Air Shipment",
			name="ASP-315",
			sales_quote="SQ-1",
			is_internal_job=0,
			main_job_type=None,
			main_job=None,
			internal_job_details=[],
			charges=[
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="LS-TR-1",
				)
			],
		)
		doc.check_permission = MagicMock()
		mock_get_doc.return_value = doc
		mock_ls_doc.return_value = frappe._dict(service_type="Transport", name="LS-TR-1")

		with patch(
			"logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
			return_value={"allow_inbound": True},
		):
			with patch(
				"logistics.utils.internal_job_from_source._job_no_for_linked_charge_row",
				return_value="",
			):
				with patch(
					"logistics.utils.internal_job_creation_eligibility.evaluate_linked_service_internal_job_eligibility",
					return_value={"eligible": True, "message": None},
				):
					result = get_internal_job_creation_choices("Air Shipment", "ASP-315")

		self.assertEqual(len(result["choices"]), 1)
		self.assertEqual(result["choices"][0]["job_type"], "Transport Order")
		self.assertTrue(result["choices"][0]["creatable"])

	@patch("logistics.utils.internal_job_from_source.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_from_source.frappe.get_doc")
	def test_blocked_when_no_linked_charges(self, mock_get_doc, _mock_exists):
		from logistics.utils.internal_job_from_source import get_internal_job_creation_choices

		doc = MagicMock(
			doctype="Air Shipment",
			name="ASP-EMPTY",
			sales_quote="SQ-1",
			is_internal_job=0,
			main_job_type=None,
			main_job=None,
			internal_job_details=[],
			charges=[frappe._dict(service_type="Air", charge_scope="Main")],
		)
		doc.check_permission = MagicMock()
		mock_get_doc.return_value = doc

		with patch(
			"logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
			return_value={},
		):
			result = get_internal_job_creation_choices("Air Shipment", "ASP-EMPTY")

		self.assertEqual(result["choices"], [])
		self.assertIn("linked-service charges", (result.get("blocked_message") or "").lower())

	def _mock_choices_doc(self, doctype, name, charges, **extra):
		doc = MagicMock(
			doctype=doctype,
			name=name,
			sales_quote="SQ-1",
			is_internal_job=0,
			main_job_type=None,
			main_job=None,
			internal_job_details=[],
			charges=charges,
			**extra,
		)
		doc.check_permission = MagicMock()
		return doc

	@patch("logistics.utils.internal_job_from_source._linked_service_doc_for_row")
	@patch("logistics.utils.internal_job_from_source.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_from_source.frappe.get_doc")
	def test_transport_job_choices_from_linked_charges(
		self, mock_get_doc, _mock_exists, mock_ls_doc
	):
		from logistics.utils.internal_job_from_source import get_internal_job_creation_choices

		doc = self._mock_choices_doc(
			"Transport Job",
			"TJ-TEST",
			[
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="LS-TR-1",
				),
				frappe._dict(
					service_type="Air",
					charge_scope="Linked",
					linked_service="LS-AIR-1",
				),
			],
		)
		mock_get_doc.return_value = doc
		mock_ls_doc.return_value = frappe._dict(service_type="Transport", name="LS-TR-1")

		with patch(
			"logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
			return_value={"allow_inbound": True},
		):
			with patch(
				"logistics.utils.internal_job_from_source._job_no_for_linked_charge_row",
				return_value="",
			):
				with patch(
					"logistics.utils.internal_job_creation_eligibility.evaluate_linked_service_internal_job_eligibility",
					return_value={"eligible": True, "message": None},
				):
					result = get_internal_job_creation_choices("Transport Job", "TJ-TEST")

		job_types = {c["job_type"] for c in result["choices"]}
		self.assertIn("Transport Order", job_types)
		self.assertIn("Air Booking", job_types)
		self.assertTrue(all(c["creatable"] for c in result["choices"]))

	@patch("logistics.utils.internal_job_from_source._linked_service_doc_for_row")
	@patch("logistics.utils.internal_job_from_source.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_from_source.frappe.get_doc")
	def test_declaration_choices_from_linked_transport_charge(
		self, mock_get_doc, _mock_exists, mock_ls_doc
	):
		from logistics.utils.internal_job_from_source import get_internal_job_creation_choices

		doc = self._mock_choices_doc(
			"Declaration",
			"DEC-TEST",
			[
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="LS-TR-1",
				),
			],
			is_main_service=1,
			transport_order=None,
		)
		mock_get_doc.return_value = doc
		mock_ls_doc.return_value = frappe._dict(service_type="Transport", name="LS-TR-1")

		with patch(
			"logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
			return_value={},
		):
			with patch(
				"logistics.utils.internal_job_from_source._job_no_for_linked_charge_row",
				return_value="",
			):
				with patch(
					"logistics.utils.internal_job_creation_eligibility.evaluate_linked_service_internal_job_eligibility",
					return_value={"eligible": True, "message": None},
				):
					result = get_internal_job_creation_choices("Declaration", "DEC-TEST")

		self.assertEqual(len(result["choices"]), 1)
		self.assertEqual(result["choices"][0]["job_type"], "Transport Order")
		self.assertTrue(result["choices"][0]["creatable"])

	@patch("logistics.utils.internal_job_from_source.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_from_source.frappe.get_doc")
	def test_transport_job_blocked_when_only_main_scoped_charges(
		self, mock_get_doc, _mock_exists
	):
		from logistics.utils.internal_job_from_source import get_internal_job_creation_choices

		doc = self._mock_choices_doc(
			"Transport Job",
			"TJ-MAIN",
			[frappe._dict(service_type="Transport", charge_scope="Main")],
		)
		mock_get_doc.return_value = doc

		with patch(
			"logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
			return_value={},
		):
			result = get_internal_job_creation_choices("Transport Job", "TJ-MAIN")

		self.assertEqual(result["choices"], [])
		self.assertIn("linked-service charges", (result.get("blocked_message") or "").lower())

	@patch("logistics.utils.internal_job_from_source.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_from_source.frappe.get_doc")
	def test_not_creatable_when_linked_charge_missing_linked_service(
		self, mock_get_doc, _mock_exists
	):
		from logistics.utils.internal_job_from_source import get_internal_job_creation_choices

		doc = self._mock_choices_doc(
			"Air Shipment",
			"ASP-NO-LS",
			[
				frappe._dict(
					service_type="Transport",
					charge_scope="Linked",
					linked_service="",
				),
			],
		)
		mock_get_doc.return_value = doc

		with patch(
			"logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
			return_value={},
		):
			with patch(
				"logistics.utils.internal_job_from_source._job_no_for_linked_charge_row",
				return_value="",
			):
				result = get_internal_job_creation_choices("Air Shipment", "ASP-NO-LS")

		self.assertEqual(len(result["choices"]), 1)
		self.assertFalse(result["choices"][0]["creatable"])
		self.assertIn(
			"linked service",
			(result["choices"][0].get("not_creatable_message") or "").lower(),
		)
