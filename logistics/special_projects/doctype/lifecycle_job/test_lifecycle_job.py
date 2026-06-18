# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests import UnitTestCase

from logistics.special_projects.doctype.lifecycle_job.lifecycle_job import LifecycleJob


class TestLifecycleJobInvalidLinks(UnitTestCase):
	def test_cancelled_order_no_not_reported_as_invalid_link(self):
		row = LifecycleJob(
			{
				"doctype": "Lifecycle Job",
				"job_type": "Transport Order",
				"order_no": "TRO-CANCELLED",
			}
		)
		with patch.object(
			LifecycleJob.__bases__[0],
			"get_invalid_links",
			return_value=([], [("order_no", "Transport Order", "TRO-CANCELLED")]),
		):
			invalid, cancelled = row.get_invalid_links()
		self.assertEqual(invalid, [])
		self.assertEqual(cancelled, [])

	def test_cancelled_job_no_not_reported_as_invalid_link(self):
		row = LifecycleJob(
			{
				"doctype": "Lifecycle Job",
				"job_type": "Transport Order",
				"job_no": "TRJ-CANCELLED",
			}
		)
		with patch.object(
			LifecycleJob.__bases__[0],
			"get_invalid_links",
			return_value=([], [("job_no", "Transport Job", "TRJ-CANCELLED")]),
		):
			invalid, cancelled = row.get_invalid_links()
		self.assertEqual(invalid, [])
		self.assertEqual(cancelled, [])

	def test_other_cancelled_links_still_reported(self):
		row = LifecycleJob(
			{
				"doctype": "Lifecycle Job",
				"lifecycle_stage": "STG-CANCELLED",
			}
		)
		with patch.object(
			LifecycleJob.__bases__[0],
			"get_invalid_links",
			return_value=([], [("lifecycle_stage", "Lifecycle Stage", "STG-CANCELLED")]),
		):
			invalid, cancelled = row.get_invalid_links()
		self.assertEqual(invalid, [])
		self.assertEqual(cancelled, [("lifecycle_stage", "Lifecycle Stage", "STG-CANCELLED")])
