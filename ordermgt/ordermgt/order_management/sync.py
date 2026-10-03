# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Import marketplace orders and push listings, stock, and fulfillment."""

from __future__ import annotations

import frappe
from frappe.utils import getdate, now_datetime

from ordermgt.order_management.decisions import (
	cust_reference,
	line_mappings,
	pancake_should_skip,
	plan_import,
	ship_to_summary,
	stock_should_push,
)
from ordermgt.order_management.integrations.registry import get_adapter
from ordermgt.order_management.integrations.sanitize import sanitize
from ordermgt.order_management.stock import available_map, available_to_sell, pick_is_posted

SECRET_FIELDS = (
	"app_secret",
	"api_key",
	"access_token",
	"refresh_token",
	"webhook_secret",
)

PLAIN_FIELDS = (
	"platform",
	"region",
	"shop_id",
	"catalog_id",
	"location_id",
	"api_url",
	"partner_id",
	"app_key",
	"commerce_orders_enabled",
)


def credentials_from_channel(channel) -> dict:
	data = {}
	for field in PLAIN_FIELDS:
		data[field] = channel.get(field) if isinstance(channel, dict) else getattr(channel, field, None)
	for field in SECRET_FIELDS:
		data[field] = _secret(channel, field)
	return data


def _secret(channel, field):
	if isinstance(channel, dict):
		return channel.get(field)
	if hasattr(channel, "get_password"):
		try:
			value = channel.get_password(field, raise_exception=False)
		except Exception:
			value = None
		if value:
			return value
	return getattr(channel, field, None)


def pull_channel_orders(channel_name: str) -> dict:
	channel = frappe.get_doc("Sales Channel", channel_name)
	if not channel.enabled or not channel.sync_orders:
		return {"skipped": True}
	log = _start_log(channel.name, "Pull Orders", "In")
	counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
	try:
		adapter = get_adapter(channel.platform, credentials_from_channel(channel))
		orders = adapter.fetch_orders(since=_since_value(channel.last_order_sync))
		direct = _direct_platforms(channel)
		for order in orders:
			try:
				outcome = import_normalized_order(channel, order, direct_platforms=direct)
				counts[outcome] = counts.get(outcome, 0) + 1
			except Exception:
				counts["failed"] += 1
				frappe.log_error(frappe.get_traceback(), "Order Management import")
		channel.db_set("last_order_sync", now_datetime())
		status = "Failed" if counts["failed"] and not (counts["created"] or counts["updated"]) else (
			"Partial Success" if counts["failed"] else "Success"
		)
		_finish_log(log, status, counts)
		return counts
	except Exception as exc:
		_finish_log(log, "Failed", counts, str(exc))
		frappe.db.commit()
		raise


def import_normalized_order(channel, order: dict, direct_platforms=None) -> str:
	"""Upsert one normalized order and create or update the warehouse document."""
	if direct_platforms is None:
		direct_platforms = _direct_platforms(channel)
	skip = channel.platform == "Pancake" and pancake_should_skip(order.get("origin_platform"), direct_platforms)
	sku_map = _sku_map(channel.name)
	lines, unmapped = line_mappings(order.get("items"), sku_map)
	existing = _existing_order(channel.name, order.get("external_order_id"))
	pick_posted = pick_is_posted(existing.release_order) if existing and existing.release_order else False
	plan = plan_import(
		order=order,
		import_on_status=channel.import_on_status,
		unmapped=unmapped,
		has_contract=bool(channel.contract),
		existing={
			"release_order": existing.release_order if existing else None,
			"inbound_order": existing.inbound_order if existing else None,
			"pick_posted": pick_posted,
		},
		skip_pancake=skip,
	)
	if plan["action"] == "skip":
		return "skipped"

	doc, existed = _upsert_platform_order(channel, order, lines, plan, existing.name if existing else None)

	try:
		if plan["create_release"]:
			release = _create_release(channel, order, lines)
			doc.db_set("release_order", release.name)
			_maybe_submit_and_job(channel, release)
		elif plan["cancel_release"] and doc.release_order:
			_cancel_release(doc.release_order)
			doc.db_set("release_order", "")
		elif plan["create_inbound"]:
			inbound = _create_inbound(channel, order, lines)
			doc.db_set("inbound_order", inbound.name)
	except Exception as exc:
		doc.db_set("status", "On Hold")
		doc.db_set("hold_reason", str(exc)[:1000])
		raise

	return "updated" if existed else "created"


