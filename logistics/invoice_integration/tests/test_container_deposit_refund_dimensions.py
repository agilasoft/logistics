# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from unittest.mock import MagicMock, patch

from frappe.tests import UnitTestCase

from logistics.logistics.deposit_processing.container_deposit_gl import _refund_je_dimension_extras


class TestContainerDepositRefundDimensions(UnitTestCase):
	def test_refund_je_dimension_extras_uses_row_item_code(self):
		row = MagicMock()

		def _get(k, d=None):
			return {"item_code": "CD-ITEM-1", "container": "CONT-A", "purchase_invoice": None}.get(k, d)

		row.get = _get
		row.item_code = "CD-ITEM-1"
		with patch(
			"logistics.logistics.deposit_processing.container_deposit_gl.item_row_dict",
			return_value={"dim_item": "CD-ITEM-1"},
		) as mock_item:
			with patch(
				"logistics.logistics.deposit_processing.container_deposit_gl.reference_dimension_row_dict",
				return_value={"dim_container": "CONT-A"},
			) as mock_ref:
				out = _refund_je_dimension_extras(row)
		self.assertEqual(out, {"dim_item": "CD-ITEM-1", "dim_container": "CONT-A"})
		mock_item.assert_called_once_with("Journal Entry Account", "CD-ITEM-1")
		mock_ref.assert_called_once_with(
			"Journal Entry Account",
			"Container",
			"CONT-A",
		)
