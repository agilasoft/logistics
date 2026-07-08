# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""ERPNext Task to Microsoft Outlook calendar event sync."""

from __future__ import annotations

import frappe
from frappe.utils import get_datetime, get_link_to_form, get_url_to_form, now_datetime

from logistics.integrations.outlook.graph_client import (
	ERPNext_TASK_PROPERTY_ID,
	OutlookGraphClient,
	OutlookGraphError,
	get_outlook_calendar_settings,
	is_outlook_sync_enabled,
)

SYNC_STATUS_SUCCESS = "Success"
SYNC_STATUS_FAILED = "Failed"
SYNC_STATUS_DELETED = "Deleted"


def should_sync(task) -> bool:
	if not is_outlook_sync_enabled():
		return False

	if task.is_group:
		return False

	if not task.exp_start_date or not task.exp_end_date:
		return False

	return True


def get_sync_users() -> list[str]:
	return frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"sync_erpnext_tasks_to_outlook": 1,
			"user_type": "System User",
		},
		pluck="name",
	)


def get_user_timezone(user: str) -> str:
	settings = get_outlook_calendar_settings()
	timezone = frappe.db.get_value("User", user, "time_zone")
	return timezone or settings.default_timezone or frappe.utils.get_system_timezone()


def build_event_payload(task, user: str) -> dict:
	settings = get_outlook_calendar_settings()
	timezone = get_user_timezone(user)

	subject = task.subject or task.name
	if task.status == "Completed":
		subject = f"[Completed] {subject}"
	elif task.status == "Cancelled":
		subject = f"[Cancelled] {subject}"

	start_dt = get_datetime(task.exp_start_date)
	end_dt = get_datetime(task.exp_end_date)
	show_as = "free" if (
		settings.mark_completed_tasks_as_free and task.status in ("Completed", "Cancelled")
	) else "busy"

	body_parts = []
	if task.description:
		body_parts.append(task.description)
	if task.project:
		body_parts.append(f"<p><strong>Project:</strong> {frappe.utils.escape_html(task.project)}</p>")
	body_parts.append(f"<p>{get_link_to_form('Task', task.name)}</p>")
	body_parts.append(f"<p>{get_url_to_form('Task', task.name)}</p>")

	datetime_format = "%Y-%m-%d %H:%M:%S"
	return {
		"subject": subject,
		"body": {
			"contentType": "HTML",
			"content": "".join(body_parts),
		},
		"start": {
			"dateTime": start_dt.strftime(datetime_format),
			"timeZone": timezone,
		},
		"end": {
			"dateTime": end_dt.strftime(datetime_format),
			"timeZone": timezone,
		},
		"showAs": show_as,
		"categories": ["ERPNext"],
		"singleValueExtendedProperties": [
			{
				"id": ERPNext_TASK_PROPERTY_ID,
				"value": task.name,
			}
		],
	}


def get_sync_map(task_name: str, user: str):
	name = frappe.db.get_value(
		"Outlook Task Sync Map",
		{"task": task_name, "user": user, "sync_status": ("!=", SYNC_STATUS_DELETED)},
		"name",
	)
	return frappe.get_doc("Outlook Task Sync Map", name) if name else None


def upsert_sync_map(task_name: str, user: str, outlook_event_id: str, sync_status: str, error_message: str | None = None):
	if not outlook_event_id and sync_status != SYNC_STATUS_DELETED:
		existing_name = frappe.db.get_value(
			"Outlook Task Sync Map",
			{"task": task_name, "user": user},
			"name",
		)
		if not existing_name:
			return

	existing_name = frappe.db.get_value(
		"Outlook Task Sync Map",
		{"task": task_name, "user": user},
		"name",
	)
	if existing_name:
		doc = frappe.get_doc("Outlook Task Sync Map", existing_name)
	else:
		doc = frappe.new_doc("Outlook Task Sync Map")
		doc.task = task_name
		doc.user = user

	doc.outlook_event_id = outlook_event_id
	doc.last_synced_on = now_datetime()
	doc.sync_status = sync_status
	doc.error_message = error_message
	doc.save(ignore_permissions=True)


