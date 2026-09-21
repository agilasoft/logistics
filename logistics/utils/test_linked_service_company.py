# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch
import unittest

import frappe

from logistics.utils.internal_job_creation_eligibility import (
	evaluate_linked_service_internal_job_eligibility,
)
from logistics.utils.linked_service_company import (
	apply_linked_service_company_to_operational_doc,
	company_from_linked_service,
	missing_linked_service_company_message,
	sync_company_scoped_fields_on_operational_doc,
)


def _meta_with_fields(*fieldnames, reqd=False):
	fields = {fn: MagicMock(reqd=reqd, label=fn.replace("_", " ").title()) for fn in fieldnames}

	meta = MagicMock()
	meta.get_field.side_effect = lambda fn: fields.get(fn)
	meta.has_field.side_effect = lambda fn: fn in fields
	return meta


def _doc(**values):
	doc = frappe._dict(values)
	doc.doctype = values.get("doctype") or "Transport Order"
	doc.set = lambda fn, val: doc.update({fn: val})
	return doc


class TestLinkedServiceCompany(unittest.TestCase):
	def test_company_from_row_direct(self):
		self.assertEqual(company_from_linked_service({"company": "Co A"}), "Co A")
		self.assertEqual(company_from_linked_service(frappe._dict(company="Co B")), "Co B")
		self.assertEqual(company_from_linked_service(None), "")

	def test_missing_company_message_mentions_quote(self):
		msg = missing_linked_service_company_message(
			linked_service="LS-1",
			service_type="Transport",
			sales_quote="SQU-1",
		)
		self.assertIn("LS-1", msg)
		self.assertIn("SQU-1", msg)
		self.assertIn("Transport", msg)

	def test_apply_stamps_company_and_syncs_scoped_fields(self):
		meta = _meta_with_fields("company", "branch", "cost_center", "profit_center")
		doc = _doc(company="Main Co", branch="BR-1", cost_center="CC-1", profit_center="PC-1")
		row = frappe._dict(linked_service="LS-1", company="Op Co", service_type="Transport")
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company.sync_company_scoped_fields_on_operational_doc"
			) as sync:
				applied = apply_linked_service_company_to_operational_doc(
					doc, row, overwrite=True, require=False
				)
		self.assertEqual(applied, "Op Co")
		self.assertEqual(doc.company, "Op Co")
		sync.assert_called_once_with(doc, "Op Co")

	def test_apply_keeps_scoped_fields_when_company_unchanged(self):
		meta = _meta_with_fields("company", "branch", "cost_center", "profit_center")
		doc = _doc(company="Op Co", branch="BR-1", cost_center="CC-1", profit_center="PC-1")
		row = frappe._dict(linked_service="LS-1", company="Op Co", service_type="Transport")
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company.sync_company_scoped_fields_on_operational_doc"
			) as sync:
				apply_linked_service_company_to_operational_doc(doc, row, overwrite=True)
		self.assertEqual(doc.company, "Op Co")
		self.assertEqual(doc.branch, "BR-1")
		sync.assert_called_once_with(doc, "Op Co")

	def test_apply_requires_company_when_quote_linked_service_has_none(self):
		meta = _meta_with_fields("company")
		doc = _doc(company="Main Co", sales_quote="SQU-1")
		row = frappe._dict(linked_service="LS-MISSING", service_type="Transport")
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company.company_from_linked_service",
				return_value="",
			):
				with self.assertRaises(frappe.ValidationError) as ctx:
					apply_linked_service_company_to_operational_doc(
						doc, row, overwrite=True, require=True, sales_quote="SQU-1"
					)
		self.assertIn("SQU-1", str(ctx.exception))

	def test_sync_keeps_values_that_belong_to_company(self):
		meta = _meta_with_fields("branch", "cost_center", "profit_center", reqd=True)
		doc = _doc(branch="BR-1", cost_center="CC-1", profit_center="PC-1")
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company._link_belongs_to_company",
				return_value=True,
			):
				sync_company_scoped_fields_on_operational_doc(doc, "Op Co")
		self.assertEqual(doc.branch, "BR-1")
		self.assertEqual(doc.cost_center, "CC-1")
		self.assertEqual(doc.profit_center, "PC-1")

	def test_sync_refills_values_for_new_company(self):
		meta = _meta_with_fields("branch", "cost_center", "profit_center", reqd=True)
		doc = _doc(branch="BR-MAIN", cost_center="CC-MAIN", profit_center="PC-MAIN")
		defaults = {"branch": "BR-OP", "cost_center": "CC-OP", "profit_center": "PC-OP"}
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company._link_belongs_to_company",
				return_value=False,
			):
				with patch(
					"logistics.utils.linked_service_company._default_scoped_value",
					side_effect=lambda fn, _dt, _co: defaults[fn],
				):
					sync_company_scoped_fields_on_operational_doc(doc, "Op Co")
		self.assertEqual(doc.branch, "BR-OP")
		self.assertEqual(doc.cost_center, "CC-OP")
		self.assertEqual(doc.profit_center, "PC-OP")

	def test_sync_throws_when_required_defaults_missing(self):
		meta = _meta_with_fields("branch", "cost_center", "profit_center", reqd=True)
		doc = _doc(branch="BR-MAIN", cost_center="CC-MAIN", profit_center="PC-MAIN")
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company._link_belongs_to_company",
				return_value=False,
			):
				with patch(
					"logistics.utils.linked_service_company._default_scoped_value",
					return_value="",
				):
					with self.assertRaises(frappe.ValidationError) as ctx:
						sync_company_scoped_fields_on_operational_doc(doc, "Op Co")
		self.assertIn("Op Co", str(ctx.exception))
		self.assertIn("Branch", str(ctx.exception))

	def test_eligibility_blocks_when_linked_service_has_no_company(self):
		ls = frappe._dict(
			doctype="Linked Service", name="LS-1", service_type="Transport", company=""
		)
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.internal_job_matches_charges",
				return_value=True,
			):
				with patch(
					"logistics.utils.internal_job_creation_eligibility._quote_has_matching_linked_service_row",
					return_value=True,
				):
					with patch(
						"logistics.utils.internal_job_creation_eligibility.frappe.db.exists",
						return_value=True,
					):
						result = evaluate_linked_service_internal_job_eligibility(
							sales_quote="SQU-1",
							parent_doc=frappe._dict(doctype="Air Shipment", sales_quote="SQU-1"),
							linked_service_doc=ls,
							service_type_label="Transport",
						)
		self.assertFalse(result["eligible"])
		self.assertIn("company", (result["message"] or "").lower())

	def test_eligibility_allows_when_linked_service_has_company(self):
		ls = frappe._dict(
			doctype="Linked Service", name="LS-1", service_type="Transport", company="Op Co"
		)
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.internal_job_matches_charges",
				return_value=True,
			):
				with patch(
					"logistics.utils.internal_job_creation_eligibility._quote_has_matching_linked_service_row",
					return_value=True,
				):
					with patch(
						"logistics.utils.internal_job_creation_eligibility.frappe.db.exists",
						return_value=True,
					):
						result = evaluate_linked_service_internal_job_eligibility(
							sales_quote="SQU-1",
							parent_doc=frappe._dict(doctype="Air Shipment", sales_quote="SQU-1"),
							linked_service_doc=ls,
							service_type_label="Transport",
						)
		self.assertTrue(result["eligible"])
		self.assertIsNone(result["message"])
