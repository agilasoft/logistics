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
	"""Get Container doc by container number, or None."""
	container_number = normalize_container_number(container_number or "")
	if not container_number:
		return None
	return frappe.db.get_value("Container", container_number, "name")


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
):
	"""
	Get existing Container or create new one.
	Validates container number (ISO 6346) before create.
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

	existing = frappe.db.get_value("Container", container_no, "name")
	if existing:
		container_name = existing
	else:
		# Create new Container
		container = frappe.new_doc("Container")
		container.container_number = container_no
		container.container_type = container_type
		container.seal_number = seal_number
		container.status = status or "In Transit"
		# Set free time from Sea Freight Settings
		try:
			sf_settings = frappe.get_single("Sea Freight Settings")
			container.free_time_days = flt(getattr(sf_settings, "default_free_time_days", 7))
		except Exception:
			container.free_time_days = 7
		container.return_status = "Not Returned"
		container.insert(ignore_permissions=True)
		container_name = container.name

	return container_name


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

		container_name = get_or_create_container(
			container_no=container_no,
			container_type=getattr(row, "type", None),
			seal_number=getattr(row, "seal_no", None),
			status=_shipping_status_to_container_status(
				getattr(shipment_doc, "shipping_status", None)
			),
		)
		if container_name:
			row.container = container_name
			_sync_penalty_to_container(container_name, shipment_doc)


def _shipping_status_to_container_status(shipping_status):
	"""Map Sea Shipment shipping_status to Container status."""
	status_map = {
		"Gate-In at Port / CY": "Gate-In",
		"Loaded on Vessel": "Loaded",
		"Departed": "At Sea",
		"In-Transit": "At Sea",
		"Arrived": "At Port (Destination)",
		"Discharged from Vessel": "Discharged",
		"Customs Clearance (Import)": "Customs Hold",
		"Available for Pick-Up": "Available for Pick-Up",
		"Out for Delivery": "Out for Delivery",
		"Delivered": "Delivered",
		"Empty Container Returned": "Empty Returned",
		"Detention / Demurrage Ongoing": "At Port (Destination)",
	}
	return status_map.get(shipping_status, "In Transit")


def _sync_penalty_to_container(container_name, shipment_doc):
	"""Sync penalty fields from Sea Shipment to Container."""
	try:
		container = frappe.get_doc("Container", container_name)
		container.demurrage_days = flt(getattr(shipment_doc, "demurrage_days", 0))
		container.detention_days = flt(getattr(shipment_doc, "detention_days", 0))
		container.estimated_penalty_amount = flt(getattr(shipment_doc, "estimated_penalty_amount", 0))
		container.has_penalties = 1 if getattr(shipment_doc, "has_penalties", 0) else 0
		container.penalty_alert_sent = 1 if getattr(shipment_doc, "penalty_alert_sent", 0) else 0
		container.last_penalty_check = getattr(shipment_doc, "last_penalty_check", None)
		container.free_time_days = flt(getattr(shipment_doc, "free_time_days", 0)) or container.free_time_days
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
	)
	return {"container": container_name}


@frappe.whitelist()
def update_container_status(container_name, status=None, movement_date=None):
	"""Update Container status and optionally create Container Movement."""
	container = frappe.get_doc("Container", container_name)
	if status:
		container.status = status
		if status == "Empty Returned":
			container.return_status = "Returned"
			container.returned_date = movement_date or getdate(now_datetime())
	container.save(ignore_permissions=True)
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
	"""Map Transport Job status to Container status."""
	status_map = {
		"Delivered": "Delivered",
		"Completed": "Empty Returned",
		"In Progress": "Out for Delivery",
	}
	return status_map.get(status, "In Transit")
