# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Scheduled Outlook task sync maintenance jobs."""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import add_to_date, now_datetime

from logistics.integrations.outlook.graph_client import is_outlook_sync_enabled
from logistics.integrations.outlook.task_sync import (
	SYNC_STATUS_FAILED,
	SYNC_STATUS_SUCCESS,
	get_sync_users,
	sync_task_for_all_users,
	sync_task_for_user,
)


def reconcile_failed_syncs() -> None:
	if not is_outlook_sync_enabled():
		return

	failed_maps = frappe.get_all(
		"Outlook Task Sync Map",
		filters={"sync_status": SYNC_STATUS_FAILED},
		fields=["task", "user"],
		limit=100,
	)
	for row in failed_maps:
		sync_task_for_user(row.task, row.user)


def sync_recent_task_changes() -> None:
	if not is_outlook_sync_enabled():
		return

	cutoff = add_to_date(now_datetime(), hours=-2)
	users = set(get_sync_users())
	if not users:
		return

	recent_tasks = frappe.get_all(
		"Task",
		filters={
			"modified": (">=", cutoff),
			"is_group": 0,
			"exp_start_date": ("is", "set"),
			"exp_end_date": ("is", "set"),
		},
		pluck="name",
	)

	for task_name in recent_tasks:
		mapped_users = frappe.get_all(
			"Outlook Task Sync Map",
			{"task": task_name, "sync_status": SYNC_STATUS_SUCCESS},
			pluck="user",
		)
		missing_users = users - set(mapped_users)
		if missing_users:
			sync_task_for_all_users(task_name)
		elif not mapped_users:
			sync_task_for_all_users(task_name)
