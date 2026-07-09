from frappe.tests import IntegrationTestCase
import frappe


class TestWorkflowCenterQueries(IntegrationTestCase):
	def test_active_workflow_doctypes_not_hardcoded(self):
		from workflow_center.workflow_center.queries import get_active_workflow_doctypes

		doctypes = get_active_workflow_doctypes()
		self.assertIsInstance(doctypes, list)

	def test_open_actions_query_returns_list(self):
		from workflow_center.workflow_center.queries import get_open_workflow_actions

		actions = get_open_workflow_actions(user="Administrator")
		self.assertIsInstance(actions, list)

	def test_dashboard_summary_structure(self):
		from workflow_center.workflow_center.queries import get_dashboard_summary

		summary = get_dashboard_summary(user="Administrator")
		self.assertIn("counts", summary)
		self.assertIn("open_actions", summary["counts"])
		self.assertIn("workflow_doctypes", summary)

	def test_purchase_invoice_in_workflow_doctypes_when_active(self):
		from workflow_center.workflow_center.queries import get_active_workflow_doctypes

		if frappe.db.exists("Workflow", {"document_type": "Purchase Invoice", "is_active": 1}):
			self.assertIn("Purchase Invoice", get_active_workflow_doctypes())
