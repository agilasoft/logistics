# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Beginning Jobs: old-system files, linked services, and prior posted charges."""

from __future__ import unicode_literals

from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from logistics.air_freight.tests.test_helpers import (
	create_test_branch,
	create_test_cost_center,
	create_test_item,
	create_test_profit_center,
	setup_basic_master_data,
)
from logistics.invoice_integration.purchase_invoice_api import (
	CHARGE_CONFIG as PURCHASE_CHARGE_CONFIG,
	_get_eligible_cost_rows,
)
from logistics.invoice_integration.sales_invoice_api import (
	SALES_CHARGE_CONFIG,
	_get_eligible_revenue_rows,
)
from logistics.job_management.beginning_jobs import create_beginning_jobs
from logistics.job_management.doc_events import update_estimates_from_charges
from logistics.job_management.job_readiness import check_charges_posted
from logistics.job_management.prior_system_posting import PRIOR_SYSTEM_POSTED_STATUS
from logistics.job_management.recognition_engine import (
	RecognitionEngine,
	resolve_charge_row_cost,
	resolve_charge_row_selling,
)


def _charge(**kwargs):
	data = {
		"item_code": "FRT",
		"charge_type": "Margin",
		"estimated_revenue": 0,
		"actual_revenue": 0,
		"estimated_cost": 0,
		"actual_cost": 0,
		"sales_invoice_status": "Not Requested",
		"purchase_invoice_status": "Not Requested",
	}
	data.update(kwargs)
	return SimpleNamespace(**data)


class TestPriorSystemPosting(FrappeTestCase):
	def test_prior_revenue_is_left_out_of_wip_and_sales_invoices(self):
		posted = _charge(
			estimated_revenue=100,
			actual_revenue=100,
			sales_invoice_status=PRIOR_SYSTEM_POSTED_STATUS,
			estimated_cost=40,
			actual_cost=40,
		)
		open_row = _charge(item_code="OPEN", estimated_revenue=25, actual_revenue=25)
		self.assertEqual(resolve_charge_row_selling(posted), 0)
		self.assertEqual(resolve_charge_row_selling(posted, prefer_actual=True), 0)
		self.assertEqual(resolve_charge_row_cost(posted), 40)
		self.assertEqual(flt(resolve_charge_row_selling(open_row)), 25)

		doc = SimpleNamespace(
			doctype="Air Shipment",
			name="OLD-AIR",
			company="Test Co",
			charges=[posted, open_row],
			estimated_revenue=0,
			estimated_costs=0,
			wip_amount=0,
			accrual_amount=0,
		)
		doc.get = lambda key, default=None: getattr(doc, key, default)
		update_estimates_from_charges(doc)
		self.assertEqual(flt(doc.estimated_revenue), 25)
		self.assertEqual(flt(doc.estimated_costs), 40)

		engine = RecognitionEngine(doc)
		wip_items = [row["item_code"] for row in engine._get_unrecognized_wip_lines()]
		accrual_items = [row["item_code"] for row in engine._get_unrecognized_accrual_lines()]
		self.assertEqual(wip_items, ["OPEN"])
		self.assertEqual(accrual_items, ["FRT"])

		issues = check_charges_posted(doc)
		codes = {issue["code"] for issue in issues}
		self.assertIn("charge_not_posted_si", codes)
		self.assertIn("charge_not_posted_pi", codes)
		self.assertEqual(len(issues), 2)

		revenue_rows = _get_eligible_revenue_rows(doc, SALES_CHARGE_CONFIG["Air Shipment"])
		cost_rows = _get_eligible_cost_rows(doc, PURCHASE_CHARGE_CONFIG["Air Shipment"])
		self.assertEqual([row[3] for row in revenue_rows], ["OPEN"])
		self.assertEqual([row[3] for row in cost_rows], ["FRT"])

	def test_booking_is_required_unless_the_file_is_a_beginning_job(self):
		normal = frappe.new_doc("Air Shipment")
		normal.booking_date = today()
		with self.assertRaises(frappe.ValidationError) as raised:
			normal.validate_required_fields_for_submit()
		self.assertIn("Air Booking", str(raised.exception))

		beginning = frappe.new_doc("Air Shipment")
		beginning.booking_date = today()
		beginning.is_beginning_job = 1
		with self.assertRaises(frappe.ValidationError) as raised:
			beginning.validate_required_fields_for_submit()
		self.assertNotIn("Air Booking", str(raised.exception))
		self.assertIn("Shipper", str(raised.exception))


