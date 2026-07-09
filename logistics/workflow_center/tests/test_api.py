from frappe.tests import IntegrationTestCase


class TestLogisticsWorkflowCenterAPI(IntegrationTestCase):
	def test_dashboard_api_callable(self):
		from logistics.workflow_center.api import get_workflow_center_dashboard

		result = get_workflow_center_dashboard()
		self.assertIn("summary", result)
		self.assertIn("items", result)
		self.assertIn("open_actions", result["summary"]["counts"])

	def test_filter_options_returns_roles(self):
		from logistics.workflow_center.api import get_workflow_center_filter_options

		result = get_workflow_center_filter_options()
		self.assertIn("roles", result)
		self.assertGreater(result.get("role_count", 0), 0)
