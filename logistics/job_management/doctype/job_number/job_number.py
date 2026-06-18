# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# When a Job Number's job_type is one of these operational doctypes, the source doc
# carries a Link to its originating "Order/Booking" doc. The Docket's
# `internal_jobs` table is keyed by that order/booking doctype + name, so we use
# this map to resolve "which Docket references this Job Number?".
JOB_TYPE_TO_BOOKING = {
	"Sea Shipment": ("Sea Booking", "sea_booking"),
	"Air Shipment": ("Air Booking", "air_booking"),
	"Transport Job": ("Transport Order", "transport_order"),
	"Declaration": ("Declaration Order", "declaration_order"),
}


class JobNumber(Document):
	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		cancelled_links = [c for c in cancelled_links if c[0] != "job_no"]
		return invalid_links, cancelled_links

	def validate(self):
		self._sync_project_and_docket()

	def _sync_project_and_docket(self):
		"""Auto-populate ``project`` and ``docket`` from the source job.

		Resolution rules:

		* If ``job_type`` is ``Docket`` and ``job_no`` is set, ``docket`` mirrors
		  ``job_no`` and ``project`` is copied from the Docket (always overwritten
		  so the Job Number stays in sync with the source).
		* Otherwise, if the source doc has a ``project`` field, mirror its value
		  onto this Job Number (always overwritten). The ``docket`` field is only
		  set from the source when ours is blank.
		* For operational jobs that originate from an order/booking, we also walk
		  the Docket ``internal_jobs`` table to find a Docket that references
		  this job (directly, via its booking, or via its reference order in the
		  case of Warehouse Job).
		* When a Docket is found and ``project`` is still blank, we pull the
		  project from the Docket as a fallback.
		"""
		if not self.job_type or not self.job_no:
			return
		if not frappe.db.exists("DocType", self.job_type):
			return
		if not frappe.db.exists(self.job_type, self.job_no):
			return

		if self.job_type == "Docket":
			self.docket = self.job_no
			dp = frappe.db.get_value("Docket", self.job_no, "project")
			if dp:
				self.project = dp
			return

		meta = frappe.get_meta(self.job_type)

		if meta.has_field("project"):
			src_project = frappe.db.get_value(self.job_type, self.job_no, "project")
			if src_project:
				self.project = src_project

		if not self.docket and meta.has_field("docket"):
			src_docket = frappe.db.get_value(self.job_type, self.job_no, "docket")
			if src_docket:
				self.docket = src_docket

		if not self.docket:
			docket = self._find_docket_via_internal_jobs(meta)
			if docket:
				self.docket = docket

		if self.docket and not self.project:
			dp = frappe.db.get_value("Docket", self.docket, "project")
			if dp:
				self.project = dp

	def _find_docket_via_internal_jobs(self, meta):
		"""Return the name of a Docket whose ``internal_jobs`` table references this job, or None."""
		candidates: list[tuple[str, str]] = [(self.job_type, self.job_no)]

		booking = JOB_TYPE_TO_BOOKING.get(self.job_type)
		if booking:
			booking_dt, booking_field = booking
			if meta.has_field(booking_field):
				bk_name = frappe.db.get_value(self.job_type, self.job_no, booking_field)
				if bk_name:
					candidates.append((booking_dt, bk_name))

		# Warehouse Job uses a Dynamic Link (``reference_order_type`` + ``reference_order``).
		if self.job_type == "Warehouse Job" and meta.has_field("reference_order"):
			ref = frappe.db.get_value(
				"Warehouse Job",
				self.job_no,
				["reference_order_type", "reference_order"],
				as_dict=True,
			)
			if ref and ref.get("reference_order_type") and ref.get("reference_order"):
				candidates.append((ref["reference_order_type"], ref["reference_order"]))

		for jt, jn in candidates:
			docket = frappe.db.get_value(
				"Internal Job Detail",
				{
					"parenttype": "Docket",
					"parentfield": "internal_jobs",
					"job_type": jt,
					"job_no": jn,
				},
				"parent",
			)
			if docket:
				return docket
		return None