def sync_channel_items(channel_name: str) -> dict:
	channel = frappe.get_doc("Sales Channel", channel_name)
	if not channel.enabled or not channel.sync_items:
		return {"skipped": True}
	log = _start_log(channel.name, "Push Items", "Out")
	counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
	try:
		adapter = get_adapter(channel.platform, credentials_from_channel(channel))
		for listing in adapter.fetch_listings():
			_upsert_channel_item(channel, listing)
			counts["updated"] += 1
		for row in frappe.get_all(
			"Channel Item",
			filters={"sales_channel": channel.name},
			fields=["name", "seller_sku", "platform_item_id", "variant_id", "listing_title", "selling_price", "weight", "image_url", "barcode", "platform_category_id", "warehouse_item"],
		):
			if not _listing_ready(row):
				counts["skipped"] += 1
				continue
			try:
				result = adapter.push_product(_item_payload(row))
				if result.get("skipped"):
					counts["skipped"] += 1
					frappe.db.set_value("Channel Item", row.name, "sync_status", "Pending")
				else:
					counts["created"] += 1
					frappe.db.set_value("Channel Item", row.name, {"sync_status": "Synced", "last_synced": now_datetime()})
			except Exception:
				counts["failed"] += 1
				frappe.db.set_value("Channel Item", row.name, "sync_status", "Error")
				frappe.log_error(frappe.get_traceback(), "Order Management item push")
		channel.db_set("last_item_sync", now_datetime())
		_finish_log(log, "Partial Success" if counts["failed"] else "Success", counts)
		return counts
	except Exception as exc:
		_finish_log(log, "Failed", counts, str(exc))
		frappe.db.commit()
		raise


def push_channel_stock(channel_name: str) -> dict:
	channel = frappe.get_doc("Sales Channel", channel_name)
	if not channel.enabled or not channel.sync_stock:
		return {"skipped": True}
	log = _start_log(channel.name, "Push Stock", "Out")
	counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
	try:
		quantities = available_map(channel.customer, channel.company, channel.branch, channel.safety_stock_qty or 0)
		safety = channel.safety_stock_qty or 0
		updates = []
		touched = []
		for row in frappe.get_all(
			"Channel Item",
			filters={"sales_channel": channel.name},
			fields=["name", "seller_sku", "platform_item_id", "variant_id", "warehouse_item", "last_stock_qty"],
		):
			if not row.warehouse_item:
				counts["skipped"] += 1
				continue
			if row.warehouse_item in quantities:
				qty = quantities[row.warehouse_item]
			else:
				qty = available_to_sell(0, 0, safety)
			if not stock_should_push(row.last_stock_qty, qty):
				counts["skipped"] += 1
				continue
			updates.append(
				{
					"seller_sku": row.seller_sku,
					"platform_item_id": row.platform_item_id,
					"variant_id": row.variant_id,
					"qty": qty,
				}
			)
			touched.append((row.name, qty))
		if updates:
			adapter = get_adapter(channel.platform, credentials_from_channel(channel))
			adapter.push_stock(updates)
			for name, qty in touched:
				frappe.db.set_value(
					"Channel Item",
					name,
					{"last_stock_qty": qty, "last_synced": now_datetime()},
				)
			counts["updated"] = len(touched)
		channel.db_set("last_stock_sync", now_datetime())
		_finish_log(log, "Success", counts)
		return counts
	except Exception as exc:
		_finish_log(log, "Failed", counts, str(exc))
		frappe.db.commit()
		raise


