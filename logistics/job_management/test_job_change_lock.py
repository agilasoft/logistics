# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import unittest
from unittest.mock import MagicMock, patch

import frappe

from logistics.job_management.job_change_lock import (
	_scalar_changed,
	is_job_change_locked,
	validate_job_locked_against_user_edits,
)
from logistics.pricing_center.change_request_field_apply import (
	parse_change_sections,
	header_fields_for_sections,
)


class TestJobChangeLock(unittest.TestCase):
	def test_scalar_changed(self):
		self.assertFalse(_scalar_changed(None, ""))
		self.assertFalse(_scalar_changed("a", "a"))
		self.assertTrue(_scalar_changed("a", "b"))

	def test_is_locked_requires_submitted(self):
		doc = MagicMock()
		doc.doctype = "Air Shipment"
		doc.docstatus = 0
		doc.is_new.return_value = False
		doc.flags = {}
		self.assertFalse(is_job_change_locked(doc))
		doc.docstatus = 1
		self.assertTrue(is_job_change_locked(doc))

	def test_from_change_request_bypasses_lock(self):
		doc = MagicMock()
		doc.doctype = "Transport Job"
		doc.docstatus = 1
		doc.is_new.return_value = False
		doc.flags = {"from_change_request": True}
		self.assertFalse(is_job_change_locked(doc))

	@patch("logistics.job_management.job_change_lock.frappe.throw")
	def test_validate_throws_on_locked_party_change(self, mock_throw):
		before = MagicMock()
		before.get = lambda fn, default=None: "Old Shipper" if fn == "shipper" else None
		before.packages = []

		doc = MagicMock()
		doc.doctype = "Air Shipment"
		doc.docstatus = 1
		doc.is_new.return_value = False
		doc.flags = {}
		doc.get_doc_before_save.return_value = before

		def _get(fn, default=None):
			if fn == "shipper":
				return "New Shipper"
			if fn == "packages":
				return []
			return None

		doc.get = _get

		with patch("logistics.job_management.job_change_lock.frappe.get_meta") as mock_meta:
			shipper_df = MagicMock(fieldname="shipper", fieldtype="Link", label="Shipper")
			mock_meta.return_value.fields = [shipper_df]
			validate_job_locked_against_user_edits(doc)
			self.assertTrue(mock_throw.called)


class TestChangeRequestSections(unittest.TestCase):
	def test_parse_sections(self):
		self.assertEqual(parse_change_sections("Parties\nCharges"), {"Parties", "Charges"})
		self.assertEqual(parse_change_sections(["Packages", "Notes"]), {"Packages", "Notes"})

	def test_header_fields_for_parties(self):
		fields = header_fields_for_sections({"Parties"})
		self.assertIn("shipper", fields)
		self.assertIn("consignee", fields)
		self.assertNotIn("etd", fields)

	def test_run_sheet_fields_in_places(self):
		fields = header_fields_for_sections({"Places & Dates"})
		self.assertIn("run_date", fields)
		self.assertIn("vehicle", fields)
		self.assertIn("driver", fields)


if __name__ == "__main__":
	unittest.main()