class TestCreateBeginningJobs(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		self.item = create_test_item()
		self.sfx = frappe.generate_hash(length=6)
		self.templates = self._templates()

	def tearDown(self):
		frappe.db.rollback()

	def _templates(self):
		milestone = frappe.get_doc(
			{
				"doctype": "Logistics Milestone",
				"code": f"BJ-MS-{self.sfx}",
				"description": "Beginning milestone",
				"air_freight": 1,
				"transport": 1,
			}
		).insert(ignore_permissions=True)
		milestone_template = frappe.get_doc(
			{
				"doctype": "Milestone Template",
				"template_name": f"BJ Air {self.sfx}",
				"product_type": "Air Freight",
				"applies_to": "Shipment/Job",
				"applies_to_doctype": "Air Shipment",
				"is_default": 0,
				"is_active": 1,
				"items": [{"milestone": milestone.name}],
			}
		).insert(ignore_permissions=True)
		document_type = frappe.get_doc(
			{
				"doctype": "Logistics Document Type",
				"document_code": f"BJ{self.sfx}",
				"document_name": f"Beginning Doc {self.sfx}",
				"category": "Other",
			}
		).insert(ignore_permissions=True)
		document_template = frappe.get_doc(
			{
				"doctype": "Document List Template",
				"template_name": f"BJ Docs {self.sfx}",
				"product_type": "Air Freight",
				"applies_to": "Shipment/Job",
				"is_active": 1,
				"documents": [{"document_type": document_type.name, "sequence": 1, "is_mandatory": 0}],
			}
		).insert(ignore_permissions=True)
		task_template = frappe.get_doc(
			{
				"doctype": "Job Task Template",
				"template_name": f"BJ Tasks {self.sfx}",
				"product_type": "Air Freight",
				"applies_to": "Shipment/Job",
				"applies_to_doctype": "Air Shipment",
				"is_default": 0,
				"is_active": 1,
				"items": [
					{
						"task_code": f"BJ-{self.sfx}",
						"subject": "Open the old file",
						"sequence": 1,
						"is_required": 1,
					}
				],
			}
		).insert(ignore_permissions=True)
		return {
			"milestone": milestone.name,
			"milestone_template": milestone_template.name,
			"document_type": document_type.name,
			"document_template": document_template.name,
			"task_code": f"BJ-{self.sfx}",
			"task_template": task_template.name,
		}

	def _payload(self, number=None):
		number = number or f"OLD-AIR-{self.sfx}"
		return {
			"file_type": "Air Shipment",
			"header": {
				"job_number": number,
				"company": self.company,
				"customer": self.customer,
				"booking_date": today(),
				"direction": "Export",
				"shipper": "TEST-SHIPPER",
				"consignee": "TEST-CONSIGNEE",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"total_weight": 10,
				"total_volume": 1,
				"milestone_template": self.templates["milestone_template"],
				"document_list_template": self.templates["document_template"],
				"job_task_template": self.templates["task_template"],
			},
			"legs": [
				{
					"service_type": "Transport",
					"job_number": f"OLD-TR-{self.sfx}",
				}
			],
			"charges": [
				{
					"applies_to": "main",
					"item_code": self.item,
					"charge_type": "Margin",
					"quantity": 1,
					"unit_rate": 100,
					"unit_cost": 40,
					"revenue_posted": 1,
					"cost_posted": 0,
				},
				{
					"applies_to": "main",
					"item_code": self.item,
					"description": "Open revenue",
					"charge_type": "Revenue",
					"quantity": 1,
					"unit_rate": 25,
				},
				{
					"applies_to": f"OLD-TR-{self.sfx}",
					"item_code": self.item,
					"charge_type": "Cost",
					"quantity": 1,
					"unit_cost": 15,
					"cost_posted": 1,
				},
			],
		}

	def test_creates_named_file_templates_and_linked_transport(self):
		result = create_beginning_jobs(self._payload())
		self.assertEqual(result["name"], f"OLD-AIR-{self.sfx}")
		self.assertEqual(result["doctype"], "Air Shipment")

		air = frappe.get_doc("Air Shipment", result["name"])
		self.assertEqual(air.is_beginning_job, 1)
		self.assertFalse(air.air_booking)
		self.assertFalse(air.sales_quote)
		self.assertEqual(air.service_role, "Main")
		self.assertEqual(air.job_number, air.name)
		self.assertEqual(len(air.charges), 2)
		posted = air.charges[0]
		self.assertEqual(posted.sales_invoice_status, PRIOR_SYSTEM_POSTED_STATUS)
		self.assertEqual(posted.purchase_invoice_status, "Not Requested")
		self.assertEqual(flt(posted.estimated_revenue), 100)
		self.assertFalse(posted.sales_invoice)
		self.assertTrue(any(row.milestone == self.templates["milestone"] for row in air.milestones))
		self.assertTrue(any(row.document_type == self.templates["document_type"] for row in air.documents))
		self.assertTrue(any(row.task_code == self.templates["task_code"] for row in air.job_tasks))

		leg = result["legs"][0]
		self.assertEqual(leg["doctype"], "Transport Job")
		self.assertEqual(leg["name"], f"OLD-TR-{self.sfx}")
		transport = frappe.get_doc("Transport Job", leg["name"])
		self.assertEqual(transport.service_role, "Linked")
		self.assertEqual(transport.main_service_type, "Air Shipment")
		self.assertEqual(transport.main_service, air.name)
		self.assertEqual(transport.linked_service, leg["linked_service"])
		self.assertEqual(transport.is_beginning_job, 1)
		self.assertFalse(transport.transport_order)
		self.assertEqual(len(transport.charges), 1)
		self.assertEqual(transport.charges[0].purchase_invoice_status, PRIOR_SYSTEM_POSTED_STATUS)
		self.assertEqual(len(air.charges), 2)

		usages = frappe.get_all(
			"Linked Service Usage",
			filters={"parent": leg["linked_service"]},
			fields=["used_on_doctype", "used_on_name", "usage_role"],
		)
		roles = {(row.used_on_doctype, row.used_on_name, row.usage_role) for row in usages}
		self.assertIn(("Air Shipment", air.name, "Parent Booking"), roles)
		self.assertIn(("Transport Job", transport.name, "Shipment"), roles)

		revenue_rows = _get_eligible_revenue_rows(air, SALES_CHARGE_CONFIG["Air Shipment"])
		self.assertEqual(len(revenue_rows), 1)
		self.assertEqual(flt(revenue_rows[0][2]), 25)
		cost_rows = _get_eligible_cost_rows(transport, PURCHASE_CHARGE_CONFIG["Transport Job"])
		self.assertEqual(cost_rows, [])

	def test_duplicate_old_number_is_rejected(self):
		create_beginning_jobs(self._payload())
		with self.assertRaises(frappe.ValidationError):
			create_beginning_jobs(self._payload())

	def test_beginning_air_shipment_submits_without_a_booking(self):
		result = create_beginning_jobs(self._payload(number=f"OLD-SUB-{self.sfx}"))
		air = frappe.get_doc("Air Shipment", result["name"])
		air.flags.ignore_permissions = True
		air.submit()
		air.reload()
		self.assertEqual(air.docstatus, 1)
		self.assertFalse(air.air_booking)
