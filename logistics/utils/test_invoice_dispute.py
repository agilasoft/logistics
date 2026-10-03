# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests import UnitTestCase

from logistics.utils.invoice_dispute import (
	ACTIVE_DISPUTE_STATUSES,
	partition_invoices_by_dispute,
	validate_payment_entry_against_disputes,
)


class _Ref:
	def __init__(self, reference_doctype, reference_name):
		self.reference_doctype = reference_doctype
		self.reference_name = reference_name


class _PaymentEntry:
	def __init__(self, references):
		self.references = references

	def get(self, key, default=None):
		if key == "references":
			return self.references
		return default


class TestInvoiceDispute(UnitTestCase):
	def test_active_statuses_include_open_and_under_review(self):
		self.assertIn("Open", ACTIVE_DISPUTE_STATUSES)
		self.assertIn("Under Review", ACTIVE_DISPUTE_STATUSES)

	def test_partition_invoices_by_dispute_splits_rows(self):
		invoices = [{"name": "SI-001"}, {"name": "SI-002"}]
		dispute_map = {
			"SI-002": {
				"name": "DSP-0001",
				"status": "Open",
				"dispute_reason": "Billing Error",
				"remarks": "<p>Test note</p>",
			}
		}

		class _Stub:
			@staticmethod
			def get_dispute_map(reference_doctype, invoice_names):
				return {k: v for k, v in dispute_map.items() if k in invoice_names}

		# Patch via local import inside function under test is harder without DB;
		# exercise partition logic with monkeypatched get_dispute_map at module level.
		import logistics.utils.invoice_dispute as mod

		original = mod.get_dispute_map
		mod.get_dispute_map = _Stub.get_dispute_map
		try:
			regular, disputed = partition_invoices_by_dispute("Sales Invoice", invoices)
		finally:
			mod.get_dispute_map = original

		self.assertEqual(len(regular), 1)
		self.assertEqual(regular[0]["name"], "SI-001")
		self.assertEqual(len(disputed), 1)
		self.assertEqual(disputed[0]["name"], "SI-002")
		self.assertEqual(disputed[0]["dispute"], "DSP-0001")
		self.assertIn("Test note", disputed[0]["dispute_remarks"])

	def test_validate_payment_entry_skips_non_invoice_refs(self):
		doc = _PaymentEntry([_Ref("Journal Entry", "JV-1")])
		validate_payment_entry_against_disputes(doc)
