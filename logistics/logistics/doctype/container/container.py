# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from logistics.utils.container_validation import (
	normalize_container_number,
	validate_container_number,
	get_strict_validation_setting,
)


class Container(Document):
	def validate(self):
		self.validate_container_number()
		self.update_current_location_name()

	def validate_container_number(self):
		if not self.container_number:
			return
		strict = get_strict_validation_setting()
		valid, err = validate_container_number(
			self.container_number,
			strict=strict,
			allow_bypass=frappe.get_request_header("X-Container-Validation-Bypass") == "1"
		)
		if not valid:
			frappe.throw(err, title=_("Invalid Container Number"))

	def update_current_location_name(self):
		if self.current_location_type and self.current_location:
			try:
				name = frappe.db.get_value(
					self.current_location_type,
					self.current_location,
					"name"
				)
				if name:
					self.current_location_name = name
			except Exception:
				pass

	def before_save(self):
		self.container_number = normalize_container_number(self.container_number or "")

	def get_linked_shipments_html(self):
		"""Virtual HTML for linked Sea Shipments."""
		links = frappe.db.sql("""
			SELECT DISTINCT sfc.parent as shipment
			FROM `tabSea Freight Containers` sfc
			WHERE sfc.container = %s AND sfc.parenttype = 'Sea Shipment'
		""", (self.name,), as_dict=True)
		if not links:
			return "<p class='text-muted'>No linked shipments</p>"
		items = ["<a href='/app/sea-shipment/{0}'>{0}</a>".format(r.shipment) for r in links]
		return "<br>".join(items)

	def get_linked_transport_jobs_html(self):
		"""Virtual HTML for linked Transport Jobs."""
		links = frappe.db.sql("""
			SELECT name FROM `tabTransport Job` WHERE container = %s
		""", (self.name,), as_dict=True)
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
	Calculate demurrage/detention penalties for a container.
	Uses linked Sea Shipment milestones and Sea Freight Settings.
	Returns dict with demurrage_days, detention_days, estimated_penalty_amount.
	"""
	from frappe.utils import now_datetime, getdate

	container = frappe.get_doc("Container", container_name)
	settings = frappe.get_single("Sea Freight Settings")
	free_time_days = flt(container.free_time_days or 0) or flt(
		getattr(settings, "default_free_time_days", 7)
	)
	detention_rate = flt(getattr(settings, "detention_rate_per_day", 0))
	demurrage_rate = flt(getattr(settings, "demurrage_rate_per_day", 0))

	# Get linked Sea Shipment
	shipment = frappe.db.sql("""
		SELECT sfc.parent FROM `tabSea Freight Containers` sfc
		WHERE sfc.container = %s AND sfc.parenttype = 'Sea Shipment'
		ORDER BY sfc.modified DESC LIMIT 1
	""", (container_name,), as_dict=True)

	demurrage_days = 0
	detention_days = 0

	if shipment:
		shipment_name = shipment[0].parent
		ship_doc = frappe.get_doc("Sea Shipment", shipment_name)
		# Use shipment's calculated values
		demurrage_days = flt(getattr(ship_doc, "demurrage_days", 0))
		detention_days = flt(getattr(ship_doc, "detention_days", 0))

	estimated_amount = (demurrage_days * demurrage_rate) + (detention_days * detention_rate)

	container.demurrage_days = demurrage_days
	container.detention_days = detention_days
	container.estimated_penalty_amount = estimated_amount
	container.has_penalties = 1 if (demurrage_days > 0 or detention_days > 0) else 0
	container.last_penalty_check = now_datetime()
	container.save(ignore_permissions=True)

	return {
		"demurrage_days": demurrage_days,
		"detention_days": detention_days,
		"estimated_penalty_amount": estimated_amount,
	}
