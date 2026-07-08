# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


class InternalJob(Document):
	"""Top-level internal job record carrying service parameters for one leg of a booking.

	Owned by a parent booking via ``parent_booking_type`` + ``parent_booking_name`` back-links.
	The booking exposes its set of Internal Jobs through an ``internal_job_details`` child table whose
	rows are thin pointers to records of this doctype.
	"""

	def get_invalid_links(self, is_submittable=False):
		# Back-links may not exist yet when the parent booking is still inserting or the
		# satellite job document has not been created from the Internal Job Detail row.
		# ``super()`` clears unresolved Dynamic Link values; preserve them for these fields.
		saved_parent = self.parent_booking_name
		saved_job_no = self.job_no
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		if saved_parent:
			self.parent_booking_name = saved_parent
		if saved_job_no:
			self.job_no = saved_job_no
		skip = ("job_no", "parent_booking_name")
		invalid_links = [c for c in invalid_links if c[0] not in skip]
		cancelled_links = [c for c in cancelled_links if c[0] not in skip]
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
			jn = (getattr(self, "job_no", None) or "").strip()
			if jt in ("Inbound Order", "Release Order", "Transfer Order") and jn:
				return
			self.job_type = "VAS Order"
			return
		self.job_type = expected


def get_internal_jobs_for_booking(parent_booking_type: str, parent_booking_name: str) -> list[Document]:
	"""All Internal Job documents linked to the given parent booking, ordered by creation."""
	if not parent_booking_type or not parent_booking_name:
		return []
	names = frappe.get_all(
		"Internal Job",
		filters={
			"parent_booking_type": parent_booking_type,
			"parent_booking_name": parent_booking_name,
		},
		pluck="name",
		order_by="creation asc",
	)
	return [frappe.get_doc("Internal Job", n) for n in names]
