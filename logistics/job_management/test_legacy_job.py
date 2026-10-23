# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Legacy Job: old-system files on the existing shipment form."""

from __future__ import unicode_literals

import json
from pathlib import Path
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
from logistics.job_management.doc_events import update_estimates_from_charges
from logistics.job_management.job_readiness import check_charges_posted
from logistics.job_management.legacy_job import (
	allow_legacy_jobs,
	get_allow_legacy_jobs,
	validate_legacy_job,
)
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


def _enable_legacy_jobs():
	if not frappe.db.exists("DocType", "Job Management Settings"):
		frappe.get_meta("Job Management Settings")
	settings = frappe.get_single("Job Management Settings")
	settings.allow_legacy_jobs = 1
	settings.save(ignore_permissions=True)


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

	def test_booking_is_required_unless_the_file_is_a_legacy_job(self):
		normal = frappe.new_doc("Air Shipment")
		normal.booking_date = today()
		with self.assertRaises(frappe.ValidationError) as raised:
			normal.validate_required_fields_for_submit()
		self.assertIn("Air Booking", str(raised.exception))

		legacy = frappe.new_doc("Air Shipment")
		legacy.booking_date = today()
		legacy.is_legacy_job = 1
		with self.assertRaises(frappe.ValidationError) as raised:
			legacy.validate_required_fields_for_submit()
		self.assertNotIn("Air Booking", str(raised.exception))
		self.assertIn("Shipper", str(raised.exception))


class TestLegacyJob(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		self.item = create_test_item()
		self.sfx = frappe.generate_hash(length=6)
		_enable_legacy_jobs()
		self.assertTrue(allow_legacy_jobs())

	def tearDown(self):
		frappe.db.rollback()

	def test_settings_gate_the_legacy_job_checkbox(self):
		settings = frappe.get_single("Job Management Settings")
		settings.allow_legacy_jobs = 0
		settings.save(ignore_permissions=True)
		self.assertFalse(get_allow_legacy_jobs())
		doc = frappe.new_doc("Air Shipment")
		doc.is_legacy_job = 1
		with self.assertRaises(frappe.ValidationError) as raised:
			validate_legacy_job(doc)
		self.assertIn("Job Management Settings", str(raised.exception))

	def test_legacy_job_field_stays_hidden_in_form_json(self):
		root = Path(__file__).resolve().parents[1]
		paths = (
			root / "air_freight/doctype/air_shipment/air_shipment.json",
			root / "sea_freight/doctype/sea_shipment/sea_shipment.json",
			root / "transport/doctype/transport_job/transport_job.json",
			root / "customs/doctype/declaration/declaration.json",
			root / "warehousing/doctype/warehouse_job/warehouse_job.json",
		)
		for path in paths:
			data = json.loads(path.read_text())
			field = next(row for row in data["fields"] if row["fieldname"] == "is_legacy_job")
			self.assertEqual(field.get("hidden"), 1, path.name)
			number = next(row for row in data["fields"] if row["fieldname"] == "legacy_job_no")
			self.assertEqual(number.get("label"), "Legacy Job No")
			self.assertIn("is_legacy_job", number.get("depends_on") or "")

	def test_saves_named_air_file_with_prior_posted_charge(self):
		name = f"OLD-AIR-{self.sfx}"
		air = frappe.new_doc("Air Shipment")
		air.naming_series = "ASP-.#########"
		air.is_legacy_job = 1
		air.legacy_job_no = name
		air.booking_date = today()
		air.company = self.company
		air.local_customer = self.customer
		air.direction = "Export"
		air.shipper = "TEST-SHIPPER"
		air.consignee = "TEST-CONSIGNEE"
		air.origin_port = "USLAX"
		air.destination_port = "USJFK"
		air.branch = self.branch
		air.cost_center = self.cost_center
		air.profit_center = self.profit_center
		air.total_weight = 10
		air.total_volume = 1
		air.override_volume_weight = 1
		charge = air.append("charges", {})
		charge.item_code = self.item
		charge.charge_type = "Margin"
		charge.quantity = 1
		charge.unit_rate = 100
		charge.revenue_calculation_method = "Per Unit"
		charge.cost_calculation_method = "Per Unit"
		charge.sales_invoice_status = PRIOR_SYSTEM_POSTED_STATUS
		charge.purchase_invoice_status = "Not Requested"
		air.insert()
		air.reload()
		self.assertEqual(air.name, name)
		self.assertEqual(air.legacy_job_no, name)
		self.assertEqual(air.is_legacy_job, 1)
		self.assertEqual(air.is_beginning_job, 1)
		self.assertFalse(air.air_booking)
		self.assertFalse(air.sales_quote)
		self.assertEqual(air.job_number, air.name)
		self.assertEqual(len(air.charges), 1)
		self.assertEqual(air.charges[0].sales_invoice_status, PRIOR_SYSTEM_POSTED_STATUS)
		self.assertFalse(air.charges[0].sales_invoice)
		revenue_rows = _get_eligible_revenue_rows(air, SALES_CHARGE_CONFIG["Air Shipment"])
		self.assertEqual(revenue_rows, [])

	def test_legacy_air_shipment_submits_without_a_booking(self):
		name = f"OLD-SUB-{self.sfx}"
		air = frappe.new_doc("Air Shipment")
		air.naming_series = "ASP-.#########"
		air.is_legacy_job = 1
		air.legacy_job_no = name
		air.booking_date = today()
		air.company = self.company
		air.local_customer = self.customer
		air.direction = "Export"
		air.shipper = "TEST-SHIPPER"
		air.consignee = "TEST-CONSIGNEE"
		air.origin_port = "USLAX"
		air.destination_port = "USJFK"
		air.branch = self.branch
		air.cost_center = self.cost_center
		air.profit_center = self.profit_center
		air.total_weight = 10
		air.total_volume = 1
		air.override_volume_weight = 1
		air.insert()
		air.submit()
		air.reload()
		self.assertEqual(air.docstatus, 1)
		self.assertEqual(air.name, name)
		self.assertEqual(air.legacy_job_no, name)
		self.assertFalse(air.air_booking)

	def test_legacy_job_no_is_required_and_must_be_a_valid_name(self):
		doc = frappe.new_doc("Air Shipment")
		doc.is_legacy_job = 1
		with self.assertRaises(frappe.ValidationError) as raised:
			validate_legacy_job(doc)
		self.assertIn("Legacy Job No", str(raised.exception))

		doc.legacy_job_no = "OLD/BAD"
		with self.assertRaises(frappe.ValidationError) as raised:
			validate_legacy_job(doc)
		self.assertIn("cannot contain /", str(raised.exception))