def push_fulfillment_for_release(release_order: str) -> dict:
	rows = frappe.get_all(
		"Platform Order",
		filters={"release_order": release_order},
		fields=["name", "sales_channel", "external_order_id", "tracking_no", "carrier"],
	)
	pushed = 0
	for row in rows:
		channel = frappe.get_doc("Sales Channel", row.sales_channel)
		if not channel.enabled or not channel.push_fulfillment:
			continue
		log = _start_log(channel.name, "Push Fulfillment", "Out")
		try:
			adapter = get_adapter(channel.platform, credentials_from_channel(channel))
			adapter.push_fulfillment(
				{
					"external_order_id": row.external_order_id,
					"tracking_no": row.tracking_no,
					"carrier": row.carrier,
				}
			)
			frappe.db.set_value("Platform Order", row.name, "status", "Shipped")
			_finish_log(log, "Success", {"updated": 1})
			pushed += 1
		except Exception as exc:
			_finish_log(log, "Failed", {"failed": 1}, str(exc))
			frappe.log_error(frappe.get_traceback(), "Order Management fulfillment")
	return {"updated": pushed}


def _direct_platforms(channel) -> set:
	rows = frappe.get_all(
		"Sales Channel",
		filters={"customer": channel.customer, "enabled": 1, "sync_orders": 1},
		pluck="platform",
	)
	return {platform for platform in rows if platform != "Pancake"}


def _sku_map(channel_name: str) -> dict:
	rows = frappe.get_all(
		"Channel Item",
		filters={"sales_channel": channel_name},
		fields=["seller_sku", "warehouse_item"],
	)
	return {row.seller_sku: row.warehouse_item for row in rows if row.seller_sku and row.warehouse_item}


def _existing_order(channel_name, external_order_id):
	if not external_order_id:
		return None
	return frappe.db.get_value(
		"Platform Order",
		{"sales_channel": channel_name, "external_order_id": external_order_id},
		["name", "release_order", "inbound_order"],
		as_dict=True,
	)


