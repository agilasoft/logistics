# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.special_projects.special_project_charge_execution import (
	_order_key_from_execution_doc,
	_planning_order_key_for_execution_log,
	_matching_programme_charges,
	cancel_charge_execution_for_doc,
	normalize_charge_execution_log_link_fields,
	post_charge_execution_for_doc,
	resolve_lifecycle_planning_row,
)
from logistics.special_projects.special_project_charge_lifecycle import (
	lifecycle_row_order_link_is_cancelled,
	planning_row_is_open,
	programme_charge_applies_to_planning_lifecycle,
	programme_charges_for_service_type,
)


def _mock_charge(**fields):
	sn = SimpleNamespace(**fields)
	sn.as_dict = lambda: dict(fields)
	return sn


class TestChargeExecutionHelpers(UnitTestCase):
	def test_order_key_from_air_shipment(self):
		doc = frappe._dict(doctype="Air Shipment", name="AS-1", air_booking="AB-1")
		self.assertEqual(_order_key_from_execution_doc(doc), ("Air Booking", "AB-1"))

	def test_order_key_from_transport_job(self):
		doc = frappe._dict(doctype="Transport Job", name="TJ-1", transport_order="TO-1")
		self.assertEqual(_order_key_from_execution_doc(doc), ("Transport Order", "TO-1"))

	def test_planning_order_key_ignores_execution_job_type_on_lifecycle_row(self):
		lifecycle_row = frappe._dict(
			job_type="Transport Job",
			order_no="TRO-1",
			order_type="",
		)
		exec_doc = frappe._dict(doctype="Transport Job", name="TJ-1", transport_order="TRO-1")
		self.assertEqual(
			_planning_order_key_for_execution_log(lifecycle_row, exec_doc),
			("Transport Order", "TRO-1"),
		)

	@patch("frappe.db.exists")
	def test_normalize_charge_execution_log_repairs_execution_job_type(self, mock_exists):
		def _exists(doctype, name):
			return (doctype, name) in {
				("Transport Job", "TJ-1"),
				("Transport Order", "TRO-1"),
			}

		mock_exists.side_effect = _exists

		log = frappe._dict(job_type="Transport Job", order_no="TRO-1", job_no="TJ-1")
		with patch(
			"logistics.special_projects.special_project_charge_execution.frappe.get_doc",
			return_value=frappe._dict(
				doctype="Transport Job", name="TJ-1", transport_order="TRO-1"
			),
		):
			normalize_charge_execution_log_link_fields(
				frappe._dict(charge_execution_logs=[log])
			)
		self.assertEqual(log.job_type, "Transport Order")
		self.assertEqual(log.order_no, "TRO-1")

	def test_planning_row_is_open_until_order_no_set(self):
		sp = frappe._dict(
			lifecycle_jobs=[
				frappe._dict(
					name="LJ-1",
					service_type="Transport",
					job_type="",
					order_no="",
					job_no="",
					lifecycle_job_line="",
				),
			]
		)
		self.assertTrue(planning_row_is_open(sp, sp.lifecycle_jobs[0]))
		sp.lifecycle_jobs[0].order_no = "TO-1"
		sp.lifecycle_jobs[0].job_type = "Transport Order"
		with patch(
			"logistics.special_projects.special_project_charge_lifecycle.lifecycle_row_order_link_is_cancelled",
			return_value=False,
		):
			self.assertFalse(planning_row_is_open(sp, sp.lifecycle_jobs[0]))

	def test_planning_row_is_open_when_order_no_cancelled(self):
		sp = frappe._dict(
			lifecycle_jobs=[
				frappe._dict(
					name="LJ-1",
					service_type="Transport",
					job_type="Transport Order",
					order_no="TO-CANCELLED",
					job_no="",
					lifecycle_job_line="",
				),
			]
		)
		with patch(
			"logistics.special_projects.special_project_charge_lifecycle.lifecycle_row_order_link_is_cancelled",
			return_value=True,
		):
			self.assertTrue(planning_row_is_open(sp, sp.lifecycle_jobs[0]))

	def test_lifecycle_row_order_link_is_cancelled_delegates(self):
		row = frappe._dict(job_type="Transport Order", order_no="TRO-1")
		with patch(
			"logistics.utils.internal_job_from_source.linked_internal_job_target_is_cancelled",
			return_value=True,
		):
			self.assertTrue(lifecycle_row_order_link_is_cancelled(row))
		with patch(
			"logistics.utils.internal_job_from_source.linked_internal_job_target_is_cancelled",
			return_value=False,
		):
			self.assertFalse(lifecycle_row_order_link_is_cancelled(row))

	def test_programme_charges_for_service_type(self):
		sp = frappe._dict(
			doctype="Special Project",
			charges=[
				_mock_charge(service_type="Air", item_code="A"),
				_mock_charge(service_type="Transport", item_code="B"),
			]
		)
		out = programme_charges_for_service_type(sp, "Air")
		self.assertEqual(len(out), 1)
		self.assertEqual(out[0].item_code, "A")

	def test_programme_charges_table_field_mice_uses_consolidation(self):
		from logistics.special_projects.special_project_charge_lifecycle import (
			programme_charges_table_field,
		)

		self.assertEqual(programme_charges_table_field("MICE Project"), "consolidation_charges")
		self.assertEqual(programme_charges_table_field("Exhibit"), "consolidation_charges")
		self.assertEqual(programme_charges_table_field("Special Project"), "charges")

	def test_programme_charges_for_mice_consolidation_blank_service_type(self):
		"""Consolidation rows without service_type match any requested service."""
		mice = frappe._dict(
			doctype="MICE Project",
			consolidation_charges=[
				_mock_charge(charge_type="Margin", item_code="MICE-BOOTH"),
			],
			charges=[],
		)
		out = programme_charges_for_service_type(mice, "MICE")
		self.assertEqual(len(out), 1)
		self.assertEqual(out[0].item_code, "MICE-BOOTH")
		out_air = programme_charges_for_service_type(mice, "Air")
		self.assertEqual(len(out_air), 1)

	def test_resolve_lifecycle_planning_row_by_order(self):
		sp = frappe._dict(
			lifecycle_jobs=[
				frappe._dict(
					name="LJ-1",
					service_type="Transport",
					job_type="Transport Order",
					order_no="TO-1",
					lifecycle_job_line="",
				),
			]
		)
		row = resolve_lifecycle_planning_row(sp, "Transport Order", "TO-1")
		self.assertIsNotNone(row)
		self.assertEqual(row.name, "LJ-1")


