# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Special Project Service: top-level service leg owned by a Special Project."""

from __future__ import annotations

import frappe
from frappe.model.document import Document

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


_HISTORICAL_LINK_FIELDS = frozenset({"job_no", "order_no", "parent_booking_name"})


class SpecialProjectService(Document):
	def get_invalid_links(self, is_submittable=False):
		saved_parent = self.parent_booking_name
		saved_job_no = self.job_no
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		if saved_parent:
			self.parent_booking_name = saved_parent
		if saved_job_no:
			self.job_no = saved_job_no
		skip = _HISTORICAL_LINK_FIELDS | {"parent_booking_name"}
		invalid_links = [c for c in invalid_links if c[0] not in skip]
		cancelled_links = [c for c in cancelled_links if c[0] not in _HISTORICAL_LINK_FIELDS]
		return invalid_links, cancelled_links

	def validate(self):
		self._sync_job_type_from_service_type()

	def _sync_job_type_from_service_type(self):
		st = (self.service_type or "").strip()
		if not st:
			return
		expected = default_job_type_for_internal_job_service_type(st)
		if not expected:
			return
		jt = (self.job_type or "").strip()
		if st == "Warehousing":
			if jt in ("Inbound Order", "Release Order", "Transfer Order"):
				return
			self.job_type = "Inbound Order"
			return
		self.job_type = expected


def get_special_project_services_for_special_project(special_project_name: str) -> list[Document]:
	"""Backward-compatible alias used by Special Project virtual view builders."""
	from logistics.special_projects.special_project_service_persistence import (
		get_special_project_services_for_special_project as _load,
	)

	return _load(special_project_name)
