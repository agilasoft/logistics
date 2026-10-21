# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Declaration Type Application: permit-application-only job and optional parties."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import today

from logistics.customs.declaration_types import (
	APPLICATION_DECLARATION_TYPE,
	DECLARATION_TYPE_OPTIONS,
	DECLARATION_TYPE_SELECT,
	PERMIT_APPLICATION_ONLY_TASKS,
	is_permit_application_only,
	optional_party_from_dialog,
	parties_optional,
)
from logistics.job_management.job_task import append_missing_job_tasks
from logistics.utils.get_charges_from_quotation import GCFQ_FILTER_CATALOG, GCFQ_SQ_HEADER_FIELD_MAP

_APP_ROOT = Path(__file__).resolve().parents[2]


class _Declaration:
	def __init__(self, declaration_type="Application", template=None):
		self.doctype = "Declaration"
		self.name = "CD-APP-1"
		self.declaration_type = declaration_type
		self.job_task_template = template
		self.direction = ""
		self.entry_type = ""
		self.job_tasks = []

	def get(self, fieldname):
		return getattr(self, fieldname, None)

	def append(self, fieldname, data):
		row = dict(data)
		getattr(self, fieldname).append(row)
		return row


class TestApplicationDeclarationType(UnitTestCase):
	def test_application_is_a_declaration_type(self):
		self.assertIn(APPLICATION_DECLARATION_TYPE, DECLARATION_TYPE_OPTIONS)
		self.assertTrue(DECLARATION_TYPE_SELECT.endswith("Application"))
		self.assertTrue(is_permit_application_only("Application"))
		self.assertFalse(is_permit_application_only("Import"))

	def test_shipper_and_consignee_are_optional_only_for_application_customs(self):
		self.assertTrue(parties_optional("Application"))
		self.assertTrue(parties_optional("Application", "Customs"))
		self.assertFalse(parties_optional("Application", "Air"))
		self.assertFalse(parties_optional("Import", "Customs"))

	def test_cleared_parties_stay_blank_on_application(self):
		self.assertIsNone(optional_party_from_dialog("", "SHIP-1", True))
		self.assertEqual(optional_party_from_dialog(None, "SHIP-1", True), "SHIP-1")
		self.assertEqual(optional_party_from_dialog("SHIP-2", "SHIP-1", True), "SHIP-2")
		self.assertEqual(optional_party_from_dialog("", "SHIP-1", False), "SHIP-1")

	def test_application_job_tasks_are_permit_application_only(self):
		parent = _Declaration()
		with patch("logistics.job_management.job_task.frappe.get_all") as get_all:
			result = append_missing_job_tasks(parent)
		get_all.assert_not_called()
		self.assertEqual(result["template"], "Permit application only")
		self.assertEqual(
			[row["task_code"] for row in parent.job_tasks],
			[task["task_code"] for task in PERMIT_APPLICATION_ONLY_TASKS],
		)
		self.assertNotIn("LODGE_ENTRY", [row["task_code"] for row in parent.job_tasks])

	def test_explicit_template_still_wins(self):
		parent = _Declaration(template="Custom Tasks")
		with patch("logistics.job_management.job_task.frappe.get_all", return_value=[]) as get_all:
			append_missing_job_tasks(parent)
		self.assertTrue(get_all.called)
		self.assertEqual(parent.job_tasks, [])

	def test_import_declaration_does_not_use_permit_checklist(self):
		parent = _Declaration(declaration_type="Import")
		with patch("logistics.job_management.job_task.frappe.get_all", return_value=[]):
			result = append_missing_job_tasks(parent)
		self.assertIsNone(result["template"])
		self.assertEqual(parent.job_tasks, [])

	def test_forms_offer_application_and_optional_parties(self):
		declaration = json.loads(
			(_APP_ROOT / "logistics/customs/doctype/declaration/declaration.json").read_text()
		)
		order = json.loads(
			(_APP_ROOT / "logistics/customs/doctype/declaration_order/declaration_order.json").read_text()
		)
		quote = json.loads(
			(_APP_ROOT / "logistics/pricing_center/doctype/sales_quote/sales_quote.json").read_text()
		)
		for meta in (declaration, order, quote):
			field = next(row for row in meta["fields"] if row["fieldname"] == "declaration_type")
			self.assertIn("Application", field["options"])
		shipper = next(row for row in quote["fields"] if row["fieldname"] == "shipper")
		consignee = next(row for row in quote["fields"] if row["fieldname"] == "consignee")
		for field in (shipper, consignee):
			self.assertIn('declaration_type == "Application"', field["mandatory_depends_on"])
			self.assertIn("Warehousing", field["mandatory_depends_on"])
		for meta, shipper_field, consignee_field in (
			(declaration, "exporter_shipper", "importer_consignee"),
			(order, "exporter_shipper", "importer_consignee"),
		):
			for fieldname in (shipper_field, consignee_field):
				field = next(row for row in meta["fields"] if row["fieldname"] == fieldname)
				self.assertNotIn("reqd", field)
				self.assertIn("Application", field.get("description") or "")

	def test_declaration_order_charge_fetch_includes_shipper_and_consignee(self):
		keys = {entry["key"] for entry in GCFQ_FILTER_CATALOG["Declaration Order"]}
		self.assertIn("shipper", keys)
		self.assertIn("consignee", keys)
		mapping = GCFQ_SQ_HEADER_FIELD_MAP["Declaration Order"]
		self.assertEqual(mapping["shipper"], "shipper")
		self.assertEqual(mapping["consignee"], "consignee")
		shipper = next(entry for entry in GCFQ_FILTER_CATALOG["Declaration Order"] if entry["key"] == "shipper")
		consignee = next(
			entry for entry in GCFQ_FILTER_CATALOG["Declaration Order"] if entry["key"] == "consignee"
		)
		self.assertEqual(shipper["doc_attr"], "exporter_shipper")
		self.assertEqual(consignee["doc_attr"], "importer_consignee")


class TestApplicationDeclarationJob(IntegrationTestCase):
	def setUp(self):
		from logistics.air_freight.tests.test_helpers import (
			create_test_branch,
			create_test_cost_center,
			create_test_profit_center,
			setup_basic_master_data,
		)

		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		try:
			self.branch = create_test_branch(self.company)
			self.cost_center = create_test_cost_center(self.company)
			self.profit_center = create_test_profit_center(self.company)
		except Exception:
			self.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			self.cost_center = frappe.db.get_value(
				"Cost Center", {"company": self.company, "is_group": 0}, "name"
			)
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def _declaration(self, **extra):
		doc = frappe.get_doc(
			{
				"doctype": "Declaration",
				"company": self.company,
				"customer": self.customer,
				"declaration_date": today(),
				"declaration_type": "Application",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				**extra,
			}
		)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_documents_milestones_populate = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_application_creates_one_permit_application_without_parties(self):
		declaration = self._declaration()
		declaration.reload()
		linked = [row.permit_application for row in declaration.permit_requirements if row.permit_application]
		self.assertEqual(len(linked), 1)
		permit = frappe.get_doc("Permit Application", linked[0])
		self.assertEqual(permit.declaration, declaration.name)
		self.assertEqual(permit.applicant, self.customer)
		self.assertEqual(permit.permit_type, "PERMIT-APPLICATION-ONLY")
		codes = [row.task_code for row in declaration.job_tasks]
		self.assertEqual(codes, [task["task_code"] for task in PERMIT_APPLICATION_ONLY_TASKS])
		again = self._declaration()
		again.reload()
		self.assertEqual(
			len([row.permit_application for row in again.permit_requirements if row.permit_application]),
			1,
		)
