# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Backfill Truck Ban Constraint.constraint_type from existing child / weight data."""

from __future__ import unicode_literals

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.exists("DocType", "Truck Ban Constraint"):
		return

	frappe.reload_doc("transport", "doctype", "truck_ban_constraint", force=True)

	if not frappe.db.has_column("Truck Ban Constraint", "constraint_type"):
		frappe.db.updatedb("Truck Ban Constraint")

	if not frappe.db.has_column("Truck Ban Constraint", "constraint_type"):
		return

	for name in frappe.get_all("Truck Ban Constraint", pluck="name"):
		current = frappe.db.get_value("Truck Ban Constraint", name, "constraint_type")
		if current:
			continue
		inferred = _infer_constraint_type(name)
		frappe.db.set_value(
			"Truck Ban Constraint",
			name,
			"constraint_type",
			inferred,
			update_modified=False,
		)

	frappe.clear_cache(doctype="Truck Ban Constraint")


def _infer_constraint_type(name: str) -> str:
	if frappe.db.exists("Truck Ban Plate Coding", {"parent": name}):
		return "Plate Coding"
	if frappe.db.exists("Truck Ban Restricted Addresses", {"parent": name}):
		return "Area Ban"
	if frappe.db.exists("Truck Ban Restricted Routes", {"parent": name}):
		return "Route Ban"
	weight = flt(
		frappe.db.get_value("Truck Ban Constraint", name, "min_vehicle_weight_restriction")
	)
	if weight > 0:
		return "Weight-Based Ban"
	if frappe.db.exists("Truck Ban Constraint Vehicle Types", {"parent": name}):
		return "Vehicle Type Ban"
	return "Time-Based Ban"
