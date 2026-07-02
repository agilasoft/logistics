# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for the Sales Quote (One-off) Internal Job propagation.

Covers three behaviours:

1. The ``Sales Quote`` charge-row mapper helpers
   (:func:`logistics.utils.sales_quote_charge_copy.apply_scope_tagging_to_mapped_charge` and
   :func:`logistics.utils.sales_quote_charge_copy.extend_charge_fields_with_scope_and_internal_job`)
   are pure-Python and tested against MagicMock rows.

2. The IJ persistence gate
   (:func:`logistics.utils.internal_job_persistence._should_run_internal_job_sync_for_parent`)
   only runs for ``quotation_type = "One-off"`` Sales Quotes.

3. The on-form validator
   (``SalesQuote.validate_internal_job_charge_tagging``) rejects charges that are scope-tagged
   ``Internal Job`` without a link and silently clears tags on non-One-off quotes.

Full DB-backed integration of the propagation flow is exercised manually via the
``_create_*_from_sales_quote`` desk action; this file keeps the fast unit coverage.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_persistence import (
	_should_run_internal_job_sync_for_parent,
)
from logistics.utils.sales_quote_charge_copy import (
	apply_scope_tagging_to_mapped_charge,
	extend_charge_fields_with_scope_and_internal_job,
)


class TestApplyScopeTaggingToMappedCharge(FrappeTestCase):
	def test_dict_source_main_scope_omits_internal_job(self):
		target = {}
		apply_scope_tagging_to_mapped_charge(
			{"charge_scope": "Main", "internal_job": "IJ-001"}, target
		)
		self.assertEqual(target["charge_scope"], "Main")
		self.assertNotIn("internal_job", target)
		self.assertNotIn("linked_service", target)

	def test_dict_source_internal_job_scope_copies_link(self):
		target = {}
		apply_scope_tagging_to_mapped_charge(
			{"charge_scope": "Internal Job", "internal_job": "IJ-001"}, target
		)
		self.assertEqual(target["charge_scope"], "Linked")
		self.assertEqual(target["linked_service"], "IJ-001")
		self.assertEqual(target["internal_job"], "IJ-001")

	def test_dict_source_linked_scope_copies_linked_service(self):
		target = {}
		apply_scope_tagging_to_mapped_charge(
			{"charge_scope": "Linked", "linked_service": "LS-001"}, target
		)
		self.assertEqual(target["charge_scope"], "Linked")
		self.assertEqual(target["linked_service"], "LS-001")
		self.assertEqual(target["internal_job"], "LS-001")

	def test_dict_source_missing_scope_defaults_to_main(self):
		target = {}
		apply_scope_tagging_to_mapped_charge({}, target)
		self.assertEqual(target["charge_scope"], "Main")
		self.assertNotIn("internal_job", target)
		self.assertNotIn("linked_service", target)

	def test_object_source_attribute_access(self):
		src = MagicMock(charge_scope="Internal Job", internal_job="IJ-XYZ")
		target = {}
		apply_scope_tagging_to_mapped_charge(src, target)
		self.assertEqual(target["charge_scope"], "Linked")
		self.assertEqual(target["linked_service"], "IJ-XYZ")
		self.assertEqual(target["internal_job"], "IJ-XYZ")

	def test_internal_job_scope_without_link_does_not_set_blank_internal_job(self):
		target = {}
		apply_scope_tagging_to_mapped_charge(
			{"charge_scope": "Internal Job", "internal_job": "   "}, target
		)
		self.assertEqual(target["charge_scope"], "Linked")
		self.assertNotIn("internal_job", target)
		self.assertNotIn("linked_service", target)

	def test_whitespace_scope_trimmed(self):
		target = {}
		apply_scope_tagging_to_mapped_charge(
			{"charge_scope": "  Internal Job  ", "internal_job": "IJ-1"}, target
		)
		self.assertEqual(target["charge_scope"], "Linked")
		self.assertEqual(target["linked_service"], "IJ-1")
		self.assertEqual(target["internal_job"], "IJ-1")


