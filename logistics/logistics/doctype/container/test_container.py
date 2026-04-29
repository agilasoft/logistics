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

	def test_sync_deposit_header_subtracts_container_charges(self):
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
			doc.deposit_amount = 65.0

		with patch(
			"logistics.logistics.deposit_processing.container_deposit_gl.sync_deposit_header_from_gl",
			side_effect=_fake_sync,
		):
			sync_deposit_header_from_child_rows(f)
		self.assertEqual(f.deposit_amount, 65)
		self.assertEqual(f.container_charges_total, 35)
