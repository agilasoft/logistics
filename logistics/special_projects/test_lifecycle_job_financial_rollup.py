# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import now_datetime

from logistics.special_projects.lifecycle_job_financial_rollup import (
	_lifecycle_row_financial_link,
	_primary_charge_doc_for_lifecycle_link,
	calculate_lifecycle_job_charge_totals,
	calculate_linked_job_stack_totals,
	sync_lifecycle_job_financials,
)
from logistics.special_projects.lifecycle_job_planned_rollup import (
	_lifecycle_rows_need_programme_charge_attribution,
	_planning_lifecycle_rows,
	sync_lifecycle_job_planned_from_charges,
)
from logistics.special_projects.special_project_charge_lifecycle import (
	programme_charges_for_lifecycle_row,
)
from logistics.utils.internal_job_main_rollup import calculate_internal_job_rollup_totals


class TestLifecycleRowFinancialLink(UnitTestCase):
	def test_reads_order_no_from_dict_service_row(self):
		row = {
			"name": "SPS-1",
			"service_type": "Air",
			"job_type": "Air Booking",
			"order_no": "ABK-1",
		}
		jt, jn = _lifecycle_row_financial_link(row)
		self.assertEqual(jt, "Air Booking")
		self.assertEqual(jn, "ABK-1")

	def test_prefers_execution_job_no_over_order_no(self):
		row = frappe._dict(
			service_type="Transport",
			job_type="Transport Order",
			order_no="TO-1",
			job_no="TJ-1",
		)
		with patch(
			"logistics.utils.special_project_internal_jobs._resolve_execution_name_to_operational_ref",
			return_value=("Transport Job", "TJ-1"),
		):
			jt, jn = _lifecycle_row_financial_link(row)
		self.assertEqual((jt, jn), ("Transport Job", "TJ-1"))


class TestProgrammeChargesForLifecycleRow(UnitTestCase):
	def test_matches_transport_row_by_parameters(self):
		sp = frappe._dict(
			charges=[
				frappe._dict(
					idx=1,
					service_type="Transport",
					transport_template="TPL-1",
					vehicle_type="20FT",
					estimated_cost=100,
				),
				frappe._dict(
					idx=2,
					service_type="Transport",
					transport_template="TPL-2",
					vehicle_type="40FT",
					estimated_cost=200,
				),
			],
			lifecycle_jobs=[],
		)
		row = frappe._dict(
			name="LJ-1",
			idx=1,
			service_type="Transport",
			transport_template="TPL-1",
			vehicle_type="20FT",
		)
		matched = programme_charges_for_lifecycle_row(sp, row)
		self.assertEqual(len(matched), 1)
		self.assertEqual(matched[0].idx, 1)


class TestLifecycleRowsNeedProgrammeAttribution(UnitTestCase):
	def test_true_when_any_row_missing_job_no(self):
		rows = [
			frappe._dict(job_no="TO-1", lifecycle_job_line="P1"),
			frappe._dict(job_no=""),
		]
		self.assertTrue(_lifecycle_rows_need_programme_charge_attribution(rows))

	def test_false_when_all_rows_are_execution(self):
		rows = [
			frappe._dict(job_no="TO-1", lifecycle_job_line="P1"),
			frappe._dict(job_no="TO-2", lifecycle_job_line="P2"),
		]
		self.assertFalse(_lifecycle_rows_need_programme_charge_attribution(rows))

	def test_planning_rows_excludes_execution_rows(self):
		rows = [
			frappe._dict(job_no="TO-1", lifecycle_job_line="P1"),
			frappe._dict(job_no=""),
			frappe._dict(job_no=None),
		]
		self.assertEqual(len(_planning_lifecycle_rows(rows)), 2)


class TestCalculateLifecycleJobChargeTotals(UnitTestCase):
	def test_uses_estimated_as_actual_when_charge_child_has_no_actual_fields(self):
		with patch(
			"logistics.special_projects.lifecycle_job_financial_rollup.charge_child_tracks_actual_amounts",
			return_value=False,
		):
			doc = frappe._dict(
				doctype="Transport Order",
				charges=[
					frappe._dict(estimated_cost=100, estimated_revenue=200),
					frappe._dict(estimated_cost=50, estimated_revenue=80),
				],
			)
			pc, pr, ac, ar = calculate_lifecycle_job_charge_totals(doc)
		self.assertEqual(pc, 150)
		self.assertEqual(pr, 280)
		self.assertEqual(ac, 150)
		self.assertEqual(ar, 280)

	def test_uses_internal_rollup_when_charge_child_has_actual_fields(self):
		doc = frappe._dict(
			doctype="Transport Job",
			charges=[frappe._dict(estimated_cost=100, estimated_revenue=200, actual_cost=10, actual_revenue=20)],
		)
		with patch(
			"logistics.special_projects.lifecycle_job_financial_rollup.charge_child_tracks_actual_amounts",
			return_value=True,
		):
			pc, pr, ac, ar = calculate_lifecycle_job_charge_totals(doc)
		self.assertEqual(pc, 100)
		self.assertEqual(ac, 10)


