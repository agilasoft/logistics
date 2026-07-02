# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.special_projects.lifecycle_job_display import (
	lifecycle_job_line_display_label,
	sync_lifecycle_row_labels,
)


class TestLifecycleJobDisplay(UnitTestCase):
	def test_lifecycle_job_line_display_label_reads_dict_rows(self):
		row = {
			"lifecycle_stage": "Port operation",
			"activity_name": "Sea import",
		}
		self.assertEqual(
			lifecycle_job_line_display_label(row),
			"Port operation — Sea import",
		)

	def test_sync_lifecycle_row_labels_handles_dict_service_rows(self):
		doc = frappe._dict(doctype="Special Project", name="SP-TEST-LABELS")
		rows = [
			{
				"name": "SPS-TEST-1",
				"special_project_service": "SPS-TEST-1",
				"lifecycle_stage": "Logistics",
				"activity_name": "Air leg",
			}
		]
		with patch(
			"logistics.special_projects.lifecycle_job_display.service_rows",
			return_value=rows,
		):
			with patch("frappe.db.exists", return_value=False):
				sync_lifecycle_row_labels(doc)
		self.assertEqual(rows[0]["lifecycle_row_label"], "Logistics — Air leg")