class TestExtendChargeFieldsHelper(FrappeTestCase):
	def test_adds_missing_fields(self):
		fields = ["item_code", "service_type"]
		extended = extend_charge_fields_with_scope_and_internal_job(fields)
		self.assertIn("charge_scope", extended)
		self.assertIn("internal_job", extended)
		self.assertIn("linked_service", extended)
		# Original entries preserved.
		self.assertIn("item_code", extended)
		self.assertIn("service_type", extended)

	def test_does_not_duplicate_existing_fields(self):
		fields = ["item_code", "charge_scope", "internal_job", "linked_service"]
		extended = extend_charge_fields_with_scope_and_internal_job(fields)
		self.assertEqual(extended.count("charge_scope"), 1)
		self.assertEqual(extended.count("internal_job"), 1)
		self.assertEqual(extended.count("linked_service"), 1)

	def test_returns_new_list_not_in_place_mutation(self):
		fields = ["item_code"]
		extended = extend_charge_fields_with_scope_and_internal_job(fields)
		self.assertEqual(fields, ["item_code"])
		self.assertNotEqual(extended, fields)

	def test_handles_none_input(self):
		extended = extend_charge_fields_with_scope_and_internal_job(None)  # type: ignore[arg-type]
		self.assertEqual(extended, ["charge_scope", "internal_job", "linked_service"])


class TestInternalJobSyncGate(FrappeTestCase):
	"""Internal Job creation runs for every parent in ``INTERNAL_JOB_DETAIL_PARENTS`` — including
	Sales Quote of any ``quotation_type`` — because a single Sales Quote can carry multiple
	Internal Jobs. The gate is permissive; UI visibility is enforced by the DocType ``depends_on``.
	"""

	def test_non_sales_quote_parent_always_runs(self):
		for dt in ("Sea Booking", "Air Booking", "Transport Order"):
			doc = MagicMock(doctype=dt, quotation_type=None)
			self.assertTrue(_should_run_internal_job_sync_for_parent(doc))

	def test_sales_quote_one_off_runs(self):
		doc = MagicMock(doctype="Sales Quote", quotation_type="One-off")
		self.assertTrue(_should_run_internal_job_sync_for_parent(doc))

	def test_sales_quote_regular_also_runs(self):
		doc = MagicMock(doctype="Sales Quote", quotation_type="Regular")
		self.assertTrue(_should_run_internal_job_sync_for_parent(doc))

	def test_sales_quote_project_also_runs(self):
		doc = MagicMock(doctype="Sales Quote", quotation_type="Project")
		self.assertTrue(_should_run_internal_job_sync_for_parent(doc))

	def test_sales_quote_blank_quotation_type_also_runs(self):
		doc = MagicMock(doctype="Sales Quote", quotation_type=None)
		self.assertTrue(_should_run_internal_job_sync_for_parent(doc))


