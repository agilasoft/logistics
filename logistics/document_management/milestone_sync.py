# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Milestone update triggers: sync parent date <-> milestone actual_end, and complete milestones from field conditions.
Update triggers (Date Based / Field Based) always set milestone actual_end and status (Completed) when conditions are met.
Runs on parent on_update after ensure_documents_and_milestones_from_template.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import getdate, now_datetime

from logistics.document_management.api import MILESTONE_DOCTYPES
from logistics.utils.milestone_status_utils import update_milestone_status


def _dates_equal(a, b):
	"""Return True if both are None or represent the same date (ignore time)."""
	if a is None and b is None:
		return True
	if a is None or b is None:
		return False
	try:
		return getdate(a) == getdate(b)
	except Exception:
		return a == b


def apply_milestone_sync_in_place(doc, method=None):
	"""
	Run Date Based sync (parent date <-> milestone actual_end) and status from actual dates
	on the doc in-place. Call from before_save so the save persists both ata and actual_end.
	Uses only automation_* on each milestone row; backfills from template if row has none.
	"""
	if not doc or doc.doctype not in MILESTONE_DOCTYPES:
		return
	if getattr(frappe.flags, "in_milestone_sync", False):
		return
	if not getattr(doc, "name", None) or doc.get("__islocal"):
		return
	if not hasattr(doc, "milestones") or not getattr(doc, "milestone_template", None):
		return
	template_name = doc.milestone_template
	items = frappe.get_all(
		"Milestone Template Item",
		filters={"parent": template_name},
		fields=[
			"milestone", "date_basis", "sync_parent_date_field", "sync_direction",
			"update_trigger_type", "trigger_type",
			"trigger_field", "trigger_condition", "trigger_value", "trigger_action",
		],
		order_by="idx asc",
	)
	item_by_milestone = {}
	if items:
		for i in items:
			k = (i.get("milestone") or "").strip()
			if k:
				item_by_milestone[k] = i
	milestones = list(doc.get("milestones") or [])

	def _cfg(row):
		ut = (getattr(row, "automation_update_trigger_type", None) or "").strip()
		sync_field = (getattr(row, "automation_sync_parent_date_field", None) or "").strip()
		direction = (getattr(row, "automation_sync_direction", None) or "").strip()
		if not ut and item_by_milestone:
			key = (getattr(row, "milestone", None) or "").strip()
			item = item_by_milestone.get(key)
			if item:
				row.automation_planned_date_basis = (item.get("date_basis") or "").strip() or None
				row.automation_update_trigger_type = (item.get("update_trigger_type") or item.get("trigger_type") or "").strip() or None
				row.automation_sync_parent_date_field = (item.get("sync_parent_date_field") or "").strip() or None
				row.automation_sync_direction = (item.get("sync_direction") or "").strip() or None
				row.automation_trigger_field = (item.get("trigger_field") or "").strip() or None
				row.automation_trigger_condition = (item.get("trigger_condition") or "").strip() or None
				row.automation_trigger_value = (item.get("trigger_value") or "").strip() or None
				row.automation_trigger_action = (item.get("trigger_action") or "").strip() or None
				ut = (getattr(row, "automation_update_trigger_type", None) or "").strip()
				sync_field = (getattr(row, "automation_sync_parent_date_field", None) or "").strip()
				direction = (getattr(row, "automation_sync_direction", None) or "").strip()
		return {"update_trigger_type": ut, "sync_parent_date_field": sync_field, "sync_direction": direction}

	def _is_date_based(cfg):
		ut = (cfg.get("update_trigger_type") or "").strip()
		return ut in ("Date Based", "Parent date field sync")

	# 1) Parent date -> milestone actual_end
	for row in milestones:
		cfg = _cfg(row)
		if not _is_date_based(cfg) or not cfg.get("sync_parent_date_field"):
			continue
		direction = (cfg.get("sync_direction") or "").strip()
		if direction not in ("Both", "Parent to Milestone only", ""):
			continue
		fieldname = cfg["sync_parent_date_field"].strip()
		if not fieldname:
			continue
		val = doc.get(fieldname)
		if val is None:
			continue
		current = getattr(row, "actual_end", None)
		if not _dates_equal(current, val):
			row.actual_end = val
			row.status = "Completed"

	# 2) Milestone actual_end -> parent date
	for row in milestones:
		cfg = _cfg(row)
		if not _is_date_based(cfg) or not cfg.get("sync_parent_date_field"):
			continue
		direction = (cfg.get("sync_direction") or "").strip()
		if direction not in ("Both", "Milestone to Parent only", ""):
			continue
		fieldname = cfg["sync_parent_date_field"].strip()
		if not fieldname:
			continue
		val = getattr(row, "actual_end", None)
		if val is None:
			continue
		current = doc.get(fieldname)
		if not _dates_equal(current, val):
			doc.set(fieldname, val)

	# 4) Status from actual_start/actual_end
	for row in milestones:
		update_milestone_status(row)


