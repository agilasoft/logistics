# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shared lifecycle stage master for Exhibits and Special Projects."""

from __future__ import annotations

import frappe
from frappe import _

FOR_EXHIBITS = "for_exhibits"
FOR_SPECIAL_PROJECT = "for_special_project"

LIFECYCLE_STAGES_FALLBACK = ["Pre-Show", "Logistics", "On-Site", "Post-Show", "Closed"]

# Used only when Lifecycle Stage has no icon/color set (or DocType missing fields).
_STAGE_APPEARANCE_FALLBACK = {
	"Pre-Show": {"icon": "calendar", "color": "#14b8a6"},
	"Pre-Shipment": {"icon": "package", "color": "#14b8a6"},
	"Logistics": {"icon": "truck", "color": "#ec4899"},
	"Port operation": {"icon": "ship", "color": "#3b82f6"},
	"Delivery to site": {"icon": "truck", "color": "#8b5cf6"},
	"On-Site": {"icon": "building-2", "color": "#f59e0b"},
	"Post-Show": {"icon": "flag", "color": "#a855f7"},
	"Closed": {"icon": "lock", "color": "#64748b"},
	"Sourcing and Procurement": {"icon": "shopping-cart", "color": "#10b981"},
	"Unassigned": {"icon": "help-circle", "color": "#64748b"},
}
_DEFAULT_STAGE_COLOR = "#94a3b8"
_DEFAULT_STAGE_ICON = "circle"


def get_lifecycle_stages(module_filter: str = FOR_EXHIBITS) -> list[str]:
	"""Ordered stage names for a module (for_exhibits or for_special_project)."""
	if not frappe.db.exists("DocType", "Lifecycle Stage"):
		return list(LIFECYCLE_STAGES_FALLBACK)
	filters = {module_filter: 1}
	rows = frappe.get_all(
		"Lifecycle Stage",
		filters=filters,
		fields=["name"],
		order_by="sort_order asc, name asc",
	)
	return [r.name for r in rows] if rows else list(LIFECYCLE_STAGES_FALLBACK)


def get_open_lifecycle_stages(module_filter: str = FOR_EXHIBITS) -> list[str]:
	"""Non-closed stages for orders and job template rows."""
	if not frappe.db.exists("DocType", "Lifecycle Stage"):
		return LIFECYCLE_STAGES_FALLBACK[:-1]
	rows = frappe.get_all(
		"Lifecycle Stage",
		filters={module_filter: 1, "is_closed": 0},
		fields=["name"],
		order_by="sort_order asc, name asc",
	)
	return [r.name for r in rows] if rows else LIFECYCLE_STAGES_FALLBACK[:-1]


def resolve_default_lifecycle_stage(
	module_filter: str = FOR_EXHIBITS,
	preferred: str = "Pre-Show",
) -> str | None:
	"""Return a Lifecycle Stage name that is guaranteed to exist for ``module_filter``.

	Tries ``preferred`` first (when it exists and is enabled for the module),
	then falls back to the first stage flagged for the module by ``sort_order``.
	Returns ``None`` when the ``Lifecycle Stage`` master is empty so callers can
	safely insert without tripping LinkValidationError on the default value.
	"""
	if not frappe.db.exists("DocType", "Lifecycle Stage"):
		return preferred or None

	if preferred:
		preferred_row = frappe.db.get_value(
			"Lifecycle Stage",
			preferred,
			["name", module_filter],
			as_dict=True,
		)
		# Only accept preferred when it is flagged for this module.
		if preferred_row and preferred_row.get(module_filter):
			return preferred_row["name"]

	return frappe.db.get_value(
		"Lifecycle Stage",
		{module_filter: 1},
		"name",
		order_by="sort_order asc, name asc",
	)


def render_lifecycle_icon_html(icon: str | None) -> str:
	"""Render a Lucide icon name (Lifecycle Stage / Logistics Milestone Icon field)."""
	from logistics.document_management.milestone_html import _render_icon_html

	return _render_icon_html(icon or _DEFAULT_STAGE_ICON)


