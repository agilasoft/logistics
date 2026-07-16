# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from frappe.tests import IntegrationTestCase

from logistics.warehousing.doctype.warehouse_contract.warehouse_contract import (
	_map_sales_quote_unit_type_to_warehouse_contract,
)


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestWarehouseContract(IntegrationTestCase):
	"""
	Integration tests for WarehouseContract.
	Use this class for testing interactions between multiple components.
	"""

	def test_map_sales_quote_unit_type_to_warehouse_contract(self):
		self.assertEqual(_map_sales_quote_unit_type_to_warehouse_contract("Container"), "TEU")
		self.assertEqual(_map_sales_quote_unit_type_to_warehouse_contract("Item Count"), "Piece")
		self.assertEqual(_map_sales_quote_unit_type_to_warehouse_contract("TEU"), "TEU")
		self.assertEqual(_map_sales_quote_unit_type_to_warehouse_contract("Weight"), "Weight")
