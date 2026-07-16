# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Unit tests for Get Charges from Quotation corridor helpers.

Integration tests for list filtering live in
``logistics.pricing_center.doctype.sales_quote.test_sales_quote.TestSalesQuote.test_get_charges_from_quotation_list_filters_by_air_corridor``
and
``logistics.pricing_center.doctype.sales_quote.test_sales_quote.TestSalesQuote.test_get_charges_from_quotation_list_filters_by_airline_when_set`` and
``TestSalesQuote.test_get_charges_from_quotation_list_filters_by_cost_center_when_set``.

Manual check (initialized bench site):

  bench --site <site> execute logistics.utils.test_get_charges_from_quotation.run
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from logistics.utils.get_charges_from_quotation import (
	_corridor_mismatch_message_for_preview,
	_effective_declaration_order_filter_fields,
	_effective_sea_air_transport_corridor,
	_gcfq_customer_matches_job,
	assert_sales_quote_customer_matches_job_before_submit,
)
from logistics.utils.charge_service_type import (
	_is_customs_related_sq_charge_row,
	_merge_unified_and_legacy_customs_rows,
	customs_charges_rows_from_sales_quote_doc,
	iter_sales_quote_charge_service_type_db_values_for_canonical,
	sales_quote_charge_filters,
)
from logistics.utils.sales_quote_link_query import (
	filter_customs_charge_rows_for_declaration_order,
	sales_quote_customs_charge_row_matches_declaration_order_filters,
	sales_quote_matches_job_org_dimensions,
	sales_quote_matches_main_service,
)


class TestSalesQuoteCustomerSubmitValidation(FrappeTestCase):
	def tearDown(self):
		import frappe

		frappe.db.rollback()

	def test_customer_match_case_insensitive(self):
		self.assertTrue(_gcfq_customer_matches_job("CUST-1", "cust-1"))

	@patch("logistics.utils.get_charges_from_quotation.frappe.db.get_value", return_value="CUST-A")
	@patch(
		"logistics.utils.operational_rep_fields._resolve_sales_quote_name_from_doc",
		return_value="SQ-001",
	)
	def test_before_submit_throws_on_customer_mismatch(self, _resolve, _get_value):
		import frappe

		doc = MagicMock()
		doc.doctype = "Transport Order"
		doc.customer = "CUST-B"
		with self.assertRaises(frappe.ValidationError):
			assert_sales_quote_customer_matches_job_before_submit(doc)

	@patch(
		"logistics.utils.operational_rep_fields._resolve_sales_quote_name_from_doc",
		return_value=None,
	)
	def test_before_submit_skips_without_sales_quote(self, _resolve):
		doc = MagicMock()
		doc.doctype = "Air Booking"
		doc.local_customer = "CUST-A"
		assert_sales_quote_customer_matches_job_before_submit(doc)


