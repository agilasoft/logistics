# Copyright (c) 2026, www.agilasoft.com and contributors
# Populate missing Special Project tab data when source-site values are unavailable.
#
# Run:
#   bench --site logistics.agilasoft.com execute \
#     logistics.scripts.populate_special_project_demo_data.run \
#     --kwargs '{"name":"PROJ-0110"}'

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, today, flt


def run(name: str = "PROJ-0110"):
	if not frappe.db.exists("Special Project", name):
		frappe.throw(_("Special Project {0} was not found.").format(name))

	doc = frappe.get_doc("Special Project", name)
	_populate_header(doc)
	_populate_scoping(doc)
	_populate_lifecycle_jobs(doc)
	_populate_packages(doc)
	_populate_charges(doc)

	frappe.set_user("Administrator")
	doc.flags.ignore_validate = False
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	result = {
		"name": doc.name,
		"project_name": doc.project_name,
		"status": doc.status,
		"child_counts": {
			df.fieldname: len(doc.get(df.fieldname) or [])
			for df in doc.meta.fields
			if df.fieldtype == "Table"
		},
	}
	print(frappe.as_json(result))
	return result


def _populate_header(doc):
	doc.project_name = doc.project_name or "Test SP Build Order"
	if "(from atndemo)" in (doc.project_name or ""):
		doc.project_name = doc.project_name.replace(" (from atndemo)", "").strip()
	doc.description = doc.description or (
		"Demo Special Project recreated from atndemo PROJ-0011. "
		"Sample programme data was generated on demo where source values were unavailable."
	)
	doc.special_handling_instructions = doc.special_handling_instructions or (
		"Handle with care. Coordinate site access before dispatch."
	)
	doc.planned_start = doc.planned_start or today()
	doc.planned_end = doc.planned_end or add_days(today(), 90)
	doc.start_date = doc.start_date or doc.planned_start
	doc.end_date = doc.end_date or doc.planned_end
	doc.priority = doc.priority or "Medium"
	doc.status = doc.status if doc.status and doc.status != "Draft" else "Scoping"
	doc.lifecycle_stage = doc.lifecycle_stage or _first_existing("Lifecycle Stage", "Pre-Show", "Logistics")
	doc.internal_notes = doc.internal_notes or "Auto-populated demo data for PROJ-0110."


def _populate_scoping(doc):
	if doc.get("scoping_activities"):
		return
	currency = frappe.db.get_value("Company", doc.company, "default_currency") or "INR"
	types = _list_names("Scoping Type", limit=3) or ["Site", "Transportation Scope", "Manpower Support Scope"]
	for idx, scoping_type in enumerate(types):
		doc.append(
			"scoping_activities",
			{
				"scoping_type": scoping_type,
				"activity_date": add_days(today(), idx * 3),
				"description": f"{scoping_type} for programme setup",
				"location": "Metro Manila",
				"cost": flt(25000 + idx * 10000),
				"currency": currency,
				"status": "Completed" if idx == 0 else "Planned",
			},
		)


def _populate_lifecycle_jobs(doc):
	if doc.get("lifecycle_jobs"):
		return
	rows = [
		("Sea", "freight_coordination", "Logistics", "Ocean freight — inbound container"),
		("Customs", None, "Logistics", "Import clearance and permits"),
		("Transport", None, "Logistics", "Site delivery — Wave 1"),
		("Special Project", "installation_supervision", "On-Site", "Site supervision and rigging"),
	]
	for service_type, activity_code, stage, notes in rows:
		if activity_code and not frappe.db.exists("Activity Code", activity_code):
			activity_code = None
		if stage and not frappe.db.exists("Lifecycle Stage", stage):
			stage = doc.lifecycle_stage
		doc.append(
			"lifecycle_jobs",
			{
				"service_type": service_type,
				"lifecycle_stage": stage,
				"activity_code": activity_code,
				"lifecycle_activity_status": "Not Started",
				"job_description": notes,
			},
		)


def _populate_packages(doc):
	if doc.get("packages"):
		return
	lines = [
		("Standard Build Kit", 1, 8, 4200),
		("Safety & PPE Crate", 1, 2, 180),
		("Electrical Components Box", 2, 4, 650),
	]
	for description, qty, packs, weight in lines:
		doc.append(
			"packages",
			{
				"description": description,
				"qty_required": qty,
				"no_of_packs": packs,
				"weight": weight,
				"weight_uom": "Kg",
				"include_on_create": 1 if "Safety" in description else 0,
			},
		)


def _populate_charges(doc):
	if doc.get("charges"):
		return
	currency = frappe.db.get_value("Company", doc.company, "default_currency") or "INR"
	item = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1}, "name", order_by="creation asc")
	charge_lines = [
		("Special Project", "Programme management / coordination", 120000, 45000),
		("Sea", "Ocean freight — 2x40ft inbound", 850000, 720000),
		("Customs", "Import clearance and permits", 95000, 65000),
		("Transport", "Site delivery — Wave 1", 320000, 240000),
	]
	lifecycle_by_service = {}
	for row in doc.get("lifecycle_jobs") or []:
		lifecycle_by_service.setdefault(row.service_type, row.name)

	for service_type, description, revenue, cost in charge_lines:
		charge = {
			"service_type": service_type,
			"description": description,
			"charge_type": "Margin",
			"charge_category": "Other" if service_type == "Special Project" else "Freight",
			"estimated_revenue": revenue,
			"estimated_cost": cost,
			"selling_currency": currency,
			"buying_currency": currency,
			"quantity": 1,
			"cost_quantity": 1,
		}
		if item:
			charge["item_code"] = item
		line = lifecycle_by_service.get(service_type)
		if line and doc.meta.get_field("charges").options == "Special Project Charges":
			meta = frappe.get_meta("Special Project Charges")
			if meta.has_field("lifecycle_job_line"):
				charge["lifecycle_job_line"] = line
		doc.append("charges", charge)


def _first_existing(doctype: str, *names: str) -> str | None:
	for name in names:
		if name and frappe.db.exists(doctype, name):
			return name
	return frappe.db.get_value(doctype, {}, "name")


def _list_names(doctype: str, limit: int = 5) -> list[str]:
	return frappe.get_all(doctype, pluck="name", limit=limit, order_by="name asc") or []
