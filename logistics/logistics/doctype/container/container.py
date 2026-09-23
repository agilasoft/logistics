# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import uuid

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from logistics.logistics.deposit_processing.container_deposit_gl import (
	resolve_default_job_number_for_container,
)
from logistics.logistics.deposit_processing.container_gl_service import (
	get_charges_gl_html as build_charges_gl_html,
	get_deposit_postings_data as build_deposit_postings_data,
	get_deposits_gl_html as build_deposits_gl_html,
	sync_deposit_header_from_gl,
)
from logistics.utils.container_validation import (
	normalize_container_number,
	validate_container_number,
	get_strict_validation_setting,
)

ALLOWED_CONTAINER_LOCATION_TYPES = frozenset({"UNLOCO", "Transport Zone"})


def normalize_container_location_pair(location_type, location):
	"""Normalize legacy Container location type/location values for Dynamic Link."""
	location_type = (location_type or "").strip()
	location = (location or "").strip()

	if not location_type and not location:
		return "", ""

	if location_type in ALLOWED_CONTAINER_LOCATION_TYPES:
		return location_type, location

	if location and frappe.db.exists("UNLOCO", location):
		return "UNLOCO", location

	if location and frappe.db.exists("Transport Zone", location):
		return "Transport Zone", location

	if location_type and not location:
		if frappe.db.exists("UNLOCO", location_type):
			return "UNLOCO", location_type
		if frappe.db.exists("Transport Zone", location_type):
			return "Transport Zone", location_type

	if location_type and location_type not in ALLOWED_CONTAINER_LOCATION_TYPES:
		return "", location

	return location_type, location


def resolve_container_location_display_name(location_type, location):
	"""Return a human-readable location label for UNLOCO / Transport Zone."""
	location_type = (location_type or "").strip()
	location = (location or "").strip()
	if not location_type or not location:
		return ""
	if location_type not in ALLOWED_CONTAINER_LOCATION_TYPES:
		return ""
	display_field = "location_name" if location_type == "UNLOCO" else "zone_name"
	display = frappe.db.get_value(location_type, location, display_field)
	return ((display or location) or "").strip()


class Container(Document):
	def autoname(self):
		self.container_number = normalize_container_number(self.container_number or "")
		if not self.container_number:
			frappe.throw(_("Container Number is required before naming."), title=_("Missing fields"))
		self.name = str(uuid.uuid4())

	def validate(self):
		self.container_number = normalize_container_number(self.container_number or "")
		self._validate_container_number_format()
		self._validate_unique_container_number_master_bill()
		self._validate_container_location_fields()
		self.update_current_location_name()
		if self.is_active:
			self._validate_active_mbl_assignment()
		self._stamp_refund_readiness_waivers()

	def _validate_unique_container_number_master_bill(self):
		if not self.container_number:
			return
		mbl = self.master_bill or ""
		existing = frappe.db.sql(
			"""
			SELECT name FROM `tabContainer`
			WHERE container_number = %s
				AND IFNULL(master_bill, '') = %s
				AND name != %s
			LIMIT 1
			""",
			(self.container_number, mbl, self.name or ""),
		)
		if existing:
			frappe.throw(
				_("A container already exists for this equipment number and Master Bill ({0}).").format(
					existing[0][0]
				),
				title=_("Duplicate container"),
			)

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
		self._sync_job_number_default()
		sync_deposit_header_from_gl(self)

	def _sync_job_number_default(self):
		if self.is_new():
			self.current_job_number = None
			return
		self.current_job_number = resolve_default_job_number_for_container(self.name)

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

	def _validate_container_location_fields(self):
		for type_field, label in (
			("current_location_type", _("Location Type")),
			("return_location_type", _("Return Location Type")),
		):
			loc_type = (self.get(type_field) or "").strip()
			if loc_type and loc_type not in ALLOWED_CONTAINER_LOCATION_TYPES:
				frappe.throw(
					_("{0} must be UNLOCO or Transport Zone.").format(label),
					title=_("Invalid Location Type"),
				)

	def update_current_location_name(self):
		display = resolve_container_location_display_name(
			self.current_location_type,
			self.current_location,
		)
		self.current_location_name = display or None

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


@frappe.whitelist()
def get_deposits_gl_html(container):
	return build_deposits_gl_html(container)


@frappe.whitelist()
def get_deposit_postings_data(container):
	return build_deposit_postings_data(container)


@frappe.whitelist()
def get_charges_gl_html(container):
	return build_charges_gl_html(container)


@frappe.whitelist()
def validate_container_number_for_form(container_number=None):
	"""
	ISO 6346 check for the Container form (live feedback + client validate hook).
	Mirrors Container._validate_container_number_format (same strict flag and bypass header).
	"""
	container_number = normalize_container_number(container_number or "")
	if not container_number:
		return {"valid": True, "message": ""}
	try:
		bypass = frappe.get_request_header("X-Container-Validation-Bypass") == "1"
	except RuntimeError:
		bypass = False
	strict = get_strict_validation_setting()
	valid, err = validate_container_number(
		container_number,
		strict=strict,
		allow_bypass=bypass,
	)
	out = {"valid": bool(valid), "message": ""}
	if not valid and err:
		out["message"] = str(err)
	return out


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
	from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings

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
		settings = SeaFreightSettings.get_settings(ship_doc.company) or SeaFreightSettings.get_settings(
			frappe.defaults.get_user_default("Company")
		)
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
