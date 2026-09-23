# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests import IntegrationTestCase, UnitTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestContainer(IntegrationTestCase):
	"""
	Integration tests for Container.
	Use this class for testing interactions between multiple components.
	"""

	pass


class UnitTestContainerLocationFields(UnitTestCase):
	def test_normalize_location_pair_unloco_from_legacy_zone_type(self):
		from logistics.logistics.doctype.container.container import normalize_container_location_pair

		with patch("logistics.logistics.doctype.container.container.frappe.db.exists") as exists:
			exists.side_effect = lambda doctype, name: doctype == "UNLOCO" and name == "MQMPT"
			result = normalize_container_location_pair("LZN-NRTS", "MQMPT")
		self.assertEqual(result, ("UNLOCO", "MQMPT"))

	def test_normalize_location_pair_transport_zone_when_type_empty(self):
		from logistics.logistics.doctype.container.container import normalize_container_location_pair

		with patch("logistics.logistics.doctype.container.container.frappe.db.exists") as exists:
			exists.side_effect = lambda doctype, name: doctype == "Transport Zone" and name == "LZN-NRTS"
			result = normalize_container_location_pair("", "LZN-NRTS")
		self.assertEqual(result, ("Transport Zone", "LZN-NRTS"))

	def test_normalize_location_pair_moves_zone_from_type_when_location_empty(self):
		from logistics.logistics.doctype.container.container import normalize_container_location_pair

		with patch("logistics.logistics.doctype.container.container.frappe.db.exists") as exists:
			exists.side_effect = lambda doctype, name: doctype == "Transport Zone" and name == "LZN-NRTS"
			result = normalize_container_location_pair("LZN-NRTS", "")
		self.assertEqual(result, ("Transport Zone", "LZN-NRTS"))

	def test_normalize_location_pair_clears_invalid_type(self):
		from logistics.logistics.doctype.container.container import normalize_container_location_pair

		with patch("logistics.logistics.doctype.container.container.frappe.db.exists", return_value=False):
			result = normalize_container_location_pair("LZN-NRTS", "UNKNOWN")
		self.assertEqual(result, ("", "UNKNOWN"))

	def test_resolve_display_name_for_unloco(self):
		from logistics.logistics.doctype.container.container import resolve_container_location_display_name

		with patch(
			"logistics.logistics.doctype.container.container.frappe.db.get_value",
			return_value="Manzanillo",
		):
			display = resolve_container_location_display_name("UNLOCO", "MQMPT")
		self.assertEqual(display, "Manzanillo")

	def test_resolve_display_name_for_transport_zone(self):
		from logistics.logistics.doctype.container.container import resolve_container_location_display_name

		with patch(
			"logistics.logistics.doctype.container.container.frappe.db.get_value",
			return_value="North RTS Zone",
		):
			display = resolve_container_location_display_name("Transport Zone", "LZN-NRTS")
		self.assertEqual(display, "North RTS Zone")

	def test_update_current_location_name_uses_display_helper(self):
		from logistics.logistics.doctype.container.container import Container

		container = Container({"doctype": "Container"})
		container.current_location_type = "UNLOCO"
		container.current_location = "MQMPT"
		with patch(
			"logistics.logistics.doctype.container.container.resolve_container_location_display_name",
			return_value="Manzanillo",
		):
			container.update_current_location_name()
		self.assertEqual(container.current_location_name, "Manzanillo")


class UnitTestContainerDepositRow(UnitTestCase):
	def test_sync_deposit_header_from_child_rows(self):
		from logistics.logistics.deposit_processing.container_deposit_gl import sync_deposit_header_from_child_rows

		class _Fake:
			doctype = "Container"
			name = "UNIT-TEST-CONTAINER"
			deposit_amount = 0
			deposit_currency = None
			deposit_paid_date = None
			container_charges_total = 0

			def get(self, k, d=None):
				return getattr(self, k, d)

		f = _Fake()

		def _fake_sync(doc):
			doc.container_charges_total = 0.0
			doc.deposit_amount = 100.0
			doc.deposit_currency = "USD"
			doc.deposit_paid_date = "2026-01-01"

		with patch(
			"logistics.logistics.deposit_processing.container_deposit_gl.sync_deposit_header_from_gl",
			side_effect=_fake_sync,
		):
			sync_deposit_header_from_child_rows(f)
		self.assertEqual(f.deposit_amount, 100)
		self.assertEqual(f.deposit_currency, "USD")
		if hasattr(f, "container_charges_total"):
			self.assertEqual(f.container_charges_total, 0)

	def test_sync_deposit_header_does_not_subtract_container_charges(self):
		from logistics.logistics.deposit_processing.container_deposit_gl import sync_deposit_header_from_child_rows

		class _Fake:
			doctype = "Container"
			name = "UNIT-TEST-CONTAINER-2"
			deposit_amount = 0
			deposit_currency = None
			deposit_paid_date = None
			container_charges_total = 0

			def get(self, k, d=None):
				return getattr(self, k, d)

		class FakeMeta:
			def has_field(self, fieldname):
				return fieldname == "container_charges_total"

		f = _Fake()
		f.meta = FakeMeta()

		def _fake_sync(doc):
			doc.container_charges_total = 35.0
			doc.deposit_amount = 100.0

		with patch(
			"logistics.logistics.deposit_processing.container_deposit_gl.sync_deposit_header_from_gl",
			side_effect=_fake_sync,
		):
			sync_deposit_header_from_child_rows(f)
		self.assertEqual(f.deposit_amount, 100)
		self.assertEqual(f.container_charges_total, 35)
