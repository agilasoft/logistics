# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Exhibit program lifecycle stages and standard lifecycle jobs."""

from __future__ import annotations

import frappe
from frappe import _

from logistics.utils.lifecycle_stage import (
	FOR_EXHIBITS,
	get_lifecycle_stages,
	get_open_lifecycle_stages,
	validate_lifecycle_stage_advance as _validate_lifecycle_stage_advance,
)

LIFECYCLE_STAGES = ["Pre-Show", "Logistics", "On-Site", "Post-Show", "Closed"]

STANDARD_EXHIBIT_ACTIVITIES = [
	("Pre-Show", "asset_retrieval", "Asset Retrieval", 1),
	("Pre-Show", "staging_qc", "Staging & QC", 1),
	("Pre-Show", "refurbishment", "Refurbishment", 0),
	("Logistics", "freight_coordination", "Freight Coordination", 0),
	("Logistics", "real_time_tracking", "Real-Time Tracking", 0),
	("Logistics", "venue_delivery", "Venue Delivery", 0),
	("On-Site", "installation_supervision", "Installation Supervision", 0),
	("On-Site", "quality_control", "Quality Control", 0),
	("On-Site", "documentation", "Documentation", 1),
	("Post-Show", "dismantle_supervision", "Dismantle Supervision", 0),
	("Post-Show", "return_shipping", "Return Shipping", 0),
	("Post-Show", "storage_reporting", "Storage & Reporting", 0),
]


def get_standard_exhibit_activities():
	"""Return exhibit lifecycle job template rows from Activity Code master."""
	if frappe.db.exists("DocType", "Activity Code"):
		rows = frappe.get_all(
			"Activity Code",
			filters={"for_exhibits": 1},
			fields=[
				"lifecycle_stage",
				"name as activity_code",
				"activity_name",
				"description",
				"photo_required",
			],
			order_by="lifecycle_stage asc, sort_order asc, name asc",
		)
		if rows:
			return rows
	return [
		{
			"lifecycle_stage": stage,
			"activity_code": code,
			"activity_name": name,
			"description": name,
			"photo_required": photo,
		}
		for stage, code, name, photo in STANDARD_EXHIBIT_ACTIVITIES
	]


def _lifecycle_job_rows(doc):
	return [
		row
		for row in doc.get("lifecycle_jobs") or []
		if (row.activity_code or "").strip()
	]


def load_standard_service_activities(doc):
	load_standard_lifecycle_jobs(doc)


def load_standard_lifecycle_jobs(doc):
	if _lifecycle_job_rows(doc):
		return
	for row in get_standard_exhibit_activities():
		doc.append(
			"lifecycle_jobs",
			{
				"service_type": "Exhibits",
				"lifecycle_stage": row["lifecycle_stage"],
				"activity_code": row["activity_code"],
				"activity_name": row["activity_name"],
				"lifecycle_activity_status": "Not Started",
				"job_description": row.get("description") or row["activity_name"],
			},
		)


def validate_lifecycle_stage_advance(doc):
	_validate_lifecycle_stage_advance(
		doc,
		settings_doctype="Exhibit Settings",
		module_filter=FOR_EXHIBITS,
	)


def create_orders_for_event(event_name):
	if not frappe.db.get_single_value("Exhibit Settings", "auto_create_phase_orders"):
		return
	existing = frappe.get_all(
		"Exhibit Order",
		filters={"exhibit": event_name},
		pluck="lifecycle_stage",
	)
	program = frappe.get_doc("Exhibit", event_name)
	for stage in get_open_lifecycle_stages(FOR_EXHIBITS):
		if stage in existing:
			continue
		order = frappe.new_doc("Exhibit Order")
		order.exhibit = event_name
		order.lifecycle_stage = stage
		order.order_title = stage
		order.status = "Draft"
		order.customer = program.customer
		order.company = program.company
		order.cost_center = program.cost_center
		order.insert(ignore_permissions=True)