class TestPrimaryChargeDocForLifecycleLink(UnitTestCase):
	def test_prefers_transport_job_when_it_has_charges(self):
		to_doc = frappe._dict(doctype="Transport Order", name="TO-1", charges=[])
		tj_doc = frappe._dict(
			doctype="Transport Job",
			name="TJ-1",
			charges=[frappe._dict(estimated_cost=10, estimated_revenue=20, actual_cost=3, actual_revenue=4)],
		)

		def _active(jt, jn):
			if jt == "Transport Order" and jn == "TO-1":
				return to_doc
			if jt == "Transport Job" and jn == "TJ-1":
				return tj_doc
			return None

		with (
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup._active_job_doc",
				side_effect=_active,
			),
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup.resolve_lifecycle_job_row_to_operational_ref",
				return_value=("Transport Job", "TJ-1"),
			),
		):
			doc = _primary_charge_doc_for_lifecycle_link(
				"Transport Order",
				"TO-1",
				frappe._dict(service_type="Transport", job_type="Transport Order", job_no="TO-1"),
			)
		self.assertEqual(doc.name, "TJ-1")

	def test_falls_back_to_transport_order_when_job_has_no_charges(self):
		to_doc = frappe._dict(
			doctype="Transport Order",
			name="TO-1",
			charges=[frappe._dict(estimated_cost=99, estimated_revenue=199)],
		)
		tj_doc = frappe._dict(doctype="Transport Job", name="TJ-1", charges=[])

		def _active(jt, jn):
			if jt == "Transport Order" and jn == "TO-1":
				return to_doc
			if jt == "Transport Job" and jn == "TJ-1":
				return tj_doc
			return None

		with (
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup._active_job_doc",
				side_effect=_active,
			),
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup.resolve_lifecycle_job_row_to_operational_ref",
				return_value=("Transport Job", "TJ-1"),
			),
		):
			doc = _primary_charge_doc_for_lifecycle_link("Transport Order", "TO-1")
		self.assertEqual(doc.name, "TO-1")


class TestCalculateLinkedJobStackTotals(UnitTestCase):
	def test_sums_main_and_internal_job_charges(self):
		main = frappe._dict(
			doctype="Transport Order",
			name="TO-MAIN",
			charges=[
				frappe._dict(estimated_cost=100, estimated_revenue=200, actual_cost=10, actual_revenue=20)
			],
		)
		satellite = frappe._dict(
			doctype="Transport Order",
			name="TO-INT",
			charges=[
				frappe._dict(estimated_cost=50, estimated_revenue=80, actual_cost=5, actual_revenue=8)
			],
		)
		with (
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup._primary_charge_doc_for_lifecycle_link",
				return_value=main,
			),
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup._iter_internal_satellite_docs",
				return_value=[satellite],
			),
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup.calculate_lifecycle_job_charge_totals",
				side_effect=calculate_internal_job_rollup_totals,
			),
		):
			pc, pr, ac, ar = calculate_linked_job_stack_totals("Transport Order", "TO-MAIN")
		self.assertEqual(pc, 150)
		self.assertEqual(pr, 280)
		self.assertEqual(ac, 15)
		self.assertEqual(ar, 28)

	def test_returns_zeros_when_main_missing(self):
		with patch(
			"logistics.special_projects.lifecycle_job_financial_rollup._primary_charge_doc_for_lifecycle_link",
			return_value=None,
		):
			self.assertEqual(calculate_linked_job_stack_totals("Transport Order", "MISSING"), (0, 0, 0, 0))


