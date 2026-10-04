# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""The declared document-event map is the list Frappe runs, in that order."""

from __future__ import annotations

import unittest
from pathlib import Path

from logistics.doc_event_hooks import DOC_EVENTS


HOOKS = Path(__file__).resolve().parents[1] / "hooks.py"

ENSURE_TEMPLATE = "logistics.document_management.api.ensure_documents_and_milestones_from_template"
ENFORCE_DOCS = "logistics.document_management.api.enforce_required_job_documents_before_submit"
PERMIT_ALERT = "logistics.customs.permit_matching.enforce_permit_alerts_before_submit"
WAREHOUSE_BEFORE_SUBMIT = "logistics.warehousing.api.warehouse_job_before_submit"
CREDIT_VALIDATE = "logistics.utils.credit_management.on_credit_validate"
CREDIT_SUBMIT = "logistics.utils.credit_management.on_credit_before_submit"
MAIN_SERVICE = "logistics.utils.charge_service_type.on_validate_main_service_internal_job"
ESTIMATES = "logistics.job_management.doc_events.on_job_validate_estimates"
CHARGE_LOCK = "logistics.job_management.charge_reopen.validate_submitted_charges_not_locked"
CHANGE_LOCK = "logistics.job_management.job_change_lock.validate_job_locked_against_user_edits"
READINESS = "logistics.job_management.job_readiness.validate_job_readiness_on_status_change"
AUTO_RECOGNIZE = "logistics.job_management.auto_recognition.enqueue_auto_recognize"
FREIGHT_SUBMIT = "logistics.special_projects.special_project_packages.on_freight_shipment_submit"
TRANSPORT_SUBMIT = "logistics.special_projects.special_project_packages.on_transport_job_submit"


def _handlers(value):
	if isinstance(value, str):
		return 1
	return sum(_handlers(item) for item in value)


class TestDocEventHooks(unittest.TestCase):
	def test_map_size_is_unchanged(self):
		self.assertEqual(len(DOC_EVENTS), 52)
		self.assertEqual(sum(_handlers(events) for events in DOC_EVENTS.values()), 221)

	def test_air_shipment_handler_order(self):
		air = DOC_EVENTS["Air Shipment"]
		self.assertEqual(air["before_save"][0], ENSURE_TEMPLATE)
		self.assertEqual(
			air["validate"],
			[
				MAIN_SERVICE,
				ESTIMATES,
				CHARGE_LOCK,
				CHANGE_LOCK,
				READINESS,
				CREDIT_VALIDATE,
			],
		)
		self.assertEqual(
			air["before_submit"],
			[ENFORCE_DOCS, PERMIT_ALERT, CREDIT_SUBMIT],
		)
		self.assertEqual(air["on_submit"][0], AUTO_RECOGNIZE)
		self.assertEqual(air["on_submit"][-1], FREIGHT_SUBMIT)

	def test_declaration_order_skips_template_populate(self):
		before_save = DOC_EVENTS["Declaration Order"]["before_save"]
		self.assertNotIn(ENSURE_TEMPLATE, before_save)
		self.assertEqual(
			before_save[0],
			"logistics.document_management.api.update_milestone_status_on_parent_before_save",
		)

	def test_warehouse_job_before_submit_order(self):
		self.assertEqual(
			DOC_EVENTS["Warehouse Job"]["before_submit"],
			[ENFORCE_DOCS, WAREHOUSE_BEFORE_SUBMIT, PERMIT_ALERT, CREDIT_SUBMIT],
		)

	def test_transport_job_posts_special_project_deliveries_last(self):
		self.assertEqual(DOC_EVENTS["Transport Job"]["on_submit"][-1], TRANSPORT_SUBMIT)

	def test_wildcard_and_credit_only_doctypes(self):
		self.assertEqual(
			DOC_EVENTS["*"]["validate"],
			[
				"logistics.utils.load_type_active.validate_load_type_links_on_doc",
				"logistics.utils.freight_agent_service.validate_freight_agent_links_on_doc",
			],
		)
		self.assertEqual(
			DOC_EVENTS["Gate Pass"]["validate"],
			CREDIT_VALIDATE,
		)
		self.assertEqual(
			DOC_EVENTS["Run Sheet"]["validate"],
			CHANGE_LOCK,
		)

	def test_hooks_use_the_declared_map(self):
		hooks = HOOKS.read_text()
		self.assertIn("doc_events = DOC_EVENTS", hooks)
		self.assertIn("_ensure_print_validation_patch()", hooks)
		self.assertNotIn("merge_credit_hooks(doc_events)", hooks)
		self.assertNotIn("_doc_milestone_doctypes", hooks)


if __name__ == "__main__":
	unittest.main()
