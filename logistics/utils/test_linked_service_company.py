# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch
import unittest

import frappe

from logistics.utils.internal_job_creation_eligibility import (
	evaluate_linked_service_internal_job_eligibility,
)
from logistics.utils.linked_service_company import (
	_link_belongs_to_company,
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
	def test_dialog_strips_company_filters_from_branch_and_profit_center(self):
		from logistics.logistics.doctype.linked_service.linked_service import _dialog_link_filters

		branch = frappe._dict(
			options="Branch",
			link_filters='[["Branch", "custom_company", "=", "eval:doc.company"]]',
		)
		profit_center = frappe._dict(options="Profit Center", link_filters="")
		active_profit_center = frappe._dict(
			options="Profit Center",
			link_filters=(
				'[["Profit Center", "company", "=", "eval:doc.company"], '
				'["Profit Center", "is_active", "=", 1]]'
			),
		)
		cost_center = frappe._dict(
			options="Cost Center",
			link_filters='[["Cost Center", "company", "=", "eval:doc.company"]]',
		)
		self.assertEqual(_dialog_link_filters(branch), "")
		self.assertEqual(_dialog_link_filters(profit_center), "")
		active_filters = _dialog_link_filters(active_profit_center)
		self.assertIn("is_active", active_filters)
		self.assertNotIn("company", active_filters)
		self.assertIn("company", _dialog_link_filters(cost_center))
		self.assertIn("eval:doc.company", _dialog_link_filters(cost_center))

	def test_only_cost_center_must_match_company(self):
		with patch("logistics.utils.linked_service_company.frappe.db.exists", return_value=True):
			with patch(
				"logistics.utils.linked_service_company._company_fields_for",
				return_value=["company"],
			):
				with patch(
					"logistics.utils.linked_service_company._master_company",
					return_value="Other Co",
				):
					self.assertTrue(_link_belongs_to_company("Branch", "BR-1", "Op Co"))
					self.assertTrue(_link_belongs_to_company("Profit Center", "PC-1", "Op Co"))
					self.assertFalse(_link_belongs_to_company("Cost Center", "CC-1", "Op Co"))

	def test_linked_service_doctype_filters_only_cost_center_by_company(self):
		import json
		from pathlib import Path

		root = Path(__file__).resolve().parents[1]
		for relative in (
			"logistics/doctype/linked_service/linked_service.json",
			"logistics/doctype/linked_service_detail/linked_service_detail.json",
		):
			data = json.loads((root / relative).read_text())
			fields = {field["fieldname"]: field for field in data["fields"]}
			self.assertNotIn("link_filters", fields["branch"])
			profit_center_filters = fields["profit_center"].get("link_filters") or ""
			self.assertIn("is_active", profit_center_filters)
			self.assertNotIn("custom_company", profit_center_filters)
			self.assertNotIn('"company"', profit_center_filters)
			self.assertIn("company", fields["cost_center"]["link_filters"])
			self.assertNotIn("custom_company", fields["cost_center"]["link_filters"])

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

	def test_virtual_charge_row_copies_linked_service_dimensions(self):
		from logistics.utils.internal_job_from_source import _virtual_ij_row_from_linked_charge

		charge = frappe._dict(
			service_type="Transport",
			linked_service="LS-1",
			charge_scope="Linked",
		)
		dims = {
			"company": "Op Co",
			"branch": "BR-OP",
			"cost_center": "CC-OP",
			"profit_center": "PC-OP",
		}
		with patch(
			"logistics.utils.sales_quote_charge_parameters.resolve_parameters_for_charge_row",
			return_value={"location_from": "A", "company": "Main Co", "branch": "BR-MAIN"},
		):
			with patch(
				"logistics.utils.linked_service_company.accounting_dimensions_from_linked_service",
				return_value=dims,
			):
				row = _virtual_ij_row_from_linked_charge(charge)
		self.assertEqual(row.company, "Op Co")
		self.assertEqual(row.branch, "BR-OP")
		self.assertEqual(row.cost_center, "CC-OP")
		self.assertEqual(row.profit_center, "PC-OP")
		self.assertEqual(row.location_from, "A")

	def test_apply_loads_scoped_fields_from_linked_service_record(self):
		meta = _meta_with_fields("company", "branch", "cost_center", "profit_center")
		doc = _doc(company="Main Co", branch="BR-MAIN", cost_center="CC-MAIN", profit_center="PC-MAIN")
		doc.flags = frappe._dict()
		row = frappe._dict(linked_service="LS-1", company="Op Co", service_type="Transport")
		stored = frappe._dict(branch="BR-OP", cost_center="CC-OP", profit_center="PC-OP")
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_compat.linked_service_record_exists",
				return_value=True,
			):
				with patch(
					"logistics.utils.linked_service_company.frappe.get_cached_doc",
					return_value=stored,
				):
					with patch(
						"logistics.utils.linked_service_company._link_belongs_to_company",
						return_value=True,
					):
						apply_linked_service_company_to_operational_doc(doc, row, overwrite=True)
		self.assertEqual(doc.company, "Op Co")
		self.assertEqual(doc.branch, "BR-OP")
		self.assertEqual(doc.cost_center, "CC-OP")
		self.assertEqual(doc.profit_center, "PC-OP")

	def test_sync_keeps_values_copied_from_linked_service(self):
		meta = _meta_with_fields("branch", "cost_center", "profit_center", reqd=True)
		doc = _doc(branch="BR-OP", cost_center="CC-OP", profit_center="PC-OP")
		doc.flags = frappe._dict(
			linked_service_scoped_fields=("branch", "cost_center", "profit_center")
		)
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company._link_belongs_to_company",
				return_value=False,
			):
				with patch(
					"logistics.utils.linked_service_company._default_scoped_value",
					return_value="DEFAULT",
				):
					sync_company_scoped_fields_on_operational_doc(doc, "Op Co")
		self.assertEqual(doc.branch, "BR-OP")
		self.assertEqual(doc.cost_center, "CC-OP")
		self.assertEqual(doc.profit_center, "PC-OP")

	def test_apply_copies_scoped_fields_from_linked_service(self):
		meta = _meta_with_fields("company", "branch", "cost_center", "profit_center")
		doc = _doc(company="Main Co", branch="BR-MAIN", cost_center="CC-MAIN", profit_center="PC-MAIN")
		row = frappe._dict(
			doctype="Linked Service",
			name="LS-1",
			company="Op Co",
			branch="BR-OP",
			cost_center="CC-OP",
			profit_center="PC-OP",
		)
		with patch("logistics.utils.linked_service_company.frappe.get_meta", return_value=meta):
			with patch(
				"logistics.utils.linked_service_company._link_belongs_to_company",
				return_value=True,
			):
				with patch(
					"logistics.utils.linked_service_company.sync_company_scoped_fields_on_operational_doc"
				):
					apply_linked_service_company_to_operational_doc(doc, row, overwrite=True)
		self.assertEqual(doc.branch, "BR-OP")
		self.assertEqual(doc.cost_center, "CC-OP")
		self.assertEqual(doc.profit_center, "PC-OP")

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
		self.assertEqual(doc.branch, "BR-MAIN")
		self.assertEqual(doc.cost_center, "CC-OP")
		self.assertEqual(doc.profit_center, "PC-MAIN")

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
		self.assertIn("Cost Center", str(ctx.exception))
		self.assertEqual(doc.branch, "BR-MAIN")
		self.assertEqual(doc.profit_center, "PC-MAIN")

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
