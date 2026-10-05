# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe

from logistics.order_management.sync import pull_channel_orders, push_channel_stock, sync_channel_items


def _channel(name):
	if not name:
		frappe.throw("Sales Channel is required")
	doc = frappe.get_doc("Sales Channel", name)
	doc.check_permission("write")
	return doc


@frappe.whitelist()
def sync_orders(channel):
	_channel(channel)
	counts = pull_channel_orders(channel)
	return _message("Orders", counts)


@frappe.whitelist()
def sync_items(channel):
	_channel(channel)
	counts = sync_channel_items(channel)
	return _message("Items", counts)


@frappe.whitelist()
def push_stock(channel):
	_channel(channel)
	counts = push_channel_stock(channel)
	return _message("Stock", counts)


def _message(label, counts):
	if counts.get("skipped") is True:
		return f"{label} sync is turned off for this channel"
	return (
		f"{label} sync finished. "
		f"Created {counts.get('created', 0)}, updated {counts.get('updated', 0)}, "
		f"skipped {counts.get('skipped', 0)}, failed {counts.get('failed', 0)}."
	)
