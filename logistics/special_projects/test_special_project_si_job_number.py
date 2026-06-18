# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for per-charge Job Number resolution on Sales Invoices from Special Project.

Data follow-up (not automated): ensure Project Jobs have Job Numbers created (e.g. SPJ-00012–14
for PROJ-0031) and correct draft SI lines on ACC-SINV-2026-00317 if still open.
"""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.special_projects.special_project_si_job_number import (
	resolve_job_number_for_special_project_charge,
)


def _sp_doc(**kwargs):
	base = {
		"doctype": "Special Project",
		"name": "PROJ-TEST",
		"job_number": "PROJ-TEST",
		"lifecycle_jobs": [],
		"charges": [],
	}
	base.update(kwargs)
	return frappe._dict(base)


class TestResolveJobNumberForSpecialProjectCharge(UnitTestCase):
	def test_special_project_service_uses_project_job_jcn(self):
		sp = _sp_doc(
			lifecycle_jobs=[
				frappe._dict(
					idx=5,
					service_type="Special Project",
					job_type="Project Order",
					job_no="SPO-00016",
				),
			],
		)
		charge = frappe._dict(
			service_type="Special Project",
			lifecycle_job_row=5,
		)

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Project Order" and name == "SPO-00016" and fieldname == "job_number":
				return None
			if dt == "DocType" and name == "Project Order":
				return True
			return None

		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_meta") as get_meta,
			patch("frappe.db.get_value", side_effect=_get_value),
			patch(
				"frappe.get_all",
				return_value=[{"job_number": "SPJ-JCN-001"}],
			),
		):
			get_meta.return_value.get_field.return_value = frappe._dict(fieldname="job_number")

			jcn = resolve_job_number_for_special_project_charge(sp, charge)

		self.assertEqual(jcn, "SPJ-JCN-001")
		self.assertNotEqual(jcn, sp.job_number)

	def test_special_project_service_uses_project_order_jcn_when_set(self):
		sp = _sp_doc(
			lifecycle_jobs=[
				frappe._dict(
					idx=5,
					service_type="Special Project",
					job_type="Project Order",
					job_no="SPO-00016",
				),
			],
		)
		charge = frappe._dict(service_type="Special Project", lifecycle_job_row=5)

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Project Order" and name == "SPO-00016" and fieldname == "job_number":
				return "ORDER-JCN-001"
			if dt == "DocType":
				return True
			return None

		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_meta") as get_meta,
			patch("frappe.db.get_value", side_effect=_get_value),
		):
			get_meta.return_value.get_field.return_value = frappe._dict(fieldname="job_number")
			jcn = resolve_job_number_for_special_project_charge(sp, charge)

		self.assertEqual(jcn, "ORDER-JCN-001")

	def test_sea_service_uses_operational_shipment_jcn(self):
		sp = _sp_doc(
			lifecycle_jobs=[
				frappe._dict(
					idx=2,
					service_type="Sea",
					job_type="Sea Booking",
					job_no="SBK-001",
				),
			],
		)
		charge = frappe._dict(service_type="Sea", lifecycle_job_row=2)

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Sea Shipment" and name == "SF-001" and fieldname == "job_number":
				return "SF-001"
			if dt == "DocType":
				return True
			return None

		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_meta") as get_meta,
			patch("frappe.db.get_value", side_effect=_get_value),
			patch(
				"logistics.special_projects.special_project_si_job_number.resolve_lifecycle_job_row_to_operational_ref",
				return_value=("Sea Shipment", "SF-001"),
			),
		):
			get_meta.return_value.get_field.return_value = frappe._dict(fieldname="job_number")
			jcn = resolve_job_number_for_special_project_charge(sp, charge)

		self.assertEqual(jcn, "SF-001")
		self.assertNotEqual(jcn, sp.job_number)

	def test_fallback_to_programme_jcn_when_unresolved(self):
		sp = _sp_doc(
			lifecycle_jobs=[
				frappe._dict(
					idx=5,
					service_type="Special Project",
					job_type="Project Order",
					job_no="SPO-EMPTY",
				),
			],
		)
		charge = frappe._dict(service_type="Special Project", lifecycle_job_row=5)

		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_meta") as get_meta,
			patch("frappe.db.get_value", return_value=None),
			patch("frappe.get_all", return_value=[]),
		):
			get_meta.return_value.get_field.return_value = frappe._dict(fieldname="job_number")
			jcn = resolve_job_number_for_special_project_charge(sp, charge)

		self.assertEqual(jcn, "PROJ-TEST")

	def test_legacy_single_lifecycle_row_without_pin(self):
		sp = _sp_doc(
			lifecycle_jobs=[
				frappe._dict(
					idx=1,
					service_type="Special Project",
					job_type="Project Job",
					job_no="SPJ-00099",
				),
			],
		)
		charge = frappe._dict(service_type="Special Project")

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Project Job" and name == "SPJ-00099" and fieldname == "job_number":
				return "SPJ-JCN-099"
			if dt == "DocType":
				return True
			return None

		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_meta") as get_meta,
			patch("frappe.db.get_value", side_effect=_get_value),
		):
			get_meta.return_value.get_field.return_value = frappe._dict(fieldname="job_number")
			jcn = resolve_job_number_for_special_project_charge(sp, charge)

		self.assertEqual(jcn, "SPJ-JCN-099")