class TestSalesQuoteChargeTagValidation(FrappeTestCase):
	"""Drive ``SalesQuote.validate_internal_job_charge_tagging`` directly via a Sales Quote stub.

	We avoid building a full Sales Quote document (which depends on many master data masters being
	seeded) by instantiating a minimal stand-in that mimics the attribute surface used by the
	validator. The validator only touches ``charges`` and ``internal_job_details`` so this is
	sufficient. The validator now applies the same rules to every ``quotation_type`` — Internal
	Job creation does not validate ``quotation_type``.
	"""

	def _stub(self, *, quotation_type, charges, internal_job_details):
		from logistics.pricing_center.doctype.sales_quote.sales_quote import SalesQuote

		stub = MagicMock(spec=SalesQuote)
		stub.quotation_type = quotation_type
		stub.charges = charges
		stub.internal_job_details = internal_job_details
		stub.validate_internal_job_charge_tagging = (
			lambda: SalesQuote.validate_internal_job_charge_tagging(stub)
		)
		return stub

	def test_main_scope_clears_stale_internal_job_on_any_quote_type(self):
		for qt in ("Regular", "One-off", "Project", None):
			with self.subTest(quotation_type=qt):
				row = MagicMock(charge_scope="Main", internal_job="IJ-STALE", idx=1)
				stub = self._stub(
					quotation_type=qt, charges=[row], internal_job_details=[]
				)
				stub.validate_internal_job_charge_tagging()
				self.assertEqual(row.charge_scope, "Main")
				self.assertIsNone(row.internal_job)

	def test_internal_job_scope_without_link_throws_on_any_quote_type(self):
		for qt in ("Regular", "One-off", "Project", None):
			with self.subTest(quotation_type=qt):
				row = MagicMock(charge_scope="Internal Job", internal_job=None, idx=2)
				stub = self._stub(
					quotation_type=qt, charges=[row], internal_job_details=[]
				)
				with self.assertRaises(frappe.exceptions.ValidationError):
					stub.validate_internal_job_charge_tagging()

	def test_internal_job_scope_unknown_link_throws(self):
		row = MagicMock(charge_scope="Internal Job", internal_job="IJ-NOT-ON-QUOTE", idx=3)
		known_ij_row = MagicMock(internal_job="IJ-ON-QUOTE")
		stub = self._stub(
			quotation_type="Regular", charges=[row], internal_job_details=[known_ij_row]
		)
		with self.assertRaises(frappe.exceptions.ValidationError):
			stub.validate_internal_job_charge_tagging()

	def test_internal_job_scope_known_link_passes(self):
		row = MagicMock(charge_scope="Internal Job", internal_job="IJ-OK", idx=4)
		known_ij_row = MagicMock(internal_job="IJ-OK")
		stub = self._stub(
			quotation_type="One-off", charges=[row], internal_job_details=[known_ij_row]
		)
		stub.validate_internal_job_charge_tagging()
		self.assertEqual(row.charge_scope, "Internal Job")
		self.assertEqual(row.internal_job, "IJ-OK")

	def test_no_materialised_ij_rows_still_allows_link(self):
		# When no IJ rows have a materialised ``internal_job`` (e.g. first save), the validator
		# falls back to "any link is acceptable" since we cannot compare against an empty set.
		# This matches the on-form UX: pick a saved IJ from the dropdown.
		row = MagicMock(charge_scope="Internal Job", internal_job="IJ-FRESH", idx=5)
		empty_ij_row = MagicMock(internal_job=None)
		stub = self._stub(
			quotation_type="One-off", charges=[row], internal_job_details=[empty_ij_row]
		)
		stub.validate_internal_job_charge_tagging()
		self.assertEqual(row.internal_job, "IJ-FRESH")


class TestPropagateInternalJobsHelpers(FrappeTestCase):
	"""Pure-Python guards on the propagation entry points (no DB writes required).

	Propagation does **not** gate on ``quotation_type``; it runs whenever the quote owns Internal
	Jobs. These tests cover the missing-input early returns, which are the only branches that can
	be exercised without a real DB-backed Internal Job.

	``MagicMock(name=...)`` is reserved by ``Mock``; the ``name`` attribute is assigned post-
	construction in every test below.
	"""

	def _make_quote(self, *, quotation_type="One-off", name="SQ-TEST"):
		sq = MagicMock(quotation_type=quotation_type)
		sq.name = name
		return sq

	def _make_booking(self, *, doctype="Sea Booking", name="SB-TEST"):
		booking = MagicMock(doctype=doctype)
		booking.name = name
		return booking

	def test_propagate_no_op_when_sales_quote_is_none(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			propagate_one_off_internal_jobs_to_booking,
		)

		booking = self._make_booking(name="SB-1")
		self.assertEqual(propagate_one_off_internal_jobs_to_booking(None, booking), {})

	def test_propagate_no_op_when_booking_is_none(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			propagate_one_off_internal_jobs_to_booking,
		)

		sq = self._make_quote(name="SQ-OO")
		self.assertEqual(propagate_one_off_internal_jobs_to_booking(sq, None), {})

	def test_propagate_no_op_when_booking_missing_name(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			propagate_one_off_internal_jobs_to_booking,
		)

		sq = self._make_quote(name="SQ-OO")
		booking = self._make_booking(name=None)
		self.assertEqual(propagate_one_off_internal_jobs_to_booking(sq, booking), {})

	def test_propagate_no_op_when_booking_missing_doctype(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			propagate_one_off_internal_jobs_to_booking,
		)

		sq = self._make_quote(name="SQ-OO-2")
		booking = self._make_booking(doctype="", name="SB-X")
		self.assertEqual(propagate_one_off_internal_jobs_to_booking(sq, booking), {})

	def test_remap_no_op_when_mapping_empty(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			remap_internal_job_links_on_booking_charges,
		)

		booking = MagicMock()
		self.assertFalse(remap_internal_job_links_on_booking_charges(booking, {}))

	def test_combined_no_op_when_inputs_missing(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			propagate_one_off_internal_jobs_and_remap_charges,
		)

		self.assertEqual(propagate_one_off_internal_jobs_and_remap_charges(None, None), {})


