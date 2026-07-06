# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from logistics.integrations.outlook.graph_client import OutlookGraphError
from logistics.integrations.outlook.task_sync import (
	SYNC_STATUS_DELETED,
	SYNC_STATUS_FAILED,
	SYNC_STATUS_SUCCESS,
	build_event_payload,
	should_sync,
	sync_task_for_user,
	delete_task_for_user,
)
from logistics.integrations.outlook.install import create_connected_app


class TestOutlookTaskSync(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self._ensure_outlook_settings(enabled=True)
		self.user = frappe.session.user

	def _ensure_outlook_settings(self, enabled=True):
		create_connected_app()
		settings = frappe.get_single("Outlook Calendar Settings")
		settings.enable_sync = 1 if enabled else 0
		settings.connected_app = create_connected_app()
		settings.azure_tenant_id = settings.azure_tenant_id or "common"
		settings.mark_completed_tasks_as_free = 1
		settings.delete_outlook_event_on_task_delete = 1
		settings.save(ignore_permissions=True)

	def _make_task(self, **kwargs):
		task = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": kwargs.get("subject", "Outlook Sync Test Task"),
				"status": kwargs.get("status", "Open"),
				"exp_start_date": kwargs.get("exp_start_date", now_datetime()),
				"exp_end_date": kwargs.get(
					"exp_end_date", add_days(now_datetime(), 1)
				),
				"is_group": kwargs.get("is_group", 0),
				"project": kwargs.get("project"),
				"description": kwargs.get("description", "Test description"),
			}
		)
		task.insert(ignore_permissions=True)
		self.addCleanup(lambda: self._delete_task(task.name))
		return task

	def _delete_task(self, name):
		if frappe.db.exists("Task", name):
			frappe.delete_doc("Task", name, force=1, ignore_permissions=True)

	def _delete_sync_maps(self, task_name):
		for row in frappe.get_all("Outlook Task Sync Map", filters={"task": task_name}, pluck="name"):
			frappe.delete_doc("Outlook Task Sync Map", row, force=1, ignore_permissions=True)

	def test_should_sync_requires_dates_and_enabled_settings(self):
		task = self._make_task()
		self.assertTrue(should_sync(task))

		task.exp_end_date = None
		self.assertFalse(should_sync(task))

		task.exp_end_date = add_days(now_datetime(), 1)
		task.is_group = 1
		self.assertFalse(should_sync(task))

		self._ensure_outlook_settings(enabled=False)
		task.is_group = 0
		self.assertFalse(should_sync(task))

	def test_build_event_payload_maps_fields(self):
		task = self._make_task(
			subject="Payload Task",
			status="Completed",
			description="<p>Body</p>",
		)
		payload = build_event_payload(task, self.user)

		self.assertIn("[Completed] Payload Task", payload["subject"])
		self.assertEqual(payload["showAs"], "free")
		self.assertEqual(payload["categories"], ["ERPNext"])
		self.assertIn("timeZone", payload["start"])
		self.assertIn("dateTime", payload["start"])
		self.assertIn("Body</p>", payload["body"]["content"])
		self.assertEqual(
			payload["singleValueExtendedProperties"][0]["value"],
			task.name,
		)

	@patch("logistics.integrations.outlook.task_sync.OutlookGraphClient")
	def test_sync_task_for_user_creates_event(self, mock_client_cls):
		task = self._make_task(subject="Create Event Task")
		mock_client = MagicMock()
		mock_client.has_token.return_value = True
		mock_client.create_event.return_value = {"id": "evt-create-1"}
		mock_client_cls.return_value = mock_client

		frappe.db.set_value("User", self.user, "sync_erpnext_tasks_to_outlook", 1)
		sync_task_for_user(task.name, self.user)

		mock_client.create_event.assert_called_once()
		map_name = frappe.db.get_value(
			"Outlook Task Sync Map",
			{"task": task.name, "user": self.user},
			["outlook_event_id", "sync_status"],
			as_dict=True,
		)
		self.assertEqual(map_name.outlook_event_id, "evt-create-1")
		self.assertEqual(map_name.sync_status, SYNC_STATUS_SUCCESS)
		self._delete_sync_maps(task.name)

	@patch("logistics.integrations.outlook.task_sync.OutlookGraphClient")
	def test_sync_task_for_user_updates_existing_event(self, mock_client_cls):
		task = self._make_task(subject="Update Event Task")
		map_doc = frappe.get_doc(
			{
				"doctype": "Outlook Task Sync Map",
				"task": task.name,
				"user": self.user,
				"outlook_event_id": "evt-existing-1",
				"sync_status": SYNC_STATUS_SUCCESS,
			}
		)
		map_doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: self._delete_sync_maps(task.name))

		mock_client = MagicMock()
		mock_client.has_token.return_value = True
		mock_client.update_event.return_value = {"id": "evt-existing-1"}
		mock_client_cls.return_value = mock_client

		sync_task_for_user(task.name, self.user)
		mock_client.update_event.assert_called_once()
		mock_client.create_event.assert_not_called()

	@patch("logistics.integrations.outlook.task_sync.OutlookGraphClient")
	def test_sync_task_for_user_recreate_on_404(self, mock_client_cls):
		task = self._make_task(subject="Recreate Event Task")
		map_doc = frappe.get_doc(
			{
				"doctype": "Outlook Task Sync Map",
				"task": task.name,
				"user": self.user,
				"outlook_event_id": "evt-missing-1",
				"sync_status": SYNC_STATUS_SUCCESS,
			}
		)
		map_doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: self._delete_sync_maps(task.name))

		mock_client = MagicMock()
		mock_client.has_token.return_value = True
		mock_client.update_event.side_effect = OutlookGraphError("missing", status_code=404)
		mock_client.create_event.return_value = {"id": "evt-new-1"}
		mock_client_cls.return_value = mock_client

		sync_task_for_user(task.name, self.user)
		mock_client.create_event.assert_called_once()
		self.assertEqual(
			frappe.db.get_value(
				"Outlook Task Sync Map",
				{"task": task.name, "user": self.user},
				"outlook_event_id",
			),
			"evt-new-1",
		)

	@patch("logistics.integrations.outlook.task_sync.OutlookGraphClient")
	def test_delete_task_for_user_marks_deleted(self, mock_client_cls):
		task = self._make_task(subject="Delete Event Task")
		map_doc = frappe.get_doc(
			{
				"doctype": "Outlook Task Sync Map",
				"task": task.name,
				"user": self.user,
				"outlook_event_id": "evt-delete-1",
				"sync_status": SYNC_STATUS_SUCCESS,
			}
		)
		map_doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: self._delete_sync_maps(task.name))

		mock_client = MagicMock()
		mock_client.has_token.return_value = True
		mock_client_cls.return_value = mock_client

		delete_task_for_user(task.name, self.user)
		mock_client.delete_event.assert_called_once_with("evt-delete-1")
		self.assertEqual(
			frappe.db.get_value(
				"Outlook Task Sync Map",
				{"task": task.name, "user": self.user},
				"sync_status",
			),
			SYNC_STATUS_DELETED,
		)

	@patch("logistics.integrations.outlook.task_sync.OutlookGraphClient")
	def test_sync_failure_records_failed_status(self, mock_client_cls):
		task = self._make_task(subject="Failed Event Task")
		map_doc = frappe.get_doc(
			{
				"doctype": "Outlook Task Sync Map",
				"task": task.name,
				"user": self.user,
				"outlook_event_id": "evt-fail-1",
				"sync_status": SYNC_STATUS_SUCCESS,
			}
		)
		map_doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: self._delete_sync_maps(task.name))

		mock_client = MagicMock()
		mock_client.has_token.return_value = True
		mock_client.update_event.side_effect = OutlookGraphError("boom", status_code=500)
		mock_client_cls.return_value = mock_client

		sync_task_for_user(task.name, self.user)
		self.assertEqual(
			frappe.db.get_value(
				"Outlook Task Sync Map",
				{"task": task.name, "user": self.user},
				"sync_status",
			),
			SYNC_STATUS_FAILED,
		)
