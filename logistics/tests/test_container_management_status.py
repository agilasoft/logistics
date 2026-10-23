# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from __future__ import unicode_literals

from frappe.tests.utils import FrappeTestCase

from logistics.container_management.api import (
	_shipping_status_to_container_status,
	_transport_status_to_container_status,
	get_or_create_container,
	movement_type_to_container_status,
)


class TestContainerStatusMapping(FrappeTestCase):
	def test_shipping_closed_maps_to_closed(self):
		self.assertEqual(_shipping_status_to_container_status("Closed"), "Closed")

	def test_shipping_unmapped_returns_none(self):
		self.assertIsNone(_shipping_status_to_container_status("Booking Received"))
		self.assertIsNone(_shipping_status_to_container_status("Future Milestone XYZ"))

	def test_shipping_customs_hold(self):
		self.assertEqual(_shipping_status_to_container_status("Customs Hold"), "Customs Hold")

	def test_transport_unmapped_returns_none(self):
		self.assertIsNone(_transport_status_to_container_status("Submitted"))
		self.assertIsNone(_transport_status_to_container_status("Draft"))

	def test_transport_completed_maps_empty_returned(self):
		self.assertEqual(_transport_status_to_container_status("Completed"), "Empty Returned")

	def test_movement_returned_maps_empty_returned(self):
		self.assertEqual(movement_type_to_container_status("Returned"), "Empty Returned")

	def test_movement_other_returns_none(self):
		self.assertIsNone(movement_type_to_container_status("Other"))

	def test_get_or_create_container_leaves_return_status_blank(self):
		from unittest.mock import patch

		created = {}

		class FakeContainer:
			def __init__(self):
				self.container_number = None
				self.master_bill = None
				self.is_active = None
				self.container_type = None
				self.seal_number = None
				self.status = None
				self.free_time_days = None
				self.return_status = None
				self.returned_date = None
				self.name = "fake-container-uuid"

			def insert(self, ignore_permissions=False):
				created["doc"] = self

		with patch(
			"logistics.container_management.api.is_container_management_enabled",
			return_value=True,
		), patch(
			"logistics.container_management.api.validate_container_number",
			return_value=(True, None),
		), patch(
			"logistics.container_management.api.get_strict_validation_setting",
			return_value=False,
		), patch(
			"logistics.container_management.api.frappe.db.get_value",
			return_value=None,
		), patch(
			"logistics.container_management.api.frappe.db.sql",
			return_value=[],
		), patch(
			"logistics.container_management.api.frappe.new_doc",
			return_value=FakeContainer(),
		):
			get_or_create_container(
				"TESTU1234567",
				master_bill="MBL-TEST-001",
				status="In Transit",
			)

		self.assertIn("doc", created)
		self.assertIsNone(created["doc"].return_status)
