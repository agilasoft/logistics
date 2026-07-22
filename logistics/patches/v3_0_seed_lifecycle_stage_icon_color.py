# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed Icon / Color on Lifecycle Stage from dashboard defaults when empty."""

from __future__ import annotations

import frappe

from logistics.utils.lifecycle_stage import _STAGE_APPEARANCE_FALLBACK


def execute():
	if not frappe.db.exists("DocType", "Lifecycle Stage"):
		return
	meta = frappe.get_meta("Lifecycle Stage")
	has_icon = meta.has_field("icon")
	has_color = meta.has_field("color")
	if not has_icon and not has_color:
		return

	for stage_name, appearance in _STAGE_APPEARANCE_FALLBACK.items():
		if stage_name == "Unassigned":
			continue
		if not frappe.db.exists("Lifecycle Stage", stage_name):
			continue
		updates = {}
		if has_icon and not (frappe.db.get_value("Lifecycle Stage", stage_name, "icon") or "").strip():
			updates["icon"] = appearance["icon"]
		if has_color and not (frappe.db.get_value("Lifecycle Stage", stage_name, "color") or "").strip():
			updates["color"] = appearance["color"]
		if updates:
			frappe.db.set_value("Lifecycle Stage", stage_name, updates, update_modified=False)
