# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Container Management API

Functions for creating, linking, and updating Container records
from Sea Shipment, Transport Job, etc.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from logistics.utils.container_validation import (
	normalize_container_number,
	validate_container_number,
	get_strict_validation_setting,
)


def is_container_management_enabled():
	"""Check if container management is enabled in Logistics Settings."""
	try:
		settings = frappe.get_single("Logistics Settings")
		return getattr(settings, "enable_container_management", False)
	except Exception:
		return False


def get_container_by_number(container_number):
	"""
	Resolve a Container document name from equipment number.
	Prefers an active assignment (`is_active`); then a legacy doc whose name equals the number.
	"""
	container_number = normalize_container_number(container_number or "")
	if not container_number:
		return None
	active_rows = frappe.get_all(
		"Container",
		filters={"container_number": container_number, "is_active": 1},
		pluck="name",
		limit_page_length=1,
		order_by="modified desc",
	)
	if active_rows:
		return active_rows[0]
	if frappe.db.exists("Container", container_number):
		return container_number
	legacy = frappe.db.sql(
		"""
		SELECT name FROM `tabContainer`
		WHERE container_number = %s AND IFNULL(master_bill, '') = ''
		ORDER BY modified DESC LIMIT 1
		""",
		(container_number,),
	)
	return legacy[0][0] if legacy else None


def get_active_container_assignment(container_no):
	"""Return name of active Container (same equipment no.), or None. Kept for API compatibility."""
	container_no = normalize_container_number(container_no or "")
	if not container_no:
		return None
	rows = frappe.get_all(
		"Container",
		filters={"container_number": container_no, "is_active": 1},
		pluck="name",
		limit_page_length=1,
		order_by="modified desc",
	)
	return rows[0] if rows else None


def sea_container_row_field_to_equipment_number(container_no_field):
	"""
	ISO equipment number from a Sea Booking / Sea Shipment child `container_no` value.
	When fieldtype is Link, `container_no_field` is a Container document name.
	Legacy rows may still store the plain container number string.
	"""
	if not container_no_field:
		return ""
	raw = str(container_no_field).strip()
	if not raw:
		return ""
	if frappe.db.exists("Container", raw):
		num = frappe.db.get_value("Container", raw, "container_number")
		return normalize_container_number(num or "") if num else ""
	return normalize_container_number(raw)


def sea_container_row_field_to_doc_name(container_no_field):
	"""Resolve a Container document name from child `container_no` (Link name or legacy number)."""
	if not container_no_field:
		return None
	raw = str(container_no_field).strip()
	if not raw:
		return None
	if frappe.db.exists("Container", raw):
		return raw
	return get_container_by_number(raw)


def expand_sea_container_no_for_sql_in(container_no_field):
	"""Possible `tabSea * Containers`.container_no DB values for duplicate checks (link + legacy)."""
	found = set()
	if not container_no_field:
		return found
	raw = str(container_no_field).strip()
	if not raw:
		return found
	found.add(raw)
	eq = sea_container_row_field_to_equipment_number(container_no_field)
	if eq:
		found.add(eq)
	doc = sea_container_row_field_to_doc_name(container_no_field)
	if doc:
		found.add(doc)
	return found


@frappe.whitelist()
def get_container_by_number_api(container_number):
	"""Whitelisted: get Container name by number."""
	name = get_container_by_number(container_number)
	return {"container": name} if name else None


def get_or_create_container(
	container_no,
	container_type=None,
	seal_number=None,
	status=None,
	parent_doctype=None,
	parent_name=None,
	master_bill=None,
):
	"""
	Get existing Container or create new one.
	When `master_bill` is set, names the doc `{master_bill}-{container_no}` and applies MBL assignment rules.
	Without `master_bill`, uses legacy behaviour (document name = container number).
	If ``status`` is None, an existing Container's status is left unchanged; a new Container defaults to "In Transit".
	Returns Container name.
	"""
	if not is_container_management_enabled():
		return None

	container_no = normalize_container_number(container_no or "")
	if not container_no:
		return None

	strict = get_strict_validation_setting()
	valid, err = validate_container_number(container_no, strict=strict)
	if not valid:
		frappe.throw(err, title=_("Invalid Container Number"))

	if master_bill:
		existing = frappe.db.get_value(
			"Container",
			{"container_number": container_no, "master_bill": master_bill, "is_active": 1},
			"name",
		)
		if existing:
			container_name = existing
			if status:
				_apply_status_with_return_sync(existing, status)
			return container_name
		container = frappe.new_doc("Container")
		container.container_number = container_no
		container.master_bill = master_bill
		container.is_active = 1
		container.container_type = container_type
		container.seal_number = seal_number
		container.status = status or "In Transit"
		try:
			sf_settings = frappe.get_single("Sea Freight Settings")
			container.free_time_days = flt(getattr(sf_settings, "default_free_time_days", 7))
		except Exception:
			container.free_time_days = 7
		container.return_status = "Not Returned"
		if container.status in ("Empty Returned", "Closed"):
			container.return_status = "Returned"
			container.returned_date = getdate(now_datetime())
		container.insert(ignore_permissions=True)
		return container.name

	existing = None
	if frappe.db.exists("Container", container_no):
		existing = container_no
	else:
		legacy = frappe.db.sql(
			"""
			SELECT name FROM `tabContainer`
			WHERE container_number = %s AND IFNULL(master_bill, '') = ''
			ORDER BY modified DESC LIMIT 1
			""",
			(container_no,),
		)
		if legacy:
			existing = legacy[0][0]

	if existing:
		if status:
			_apply_status_with_return_sync(existing, status)
		return existing

	container = frappe.new_doc("Container")
	container.container_number = container_no
	container.container_type = container_type
	container.seal_number = seal_number
	container.status = status or "In Transit"
	try:
		sf_settings = frappe.get_single("Sea Freight Settings")
		container.free_time_days = flt(getattr(sf_settings, "default_free_time_days", 7))
	except Exception:
		container.free_time_days = 7
	container.return_status = "Not Returned"
	if container.status in ("Empty Returned", "Closed"):
		container.return_status = "Returned"
		container.returned_date = getdate(now_datetime())
	container.insert(ignore_permissions=True)
	return container.name