def apply_milestone_sync_and_triggers(doc, method=None):
	"""
	Apply template-driven sync (parent date field <-> milestone actual_end) and
	field triggers (when parent field condition is met, complete milestone).
	Called from ensure_documents_and_milestones_from_template for doctypes in MILESTONE_DOCTYPES.
	"""
	if not doc or doc.doctype not in MILESTONE_DOCTYPES:
		return
	if getattr(frappe.flags, "in_milestone_sync", False):
		return
	name = getattr(doc, "name", None)
	if not name or name == "new" or getattr(doc, "__islocal", True):
		return
	if not hasattr(doc, "milestones") or not getattr(doc, "milestone_template", None):
		return

	frappe.flags.in_milestone_sync = True
	try:
		# Reload to get latest milestones (populate may have just added rows)
		parent = frappe.get_doc(doc.doctype, name)
		template_name = parent.milestone_template
		items = frappe.get_all(
			"Milestone Template Item",
			filters={"parent": template_name},
			fields=[
				"milestone", "date_basis", "sync_parent_date_field", "sync_direction",
				"update_trigger_type", "trigger_type",
				"trigger_field", "trigger_condition", "trigger_value", "trigger_action",
			],
			order_by="idx asc",
		)
		# Normalize milestone name for lookup (strip) so template item matches row
		item_by_milestone = {}
		if items:
			for i in items:
				k = (i.get("milestone") or "").strip()
				if k:
					item_by_milestone[k] = i
		milestones = list(parent.get("milestones") or [])
		changed = False

		def _get_row_config(row):
			"""Get trigger config from this milestone row's automation fields only (data as stored on the row).
			If row has no automation data, backfill once from template so the row has it; then use row data."""
			nonlocal changed
			# Use only automation_* stored on the milestone row (fetched when milestone was added from template)
			ut = (getattr(row, "automation_update_trigger_type", None) or "").strip()
			sync_field = (getattr(row, "automation_sync_parent_date_field", None) or "").strip()
			direction = (getattr(row, "automation_sync_direction", None) or "").strip()
			trigger_field = (getattr(row, "automation_trigger_field", None) or "").strip()
			trigger_condition = (getattr(row, "automation_trigger_condition", None) or "").strip()
			trigger_value = (getattr(row, "automation_trigger_value", None) or "").strip()
			trigger_action = (getattr(row, "automation_trigger_action", None) or "").strip()
			# One-time backfill from template only when row has no automation data
			if not ut and item_by_milestone:
				row_milestone_key = (getattr(row, "milestone", None) or "").strip()
				item = item_by_milestone.get(row_milestone_key)
				if item:
					row.automation_planned_date_basis = (item.get("date_basis") or "").strip() or None
					row.automation_update_trigger_type = (item.get("update_trigger_type") or item.get("trigger_type") or "").strip() or None
					row.automation_sync_parent_date_field = (item.get("sync_parent_date_field") or "").strip() or None
					row.automation_sync_direction = (item.get("sync_direction") or "").strip() or None
					row.automation_trigger_field = (item.get("trigger_field") or "").strip() or None
					row.automation_trigger_condition = (item.get("trigger_condition") or "").strip() or None
					row.automation_trigger_value = (item.get("trigger_value") or "").strip() or None
					row.automation_trigger_action = (item.get("trigger_action") or "").strip() or None
					changed = True
					# Re-read from row after backfill
					ut = (getattr(row, "automation_update_trigger_type", None) or "").strip()
					sync_field = (getattr(row, "automation_sync_parent_date_field", None) or "").strip()
					direction = (getattr(row, "automation_sync_direction", None) or "").strip()
					trigger_field = (getattr(row, "automation_trigger_field", None) or "").strip()
					trigger_condition = (getattr(row, "automation_trigger_condition", None) or "").strip()
					trigger_value = (getattr(row, "automation_trigger_value", None) or "").strip()
					trigger_action = (getattr(row, "automation_trigger_action", None) or "").strip()
			return {
				"update_trigger_type": ut,
				"sync_parent_date_field": sync_field,
				"sync_direction": direction,
				"trigger_field": trigger_field,
				"trigger_condition": trigger_condition,
				"trigger_value": trigger_value,
				"trigger_action": trigger_action,
			}

		def _is_date_based(cfg):
			ut = (cfg.get("update_trigger_type") or "").strip()
			if ut == "Date Based":
				return True
			if ut == "Parent date field sync":
				return True
			return False

		def _is_field_based(cfg):
			ut = (cfg.get("update_trigger_type") or "").strip()
			if ut == "Field Based":
				return True
			if ut == "Parent field condition":
				return True
			return False

		# 1) Date Based: parent date field -> milestone actual_end and status
		# Use doc (just-saved) for parent date so we see the update; fallback to parent if needed
		for row in milestones:
			cfg = _get_row_config(row)
			if not _is_date_based(cfg) or not cfg.get("sync_parent_date_field"):
				continue
			direction = (cfg.get("sync_direction") or "").strip()
			if direction not in ("Both", "Parent to Milestone only", ""):
				continue
			fieldname = cfg["sync_parent_date_field"].strip()
			if not fieldname:
				continue
			# Parent date: doc (just-saved) -> parent -> DB, so we always see the latest
			val = doc.get(fieldname) if hasattr(doc, fieldname) else None
			if val is None:
				val = parent.get(fieldname) if hasattr(parent, fieldname) else None
			if val is None:
				val = frappe.db.get_value(parent.doctype, parent.name, fieldname)
			if val is None:
				continue
			current = row.actual_end
			if not _dates_equal(current, val):
				row.actual_end = val
				row.status = "Completed"
				changed = True

		# 2) Date Based: milestone actual_end -> parent date field
		for row in milestones:
			cfg = _get_row_config(row)
			if not _is_date_based(cfg) or not cfg.get("sync_parent_date_field"):
				continue
			direction = (cfg.get("sync_direction") or "").strip()
			if direction not in ("Both", "Milestone to Parent only", ""):
				continue
			fieldname = cfg["sync_parent_date_field"].strip()
			if not fieldname or not hasattr(parent, fieldname):
				continue
			val = row.actual_end
			if val is None:
				continue
			current_parent = parent.get(fieldname)
			if not _dates_equal(current_parent, val):
				parent.set(fieldname, val)
				changed = True

		# 3) Field Based: when condition is met, set milestone actual_end and status (Completed)
		for row in milestones:
			cfg = _get_row_config(row)
			if not _is_field_based(cfg):
				continue
			fieldname = (cfg.get("trigger_field") or "").strip()
			if not fieldname or not hasattr(parent, fieldname):
				continue
			condition = (cfg.get("trigger_condition") or "").strip()
			trigger_value = (cfg.get("trigger_value") or "").strip()
			action = (cfg.get("trigger_action") or "").strip()
			if not _trigger_condition_met(parent.get(fieldname), condition, trigger_value):
				continue
			if row.status == "Completed":
				continue
			# Update actual_end and status (update triggers always set both)
			if action == "Set actual_end from field":
				val = parent.get(fieldname)
				if val is not None:
					row.actual_end = val
			else:
				row.actual_end = row.actual_end or now_datetime()
			row.status = "Completed"
			changed = True

		# 4) Always: set status from actual_start/actual_end (Started/Completed/Delayed/Planned)
		for row in milestones:
			old_status = (row.status or "").strip()
			update_milestone_status(row)
			if (row.status or "").strip() != old_status:
				changed = True

		if changed:
			parent.flags.ignore_validate = True
			parent.flags.ignore_documents_milestones_populate = True
			parent.save()
	finally:
		frappe.flags.in_milestone_sync = False


def _trigger_condition_met(field_value, condition, trigger_value):
	"""Return True if field_value meets the trigger condition."""
	if condition == "Is set":
		return field_value is not None and field_value != ""
	if condition == "Not empty":
		return field_value is not None and str(field_value).strip() != ""
	if condition == "Is empty":
		return field_value is None or field_value == "" or (hasattr(field_value, "strip") and field_value.strip() == "")
	if condition == "Equals":
		return field_value is not None and str(field_value).strip() == trigger_value
	if condition == "In list":
		if not trigger_value:
			return False
		allowed = [v.strip() for v in trigger_value.split(",") if v.strip()]
		return field_value is not None and str(field_value).strip() in allowed
	return False
