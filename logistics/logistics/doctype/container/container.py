# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from logistics.logistics.deposit_processing.container_deposit_gl import (
	resolve_default_job_number_for_container,
	sync_deposit_header_from_child_rows,
)
from logistics.utils.container_validation import (
	normalize_container_number,
	validate_container_number,
	get_strict_validation_setting,
)


def _unique_container_doc_name(base):
	name = base
	suffix = 2
	while frappe.db.exists("Container", name):
		name = "{0}-{1}".format(base, suffix)
		suffix += 1
	return name


class Container(Document):
	def autoname(self):
		self.container_number = normalize_container_number(self.container_number or "")
		if not self.container_number:
			frappe.throw(_("Container Number is required before naming."), title=_("Missing fields"))
		if self.master_bill:
			base = "{0}-{1}".format(self.master_bill, self.container_number)
			if len(base) > 140:
				h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
				base = "{0}-{1}".format(self.master_bill, h)
			self.name = _unique_container_doc_name(base)
		else:
			self.name = self.container_number

	def validate(self):
		self.container_number = normalize_container_number(self.container_number or "")
		self._validate_container_number_format()
		self.update_current_location_name()
		if self.is_active:
			self._validate_active_mbl_assignment()
		self._stamp_refund_readiness_waivers()

	def _validate_container_number_format(self):
		if not self.container_number:
			return
		try:
			bypass = frappe.get_request_header("X-Container-Validation-Bypass") == "1"
		except RuntimeError:
			bypass = False
		strict = get_strict_validation_setting()
		valid, err = validate_container_number(
			self.container_number,
			strict=strict,
			allow_bypass=bypass,
		)
		if not valid:
			frappe.throw(err, title=_("Invalid Container Number"))

	def before_save(self):
		self.container_number = normalize_container_number(self.container_number or "")
		if not self.is_new() and self.has_value_changed("is_active"):
			if not self.is_active and not self.assignment_inactive_date:
				self.assignment_inactive_date = getdate()
			elif self.is_active:
				self.assignment_inactive_date = None
		self._sync_deposit_lines_defaults()
		sync_deposit_header_from_child_rows(self)

	def _sync_deposit_lines_defaults(self):
		if self.is_new():
			self.current_job_number = None
			return
		jn = resolve_default_job_number_for_container(self.name)
		self.current_job_number = jn
		for row in self.get("deposits") or []:
			if not row.get("job_number") and jn:
				row.job_number = jn
			if not row.get("company") and row.get("job_number"):
				row.company = frappe.db.get_value("Job Number", row.job_number, "company")

	def _stamp_refund_readiness_waivers(self):
		for line in self.get("refund_readiness") or []:
			if line.status == "Waived" and not line.get("waived_by"):
				line.waived_by = frappe.session.user

	def _validate_active_mbl_assignment(self):
		rows = frappe.get_all(
			"Container",
			filters={"container_number": self.container_number, "is_active": 1},
			fields=["name", "master_bill"],
			limit=5,
		)
		conflicts = [r for r in rows if r.name != self.name]
		if not conflicts:
			return
		other = conflicts[0]
		if (other.master_bill or "") == (self.master_bill or ""):
			frappe.throw(
				_("An active container record already exists for this Master Bill and container number ({0}).").format(
					other.name
				),
				title=_("Duplicate active assignment"),
			)
		frappe.throw(
			_("Container {0} is already active on another Master Bill record ({1}: {2}).").format(
				self.container_number,
				other.master_bill or _("(no Master Bill)"),
				other.name,
			),
			title=_("Container already active"),
		)

	def update_current_location_name(self):
		if self.current_location_type and self.current_location:
			try:
				name = frappe.db.get_value(
					self.current_location_type,
					self.current_location,
					"name",
				)
				if name:
					self.current_location_name = name
			except Exception:
				pass

	def get_linked_shipments_html(self):
		"""Virtual HTML for linked Sea Shipments."""
		links = frappe.db.sql(
			"""
			SELECT DISTINCT sfc.parent as shipment
			FROM `tabSea Freight Containers` sfc
			WHERE sfc.container = %s AND sfc.parenttype = 'Sea Shipment'
		""",
			(self.name,),
			as_dict=True,
		)
		if not links:
			return "<p class='text-muted'>No linked shipments</p>"
		items = ["<a href='/app/sea-shipment/{0}'>{0}</a>".format(r.shipment) for r in links]
		return "<br>".join(items)

	def get_linked_transport_jobs_html(self):
		"""Virtual HTML for linked Transport Jobs."""
		links = frappe.db.sql(
			"""
			SELECT name FROM `tabTransport Job` WHERE container = %s
		""",
			(self.name,),
			as_dict=True,
		)
		if not links:
			return "<p class='text-muted'>No linked transport jobs</p>"
		items = ["<a href='/app/transport-job/{0}'>{0}</a>".format(r.name) for r in links]
		return "<br>".join(items)


@frappe.whitelist()
def get_linked_shipments_html(container):
	if not container or container.startswith("new-") or not frappe.db.exists("Container", container):
		return "<p class='text-muted'>No linked shipments</p>"
	doc = frappe.get_doc("Container", container)
	return doc.get_linked_shipments_html()


@frappe.whitelist()
def get_linked_transport_jobs_html(container):
	if not container or container.startswith("new-") or not frappe.db.exists("Container", container):
		return "<p class='text-muted'>No linked transport jobs</p>"
	doc = frappe.get_doc("Container", container)
	return doc.get_linked_transport_jobs_html()


def calculate_penalties_for_container(container_name):
	"""
	Calculate demurrage/detention penalties for a container using linked Sea Shipment milestones
	and this container's free time (Sea Freight default when unset).
	Returns dict with demurrage_days, detention_days, estimated_penalty_amount.
	"""
	from frappe.utils import now_datetime, getdate
	from logistics.sea_freight.penalty_utils import compute_penalty_for_single_container

	container = frappe.get_doc("Container", container_name)
	if getattr(container, "penalty_manual_override", 0):
		return {
			"demurrage_days": flt(getattr(container, "demurrage_days", 0)),
			"detention_days": flt(getattr(container, "detention_days", 0)),
			"estimated_penalty_amount": flt(getattr(container, "estimated_penalty_amount", 0)),
			"skipped": True,
		}
	settings = frappe.get_single("Sea Freight Settings")

	shipment = frappe.db.sql(
		"""
		SELECT sfc.parent FROM `tabSea Freight Containers` sfc
		WHERE sfc.container = %s AND sfc.parenttype = 'Sea Shipment'
		ORDER BY sfc.modified DESC LIMIT 1
	""",
		(container_name,),
		as_dict=True,
	)

	demurrage_days = 0
	detention_days = 0
	estimated_amount = 0

	if shipment:
		ship_doc = frappe.get_doc("Sea Shipment", shipment[0].parent)
		today = getdate(now_datetime())
		out = compute_penalty_for_single_container(container, ship_doc, settings, today)
		demurrage_days = out["demurrage_days"]
		detention_days = out["detention_days"]
		estimated_amount = out["estimated_penalty_amount"]
		container.has_penalties = out["has_penalties"]
	else:
		container.has_penalties = 0

	container.demurrage_days = demurrage_days
	container.detention_days = detention_days
	container.estimated_penalty_amount = estimated_amount
	container.last_penalty_check = now_datetime()
	container.save(ignore_permissions=True)

	return {
		"demurrage_days": demurrage_days,
		"detention_days": detention_days,
		"estimated_penalty_amount": estimated_amount,
	}
