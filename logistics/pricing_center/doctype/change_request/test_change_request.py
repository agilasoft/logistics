# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from logistics.pricing_center.additional_charge_to_job import (
	INTERNAL_JOB_SATELLITE_JOB_TYPES,
	MAIN_JOB_TYPES_FOR_CHANGE_REQUEST,
	_charge_row_service_type_matches_job,
)
from logistics.pricing_center.change_request_to_job import (
	_resolve_main_and_default_internal_job,
	apply_change_request_charges_to_job,
	change_request_cost_rows_missing_on_main_job,
	ensure_change_request_cost_rows_on_job,
	merge_sales_quote_revenue_into_change_request_job_rows,
)


class TestChangeRequestToJob(UnitTestCase):
	def test_charge_row_service_type_matches_job_accepts_canonical_aliases(self):
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "air"))
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "Air"))
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "Warehousing"))
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "Transport"))
		self.assertTrue(_charge_row_service_type_matches_job("Sea Shipment", "sea"))
		self.assertTrue(_charge_row_service_type_matches_job("Sea Shipment", "Customs"))
		self.assertFalse(_charge_row_service_type_matches_job("Transport Job", "Air"))

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_apply_change_request_accepts_lowercase_air_service_type(
		self, _exists, mock_get_doc, _msgprint
	):
		job_doc = MagicMock()
		job_doc.charges = []
		job_doc.append = MagicMock()
		mock_get_doc.return_value = job_doc

		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[
				frappe._dict(
					name="crc-1",
					item_code="EXTRA-FEE",
					service_type="air",
					estimated_cost=100,
					cost_quantity=1,
				),
			],
		)

		apply_change_request_charges_to_job(cr_doc)

		self.assertEqual(job_doc.append.call_count, 1)
		charge_data = job_doc.append.call_args[0][1]
		self.assertEqual(charge_data["item_code"], "EXTRA-FEE")
		self.assertEqual(charge_data["change_request"], "CR-TEST")
		job_doc.save.assert_called_once()

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_apply_change_request_accepts_non_matching_service_type_on_job_scoped_cr(
		self, _exists, mock_get_doc, _msgprint
	):
		job_doc = MagicMock()
		job_doc.charges = []
		job_doc.append = MagicMock()
		mock_get_doc.return_value = job_doc

		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[
				frappe._dict(
					name="crc-1",
					item_code="AMBRACK",
					service_type="Warehousing",
					estimated_cost=78390,
					cost_quantity=1,
				),
			],
		)

		apply_change_request_charges_to_job(cr_doc)

		self.assertEqual(job_doc.append.call_count, 1)
		charge_data = job_doc.append.call_args[0][1]
		self.assertEqual(charge_data["item_code"], "AMBRACK")
		self.assertEqual(charge_data["service_type"], "Warehousing")

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_merge_sq_revenue_updates_row_matched_by_change_request_charge(
		self, _exists, mock_get_doc, _msgprint
	):
		job_row = frappe._dict(
			change_request="CR-TEST",
			change_request_charge="crc-1",
			estimated_revenue=0,
			unit_rate=0,
		)
		job_doc = frappe._dict(charges=[job_row])
		job_doc.flags = frappe._dict()
		job_doc.save = MagicMock()
		mock_get_doc.return_value = job_doc

		sq_doc = frappe._dict(
			name="OOQ-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			change_request="CR-TEST",
			charges=[
				frappe._dict(
					item_code="AMBRACK",
					service_type="Warehousing",
					change_request_charge="crc-1",
					charge_type="Margin",
					calculation_method="Flat Rate",
					quantity=1,
					unit_rate=197650,
					estimated_revenue=197650,
				),
			],
		)

		updated = merge_sales_quote_revenue_into_change_request_job_rows(sq_doc)

		self.assertEqual(updated, 1)
		self.assertEqual(job_row.sales_quote_link, "OOQ-TEST")
		job_doc.save.assert_called_once()

	@patch("logistics.pricing_center.change_request_to_job.apply_change_request_charges_to_job")
	def test_ensure_change_request_cost_rows_on_job_applies_when_missing(self, mock_apply):
		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[frappe._dict(name="crc-1", item_code="AMBRACK")],
		)
		job_doc = frappe._dict(charges=[])
		with patch(
			"logistics.pricing_center.change_request_to_job._resolve_main_and_default_internal_job",
			return_value=("Air Shipment", "ASP-TEST", None),
		), patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True), patch(
			"logistics.pricing_center.change_request_to_job.frappe.get_doc",
			return_value=job_doc,
		):
			self.assertTrue(change_request_cost_rows_missing_on_main_job(cr_doc))
			ensure_change_request_cost_rows_on_job(cr_doc)
		mock_apply.assert_called_once_with(cr_doc)

	@patch("logistics.pricing_center.change_request_to_job.apply_change_request_charges_to_job")
	def test_ensure_change_request_cost_rows_on_job_skips_when_present(self, mock_apply):
		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[frappe._dict(name="crc-1", item_code="AMBRACK")],
		)
		job_doc = frappe._dict(
			charges=[
				frappe._dict(
					change_request="CR-TEST",
					change_request_charge="crc-1",
				),
			]
		)
		with patch(
			"logistics.pricing_center.change_request_to_job._resolve_main_and_default_internal_job",
			return_value=("Air Shipment", "ASP-TEST", None),
		), patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True), patch(
			"logistics.pricing_center.change_request_to_job.frappe.get_doc",
			return_value=job_doc,
		):
			self.assertFalse(change_request_cost_rows_missing_on_main_job(cr_doc))
			ensure_change_request_cost_rows_on_job(cr_doc)
		mock_apply.assert_not_called()

	# -----------------------------------------------------------------------------------
	# Bidirectional Main ↔ Internal Job satellite mirror
	# -----------------------------------------------------------------------------------

	def test_main_and_satellite_constants_cover_expected_job_types(self):
		"""Sanity: the constants used by the resolver list the doctypes Change Request supports."""
		self.assertIn("Sea Shipment", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Air Shipment", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Transport Job", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Warehouse Job", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Declaration", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Special Project", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Sea Booking", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Air Booking", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Transport Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Declaration Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Inbound Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Release Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		# A doctype must be in exactly one set (Main vs Satellite) — never both.
		self.assertEqual(
			MAIN_JOB_TYPES_FOR_CHANGE_REQUEST & INTERNAL_JOB_SATELLITE_JOB_TYPES,
			set(),
		)

	def test_resolve_main_for_change_request_on_main_returns_target_directly(self):
		"""CR filed on a Main job → resolver returns the target itself with no default IJ."""
		cr = frappe._dict(job_type="Sea Shipment", job="SS-001")
		mt, mn, ij = _resolve_main_and_default_internal_job(cr)
		self.assertEqual(mt, "Sea Shipment")
		self.assertEqual(mn, "SS-001")
		self.assertIsNone(ij)

	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.get_value")
	def test_resolve_main_for_change_request_on_ij_satellite_walks_back_links(
		self, mock_get_value, _exists
	):
		"""CR filed on an IJ satellite → resolver walks main_job_type/main_job back-links."""
		mock_get_value.return_value = {
			"main_job_type": "Sea Shipment",
			"main_job": "SS-002",
			"internal_job": "IJ-2026-000001",
			"is_internal_job": 1,
		}
		cr = frappe._dict(job_type="Sea Booking", job="SB-9")
		mt, mn, ij = _resolve_main_and_default_internal_job(cr)
		self.assertEqual(mt, "Sea Shipment")
		self.assertEqual(mn, "SS-002")
		self.assertEqual(ij, "IJ-2026-000001")

	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.get_value")
	def test_resolve_main_returns_none_when_satellite_is_not_flagged_as_ij(
		self, mock_get_value, _exists
	):
		"""Satellite with ``is_internal_job=0`` is treated as standalone — no Main mirroring."""
		mock_get_value.return_value = {
			"main_job_type": "",
			"main_job": "",
			"internal_job": "",
			"is_internal_job": 0,
		}
		cr = frappe._dict(job_type="Sea Booking", job="SB-LEGACY")
		mt, mn, ij = _resolve_main_and_default_internal_job(cr)
		self.assertIsNone(mt)
		self.assertIsNone(mn)
		self.assertIsNone(ij)

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job._safe_append_charge_to_doc")
	@patch("logistics.pricing_center.change_request_to_job._satellite_for_internal_job")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_apply_cr_on_main_with_ij_tagged_row_mirrors_to_satellite(
		self,
		_exists,
		mock_get_doc,
		mock_sat_lookup,
		mock_safe_append,
		_msgprint,
	):
		"""CR on Main with an Internal Job tag on a row → row mirrored to the IJ's satellite booking."""
		main_doc = MagicMock(name="main_doc")
		main_doc.charges = []
		main_doc.doctype = "Sea Shipment"
		sat_doc = MagicMock(name="sat_doc")
		sat_doc.charges = []
		sat_doc.doctype = "Sea Booking"

		def get_doc_side_effect(doctype, name):
			if doctype == "Sea Shipment":
				return main_doc
			if doctype == "Sea Booking":
				return sat_doc
			return MagicMock()

		mock_get_doc.side_effect = get_doc_side_effect
		mock_sat_lookup.return_value = ("Sea Booking", "SB-001")
		mock_safe_append.return_value = True

		cr_doc = frappe._dict(
			name="CR-IJ",
			job_type="Sea Shipment",
			job="SS-100",
			charges=[
				frappe._dict(
					name="crc-1",
					item_code="EXTRA",
					service_type="Sea",
					internal_job="IJ-X",
					estimated_cost=50,
					cost_quantity=1,
				),
			],
		)
		apply_change_request_charges_to_job(cr_doc)

		# Both Main and Satellite should have received an appended row.
		# _safe_append_charge_to_doc is called twice: once for main, once for satellite.
		self.assertEqual(mock_safe_append.call_count, 2)
		target_docs_appended_to = {call.args[0] for call in mock_safe_append.call_args_list}
		self.assertIn(main_doc, target_docs_appended_to)
		self.assertIn(sat_doc, target_docs_appended_to)
		# Main row should carry the Internal Job scope tag.
		main_call = next(c for c in mock_safe_append.call_args_list if c.args[0] is main_doc)
		main_payload = main_call.args[1]
		self.assertEqual(main_payload.get("change_request"), "CR-IJ")
		# The dict handed to ``_safe_append_charge_to_doc`` must already carry the IJ scope —
		# ``_decorate_charge_dict_with_internal_job_scope`` is responsible for it and uses direct
		# assignment (not ``setdefault``) so even mapper-produced ``Main`` would be overwritten.
		self.assertEqual(main_payload.get("charge_scope"), "Internal Job")
		self.assertEqual(main_payload.get("internal_job"), "IJ-X")
		# Same expectation on the satellite side — the row mirror must persist as IJ-scoped.
		sat_call = next(c for c in mock_safe_append.call_args_list if c.args[0] is sat_doc)
		sat_payload = sat_call.args[1]
		self.assertEqual(sat_payload.get("charge_scope"), "Internal Job")
		self.assertEqual(sat_payload.get("internal_job"), "IJ-X")
		main_doc.save.assert_called_once()
		sat_doc.save.assert_called_once()

	def test_decorate_charge_dict_overrides_existing_main_scope(self):
		"""Decoration must overwrite a pre-existing ``charge_scope='Main'`` with ``Internal Job``.

		This guards the regression where the Sales Quote Charge (created from a CR Charge) was
		showing as ``Main`` on the Internal Job satellite booking because the default ``Main``
		scope was never overwritten by ``setdefault``-style decoration.
		"""
		from logistics.pricing_center.change_request_to_job import (
			_decorate_charge_dict_with_internal_job_scope,
		)

		# Use a real Frappe doctype with the scope columns (Sea Booking → Sea Booking Charges).
		target = frappe._dict(doctype="Sea Booking")
		payload = {"item_code": "EXTRA", "charge_scope": "Main", "internal_job": "OLD"}
		_decorate_charge_dict_with_internal_job_scope(payload, target, "IJ-X")
		self.assertEqual(payload["charge_scope"], "Internal Job")
		self.assertEqual(payload["internal_job"], "IJ-X")

	def test_sales_quote_dict_from_ij_tagged_cr_charge_sets_internal_job_scope(self):
		"""Sales Quote Charge produced from an IJ-tagged CR Charge must carry the IJ scope.

		Without this, the SQ Charge inherits the schema default ``charge_scope='Main'`` and
		any downstream copy (``_populate_charges_from_sales_quote_doc`` Path-2 fallback, GCFQ
		per-scope helpers, …) reads ``Main`` and writes ``Main`` on the satellite booking.
		"""
		from logistics.pricing_center.doctype.change_request.change_request import (
			_charge_row_as_sales_quote_dict,
		)

		def _fake_charge_row(**kw):
			data = dict(kw)
			row = MagicMock()
			row.as_dict = MagicMock(return_value=data)
			return row

		# CR Charge tagged with internal_job=IJ-X — the SQ row must inherit IJ scope.
		row = _fake_charge_row(
			name="crc-1",
			item_code="EXTRA",
			service_type="Sea",
			internal_job="IJ-X",
			estimated_cost=100,
			cost_quantity=1,
		)
		out = _charge_row_as_sales_quote_dict(row, "Sea")
		self.assertEqual(out["charge_scope"], "Internal Job")
		self.assertEqual(out["internal_job"], "IJ-X")
		self.assertEqual(out["item_code"], "EXTRA")

		# CR Charge with no internal_job → SQ row stays without forcing scope (defaults to Main).
		row2 = _fake_charge_row(
			name="crc-2",
			item_code="EXTRA2",
			service_type="Sea",
			estimated_cost=100,
			cost_quantity=1,
		)
		out2 = _charge_row_as_sales_quote_dict(row2, "Sea")
		self.assertNotIn("charge_scope", out2)
