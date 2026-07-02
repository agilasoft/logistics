# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Internal Job link validation pre-flight on parent saves."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import frappe

from logistics.utils.internal_job_persistence import (
	prepare_internal_jobs_before_link_validation,
	reconcile_orphan_charge_internal_job_links,
)
from logistics.utils.linked_service_compat import (
	filter_invalid_links_with_linked_service_compat,
)


def _row(**kw):
	return frappe._dict(kw)


def _stub_air_booking(**kw):
	doc = _row(doctype="Air Booking", name=kw.get("name", "ABK-TEST"), flags=frappe._dict())
	doc.internal_job_details = kw.get("internal_job_details", [])
	doc.charges = kw.get("charges", [])
	return doc


class TestReconcileOrphanChargeInternalJobLinks(unittest.TestCase):
	def test_remaps_via_ij_remap(self):
		parent = _stub_air_booking(
			internal_job_details=[
				_row(service_type="Warehousing", internal_job="IJ-NEW"),
			],
			charges=[
				_row(
					charge_scope="Internal Job",
					internal_job="IJ-STALE",
					service_type="Warehousing",
				),
			],
		)
		with patch(
			"logistics.utils.internal_job_persistence.linked_service_record_exists",
			side_effect=lambda name: name == "IJ-NEW",
		):
			reconcile_orphan_charge_internal_job_links(parent, {"IJ-STALE": "IJ-NEW"})
		self.assertEqual(parent.charges[0].internal_job, "IJ-NEW")
		self.assertEqual(parent.charges[0].charge_scope, "Linked")

	def test_matches_by_service_type_when_remap_missing(self):
		parent = _stub_air_booking(
			internal_job_details=[
				_row(service_type="Transport", internal_job="IJ-TRANSPORT"),
			],
			charges=[
				_row(
					charge_scope="Internal Job",
					internal_job="IJ-MISSING",
					service_type="Transport",
				),
			],
		)
		with patch(
			"logistics.utils.internal_job_persistence.linked_service_record_exists",
			side_effect=lambda name: name == "IJ-TRANSPORT",
		):
			reconcile_orphan_charge_internal_job_links(parent, {})
		self.assertEqual(parent.charges[0].internal_job, "IJ-TRANSPORT")

	def test_clears_unresolvable_orphans_to_main_scope(self):
		parent = _stub_air_booking(
			internal_job_details=[],
			charges=[
				_row(
					charge_scope="Internal Job",
					internal_job="IJ-GHOST",
					service_type="Sea",
				),
			],
		)
		with patch(
			"logistics.utils.internal_job_persistence.linked_service_record_exists",
			return_value=False,
		):
			reconcile_orphan_charge_internal_job_links(parent, {})
		self.assertIsNone(parent.charges[0].internal_job)
		self.assertIsNone(parent.charges[0].linked_service)
		self.assertEqual(parent.charges[0].charge_scope, "Main")

	def test_fills_empty_linked_scope_by_service_type(self):
		parent = _stub_air_booking(
			internal_job_details=[
				_row(service_type="Transport", internal_job="IJ-TRANSPORT"),
			],
			charges=[
				_row(
					charge_scope="Linked",
					service_type="Transport",
				),
			],
		)
		with patch(
			"logistics.utils.internal_job_persistence.linked_service_record_exists",
			side_effect=lambda name: name == "IJ-TRANSPORT",
		):
			reconcile_orphan_charge_internal_job_links(parent, {})
		self.assertEqual(parent.charges[0].internal_job, "IJ-TRANSPORT")
		self.assertEqual(parent.charges[0].charge_scope, "Linked")

	def test_resets_empty_linked_scope_to_main_when_no_match(self):
		parent = _stub_air_booking(
			internal_job_details=[],
			charges=[
				_row(
					charge_scope="Linked",
					service_type="Transport",
				),
			],
		)
		reconcile_orphan_charge_internal_job_links(parent, {})
		self.assertEqual(parent.charges[0].charge_scope, "Main")
		self.assertIsNone(parent.charges[0].internal_job)
		self.assertIsNone(parent.charges[0].linked_service)

	def test_leaves_valid_internal_job_links_unchanged(self):
		parent = _stub_air_booking(
			charges=[
				_row(
					charge_scope="Internal Job",
					internal_job="IJ-OK",
					service_type="Sea",
				),
			],
		)
		with patch(
			"logistics.utils.internal_job_persistence.linked_service_record_exists",
			return_value=True,
		):
			reconcile_orphan_charge_internal_job_links(parent, {"IJ-OK": "IJ-OTHER"})
		self.assertEqual(parent.charges[0].internal_job, "IJ-OK")


