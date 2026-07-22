# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace

from logistics.job_management.logistics_job_status import sync_declaration_job_status


def _declaration(**kwargs):
	defaults = {
		"docstatus": 0,
		"status": "Draft",
		"job_status": "",
		"flags": SimpleNamespace(skip_job_status_sync=False),
	}
	defaults.update(kwargs)
	return SimpleNamespace(**defaults)


class TestSyncDeclarationJobStatus(unittest.TestCase):
	def test_draft_doc_sets_job_status_draft(self):
		doc = _declaration(docstatus=0, status="Draft", job_status="")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "Draft")

	def test_submit_path_with_customs_status_still_draft(self):
		"""validate runs before before_submit flips status Draft→Submitted."""
		doc = _declaration(docstatus=1, status="Draft", job_status="Draft")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "Submitted")

	def test_customs_submitted_sets_job_status_submitted(self):
		doc = _declaration(docstatus=1, status="Submitted", job_status="Draft")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "Submitted")

	def test_under_review_sets_in_progress(self):
		doc = _declaration(docstatus=1, status="Under Review", job_status="Submitted")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "In Progress")

	def test_cleared_sets_completed(self):
		doc = _declaration(docstatus=1, status="Cleared", job_status="In Progress")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "Completed")

	def test_released_sets_completed(self):
		doc = _declaration(docstatus=1, status="Released", job_status="In Progress")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "Completed")

	def test_preserves_reopened(self):
		doc = _declaration(docstatus=1, status="Cleared", job_status="Reopened")
		sync_declaration_job_status(doc)
		self.assertEqual(doc.job_status, "Reopened")