class TestLifecycleJobFinancialRollup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._has_lifecycle_jobs = bool(
			frappe.get_meta("Special Project").has_field("lifecycle_jobs")
		)
		cls._has_charge_tag = bool(
			frappe.get_meta("Special Project Charges").has_field("lifecycle_job_line")
		)

	def setUp(self):
		if not self._has_lifecycle_jobs:
			self.skipTest("lifecycle_jobs not installed")

	def _new_special_project(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		cost_center = frappe.db.get_value("Cost Center", {}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")
		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test Lifecycle Financial Rollup {now_datetime()}"
		sp.customer = customer
		sp.company = company
		if cost_center:
			sp.cost_center = cost_center
		return sp

	def test_lifecycle_row_uses_job_financials_when_job_no_set(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"activity_name": "Leg 1",
				"job_type": "Transport Order",
				"order_no": "TO-LINKED-1",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"estimated_cost": 999,
				"estimated_revenue": 1999,
			},
		)
		with (
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup._active_job_doc",
				return_value=frappe._dict(doctype="Transport Order", name="TO-LINKED-1"),
			),
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup.calculate_linked_job_stack_totals",
				return_value=(0, 0, 33, 44),
			),
		):
			sync_lifecycle_job_financials(sp)
		row = sp.lifecycle_jobs[0]
		self.assertEqual(row.planned_cost, 999)
		self.assertEqual(row.planned_revenue, 1999)
		self.assertEqual(row.actual_cost, 33)
		self.assertEqual(row.actual_revenue, 44)

	def test_transport_planned_from_matching_params_not_linked_job(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"activity_name": "Leg A",
				"transport_template": "TPL-A",
				"vehicle_type": "20FT",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Match A",
				"transport_template": "TPL-A",
				"vehicle_type": "20FT",
				"estimated_cost": 100,
				"estimated_revenue": 200,
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Other leg",
				"transport_template": "TPL-B",
				"vehicle_type": "40FT",
				"estimated_cost": 500,
				"estimated_revenue": 900,
			},
		)
		sync_lifecycle_job_financials(sp)
		row = sp.lifecycle_jobs[0]
		self.assertEqual(row.planned_cost, 100)
		self.assertEqual(row.planned_revenue, 200)

	def test_linked_transport_order_planned_from_programme_actual_from_job(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"activity_name": "Leg",
				"job_type": "Transport Order",
				"order_no": "TO-LINKED-1",
				"transport_template": "TPL-A",
				"vehicle_type": "20FT",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Match",
				"transport_template": "TPL-A",
				"vehicle_type": "20FT",
				"estimated_cost": 100,
				"estimated_revenue": 200,
			},
		)
		with (
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup._active_job_doc",
				return_value=frappe._dict(doctype="Transport Order", name="TO-LINKED-1"),
			),
			patch(
				"logistics.special_projects.lifecycle_job_financial_rollup.calculate_linked_job_stack_totals",
				return_value=(0, 0, 55, 66),
			),
		):
			sync_lifecycle_job_financials(sp)
		row = sp.lifecycle_jobs[0]
		self.assertEqual(row.planned_cost, 100)
		self.assertEqual(row.planned_revenue, 200)
		self.assertEqual(row.actual_cost, 55)
		self.assertEqual(row.actual_revenue, 66)

	def test_saves_with_untagged_charge_when_single_linked_transport_row(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"job_no": "TO-A",
				"job_type": "Transport Order",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "DELIVERY",
				"estimated_cost": 10,
				"estimated_revenue": 20,
			},
		)
		with patch(
			"logistics.special_projects.lifecycle_job_financial_rollup.calculate_linked_job_stack_totals",
			return_value=(0, 0, 0, 0),
		):
			sp.insert(ignore_permissions=True, ignore_links=True)

	def test_allows_untagged_charge_with_duplicate_transport_planning_rows(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "A"})
		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "B"})
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "DELIVERY",
				"estimated_cost": 10,
				"estimated_revenue": 20,
			},
		)
		sp.insert(ignore_permissions=True, ignore_links=True)

	def test_linked_transport_row_does_not_require_tag_when_only_execution_rows(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"job_no": "TO-A",
				"job_type": "Transport Order",
			},
		)
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"job_no": "TO-B",
				"job_type": "Transport Order",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "DELIVERY",
				"estimated_cost": 10,
				"estimated_revenue": 20,
			},
		)
		with patch(
			"logistics.special_projects.lifecycle_job_financial_rollup.calculate_linked_job_stack_totals",
			return_value=(0, 0, 0, 0),
		):
			sp.insert(ignore_permissions=True, ignore_links=True)

	def test_cancelled_job_link_zeros_lifecycle_financials(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"job_type": "Transport Order",
				"job_no": "TO-CANCELLED",
			},
		)
		with patch(
			"logistics.special_projects.lifecycle_job_financial_rollup._active_job_doc",
			return_value=None,
		):
			sync_lifecycle_job_financials(sp)
		row = sp.lifecycle_jobs[0]
		self.assertEqual(row.planned_cost, 0)
		self.assertEqual(row.planned_revenue, 0)
		self.assertEqual(row.actual_cost, 0)
		self.assertEqual(row.actual_revenue, 0)

	def test_planned_wrapper_delegates_to_financial_sync(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Special Project", "activity_name": "Phase"})
		sp.append(
			"charges",
			{
				"service_type": "Special Project",
				"estimated_cost": 40,
				"estimated_revenue": 70,
			},
		)
		sync_lifecycle_job_planned_from_charges(sp)
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 40)
		self.assertEqual(sp.lifecycle_jobs[0].planned_revenue, 70)
		self.assertEqual(sp.lifecycle_jobs[0].actual_cost, 0)
		self.assertEqual(sp.lifecycle_jobs[0].actual_revenue, 0)


class TestCalculateInternalJobRollupUsedByFinancial(UnitTestCase):
	def test_disbursement_excluded(self):
		doc = frappe._dict(
			charges=[
				frappe._dict(
					charge_type="Disbursement",
					estimated_cost=500,
					estimated_revenue=500,
					actual_cost=500,
					actual_revenue=500,
				),
				frappe._dict(estimated_cost=25, estimated_revenue=35, actual_cost=3, actual_revenue=4),
			]
		)
		pc, pr, ac, ar = calculate_internal_job_rollup_totals(doc)
		self.assertEqual(pc, 25)
		self.assertEqual(pr, 35)
		self.assertEqual(ac, 3)
		self.assertEqual(ar, 4)
