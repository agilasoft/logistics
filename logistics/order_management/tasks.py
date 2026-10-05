# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Scheduled pull, stock push, and warehouse-job fulfillment."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime

from logistics.order_management.sync import pull_channel_orders, push_channel_stock, push_fulfillment_for_release


def pull_orders():
	for name in _enabled_channels("sync_orders"):
		try:
			pull_channel_orders(name)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Order Management order pull")


def push_stock():
	for name in _enabled_channels("sync_stock"):
		try:
			push_channel_stock(name)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Order Management stock push")


def cleanup_sync_logs():
	cutoff = add_days(now_datetime(), -30)
	names = frappe.get_all("Order Sync Log", filters={"finished": ["<", cutoff]}, pluck="name")
	for name in names:
		frappe.delete_doc("Order Sync Log", name, ignore_permissions=True)


def on_warehouse_job_submit(doc, method=None):
	if getattr(doc, "type", None) != "Pick" or doc.docstatus != 1:
		return
	if doc.reference_order_type != "Release Order" or not doc.reference_order:
		return
	release_order = doc.reference_order
	channels = frappe.get_all(
		"Platform Order",
		filters={"release_order": release_order},
		pluck="sales_channel",
	)
	if not channels:
		return

	def _run():
		push_fulfillment_for_release(release_order)
		for channel in set(channels):
			try:
				push_channel_stock(channel)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Order Management stock push")

	if frappe.flags.in_test:
		_run()
		return
	frappe.enqueue(
		"logistics.order_management.tasks._run_after_pick",
		queue="short",
		release_order=release_order,
		enqueue_after_commit=True,
		job_id=f"order-management-pick|{release_order}",
		deduplicate=True,
	)


def _run_after_pick(release_order):
	push_fulfillment_for_release(release_order)
	channels = frappe.get_all(
		"Platform Order",
		filters={"release_order": release_order},
		pluck="sales_channel",
	)
	for channel in set(channels):
		try:
			push_channel_stock(channel)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Order Management stock push")


def _enabled_channels(flag):
	return frappe.get_all(
		"Sales Channel",
		filters={"enabled": 1, flag: 1},
		pluck="name",
	)