class TestBookingIJDetailPayload(FrappeTestCase):
	"""Booking-side IJ Detail rows mirror SQ-side rows with the same Linked Service link."""

	def test_payload_copies_all_parameter_columns(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			_booking_ij_detail_payload,
		)

		sq_row = MagicMock()
		sq_row.as_dict = MagicMock(
			return_value={
				"name": "row-1",
				"parent": "SQ-001",
				"parenttype": "Sales Quote",
				"parentfield": "internal_job_details",
				"idx": 1,
				"doctype": "Internal Job Detail",
				"internal_job": "IJ-SQ-001",
				"service_type": "Transport",
				"job_type": "Transport Order",
				"job_no": "TO-SHOULD-NOT-CARRY",
				"job_description": "Pickup at warehouse",
				"transport_template": "TT-001",
				"vehicle_type": "10ft Truck",
				"location_type": "Door",
				"location_from": "WH-A",
				"location_to": "Port-X",
				"pick_mode": "Door",
				"drop_mode": "Terminal",
				"actual_cost": 100,
				"actual_revenue": 200,
				"planned_cost": 80,
				"planned_revenue": 150,
			}
		)
		payload = _booking_ij_detail_payload(sq_row, "LS-BK-SAME")
		# Identity/parent keys stripped.
		self.assertNotIn("name", payload)
		self.assertNotIn("parent", payload)
		self.assertNotIn("idx", payload)
		# Same Linked Service document as on the quote.
		self.assertEqual(payload["internal_job"], "LS-BK-SAME")
		# Operational link + actuals cleared so rollup starts fresh on the booking.
		self.assertIsNone(payload["job_no"])
		self.assertIsNone(payload["actual_cost"])
		self.assertIsNone(payload["actual_revenue"])
		# Every other parameter column carried over verbatim.
		self.assertEqual(payload["service_type"], "Transport")
		self.assertEqual(payload["job_type"], "Transport Order")
		self.assertEqual(payload["job_description"], "Pickup at warehouse")
		self.assertEqual(payload["transport_template"], "TT-001")
		self.assertEqual(payload["vehicle_type"], "10ft Truck")
		self.assertEqual(payload["location_type"], "Door")
		self.assertEqual(payload["location_from"], "WH-A")
		self.assertEqual(payload["location_to"], "Port-X")
		self.assertEqual(payload["pick_mode"], "Door")
		self.assertEqual(payload["drop_mode"], "Terminal")
		# Planned figures stay because they describe the offered job; only actuals reset.
		self.assertEqual(payload["planned_cost"], 80)
		self.assertEqual(payload["planned_revenue"], 150)

	def test_payload_with_no_source_row_returns_minimal_link(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			_booking_ij_detail_payload,
		)

		payload = _booking_ij_detail_payload(None, "LS-BK-SAME")
		self.assertEqual(payload["internal_job"], "LS-BK-SAME")

	def test_sq_linked_service_detail_rows_by_ls_indexes_by_link(self):
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			_sq_linked_service_detail_rows_by_ls,
		)

		row_a = MagicMock(linked_service="LS-1", internal_job=None)
		row_b = MagicMock(linked_service="LS-2", internal_job=None)
		row_blank = MagicMock(linked_service=None, internal_job=None)
		row_dup = MagicMock(linked_service="LS-1", internal_job=None)
		sq = MagicMock(doctype="Sales Quote")
		sq.flags = frappe._dict(_linked_services_from_form=True)
		sq.__dict__["linked_services"] = [row_a, row_b, row_blank, row_dup]
		idx = _sq_linked_service_detail_rows_by_ls(sq)
		self.assertEqual(set(idx.keys()), {"LS-1", "LS-2"})
		self.assertIs(idx["LS-1"], row_a)
		self.assertIs(idx["LS-2"], row_b)


