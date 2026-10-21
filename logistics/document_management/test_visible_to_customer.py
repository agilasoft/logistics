# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Visible to Customer defaults from Document Type when documents are extracted."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.document_management.api import populate_documents_from_template

APP = Path(__file__).resolve().parents[1]


class _Flags:
	def __init__(self):
		self.ignore_validate = False


class _Parent:
	def __init__(self, documents=None):
		self.doctype = "Transport Job"
		self.name = "TRJ-00001"
		self.direction = ""
		self.entry_type = ""
		self.document_list_template = "Transport Docs"
		self.documents = list(documents or [])
		self.flags = _Flags()
		self.saves = 0

	def get(self, fieldname):
		return getattr(self, fieldname, None)

	def append(self, fieldname, data):
		row = frappe._dict(data)
		getattr(self, fieldname).append(row)
		return row

	def save(self):
		self.saves += 1


def _item(document_type, mandatory=0):
	return frappe._dict(
		document_type=document_type,
		is_mandatory=mandatory,
		date_required_basis=None,
	)


def _field(doctype_json, fieldname):
	for field in doctype_json["fields"]:
		if field.get("fieldname") == fieldname:
			return field
	return None


class TestVisibleToCustomer(UnitTestCase):
	def test_document_type_and_documents_row_define_the_checkbox(self):
		document_type = json.loads(
			(APP / "logistics/doctype/logistics_document_type/logistics_document_type.json").read_text()
		)
		job_document = json.loads(
			(APP / "logistics/doctype/job_document/job_document.json").read_text()
		)

		master = _field(document_type, "visible_to_customer")
		self.assertIsNotNone(master)
		self.assertEqual(master["fieldtype"], "Check")
		self.assertEqual(master["label"], "Visible to Customer")
		self.assertEqual(master["default"], "0")
		self.assertIn("visible_to_customer", document_type["field_order"])

		row = _field(job_document, "visible_to_customer")
		self.assertIsNotNone(row)
		self.assertEqual(row["fieldtype"], "Check")
		self.assertEqual(row["label"], "Visible to Customer")
		self.assertEqual(row["fetch_from"], "document_type.visible_to_customer")
		self.assertEqual(row["default"], "0")
		self.assertEqual(row.get("in_list_view"), 1)
		order = job_document["field_order"]
		self.assertLess(order.index("is_required"), order.index("visible_to_customer"))

	def test_extract_defaults_visible_to_customer_from_document_type(self):
		parent = _Parent()
		items = [_item("CI", 1), _item("CI", 1), _item("BL", 0), _item("POD", 1)]

		def get_all(doctype, **kwargs):
			self.assertEqual(doctype, "Logistics Document Type")
			self.assertEqual(kwargs["fields"], ["name", "visible_to_customer"])
			self.assertEqual(set(kwargs["filters"]["name"][1]), {"CI", "BL", "POD"})
			return [
				frappe._dict(name="CI", visible_to_customer=1),
				frappe._dict(name="BL", visible_to_customer=0),
			]

		frappe.flags.in_ensure_documents_milestones = False
		with patch("logistics.utils.menu_permission.assert_perm"), patch(
			"logistics.document_management.api._get_document_template_items_for_doc",
			return_value=items,
		), patch(
			"logistics.document_management.api.frappe.get_all",
			side_effect=get_all,
		), patch(
			"logistics.document_management.api.frappe.utils.now",
			return_value="2026-10-21 08:00:00",
		):
			result = populate_documents_from_template("Transport Job", parent.name, doc=parent)

		self.assertEqual(result["added"], 3)
		self.assertEqual(parent.saves, 1)
		self.assertTrue(parent.flags.ignore_validate)
		by_type = {row.document_type: row.visible_to_customer for row in parent.documents}
		self.assertEqual(by_type, {"CI": 1, "BL": 0, "POD": 0})
		self.assertTrue(all(row.source == "Fetched" for row in parent.documents))
		self.assertEqual(parent.documents[0].is_required, 1)
		self.assertEqual(parent.documents[1].is_required, 0)

	def test_extract_leaves_existing_rows_unchanged(self):
		existing = frappe._dict(document_type="CI", visible_to_customer=0, source="Manual")
		parent = _Parent(documents=[existing])

		def get_all(doctype, **kwargs):
			self.assertEqual(kwargs["filters"]["name"][1], ["PL"])
			return [frappe._dict(name="PL", visible_to_customer="1")]

		frappe.flags.in_ensure_documents_milestones = False
		with patch("logistics.utils.menu_permission.assert_perm"), patch(
			"logistics.document_management.api._get_document_template_items_for_doc",
			return_value=[_item("CI", 1), _item("PL", 1)],
		), patch(
			"logistics.document_management.api.frappe.get_all",
			side_effect=get_all,
		), patch(
			"logistics.document_management.api.frappe.utils.now",
			return_value="2026-10-21 08:00:00",
		):
			result = populate_documents_from_template("Transport Job", parent.name, doc=parent)

		self.assertEqual(result["added"], 1)
		self.assertEqual(existing.visible_to_customer, 0)
		self.assertEqual(existing.source, "Manual")
		self.assertEqual(parent.documents[1].document_type, "PL")
		self.assertEqual(parent.documents[1].visible_to_customer, 1)

	def test_sea_booking_copies_customer_visibility_onto_the_shipment(self):
		source = (APP / "sea_freight/doctype/sea_booking/sea_booking.py").read_text()
		self.assertIn(
			'"visible_to_customer": getattr(doc_row, "visible_to_customer", 0)',
			source,
		)