class TestGetChargesCorridorHelpers(FrappeTestCase):
	"""Pure helpers; no DB."""

	def tearDown(self):
		import frappe

		frappe.db.rollback()

	def _service_type_filter_variants(self, filters):
		st = filters.get("service_type")
		if isinstance(st, (list, tuple)) and len(st) == 2 and st[0] == "in":
			return set(st[1])
		if st:
			return {st}
		return set()

	def _assert_air_only_service_type_filter(self, filters):
		variants = self._service_type_filter_variants(filters)
		air = set(iter_sales_quote_charge_service_type_db_values_for_canonical("Air"))
		sea = set(iter_sales_quote_charge_service_type_db_values_for_canonical("Sea"))
		self.assertTrue(variants <= air)
		self.assertFalse(variants & sea)

	def test_effective_corridor_air_strips(self):
		d = MagicMock()
		d.doctype = "Air Booking"
		d.origin_port = " USLAX "
		d.destination_port = "USJFK"
		d.airline = ""
		self.assertEqual(_effective_sea_air_transport_corridor(d, {}), ("USLAX", "USJFK", None, None))

	def test_effective_corridor_transport(self):
		d = MagicMock()
		d.doctype = "Transport Order"
		d.location_from = "A"
		d.location_to = "B"
		self.assertEqual(_effective_sea_air_transport_corridor(d, {}), ("A", "B", None, None))

	def test_effective_corridor_override_partial_only_origin(self):
		d = MagicMock()
		d.doctype = "Air Booking"
		d.origin_port = "A"
		d.destination_port = "B"
		d.airline = "AL1"
		# Any override → keys not sent are wildcards, not parent values.
		self.assertEqual(
			_effective_sea_air_transport_corridor(d, {"origin_port": "O1"}),
			("O1", "", None, None),
		)

	def test_effective_corridor_override_airline_only(self):
		d = MagicMock()
		d.doctype = "Air Booking"
		d.origin_port = "A"
		d.destination_port = "B"
		d.airline = "AL1"
		self.assertEqual(
			_effective_sea_air_transport_corridor(d, {"airline": "AL2"}),
			("", "", "AL2", None),
		)

	def test_effective_declaration_order_fields(self):
		d = MagicMock()
		d.doctype = "Declaration Order"
		d.customs_authority = " CA "
		d.declaration_type = "Import"
		d.customs_broker = "BR"
		d.transport_mode = "TM"
		d.port_of_loading = " USNYC "
		d.port_of_discharge = "USLAX"
		self.assertEqual(
			_effective_declaration_order_filter_fields(d, {}),
			("CA", "Import", "BR", "TM", "USNYC", "USLAX"),
		)

	@patch("logistics.utils.get_charges_from_quotation.sales_quote_matches_job_corridor", return_value=False)
	def test_corridor_mismatch_message_when_quote_no_match(self, _mock):
		doc = MagicMock()
		doc.doctype = "Air Booking"
		doc.origin_port = "USLAX"
		doc.destination_port = "USJFK"
		doc.airline = ""
		msg = _corridor_mismatch_message_for_preview(doc, "Air", "SQ-TEST-001", {})
		self.assertIsNotNone(msg)
		self.assertIn("SQ-TEST-001", msg)

	@patch("logistics.utils.sales_quote_link_query.frappe.db.get_value")
	def test_org_dimensions_blank_quote_header_is_wildcard(self, mock_gv):
		mock_gv.return_value = {"branch": "", "cost_center": "", "profit_center": ""}
		self.assertTrue(
			sales_quote_matches_job_org_dimensions("SQ-X", job_profit_center="PC-FILTER")
		)

	@patch("logistics.utils.sales_quote_link_query.frappe.db.get_value")
	def test_main_service_match_customs(self, mock_gv):
		mock_gv.return_value = "Customs"
		self.assertTrue(sales_quote_matches_main_service("SQ-1", "Customs"))
		self.assertFalse(sales_quote_matches_main_service("SQ-1", "Sea"))

	@patch("logistics.utils.sales_quote_link_query.frappe.db.exists", return_value=True)
	@patch("logistics.utils.sales_quote_link_query.frappe.db.get_value")
	def test_main_service_sea_quote_not_customs(self, mock_gv, _mock_exists):
		mock_gv.return_value = "Sea"
		self.assertFalse(sales_quote_matches_main_service("SQ-SEA", "Customs"))

	@patch("logistics.utils.sales_quote_link_query.frappe.db.get_value")
	def test_org_dimensions_nonblank_mismatch_fails(self, mock_gv):
		mock_gv.return_value = {"branch": "", "cost_center": "", "profit_center": "PC-OTHER"}
		self.assertFalse(
			sales_quote_matches_job_org_dimensions("SQ-X", job_profit_center="PC-FILTER")
		)

	def test_customs_related_row_by_params_without_service_type(self):
		row = {"customs_authority": "CA-1", "declaration_type": "Import"}
		self.assertTrue(_is_customs_related_sq_charge_row(row))
		self.assertFalse(_is_customs_related_sq_charge_row({"service_type": "Air"}))

	def test_merge_unified_and_legacy_customs_rows(self):
		unified = [{"item_code": "ITEM-1", "customs_authority": "CA-1", "declaration_type": "Import"}]
		legacy = [
			{"item_code": "ITEM-1", "customs_authority": "CA-1", "declaration_type": "Import"},
			{"item_code": "ITEM-2", "customs_authority": "CA-1", "declaration_type": "Import"},
		]
		merged = _merge_unified_and_legacy_customs_rows(unified, legacy)
		self.assertEqual(len(merged), 2)

	def test_declaration_order_row_filter_includes_all_matching_lines(self):
		parent = MagicMock()
		parent.doctype = "Declaration Order"
		parent.customs_authority = "CA-1"
		parent.declaration_type = "Import"
		parent.customs_broker = ""
		parent.transport_mode = ""
		rows = [
			{"service_type": "Customs", "customs_authority": "CA-1", "declaration_type": "Import"},
			{"service_type": "Customs", "customs_authority": "CA-1", "declaration_type": "Export"},
			{"service_type": "Customs", "customs_authority": "CA-2", "declaration_type": "Import"},
		]
		filtered = filter_customs_charge_rows_for_declaration_order(parent, rows)
		self.assertEqual(len(filtered), 1)
		self.assertEqual(filtered[0]["declaration_type"], "Import")

	def test_declaration_order_row_filter_blank_broker_matches_any(self):
		self.assertTrue(
			sales_quote_customs_charge_row_matches_declaration_order_filters(
				{"service_type": "Customs", "customs_broker": ""},
				customs_broker="BR-1",
			)
		)

	def test_declaration_order_row_filter_different_broker_excluded(self):
		self.assertFalse(
			sales_quote_customs_charge_row_matches_declaration_order_filters(
				{"service_type": "Customs", "customs_broker": "ABC Brokerage"},
				customs_broker="B-001",
			)
		)
		self.assertTrue(
			sales_quote_customs_charge_row_matches_declaration_order_filters(
				{"service_type": "Customs", "customs_broker": "ABC Brokerage"},
				customs_broker="ABC Brokerage",
			)
		)

	@patch("logistics.utils.charge_service_type._legacy_customs_rows_for_quote", return_value=[])
	def test_customs_charges_rows_returns_all_when_separate_billings_off(self, _mock_legacy):
		parent = MagicMock()
		parent.doctype = "Declaration Order"
		parent.is_internal_job = 0
		parent.is_main_service = 0
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.separate_billings_per_service_type = 0
		sq.charges = [
			MagicMock(service_type="Sea"),
			MagicMock(service_type="Customs"),
			MagicMock(service_type="Transport"),
			MagicMock(service_type="Warehousing"),
		]
		sq.routing_legs = []
		sq.customs = []
		rows = customs_charges_rows_from_sales_quote_doc(parent, sq)
		self.assertEqual(len(rows), 4)

	@patch(
		"logistics.utils.routing_quote_context.routing_leg_service_type_for_parent",
		return_value=None,
	)
	def test_sales_quote_charge_filters_gcfq_main_only_restricts_when_separate_billings_on(self, _mock_rt):
		"""GCFQ adds ``service_type`` filter when separate billings is on."""
		import frappe

		parent = MagicMock()
		parent.doctype = "Sea Booking"
		parent.is_internal_job = 0
		parent.is_main_service = 1
		parent.flags = frappe._dict({"gcfq_main_service_only": 1})
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.main_service = "Sea"
		sq.separate_billings_per_service_type = 1
		filters = sales_quote_charge_filters(parent, sq)
		self.assertIn("service_type", filters)

	@patch(
		"logistics.utils.routing_quote_context.routing_leg_service_type_for_parent",
		return_value=None,
	)
	def test_sales_quote_charge_filters_gcfq_combined_billing_returns_all(self, _mock_rt):
		"""GCFQ on main service with separate billings off loads all quote charge rows."""
		import frappe

		parent = MagicMock()
		parent.doctype = "Sea Booking"
		parent.is_internal_job = 0
		parent.is_main_service = 1
		parent.flags = frappe._dict({"gcfq_main_service_only": 1})
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.main_service = "Sea"
		sq.separate_billings_per_service_type = 0
		filters = sales_quote_charge_filters(parent, sq)
		self.assertNotIn("service_type", filters)

	@patch(
		"logistics.utils.routing_quote_context.routing_leg_service_type_for_parent",
		return_value=None,
	)
	def test_sales_quote_charge_filters_separate_off_matching_quote_main_service_returns_all(self, _mock_rt):
		"""Separate billings off: Sea Booking gets all charges when quote Main Service is Sea."""
		parent = MagicMock()
		parent.doctype = "Sea Booking"
		parent.is_internal_job = 0
		parent.is_main_service = 0
		parent.flags = None
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.main_service = "Sea"
		sq.separate_billings_per_service_type = 0
		filters = sales_quote_charge_filters(parent, sq)
		self.assertNotIn("service_type", filters)

	@patch(
		"logistics.utils.routing_quote_context.routing_leg_service_type_for_parent",
		return_value=None,
	)
	def test_sales_quote_charge_filters_separate_off_other_service_type_restricts(self, _mock_rt):
		"""Separate billings off: Air Booking still gets only Air when quote Main Service is Sea."""
		parent = MagicMock()
		parent.doctype = "Air Booking"
		parent.is_internal_job = 0
		parent.is_main_service = 0
		parent.flags = None
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.main_service = "Sea"
		sq.separate_billings_per_service_type = 0
		filters = sales_quote_charge_filters(parent, sq)
		self._assert_air_only_service_type_filter(filters)

	@patch(
		"logistics.utils.routing_quote_context.routing_leg_service_type_for_parent",
		return_value=None,
	)
	def test_sales_quote_charge_filters_air_booking_excludes_sea_for_special_project_main(self, _mock_rt):
		"""Multimodal quote with Main Service Special Project: Air Booking gets Air charges only."""
		parent = MagicMock()
		parent.doctype = "Air Booking"
		parent.is_internal_job = 0
		parent.is_main_service = 0
		parent.flags = None
		sq = MagicMock()
		sq.name = "PQ00234"
		sq.main_service = "Special Project"
		sq.separate_billings_per_service_type = 0
		filters = sales_quote_charge_filters(parent, sq)
		self._assert_air_only_service_type_filter(filters)

	@patch("logistics.utils.charge_service_type._legacy_customs_rows_for_quote", return_value=[])
	def test_customs_charges_rows_gcfq_main_only_keeps_customs_only_when_separate_on(self, _mock_legacy):
		"""GCFQ restricts Main Declaration Order to Customs rows when separate billings is on."""
		import frappe

		parent = MagicMock()
		parent.doctype = "Declaration Order"
		parent.is_internal_job = 0
		parent.is_main_service = 1
		parent.customs_authority = ""
		parent.declaration_type = ""
		parent.customs_broker = ""
		parent.transport_mode = ""
		parent.flags = frappe._dict({"gcfq_main_service_only": 1})
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.main_service = "Customs"
		sq.separate_billings_per_service_type = 1
		sq.charges = [
			MagicMock(
				service_type="Sea",
				customs_authority="",
				declaration_type="",
				customs_broker="",
			),
			MagicMock(
				service_type="Customs",
				customs_authority="",
				declaration_type="",
				customs_broker="",
			),
			MagicMock(
				service_type="Transport",
				customs_authority="",
				declaration_type="",
				customs_broker="",
			),
		]
		sq.routing_legs = []
		sq.customs = []
		rows = customs_charges_rows_from_sales_quote_doc(parent, sq)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].service_type, "Customs")

	@patch("logistics.utils.charge_service_type._legacy_customs_rows_for_quote", return_value=[])
	def test_customs_charges_rows_gcfq_combined_billing_returns_all(self, _mock_legacy):
		"""GCFQ on main Customs job with separate billings off returns all quote charge rows."""
		import frappe

		parent = MagicMock()
		parent.doctype = "Declaration Order"
		parent.is_internal_job = 0
		parent.is_main_service = 1
		parent.customs_authority = ""
		parent.declaration_type = ""
		parent.customs_broker = ""
		parent.transport_mode = ""
		parent.flags = frappe._dict({"gcfq_main_service_only": 1})
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.main_service = "Customs"
		sq.separate_billings_per_service_type = 0
		sq.charges = [
			MagicMock(
				service_type="Sea",
				customs_authority="",
				declaration_type="",
				customs_broker="",
			),
			MagicMock(
				service_type="Customs",
				customs_authority="",
				declaration_type="",
				customs_broker="",
			),
			MagicMock(
				service_type="Transport",
				customs_authority="",
				declaration_type="",
				customs_broker="",
			),
		]
		sq.routing_legs = []
		sq.customs = []
		rows = customs_charges_rows_from_sales_quote_doc(parent, sq)
		self.assertEqual(len(rows), 3)

	@patch("logistics.utils.charge_service_type._legacy_customs_rows_for_quote", return_value=[])
	def test_customs_charges_rows_merges_params_only_unified_lines(self, _mock_legacy):
		parent = MagicMock()
		parent.doctype = "Declaration Order"
		parent.is_internal_job = 0
		parent.is_main_service = 0
		parent.customs_authority = ""
		parent.declaration_type = ""
		parent.customs_broker = ""
		parent.transport_mode = ""
		sq = MagicMock()
		sq.name = "SQ-1"
		sq.separate_billings_per_service_type = 1
		sq.charges = [
			MagicMock(
				service_type="Air",
				customs_authority="CA-1",
				declaration_type="Import",
				customs_broker="",
			),
			MagicMock(service_type="Customs", customs_authority="", declaration_type="", customs_broker=""),
		]
		sq.routing_legs = []
		sq.customs = []
		with patch(
			"logistics.utils.charge_service_type.is_parent_main_job_for_quote_charges",
			return_value=False,
		):
			rows = customs_charges_rows_from_sales_quote_doc(parent, sq)
		self.assertEqual(len(rows), 2)


def run():
	"""Smoke-test helpers on a live site (no DB writes)."""
	from unittest.mock import MagicMock

	from logistics.utils.get_charges_from_quotation import _effective_sea_air_transport_corridor

	d = MagicMock()
	d.doctype = "Air Booking"
	d.origin_port = " X "
	d.destination_port = "Y"
	d.airline = ""
	assert _effective_sea_air_transport_corridor(d, {}) == ("X", "Y", None, None), _effective_sea_air_transport_corridor(
		d, {}
	)
	print("logistics.utils.test_get_charges_from_quotation.run: OK")
