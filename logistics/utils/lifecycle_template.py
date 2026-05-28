# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Apply a Lifecycle Template's activities onto the target parent's ``lifecycle_jobs`` child.

Shared by Special Project and Exhibit. The whitelisted entry point
``apply_lifecycle_template`` is invoked from each parent's form via a custom button.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint


SUPPORTED_PARENT_DOCTYPES: tuple[str, ...] = ("Special Project", "Exhibit")

_APPLICABILITY_FLAG_BY_PARENT: dict[str, str] = {
	"Special Project": "for_special_project",
	"Exhibit": "for_exhibits",
}

_STAGE_FLAG_BY_PARENT: dict[str, str] = {
	"Special Project": "for_special_project",
	"Exhibit": "for_exhibits",
}

_SEEDED_LIFECYCLE_JOB_FIELDS: tuple[str, ...] = (
	"lifecycle_stage",
	"activity_code",
	"activity_name",
	"service_type",
	"job_description",
	"transport_template",
	"vehicle_type",
	"load_type",
	"direction",
	"air_house_type",
	"sea_house_type",
)


def _norm(value: Any) -> str:
	return (value or "").strip()


def _stage_is_applicable(stage_name: str, parent_doctype: str) -> bool:
	flag = _STAGE_FLAG_BY_PARENT.get(parent_doctype)
	if not flag or not stage_name:
		return False
	return bool(frappe.db.get_value("Lifecycle Stage", stage_name, flag))


@frappe.whitelist()
def apply_lifecycle_template(
	parent_doctype: str,
	parent_name: str,
	template: str,
	replace_existing: int | str | None = 0,
) -> dict[str, Any]:
	"""Seed ``lifecycle_jobs`` rows from a Lifecycle Template's activities.

	Returns ``{"added": N, "skipped": M, "removed": K, "kept": L}``.

	Rules:
	- ``parent_doctype`` must be one of :data:`SUPPORTED_PARENT_DOCTYPES`.
	- ``template`` must have the matching applicability flag (``for_special_project`` or
	  ``for_exhibits``) set; otherwise we throw.
	- Activities whose ``lifecycle_stage`` is not flagged for the parent type are skipped
	  with a soft msgprint (counted in ``skipped``).
	- When ``replace_existing`` is truthy, existing ``lifecycle_jobs`` rows whose
	  ``job_no`` is blank are removed before appending; rows that already have a booking
	  /order linked (``job_no`` set) are preserved and counted in ``kept``.
	- Seeded rows are always created with blank ``job_type``/``job_no`` and
	  ``lifecycle_activity_status = "Not Started"``.
	"""
	parent_doctype = _norm(parent_doctype)
	parent_name = _norm(parent_name)
	template = _norm(template)
	replace_existing = bool(cint(replace_existing or 0))

	if parent_doctype not in SUPPORTED_PARENT_DOCTYPES:
		frappe.throw(
			_("Lifecycle Templates can only be applied to: {0}.").format(
				", ".join(SUPPORTED_PARENT_DOCTYPES)
			),
			title=_("Lifecycle Template"),
		)
	if not parent_name or not frappe.db.exists(parent_doctype, parent_name):
		frappe.throw(
			_("{0} {1} does not exist.").format(parent_doctype, parent_name),
			title=_("Lifecycle Template"),
		)
	if not template or not frappe.db.exists("Lifecycle Template", template):
		frappe.throw(
			_("Lifecycle Template {0} does not exist.").format(template),
			title=_("Lifecycle Template"),
		)

	tpl_doc = frappe.get_doc("Lifecycle Template", template)
	if not cint(tpl_doc.get("enabled")):
		frappe.throw(
			_("Lifecycle Template {0} is disabled.").format(template),
			title=_("Lifecycle Template"),
		)
	applicability_flag = _APPLICABILITY_FLAG_BY_PARENT[parent_doctype]
	if not cint(tpl_doc.get(applicability_flag)):
		frappe.throw(
			_("Lifecycle Template {0} is not marked for {1}.").format(template, parent_doctype),
			title=_("Lifecycle Template"),
		)

	parent_doc = frappe.get_doc(parent_doctype, parent_name)
	parent_doc.check_permission("write")

	removed = 0
	kept = 0
	if replace_existing:
		new_rows = []
		for row in parent_doc.get("lifecycle_jobs") or []:
			if _norm(row.get("job_no")):
				new_rows.append(row)
				kept += 1
			else:
				removed += 1
		if removed:
			parent_doc.set("lifecycle_jobs", new_rows)

	activities = sorted(
		tpl_doc.get("activities") or [],
		key=lambda r: (cint(r.get("sort_order") or 0), cint(r.get("idx") or 0)),
	)

	skipped_stages: list[str] = []
	added = 0
	for act in activities:
		stage = _norm(act.get("lifecycle_stage"))
		if not _stage_is_applicable(stage, parent_doctype):
			skipped_stages.append(stage or "(blank)")
			continue
		row_dict: dict[str, Any] = {
			"lifecycle_activity_status": "Not Started",
			"job_type": "",
			"job_no": "",
		}
		for fn in _SEEDED_LIFECYCLE_JOB_FIELDS:
			value = act.get(fn)
			if value not in (None, ""):
				row_dict[fn] = value
		parent_doc.append("lifecycle_jobs", row_dict)
		added += 1

	if added == 0 and removed == 0:
		return {
			"added": 0,
			"skipped": len(skipped_stages),
			"removed": 0,
			"kept": kept,
		}

	parent_doc.flags.ignore_validate_update_after_submit = True
	parent_doc.save(ignore_permissions=False)

	if skipped_stages:
		frappe.msgprint(
			_("Skipped {0} activity row(s) whose Lifecycle Stage is not flagged for {1}: {2}").format(
				len(skipped_stages),
				parent_doctype,
				", ".join(sorted(set(skipped_stages))),
			),
			indicator="orange",
			title=_("Lifecycle Template"),
		)

	frappe.msgprint(
		_("Applied template {0}: added {1}, removed {2}, kept {3}.").format(
			template, added, removed, kept
		),
		indicator="green",
		title=_("Lifecycle Template"),
	)

	return {
		"added": added,
		"skipped": len(skipped_stages),
		"removed": removed,
		"kept": kept,
	}
