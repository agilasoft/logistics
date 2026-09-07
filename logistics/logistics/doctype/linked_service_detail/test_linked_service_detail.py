# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Linked Service Detail grid columns (operational / CR / TSC).

Sales Quote hides Order No / Job No / Job Description in client JS.
"""

from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase

_GRID_COLUMNS = (
	"linked_service",
	"service_type",
	"order_no",
	"job_no",
	"job_description",
)


class TestLinkedServiceDetailGrid(FrappeTestCase):
	def test_operational_grid_matches_canvas_columns(self):
		meta = frappe.get_meta("Linked Service Detail")
		shown = tuple(f.fieldname for f in meta.fields if f.in_list_view)
		self.assertEqual(shown, _GRID_COLUMNS)
		df = meta.get_field("job_type")
		self.assertIsNotNone(df)
		self.assertFalse(df.in_list_view)
