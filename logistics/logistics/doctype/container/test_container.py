# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

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

		class Row:
			event_type = "Pay Carrier"
			deposit_amount = 100
			refund_amount = 0
			deposit_currency = "USD"
			deposit_date = "2026-01-01"

			def get(self, k, d=None):
				return getattr(self, k, d)

		class _Fake:
			deposit_amount = 0
			deposit_currency = None
			deposit_paid_date = None

			def get(self, k, d=None):
				if k == "deposits":
					return [Row()]
				return getattr(self, k, d)

		f = _Fake()
		sync_deposit_header_from_child_rows(f)
		self.assertEqual(f.deposit_amount, 100)
		self.assertEqual(f.deposit_currency, "USD")
