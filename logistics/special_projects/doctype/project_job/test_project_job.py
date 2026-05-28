# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.special_projects.doctype.project_order.project_order import (
	_apply_org_defaults_to_job,
	_build_project_job_from_order,
)


EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def _org_for_company(company: str) -> dict:
	"""Minimal company / branch / cost_center / profit_center for test inserts."""
	out = {"company": company}
	cc = frappe.db.get_value(
		"Cost Center",
		{"is_group": 0, "disabled": 0, "company": company},
		"name",
		order_by="creation asc",
	)
	if cc:
		out["cost_center"] = cc
	branch = frappe.db.get_value("Branch", {}, "name", order_by="modified desc")
	if branch:
		out["branch"] = branch
	pc = frappe.db.get_value("Profit Center", {}, "name", order_by="creation asc")
	if pc:
		out["profit_center"] = pc
	return out


class IntegrationTestProjectJob(IntegrationTestCase):
	def test_job_number_created_and_synced_to_project_order(self):
		sp_name = frappe.db.get_value("Special Project", {}, "name")
		if not sp_name:
			self.skipTest("No Special Project on site")

		sp = frappe.get_doc("Special Project", sp_name)
		company = sp.company
		if not company:
			self.skipTest("Special Project has no company")

		order = frappe.new_doc("Project Order")
		order.naming_series = "SPOR-.#####"
		order.special_project = sp.name
		order.order_title = "Order for JCN test"
		for k, v in _org_for_company(company).items():
			setattr(order, k, v)
		order.insert(ignore_permissions=True)
		self.assertFalse(order.job_number)

		job = _build_project_job_from_order(order, title="JCN Test Job")
		job.naming_series = "SPJ-.#####"
		_apply_org_defaults_to_job(job, order)
		job.insert(ignore_permissions=True)

		job.reload()
		self.assertTrue(job.job_number)
		self.assertTrue(
			frappe.db.exists(
				"Job Number",
				{"job_type": "Project Job", "job_no": job.name, "name": job.job_number},
			)
		)

		order.reload()
		self.assertEqual(order.job_number, job.job_number)