class TestChargeExecutionPosting(UnitTestCase):
	def test_post_increments_qty_and_appends_log(self):
		charge = _mock_charge(
			idx=1,
			doctype="Special Project Charges",
			service_type="Air",
			item_code="TEST-ITEM",
			item_name="Test",
			quantity=1,
			unit_rate=100,
			unit_type="Job",
			revenue_calculation_method="Per Unit",
			cost_calculation_method="Per Unit",
			charge_type="Revenue",
			estimated_revenue=100,
			estimated_cost=50,
			actual_revenue=0,
			actual_cost=0,
		)
		lifecycle_row = frappe._dict(
			name="LJ-1",
			service_type="Air",
			job_type="Air Booking",
			order_no="AB-1",
			lifecycle_job_line="",
		)
		sp = SimpleNamespace(
			name="SP-1",
			doctype="Special Project",
			charges=[charge],
			charge_execution_logs=[],
			lifecycle_jobs=[lifecycle_row],
			flags=SimpleNamespace(),
		)
		sp.get = lambda k, default=None: getattr(sp, k, default if default is not None else [])

		def _append(field, row):
			if field == "charge_execution_logs":
				created = SimpleNamespace(**row)
				sp.charge_execution_logs.append(created)
				return created
			if field == "lifecycle_jobs":
				created = SimpleNamespace(**row)
				sp.lifecycle_jobs.append(created)
				return created
			return None

		sp.append = _append
		sp.save = lambda **kwargs: None

		exec_doc = frappe._dict(
			doctype="Air Shipment",
			name="AS-1",
			air_booking="AB-1",
			project="SP-1",
			charges=[_mock_charge(item_code="TEST-ITEM", service_type="Air")],
		)

		with (
			patch(
				"logistics.special_projects.special_project_charge_execution.resolve_lifecycle_row_for_execution_doc",
				return_value=(sp, lifecycle_row),
			),
			patch(
				"logistics.special_projects.special_project_charge_execution.sync_lifecycle_job_financials"
			),
		):
			n = post_charge_execution_for_doc(exec_doc)
		self.assertEqual(n, 1)
		self.assertEqual(charge.quantity, 1)
		self.assertEqual(charge.estimated_revenue, 100)
		self.assertEqual(charge.actual_revenue, 100)
		self.assertEqual(len(sp.charge_execution_logs), 1)
		self.assertEqual(lifecycle_row.job_type, "Air Booking")
		self.assertEqual(lifecycle_row.order_no, "AB-1")
		self.assertEqual(lifecycle_row.job_no, "AS-1")
		self.assertEqual(len(sp.lifecycle_jobs), 1)
		self.assertFalse(
			[
				r
				for r in sp.lifecycle_jobs
				if getattr(r, "lifecycle_job_line", None) == "LJ-1"
			]
		)

	def test_post_is_idempotent_per_job_and_item(self):
		charge = _mock_charge(
			idx=1,
			service_type="Transport",
			item_code="TEST-ITEM",
			quantity=1,
			revenue_calculation_method="Per Unit",
			charge_type="Revenue",
		)
		lifecycle_row = frappe._dict(
			name="LJ-1",
			service_type="Transport",
			job_type="Transport Order",
			order_no="TO-1",
		)
		sp = SimpleNamespace(
			name="SP-1",
			charges=[charge],
			charge_execution_logs=[
				SimpleNamespace(
					charge_idx=1,
					job_type="Transport Order",
					order_no="TO-1",
					job_no="TJ-1",
					item_code="TEST-ITEM",
					status="Posted",
				)
			],
			lifecycle_jobs=[lifecycle_row],
			flags=SimpleNamespace(),
		)
		sp.get = lambda k, default=None: getattr(sp, k, default if default is not None else [])
		sp.append = lambda field, row: sp.charge_execution_logs.append(SimpleNamespace(**row))
		sp.save = lambda **kwargs: None
		tj = frappe._dict(
			doctype="Transport Job",
			name="TJ-1",
			transport_order="TO-1",
			project="SP-1",
			charges=[],
		)
		with patch(
			"logistics.special_projects.special_project_charge_execution.resolve_lifecycle_row_for_execution_doc",
			return_value=(sp, lifecycle_row),
		):
			n = post_charge_execution_for_doc(tj)
		self.assertEqual(n, 0)
		self.assertEqual(charge.quantity, 1)

	def test_cancel_reverses_qty_and_log(self):
		charge = _mock_charge(
			idx=1,
			service_type="Transport",
			item_code="TEST-ITEM",
			quantity=1,
			revenue_calculation_method="Per Unit",
			charge_type="Revenue",
		)
		log_row = frappe._dict(
			charge_idx=1,
			item_code="TEST-ITEM",
			qty=1,
			job_type="Air Booking",
			order_no="AB-1",
			job_no="AS-1",
			lifecycle_job_line="LJ-1",
			status="Posted",
		)
		lifecycle_row = frappe._dict(
			name="LJ-1",
			service_type="Air",
			job_type="Air Booking",
			order_no="AB-1",
		)
		exec_row = frappe._dict(
			name="LJ-2",
			service_type="Air",
			job_type="Air Shipment",
			job_no="AS-1",
			lifecycle_job_line="LJ-1",
		)
		sp = SimpleNamespace(
			name="SP-1",
			charges=[charge],
			charge_execution_logs=[log_row],
			lifecycle_jobs=[lifecycle_row, exec_row],
			flags=SimpleNamespace(),
		)
		sp.get = lambda k, default=None: getattr(sp, k, default if default is not None else [])
		sp.remove = lambda row: sp.lifecycle_jobs.remove(row)
		sp.save = lambda **kwargs: None
		exec_doc = frappe._dict(
			doctype="Air Shipment",
			name="AS-1",
			air_booking="AB-1",
			project="SP-1",
		)
		with (
			patch(
				"logistics.special_projects.special_project_charge_execution.resolve_lifecycle_row_for_execution_doc",
				return_value=(sp, lifecycle_row),
			),
			patch(
				"logistics.special_projects.special_project_charge_execution._recalculate_programme_charge"
			),
			patch(
				"logistics.special_projects.special_project_charge_execution.sync_lifecycle_job_financials"
			),
		):
			n = cancel_charge_execution_for_doc(exec_doc)
		self.assertEqual(n, 1)
		self.assertEqual(log_row.status, "Cancelled")
		self.assertEqual(charge.quantity, 1)
		self.assertEqual(lifecycle_row.job_type, "Air Booking")
		self.assertEqual(
			[r for r in sp.lifecycle_jobs if getattr(r, "lifecycle_job_line", None) == "LJ-1"],
			[],
		)

	def test_multiple_delivery_rows_map_to_distinct_lifecycle_legs(self):
		legs = [
			frappe._dict(name="LJ-1", idx=1, service_type="Transport"),
			frappe._dict(name="LJ-2", idx=2, service_type="Transport"),
		]
		charges = [
			_mock_charge(idx=1, service_type="Transport", item_code="DELIVERY", unit_rate=100),
			_mock_charge(idx=2, service_type="Transport", item_code="DELIVERY", unit_rate=200),
		]
		sp = frappe._dict(charges=charges, lifecycle_jobs=legs)
		matched_leg_1 = _matching_programme_charges(
			sp,
			legs[0],
			frappe._dict(charges=[_mock_charge(item_code="DELIVERY")]),
		)
		matched_leg_2 = _matching_programme_charges(
			sp,
			legs[1],
			frappe._dict(charges=[_mock_charge(item_code="DELIVERY")]),
		)
		self.assertEqual([c.idx for c in matched_leg_1], [1])
		self.assertEqual([c.idx for c in matched_leg_2], [2])

	def test_shared_freight_row_matches_all_legs_of_service_type(self):
		legs = [
			frappe._dict(name="LJ-1", idx=1, service_type="Sea"),
			frappe._dict(name="LJ-2", idx=2, service_type="Sea"),
		]
		charge = _mock_charge(idx=4, service_type="Sea", item_code="FREIGHT", unit_rate=850)
		sp = frappe._dict(charges=[charge], lifecycle_jobs=legs)
		for leg in legs:
			self.assertTrue(
				programme_charge_applies_to_planning_lifecycle(sp, charge, leg)
			)
			matched = _matching_programme_charges(
				sp, leg, frappe._dict(charges=[_mock_charge(item_code="FREIGHT")])
			)
			self.assertEqual(matched, [charge])
