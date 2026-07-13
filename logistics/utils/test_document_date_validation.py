# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.document_date_validation import (
	validate_planned_date_range,
	warn_if_planned_end_before_reference,
)


class TestDocumentDateValidation(FrappeTestCase):
	def test_validate_planned_date_range_allows_equal_and_ordered(self):
		doc = frappe._dict(planned_start="2026-07-01", planned_end="2026-07-01")
		validate_planned_date_range(doc)
		doc.planned_end = "2026-07-10"
		validate_planned_date_range(doc)

	def test_validate_planned_date_range_blocks_inverted(self):
		doc = frappe._dict(planned_start="2026-07-13", planned_end="2026-07-01")
		with self.assertRaises(frappe.ValidationError):
			validate_planned_date_range(doc)

	def test_validate_planned_date_range_datetime(self):
		doc = frappe._dict(
			planned_start="2026-07-01 12:00:00",
			planned_end="2026-07-01 11:00:00",
		)
		with self.assertRaises(frappe.ValidationError):
			validate_planned_date_range(doc, use_datetime=True)

	def test_warn_if_planned_end_before_reference(self):
		doc = frappe._dict(
			planned_start="2026-07-01",
			planned_end="2026-07-10",
			date="2026-07-13",
		)
		# Should not raise — soft warning only.
		warn_if_planned_end_before_reference(
			doc, reference_field="date", reference_label="Quote Date"
		)