def sync_task_for_user(task_name: str, user: str) -> None:
	if not frappe.db.exists("Task", task_name):
		return

	task = frappe.get_doc("Task", task_name)
	if not should_sync(task):
		return

	if not OutlookGraphClient(user).has_token():
		return

	client = OutlookGraphClient(user)
	payload = build_event_payload(task, user)
	sync_map = get_sync_map(task_name, user)

	try:
		if sync_map and sync_map.outlook_event_id:
			try:
				response = client.update_event(sync_map.outlook_event_id, payload)
				event_id = sync_map.outlook_event_id
			except OutlookGraphError as exc:
				if exc.status_code == 404:
					response = client.create_event(payload)
					event_id = response.get("id")
				else:
					raise
		else:
			response = client.create_event(payload)
			event_id = response.get("id")

		if not event_id:
			raise OutlookGraphError("Microsoft Graph did not return an event ID.")

		upsert_sync_map(task_name, user, event_id, SYNC_STATUS_SUCCESS)
	except OutlookGraphError as exc:
		upsert_sync_map(
			task_name,
			user,
			sync_map.outlook_event_id if sync_map else "",
			SYNC_STATUS_FAILED,
			str(exc),
		)
		frappe.log_error(
			title=f"Outlook task sync failed ({task_name}, {user})",
			message=frappe.get_traceback(),
		)


def delete_task_for_user(task_name: str, user: str) -> None:
	settings = get_outlook_calendar_settings()
	if not settings.delete_outlook_event_on_task_delete:
		return

	sync_map = get_sync_map(task_name, user)
	if not sync_map or not sync_map.outlook_event_id:
		return

	if not OutlookGraphClient(user).has_token():
		return

	client = OutlookGraphClient(user)
	try:
		client.delete_event(sync_map.outlook_event_id)
		upsert_sync_map(task_name, user, sync_map.outlook_event_id, SYNC_STATUS_DELETED)
	except OutlookGraphError as exc:
		if exc.status_code != 404:
			upsert_sync_map(task_name, user, sync_map.outlook_event_id, SYNC_STATUS_FAILED, str(exc))
			frappe.log_error(
				title=f"Outlook task delete failed ({task_name}, {user})",
				message=frappe.get_traceback(),
			)
		else:
			upsert_sync_map(task_name, user, sync_map.outlook_event_id, SYNC_STATUS_DELETED)


def sync_task_for_all_users(task_name: str) -> None:
	if not is_outlook_sync_enabled():
		return

	for user in get_sync_users():
		sync_task_for_user(task_name, user)


def delete_task_for_all_users(task_name: str) -> None:
	if not is_outlook_sync_enabled():
		return

	for user in get_sync_users():
		delete_task_for_user(task_name, user)


def on_task_change(doc, method=None):
	if not is_outlook_sync_enabled():
		return

	settings = get_outlook_calendar_settings()
	if not settings.sync_on_save:
		return

	if not should_sync(doc):
		return

	frappe.enqueue(
		"logistics.integrations.outlook.task_sync.sync_task_for_all_users",
		task_name=doc.name,
		queue="short",
		enqueue_after_commit=True,
	)


def on_task_delete(doc, method=None):
	if not is_outlook_sync_enabled():
		return

	frappe.enqueue(
		"logistics.integrations.outlook.task_sync.delete_task_for_all_users",
		task_name=doc.name,
		queue="short",
		enqueue_after_commit=True,
	)


def sync_all_tasks_for_user(user: str, offset: int = 0, limit: int = 20) -> None:
	tasks = frappe.get_all(
		"Task",
		filters={
			"is_group": 0,
			"exp_start_date": ("is", "set"),
			"exp_end_date": ("is", "set"),
		},
		pluck="name",
		order_by="modified desc",
		limit_start=offset,
		limit_page_length=limit,
	)

	for task_name in tasks:
		sync_task_for_user(task_name, user)

	if len(tasks) == limit:
		frappe.enqueue(
			"logistics.integrations.outlook.task_sync.sync_all_tasks_for_user",
			user=user,
			offset=offset + limit,
			limit=limit,
			queue="long",
		)