def get_lifecycle_stage_appearance(stage: str | None) -> dict[str, str]:
	"""Return ``{icon, color}`` for a stage from the Lifecycle Stage master.

	Falls back to built-in defaults when the master row or fields are empty.
	"""
	stage = (stage or "").strip()
	fallback = _STAGE_APPEARANCE_FALLBACK.get(stage) or {
		"icon": _DEFAULT_STAGE_ICON,
		"color": _DEFAULT_STAGE_COLOR,
	}
	icon = fallback["icon"]
	color = fallback["color"]
	if not stage or not frappe.db.exists("DocType", "Lifecycle Stage"):
		return {"icon": icon, "color": color}
	meta = frappe.get_meta("Lifecycle Stage")
	fields = ["name"]
	if meta.has_field("icon"):
		fields.append("icon")
	if meta.has_field("color"):
		fields.append("color")
	row = frappe.db.get_value("Lifecycle Stage", stage, fields, as_dict=True)
	if not row:
		return {"icon": icon, "color": color}
	master_icon = (row.get("icon") or "").strip()
	master_color = (row.get("color") or "").strip()
	return {
		"icon": master_icon or icon,
		"color": master_color or color,
	}


def _stage_index(stage: str, stages: list[str]) -> int | None:
	stage = (stage or "").strip()
	if not stage:
		return None
	try:
		return stages.index(stage)
	except ValueError:
		return None


def validate_internal_job_activity_codes(
	doc, *, module_filter: str, field_name: str = "lifecycle_jobs"
):
	"""Ensure linked Activity Code rows match parent module and lifecycle stage.

	``field_name`` is the child table fieldname on the parent doctype (defaults
	to ``lifecycle_jobs`` for Special Project/Exhibit).
	"""
	if not frappe.db.exists("DocType", "Activity Code"):
		return
	for row in doc.get(field_name) or []:
		code = (row.activity_code or "").strip()
		if not code:
			continue
		activity = frappe.db.get_value(
			"Activity Code",
			code,
			["activity_name", "lifecycle_stage", "for_exhibits", "for_special_project"],
			as_dict=True,
		)
		if not activity:
			frappe.throw(_("Activity Code {0} does not exist.").format(code))
		if not activity.get(module_filter):
			module_label = _("MICE") if module_filter == FOR_EXHIBITS else _("Special Project")
			frappe.throw(
				_("Activity {0} is not enabled for {1}.").format(
					activity.activity_name or code, module_label
				)
			)
		stage = (row.lifecycle_stage or "").strip()
		if stage and activity.lifecycle_stage and activity.lifecycle_stage != stage:
			frappe.throw(
				_("Activity {0} belongs to lifecycle stage {1}, not {2}.").format(
					activity.activity_name or code, activity.lifecycle_stage, stage
				)
			)


def validate_lifecycle_stage_advance(
	doc,
	*,
	settings_doctype: str,
	module_filter: str,
	default_stage: str = "Pre-Show",
	field_name: str = "lifecycle_jobs",
):
	"""Block forward lifecycle_stage moves when strict mode is on and checklist jobs are incomplete."""
	if not doc.has_value_changed("lifecycle_stage"):
		return
	old = doc.get_doc_before_save()
	if not old:
		return
	prev_stage = (old.lifecycle_stage or default_stage).strip()
	new_stage = (doc.lifecycle_stage or default_stage).strip()
	if prev_stage == new_stage:
		return
	stages = get_lifecycle_stages(module_filter)
	prev_idx = _stage_index(prev_stage, stages)
	new_idx = _stage_index(new_stage, stages)
	if prev_idx is None or new_idx is None:
		return
	if new_idx <= prev_idx:
		return
	if not frappe.db.get_single_value(settings_doctype, "strict_lifecycle_mode"):
		return
	incomplete = [
		row.activity_name or row.activity_code
		for row in doc.get(field_name) or []
		if (row.activity_code or "").strip()
		and (row.lifecycle_stage or "") == prev_stage
		and (row.lifecycle_activity_status or "Not Started") not in ("Completed", "N/A")
	]
	if incomplete:
		frappe.throw(
			_("Cannot advance from {0} until these activities are Completed or N/A: {1}").format(
				prev_stage, ", ".join(incomplete[:5])
			)
			+ ("..." if len(incomplete) > 5 else "")
		)
