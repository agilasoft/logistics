# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Verify issue #1026: Transport Order from main-service Air Shipment Internal Job Detail."""

from __future__ import annotations

import unittest

import frappe

from logistics.utils.module_integration import (
	_declaration_order_job_context_from_freight_shipment,
	_inbound_order_job_context_from_freight_shipment,
	final_transport_order_job_context_from_freight_shipment,
)


def _air_shipment_main_service(
	name: str = "ASP-000000256",
	*,
	charges: list | None = None,
	internal_job_details: list | None = None,
):
	return frappe._dict(
		name=name,
		is_main_service=1,
		is_internal_job=0,
		main_job_type=None,
		main_job=None,
		sales_quote="SQ-TEST-1026",
		charges=charges or [],
		internal_job_details=internal_job_details or [],
	)


class TestIssue1026TransportOrderMainJob(unittest.TestCase):
	"""Main-service air leg + Transport Internal Job Detail without transport charges."""

	def test_declaration_order_always_links_to_freight_shipment(self):
		shipment = _air_shipment_main_service(
			internal_job_details=[frappe._dict(service_type="Customs", job_no="")]
		)
		ij, mjt, mj = _declaration_order_job_context_from_freight_shipment(
			shipment, "Air Shipment", shipment.name
		)
		self.assertEqual((ij, mjt, mj), (1, "Air Shipment", "ASP-000000256"))

	def test_inbound_order_links_via_internal_job_detail_without_charges(self):
		shipment = _air_shipment_main_service(
			internal_job_details=[frappe._dict(service_type="Warehousing", job_no="")]
		)
		ij, mjt, mj = _inbound_order_job_context_from_freight_shipment(
			shipment, "Air Shipment", shipment.name
		)
		self.assertEqual((ij, mjt, mj), (1, "Air Shipment", "ASP-000000256"))

	def test_transport_order_links_via_internal_job_detail_without_charges(self):
		"""Issue #1026: transport IJ line links TO to main-service freight shipment."""
		shipment = _air_shipment_main_service(
			charges=[frappe._dict(service_type="Air", item_code="AIR-FRT")],
			internal_job_details=[frappe._dict(service_type="Transport", job_no="")],
		)
		ij, mjt, mj = final_transport_order_job_context_from_freight_shipment(
			shipment, "Air Shipment", shipment.name
		)
		self.assertEqual((ij, mjt, mj), (1, "Air Shipment", "ASP-000000256"))

	def test_transport_order_links_when_transport_charges_exist(self):
		shipment = _air_shipment_main_service(
			charges=[frappe._dict(service_type="Transport", item_code="TRK-FRT")],
			internal_job_details=[frappe._dict(service_type="Transport", job_no="")],
		)
		ij, mjt, mj = final_transport_order_job_context_from_freight_shipment(
			shipment, "Air Shipment", shipment.name
		)
		self.assertEqual((ij, mjt, mj), (1, "Air Shipment", "ASP-000000256"))