def _apply_status_with_return_sync(container_name, status, movement_date=None):
	"""Keep status and return fields in sync for returned/closed containers."""
	if not status:
		return
	container = frappe.get_doc("Container", container_name)
	container.status = status
	if status in ("Empty Returned", "Closed"):
		container.return_status = "Returned"
		container.returned_date = movement_date or container.returned_date or getdate(now_datetime())
	container.save(ignore_permissions=True)


def sync_shipment_containers_and_penalties(shipment_doc):
	"""
	For each container in Sea Shipment:
	- Create/link Container record
	- Set container link on child row
	- Sync penalty fields from shipment to container
	"""
	if not is_container_management_enabled():
		return

	containers = getattr(shipment_doc, "containers", []) or []
	for row in containers:
		container_no = getattr(row, "container_no", None)
		if not container_no or not str(container_no).strip():
			continue
		raw = str(container_no).strip()
		if frappe.db.exists("Container", raw):
			container_name = raw
		else:
			eq = sea_container_row_field_to_equipment_number(raw) or raw
			container_name = get_or_create_container(
				container_no=eq,
				container_type=getattr(row, "type", None),
				seal_number=getattr(row, "seal_no", None),
				status=_shipping_status_to_container_status(
					getattr(shipment_doc, "shipping_status", None)
				),
				master_bill=getattr(shipment_doc, "master_bill", None) or None,
			)
		if container_name:
			row.container = container_name
			_sync_penalty_to_container(container_name, shipment_doc)


def _shipping_status_to_container_status(shipping_status):
	"""
	Map Sea Shipment shipping_status to Container status.
	Returns None when there is no mapping so existing Container status is not overwritten
	(e.g. early milestones like Booking Received or future options not yet listed here).
	"""
	if not shipping_status:
		return None
	status_map = {
		"Gate-In at Port / CY": "Gate-In",
		"Loaded on Vessel": "Loaded",
		"Departed": "At Sea",
		"In-Transit": "At Sea",
		"Arrived": "At Port (Destination)",
		"Discharged from Vessel": "Discharged",
		"Customs Clearance (Import)": "Customs Hold",
		"Customs Hold": "Customs Hold",
		"Available for Pick-Up": "Available for Pick-Up",
		"Out for Delivery": "Out for Delivery",
		"Delivered": "Delivered",
		"Empty Container Returned": "Empty Returned",
		"Detention / Demurrage Ongoing": "At Port (Destination)",
		"Closed": "Closed",
	}
	return status_map.get(shipping_status)


