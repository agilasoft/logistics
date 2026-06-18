# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Template controller.

A Lifecycle Template is a reusable set of activities (each tagged with a Lifecycle Stage,
an Activity Code, and a Service Type) that can be applied to a Special Project or an
Exhibit to seed its ``lifecycle_jobs`` child table in one click.

Templates are scoped to their applicable parent doctype(s) via the ``for_special_project``
and ``for_exhibits`` checkboxes; the apply utility refuses to seed a template into a parent
that the template is not marked for.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class LifecycleTemplate(Document):
	def validate(self) -> None:
		if not (self.get("for_special_project") or self.get("for_exhibits")):
			frappe.throw(
				_("Tick at least one of: For Special Project, For Exhibits."),
				title=_("Lifecycle Template"),
			)
		if not (self.get("activities") or []):
			frappe.throw(
				_("Add at least one activity row."),
				title=_("Lifecycle Template"),
			)
		self._validate_activity_rows()

	def _validate_activity_rows(self) -> None:
		for i, row in enumerate(self.get("activities") or [], start=1):
			stage = (row.get("lifecycle_stage") or "").strip()
			service = (row.get("service_type") or "").strip()
			if not stage:
				frappe.throw(
					_("Activity row {0}: Lifecycle Stage is required.").format(i),
					title=_("Lifecycle Template"),
				)
			if not service:
				frappe.throw(
					_("Activity row {0}: Service Type is required.").format(i),
					title=_("Lifecycle Template"),
				)
			activity = (row.get("activity_code") or "").strip()
			if activity:
				ac_stage = frappe.db.get_value("Activity Code", activity, "lifecycle_stage")
				if ac_stage and ac_stage != stage:
					frappe.throw(
						_(
							"Activity row {0}: Activity Code {1} belongs to stage {2}, not {3}."
						).format(i, activity, ac_stage, stage),
						title=_("Lifecycle Template"),
					)