class TestCreateInternalJobPreferredName(unittest.TestCase):
	def test_uses_preferred_name_when_available(self):
		parent = _stub_air_booking(name="ABK-PREF")
		row = _row(service_type="Warehousing", job_type="Inbound Order")
		ij_doc = Mock()
		ij_doc.name = "IJ-2026-001145"
		ij_doc.flags = Mock()
		with patch(
			"logistics.utils.internal_job_persistence.linked_service_record_exists",
			return_value=False,
		), patch(
			"logistics.utils.internal_job_persistence._copy_row_params_to_internal_job"
		), patch(
			"logistics.utils.internal_job_persistence._ensure_job_type_from_service"
		), patch.object(frappe, "new_doc", return_value=ij_doc):
			from logistics.utils.internal_job_persistence import _create_internal_job_from_row

			name = _create_internal_job_from_row(
				parent, row, preferred_name="IJ-2026-001145"
			)
		ij_doc.insert.assert_called_once_with(
			ignore_permissions=True, set_name="IJ-2026-001145"
		)
		self.assertEqual(name, "IJ-2026-001145")


class TestPrepareInternalJobsBeforeLinkValidation(unittest.TestCase):
	def test_noop_for_unrelated_doctype(self):
		doc = _row(doctype="Customer", flags=frappe._dict())
		with patch(
			"logistics.utils.internal_job_persistence._ensure_internal_job_docs_for_detail_rows"
		) as ensure_mock:
			prepare_internal_jobs_before_link_validation(doc)
		ensure_mock.assert_not_called()

	def test_noop_when_ignore_links(self):
		doc = _stub_air_booking()
		doc.flags.ignore_links = True
		with patch(
			"logistics.utils.internal_job_persistence._ensure_internal_job_docs_for_detail_rows"
		) as ensure_mock:
			prepare_internal_jobs_before_link_validation(doc)
		ensure_mock.assert_not_called()

	def test_runs_ensure_and_reconcile_for_air_booking(self):
		doc = _stub_air_booking()
		with patch(
			"logistics.utils.internal_job_persistence._ensure_internal_job_docs_for_detail_rows",
			return_value={"IJ-STALE": "IJ-NEW"},
		) as ensure_mock, patch(
			"logistics.utils.internal_job_persistence.reconcile_orphan_charge_internal_job_links"
		) as reconcile_mock:
			prepare_internal_jobs_before_link_validation(doc)
		ensure_mock.assert_called_once_with(doc)
		reconcile_mock.assert_called_once_with(doc, {"IJ-STALE": "IJ-NEW"})


class TestLinkedServiceLinkValidationCompat(unittest.TestCase):
	def test_filter_accepts_linked_service_storage_for_internal_job_field(self):
		invalid = [("internal_job", "IJ-LS-1", "Row #1: Internal Job: IJ-LS-1")]
		with patch(
			"logistics.utils.linked_service_compat.linked_service_record_exists",
			return_value=True,
		):
			out = filter_invalid_links_with_linked_service_compat(invalid)
		self.assertEqual(out, [])

	def test_filter_keeps_unresolvable_internal_job_links(self):
		invalid = [("internal_job", "IJ-GHOST", "Row #1: Internal Job: IJ-GHOST")]
		with patch(
			"logistics.utils.linked_service_compat.linked_service_record_exists",
			return_value=False,
		):
			out = filter_invalid_links_with_linked_service_compat(invalid)
		self.assertEqual(out, invalid)
