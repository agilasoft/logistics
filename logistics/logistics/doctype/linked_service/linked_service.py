# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


class LinkedService(Document):
	"""Top-level linked service record carrying service parameters for one subsidiary leg.

	Owned by a parent booking via ``parent_booking_type`` + ``parent_booking_name`` back-links.
	The parent exposes linked services through a ``linked_services`` / ``internal_job_details``
	child table whose rows are thin pointers to records of this doctype.
	"""

	def get_invalid_links(self, is_submittable=False):
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
		self._validate_transport_template_compatibility()

	def _validate_transport_template_compatibility(self):
		if (self.service_type or "").strip() != "Transport":
			return
		if not getattr(self, "transport_template", None):
			return

		from logistics.transport.doctype.transport_template.transport_template import (
			validate_doc_transport_template,
		)

		validate_doc_transport_template(self, context=_("Linked Service"))

	def _sync_job_type_from_service_type(self):
		st = (self.service_type or "").strip()
		if not st:
			return
		expected = default_job_type_for_internal_job_service_type(st)
		if not expected:
			return
		jt = (self.job_type or "").strip()
		if st == "Warehousing":
			# Linked warehousing is cross-dock / in-transit VAS only (not storage orders).
			jn = (getattr(self, "job_no", None) or "").strip()
			if jt in ("Inbound Order", "Release Order", "Transfer Order") and jn:
				return
			self.job_type = "VAS Order"
			return
		self.job_type = expected


def get_linked_services_for_booking(parent_booking_type: str, parent_booking_name: str) -> list[Document]:
	"""All Linked Service documents linked to the given parent booking, ordered by creation."""
	if not parent_booking_type or not parent_booking_name:
		return []
	names = frappe.get_all(
		"Linked Service",
		filters={
			"parent_booking_type": parent_booking_type,
			"parent_booking_name": parent_booking_name,
		},
		pluck="name",
		order_by="creation asc",
	)
	return [frappe.get_doc("Linked Service", n) for n in names]


def get_linked_services_for_sales_quote(sales_quote_name: str) -> list[Document]:
	"""Linked Service rows parented directly to a Sales Quote."""
	if not sales_quote_name:
		return []
	names = frappe.get_all(
		"Linked Service",
		filters={
			"parent_booking_type": "Sales Quote",
			"parent_booking_name": sales_quote_name,
		},
		pluck="name",
		order_by="creation asc",
	)
	return [frappe.get_doc("Linked Service", n) for n in names]


def get_linked_services_for_change_request(change_request_name: str) -> list[Document]:
	"""Linked Service rows parented directly to a Change Request."""
	if not change_request_name:
		return []
	names = frappe.get_all(
		"Linked Service",
		filters={
			"parent_booking_type": "Change Request",
			"parent_booking_name": change_request_name,
		},
		pluck="name",
		order_by="creation asc",
	)
	return [frappe.get_doc("Linked Service", n) for n in names]


# Backward-compatible aliases
InternalJob = LinkedService
get_internal_jobs_for_booking = get_linked_services_for_booking
