# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for per-charge Job Number on Purchase Invoices from Special Project."""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.job_number_dimension_sync import (
	_apply_job_number_dimension_on_pi_item,
	_charge_matches_pi_item,
	_sync_special_project_pi_item_job_numbers,
)
from logistics.invoice_integration.purchase_invoice_api import (
	_line_job_number_for_purchase_invoice,
)


def _sp_doc(**kwargs):
	base = {
		"doctype": "Special Project",
		"name": "PROJ-TEST",
		"job_number": "PROJ-PROGRAMME",
		"lifecycle_jobs": [],
		"charges": [],
	}
	base.update(kwargs)
	return frappe._dict(base)


class TestLineJobNumberForPurchaseInvoice(UnitTestCase):
	def test_special_project_uses_resolver_not_programme_only(self):
		sp = _sp_doc()
		charge = frappe._dict(service_type="Sea", lifecycle_job_row=2)

		with patch(
			"logistics.invoice_integration.purchase_invoice_api.resolve_job_number_for_special_project_charge",
			return_value="LEG-JCN-001",
		) as resolver:
			jcn = _line_job_number_for_purchase_invoice("Special Project", sp, charge)

		resolver.assert_called_once_with(sp, charge)
		self.assertEqual(jcn, "LEG-JCN-001")
		self.assertNotEqual(jcn, sp.job_number)

	def test_non_special_project_uses_job_header(self):
		job = frappe._dict(job_number="SHIP-JCN-001")
		charge = frappe._dict()
		jcn = _line_job_number_for_purchase_invoice("Sea Shipment", job, charge)
		self.assertEqual(jcn, "SHIP-JCN-001")


class TestSpecialProjectPiDimensionSync(UnitTestCase):
	def test_charge_matches_pi_item_by_item_code_and_cost(self):
		charge = frappe._dict(item_code="FREIGHT", estimated_cost=100, unit_cost=0, cost_quantity=1)
		item = frappe._dict(item_code="FREIGHT", rate=100)
		self.assertTrue(_charge_matches_pi_item(charge, item))
		self.assertFalse(_charge_matches_pi_item(charge, frappe._dict(item_code="OTHER", rate=100)))

	def test_sync_overwrites_programme_jcn_with_leg_jcn(self):
		sp = _sp_doc(
			charges=[
				frappe._dict(
					name="ch-1",
					item_code="FREIGHT",
					estimated_cost=100,
					unit_cost=0,
					cost_quantity=1,
					purchase_invoice="ACC-PINV-2026-00350",
					service_type="Special Project",
					lifecycle_job_row=5,
				),
			],
		)
		pi_item = type("PIItem", (), {"item_code": "FREIGHT", "rate": 100, "job_number": "PROJ-PROGRAMME"})()
		pi = frappe._dict(
			doctype="Purchase Invoice",
			name="ACC-PINV-2026-00350",
			docstatus=0,
			reference_doctype="Special Project",
			reference_name="PROJ-TEST",
			job_number="PROJ-PROGRAMME",
		)
		pi["items"] = [pi_item]

		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_doc", return_value=sp),
			patch(
				"logistics.invoice_integration.job_number_dimension_sync.reference_dimension_row_dict",
				side_effect=lambda _dt, _dim, jn: {"job_number": jn},
			),
			patch(
				"logistics.invoice_integration.job_number_dimension_sync.resolve_job_number_for_special_project_charge",
				return_value="LEG-JCN-001",
			),
		):
			handled = _sync_special_project_pi_item_job_numbers(pi)

		self.assertTrue(handled)
		self.assertEqual(pi.get("items")[0].job_number, "LEG-JCN-001")

	def test_apply_dimension_sets_when_missing(self):
		row = frappe._dict()
		with patch(
			"logistics.invoice_integration.job_number_dimension_sync.reference_dimension_row_dict",
			return_value={"job_number": "LEG-JCN-001"},
		):
			_apply_job_number_dimension_on_pi_item(row, "LEG-JCN-001")
		self.assertEqual(row.job_number, "LEG-JCN-001")