def _sync_penalty_to_container(container_name, shipment_doc):
	"""Sync per-container penalty fields from Sea Shipment dates and Container free time."""
	try:
		from frappe.utils import now_datetime, getdate
		from logistics.sea_freight.penalty_utils import compute_penalty_for_single_container

		container = frappe.get_doc("Container", container_name)
		if getattr(container, "penalty_manual_override", 0):
			return
		settings = frappe.get_single("Sea Freight Settings")
		today = getdate(now_datetime())
		out = compute_penalty_for_single_container(container, shipment_doc, settings, today)
		container.demurrage_days = out["demurrage_days"]
		container.detention_days = out["detention_days"]
		container.estimated_penalty_amount = out["estimated_penalty_amount"]
		container.has_penalties = out["has_penalties"]
		container.penalty_alert_sent = 1 if getattr(shipment_doc, "penalty_alert_sent", 0) else 0
		container.last_penalty_check = getattr(shipment_doc, "last_penalty_check", None)
		container.save(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(
			"Container penalty sync error: {0}".format(str(e)),
			"Container Management"
		)


@frappe.whitelist()
def create_container_from_shipment(sea_shipment_name, container_no, container_type=None, seal_no=None):
	"""Create Container from Sea Shipment container row."""
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
	container_name = get_or_create_container(
		container_no=container_no,
		container_type=container_type,
		seal_number=seal_no,
		status=_shipping_status_to_container_status(shipment.shipping_status),
		master_bill=getattr(shipment, "master_bill", None) or None,
	)
	return {"container": container_name}


@frappe.whitelist()
def update_container_status(container_name, status=None, movement_date=None):
	"""Update Container status and sync return fields when status is terminal (Empty Returned / Closed)."""
	if status:
		_apply_status_with_return_sync(container_name, status, movement_date=movement_date)
	return {"success": True}


@frappe.whitelist()
def calculate_container_penalties(container_name):
	"""Calculate penalties for a container. Returns dict with demurrage_days, detention_days, estimated_amount."""
	from logistics.logistics.doctype.container.container import calculate_penalties_for_container
	return calculate_penalties_for_container(container_name)


@frappe.whitelist()
def link_container_to_job(container_name, reference_doctype, reference_name):
	"""Link container to a job/shipment. Used when container field is set on Transport Job etc."""
	# The link is typically set on the child (Transport Job has container field)
	# This API can be used to ensure Container exists and return it
	return {"container": container_name, "success": True}


def sync_transport_job_container(job_doc):
	"""Create/link Container for Transport Job when container_no is set."""
	if not is_container_management_enabled():
		return
	if job_doc.transport_job_type != "Container":
		return
	container_no = getattr(job_doc, "container_no", None)
	if not container_no or not str(container_no).strip():
		return

	container_name = get_or_create_container(
		container_no=container_no,
		container_type=getattr(job_doc, "container_type", None),
		status=_transport_status_to_container_status(getattr(job_doc, "status", None)),
	)
	if container_name:
		job_doc.container = container_name


def sync_transport_order_container(order_doc):
	"""Create/link Container for Transport Order when container_no is set."""
	if not is_container_management_enabled():
		return
	if order_doc.transport_job_type != "Container":
		return
	container_no = getattr(order_doc, "container_no", None)
	if not container_no or not str(container_no).strip():
		return

	container_name = get_or_create_container(
		container_no=container_no,
		container_type=getattr(order_doc, "container_type", None),
		status="In Transit",
	)
	if container_name:
		order_doc.container = container_name


def _transport_status_to_container_status(status):
	"""
	Map Transport Job status to Container status.
	Returns None when unmapped so an existing Container is not forced to In Transit.
	"""
	if not status:
		return None
	status_map = {
		"Delivered": "Delivered",
		"Completed": "Empty Returned",
		"In Progress": "Out for Delivery",
	}
	return status_map.get(status)


def movement_type_to_container_status(movement_type):
	"""Map Container Movement movement_type to Container status. None = do not change Container."""
	if not movement_type:
		return None
	status_map = {
		"Gate-In": "Gate-In",
		"Loaded": "Loaded",
		"Discharged": "Discharged",
		"Picked Up": "Available for Pick-Up",
		"Delivered": "Delivered",
		"Returned": "Empty Returned",
	}
	return status_map.get(movement_type)


def sync_container_from_movement(movement_doc):
	"""Apply Container status from a Container Movement (on save)."""
	if not is_container_management_enabled():
		return
	container_name = getattr(movement_doc, "container", None)
	if not container_name:
		return
	status = movement_type_to_container_status(getattr(movement_doc, "movement_type", None))
	if not status:
		return
	movement_dt = getattr(movement_doc, "movement_date", None)
	movement_date = getdate(movement_dt) if movement_dt else None
	_apply_status_with_return_sync(container_name, status, movement_date=movement_date)


def reconcile_containers_from_terminal_sea_shipments(limit=500):
	"""
	Daily reconciliation: re-run shipment→container sync for submitted Sea Shipments
	in a terminal shipping status so Container return state matches (fixes drift / legacy data).
	"""
	if not is_container_management_enabled():
		return
	terminal = ("Empty Container Returned", "Closed")
	names = frappe.get_all(
		"Sea Shipment",
		filters={"docstatus": 1, "shipping_status": ["in", list(terminal)]},
		pluck="name",
		limit_page_length=limit,
	)
	for name in names:
		try:
			doc = frappe.get_doc("Sea Shipment", name)
			sync_shipment_containers_and_penalties(doc)
		except Exception as e:
			frappe.log_error(
				title="Container reconciliation",
				message="Sea Shipment {0}: {1}".format(name, str(e)),
			)