class TestBookingMappersApplyScopeTagging(FrappeTestCase):
	"""Regression guard: every booking mapper that consumes a Sales Quote Charge row must call
	``apply_scope_tagging_to_mapped_charge`` so the per-charge Internal Job link survives the
	conversion. We verify by inspecting source code rather than running the mappers (which require
	a fully-formed parent doc with masters seeded); this catches accidental removal of the call.
	"""

	_MAPPER_SOURCES: tuple[tuple[str, str], ...] = (
		(
			"logistics/sea_freight/doctype/sea_booking/sea_booking.py",
			"_map_sales_quote_sea_freight_to_charge",
		),
		(
			"logistics/air_freight/doctype/air_booking/air_booking.py",
			"_map_sales_quote_air_freight_to_charge",
		),
		(
			"logistics/transport/doctype/transport_order/transport_order.py",
			"_map_sales_quote_transport_to_charge",
		),
	)

	def test_every_booking_mapper_calls_apply_scope_tagging(self):
		import os
		import re

		app_root = frappe.get_app_path("logistics", "..")
		for rel_path, mapper_name in self._MAPPER_SOURCES:
			with self.subTest(mapper=mapper_name):
				full_path = os.path.normpath(os.path.join(app_root, rel_path))
				with open(full_path) as fh:
					src = fh.read()
				# Find the mapper's body up to the next top-level def/end-of-file.
				mapper_re = re.compile(
					rf"def {re.escape(mapper_name)}\b.*?(?=\n(?:def |\tdef |class )|\Z)",
					re.DOTALL,
				)
				match = mapper_re.search(src)
				self.assertIsNotNone(
					match, f"Mapper {mapper_name} not found in {rel_path}"
				)
				body = match.group(0)
				self.assertIn(
					"apply_scope_tagging_to_mapped_charge",
					body,
					f"{mapper_name} in {rel_path} must call apply_scope_tagging_to_mapped_charge "
					"so the per-charge Internal Job link is carried into the booking charge row.",
				)

	def test_every_booking_populate_extends_charge_fields(self):
		import os

		app_root = frappe.get_app_path("logistics", "..")
		populate_sources = (
			(
				"logistics/sea_freight/doctype/sea_booking/sea_booking.py",
				"_populate_charges_from_sales_quote",
			),
			(
				"logistics/sea_freight/doctype/sea_booking/sea_booking.py",
				"_populate_charges_from_sales_quote_doc",
			),
			(
				"logistics/air_freight/doctype/air_booking/air_booking.py",
				"_populate_charges_from_sales_quote",
			),
		)
		for rel_path, func_name in populate_sources:
			with self.subTest(func=func_name, path=rel_path):
				full_path = os.path.normpath(os.path.join(app_root, rel_path))
				with open(full_path) as fh:
					src = fh.read()
				# Quick contains-check: the populate method must extend the charge field list so
				# the SQ-side ``charge_scope`` / ``internal_job`` columns are fetched from DB.
				self.assertIn(
					"extend_charge_fields_with_scope_and_internal_job",
					src,
					f"{func_name} in {rel_path} must call extend_charge_fields_with_scope_and_internal_job "
					"so the per-charge Internal Job link is fetched from the SQ.",
				)