def _upsert_platform_order(channel, order, lines, plan, existing_name):
	payload = {
		"status": plan["order_status"],
		"platform_status": order.get("platform_status"),
		"origin_platform": order.get("origin_platform"),
		"hold_reason": plan.get("hold_reason"),
		"buyer_name": order.get("buyer_name"),
		"phone": order.get("phone"),
		"address_line": order.get("address_line"),
		"city": order.get("city"),
		"state": order.get("state"),
		"country": order.get("country"),
		"postal_code": order.get("postal_code"),
		"grand_total": order.get("grand_total") or 0,
		"payment_method": order.get("payment_method"),
		"is_cod": order.get("is_cod") or 0,
		"ordered_at": order.get("ordered_at"),
		"ship_by": order.get("ship_by"),
		"tracking_no": order.get("tracking_no"),
		"carrier": order.get("carrier"),
		"raw_payload": sanitize(order.get("raw") or {}),
	}
	currency = order.get("currency")
	if currency and frappe.db.exists("Currency", currency):
		payload["currency"] = currency
	if existing_name:
		doc = frappe.get_doc("Platform Order", existing_name)
		doc.update(payload)
		doc.items = []
		for line in lines:
			doc.append("items", _child_line(line))
		doc.save(ignore_permissions=True)
		return doc, True
	doc = frappe.get_doc(
		{
			"doctype": "Platform Order",
			"naming_series": "EOM.#########",
			"sales_channel": channel.name,
			"external_order_id": order.get("external_order_id"),
			**payload,
			"items": [_child_line(line) for line in lines],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc, False


def _child_line(line) -> dict:
	return {
		"seller_sku": line.get("seller_sku"),
		"platform_item_id": line.get("platform_item_id"),
		"variant_id": line.get("variant_id"),
		"item_name": line.get("item_name"),
		"qty": line.get("qty") or 0,
		"price": line.get("price") or 0,
		"warehouse_item": line.get("warehouse_item"),
		"mapped": 1 if line.get("mapped") else 0,
	}


def _order_date(order) -> str:
	value = order.get("ordered_at")
	if not value:
		return frappe.utils.today()
	try:
		return str(getdate(value))
	except Exception:
		return frappe.utils.today()


def _contract_accounts(channel) -> dict:
	contract = frappe.get_doc("Warehouse Contract", channel.contract)
	return {
		"customer": channel.customer,
		"contract": channel.contract,
		"company": contract.company or channel.company,
		"branch": contract.branch or channel.branch,
		"cost_center": contract.cost_center,
		"profit_center": contract.profit_center,
	}


def _warehouse_lines(lines) -> list:
	rows = []
	for line in lines:
		if not line.get("warehouse_item"):
			continue
		uom = frappe.db.get_value("Warehouse Item", line["warehouse_item"], "uom")
		rows.append({"item": line["warehouse_item"], "quantity": line.get("qty") or 0, "uom": uom})
	return rows


def _create_release(channel, order, lines):
	accounts = _contract_accounts(channel)
	doc = frappe.get_doc(
		{
			"doctype": "Release Order",
			"naming_series": "WRO.######",
			"order_date": _order_date(order),
			"priority": "Normal",
			"cust_reference": cust_reference(channel.platform, order.get("external_order_id")),
			"notes": ship_to_summary(order),
			"items": _warehouse_lines(lines),
			**accounts,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _create_inbound(channel, order, lines):
	accounts = _contract_accounts(channel)
	doc = frappe.get_doc(
		{
			"doctype": "Inbound Order",
			"naming_series": "WIN.########",
			"order_date": _order_date(order),
			"priority": "Normal",
			"cust_reference": cust_reference(channel.platform, order.get("external_order_id"), prefix="RET:"),
			"items": _warehouse_lines(lines),
			**accounts,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _maybe_submit_and_job(channel, release):
	if not channel.auto_submit_release_order:
		return
	release.submit()
	if channel.auto_create_warehouse_job:
		from logistics.warehousing.doctype.release_order.release_order import make_warehouse_job

		make_warehouse_job(release.name)


def _cancel_release(release_name):
	doc = frappe.get_doc("Release Order", release_name)
	if doc.docstatus == 1:
		doc.cancel()
	elif doc.docstatus == 0:
		# The Platform Order still links this draft, so a normal delete is blocked.
		frappe.delete_doc("Release Order", release_name, ignore_permissions=True, force=1)


def _upsert_channel_item(channel, listing: dict):
	sku = (listing.get("seller_sku") or "").strip()
	if not sku:
		return
	warehouse_item = frappe.db.get_value(
		"Warehouse Item",
		{"code": sku, "customer": channel.customer},
		"name",
	)
	existing = frappe.db.get_value(
		"Channel Item",
		{"sales_channel": channel.name, "seller_sku": sku},
		"name",
	)
	values = {
		"platform_item_id": listing.get("platform_item_id"),
		"variant_id": listing.get("variant_id"),
		"listing_title": listing.get("listing_title"),
		"selling_price": listing.get("selling_price") or 0,
		"weight": listing.get("weight") or 0,
		"image_url": listing.get("image_url"),
		"barcode": listing.get("barcode"),
	}
	if warehouse_item:
		values["warehouse_item"] = warehouse_item
	if existing:
		frappe.db.set_value("Channel Item", existing, values)
		return
	doc = frappe.get_doc(
		{
			"doctype": "Channel Item",
			"naming_series": "CIM-.######",
			"sales_channel": channel.name,
			"seller_sku": sku,
			**values,
		}
	)
	doc.insert(ignore_permissions=True)


def _listing_ready(row) -> bool:
	return bool(row.listing_title) and row.selling_price not in (None, "", 0) and row.weight not in (None, "", 0)


def _item_payload(row) -> dict:
	return {
		"seller_sku": row.seller_sku,
		"platform_item_id": row.platform_item_id,
		"variant_id": row.variant_id,
		"listing_title": row.listing_title,
		"selling_price": row.selling_price,
		"weight": row.weight,
		"image_url": row.image_url,
		"barcode": row.barcode,
		"platform_category_id": row.platform_category_id,
	}


def _since_value(last_sync):
	if not last_sync:
		return None
	try:
		return int(last_sync.timestamp())
	except Exception:
		return str(last_sync)


def _start_log(channel, operation, direction):
	doc = frappe.get_doc(
		{
			"doctype": "Order Sync Log",
			"sales_channel": channel,
			"operation": operation,
			"direction": direction,
			"status": "Running",
			"started": now_datetime(),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _finish_log(log, status, counts, error=None):
	log.db_set("status", status)
	log.db_set("finished", now_datetime())
	log.db_set("created_count", counts.get("created", 0))
	log.db_set("updated_count", counts.get("updated", 0))
	log.db_set("skipped_count", counts.get("skipped", 0))
	log.db_set("failed_count", counts.get("failed", 0))
	if error:
		log.db_set("error_message", str(error)[:2000])
