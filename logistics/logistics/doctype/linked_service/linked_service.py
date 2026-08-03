# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document


class LinkedService(Document):
	"""Top-level linked service record carrying service parameters for one subsidiary leg.

	Owned by a parent booking via ``parent_booking_type`` + ``parent_booking_name`` back-links.
	The parent exposes linked services through a ``linked_services`` / ``internal_job_details``
	child table whose rows are thin pointers to records of this doctype.
	Consumers that reuse the same ``IJ-…`` ID (without re-parenting) are listed under ``usages``.
	"""

	def get_invalid_links(self, is_submittable=False):
		saved_parent = self.parent_booking_name
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		if saved_parent:
			self.parent_booking_name = saved_parent
		skip = ("parent_booking_name",)
		invalid_links = [c for c in invalid_links if c[0] not in skip]
		cancelled_links = [c for c in cancelled_links if c[0] not in skip]
		return invalid_links, cancelled_links

	def validate(self):
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


def get_linked_services_for_booking(parent_booking_type: str, parent_booking_name: str) -> list[Document]:
	"""Linked Services for a booking/order: owned via parent_booking_* and/or Usage rows.

	Quote-owned IJ-… records reused by a booking appear through Linked Service Usage, so the
	booking Services grid still lists every leg without re-parenting or cloning.
	"""
	if not parent_booking_type or not parent_booking_name:
		return []
	owned = frappe.get_all(
		"Linked Service",
		filters={
			"parent_booking_type": parent_booking_type,
			"parent_booking_name": parent_booking_name,
		},
		pluck="name",
		order_by="creation asc",
	)
	names: list[str] = list(owned)
	seen = set(owned)
	if frappe.db.exists("DocType", "Linked Service Usage"):
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		for n in get_linked_services_used_by(parent_booking_type, parent_booking_name):
			if n and n not in seen:
				seen.add(n)
				names.append(n)
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


# Fieldsets for Manage Linked Services in-dialog edit (linked_services_dialog_1).
_DIALOG_EDIT_LABELS = {
	"airline": "Carrier / Airline",
	"shipping_line": "Carrier / Shipping Line",
	"origin_port": "Origin",
	"destination_port": "Destination",
	"location_from": "Origin",
	"location_to": "Destination",
	"reference_no": "Reference No.",
}

_DIALOG_EDIT_FIELDS = {
	"Air": [
		"service_type",
		"airline",
		"origin_port",
		"destination_port",
		"shipper",
		"consignee",
		"reference_no",
		"notes",
	],
	"Sea": [
		"service_type",
		"shipping_line",
		"origin_port",
		"destination_port",
		"shipper",
		"consignee",
		"reference_no",
		"notes",
	],
	"Transport": [
		"service_type",
		"location_type",
		"location_from",
		"location_to",
		"vehicle_type",
		"container_type",
		"transport_template",
		"reference_no",
		"notes",
	],
	"Customs": [
		"service_type",
		"customs_authority",
		"declaration_type",
		"customs_broker",
		"customs_charge_category",
		"reference_no",
		"notes",
	],
}

_DIALOG_EDIT_DEFAULT_FIELDS = ["service_type", "reference_no", "notes"]


def _dialog_edit_fieldnames(service_type: str) -> list[str]:
	return list(_DIALOG_EDIT_FIELDS.get(service_type or "", _DIALOG_EDIT_DEFAULT_FIELDS))


def _dialog_edit_field_defs(service_type: str) -> list[dict[str, Any]]:
	meta = frappe.get_meta("Linked Service")
	defs: list[dict[str, Any]] = []
	for fieldname in _dialog_edit_fieldnames(service_type):
		df = meta.get_field(fieldname)
		if not df:
			continue
		item: dict[str, Any] = {
			"fieldname": fieldname,
			"label": _DIALOG_EDIT_LABELS.get(fieldname) or df.label or fieldname,
			"fieldtype": df.fieldtype,
			"options": df.options or "",
			"read_only": 1 if fieldname == "service_type" else 0,
		}
		link_filters = getattr(df, "link_filters", None)
		if link_filters:
			item["link_filters"] = link_filters
		defs.append(item)
	return defs


def _linked_service_names_for_parent(parent_doctype: str, parent_name: str) -> set[str]:
	if parent_doctype == "Sales Quote":
		return {row.name for row in get_linked_services_for_sales_quote(parent_name)}
	if parent_doctype == "Time Sensitive Case":
		from logistics.time_sensitive.service_linking import get_case_linked_services

		case = frappe.get_doc(parent_doctype, parent_name)
		return {row.name for row in get_case_linked_services(case)}
	if parent_doctype == "Change Request":
		return {row.name for row in get_linked_services_for_change_request(parent_name)}
	return {row.name for row in get_linked_services_for_booking(parent_doctype, parent_name)}


def _load_linked_service_for_dialog(
	linked_service: str, parent_doctype: str, parent_name: str, *, write: bool = False
):
	if not linked_service:
		frappe.throw(_("Linked Service is required."))
	if not parent_doctype or not parent_name:
		frappe.throw(_("Parent document is required."))

	parent = frappe.get_doc(parent_doctype, parent_name)
	frappe.has_permission(parent_doctype, "write" if write else "read", doc=parent, throw=True)

	if linked_service not in _linked_service_names_for_parent(parent_doctype, parent_name):
		frappe.throw(
			_("Linked Service {0} is not linked to {1} {2}.").format(
				linked_service, parent_doctype, parent_name
			)
		)

	doc = frappe.get_doc("Linked Service", linked_service)
	frappe.has_permission("Linked Service", "write" if write else "read", doc=doc, throw=True)
	return parent, doc


@frappe.whitelist()
def get_dialog_edit_payload(linked_service: str, parent_doctype: str, parent_name: str):
	"""Return field defs + values for the Manage Linked Services edit panel."""
	_parent, doc = _load_linked_service_for_dialog(
		linked_service, parent_doctype, parent_name, write=False
	)
	fields = _dialog_edit_field_defs(doc.service_type)
	values = {f["fieldname"]: doc.get(f["fieldname"]) or "" for f in fields}
	return {
		"name": doc.name,
		"service_type": doc.service_type,
		"fields": fields,
		"values": values,
	}


@frappe.whitelist()
def update_dialog_edit(
	linked_service: str, parent_doctype: str, parent_name: str, values=None
):
	"""Persist in-dialog edits for a Linked Service owned/linked to the parent."""
	import json

	_parent, doc = _load_linked_service_for_dialog(
		linked_service, parent_doctype, parent_name, write=True
	)
	if isinstance(values, str):
		values = json.loads(values or "{}")
	values = values or {}

	allowed = {
		f["fieldname"]
		for f in _dialog_edit_field_defs(doc.service_type)
		if not f.get("read_only")
	}
	changed = False
	for fieldname, value in values.items():
		if fieldname not in allowed:
			continue
		if doc.get(fieldname) != value:
			doc.set(fieldname, value)
			changed = True

	if changed:
		doc.flags.ignore_mandatory = True
		doc.save()

	return {
		"name": doc.name,
		"service_type": doc.service_type,
		"changed": 1 if changed else 0,
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def linked_service_charge_link_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for charge ``linked_service``: booking-owned, Usage-tagged, or quote-owned.

	``filters`` may include:
	- ``parent_booking_type`` / ``parent_booking_name`` — current operational document
	- ``service_type`` — Linked Service Select label (Air, Sea, Transport, …)
	- ``sales_quote`` — optional Sales Quote name on the booking
	"""
	filters = filters or {}
	parent_type = (filters.get("parent_booking_type") or "").strip()
	parent_name = (filters.get("parent_booking_name") or "").strip()
	service_type = (filters.get("service_type") or "").strip()
	sales_quote = (filters.get("sales_quote") or "").strip()

	conditions = ["1=1"]
	values: dict[str, Any] = {
		"txt": f"%{txt or ''}%",
		"start": int(start or 0),
		"page_len": int(page_len or 20),
	}
	if service_type:
		conditions.append("`tabLinked Service`.service_type = %(service_type)s")
		values["service_type"] = service_type
	if txt:
		conditions.append(
			"(`tabLinked Service`.name LIKE %(txt)s OR IFNULL(`tabLinked Service`.service_type, '') LIKE %(txt)s)"
		)

	ownership_parts = []
	if parent_type and parent_name:
		ownership_parts.append(
			"(`tabLinked Service`.parent_booking_type = %(parent_type)s "
			"AND `tabLinked Service`.parent_booking_name = %(parent_name)s)"
		)
		values["parent_type"] = parent_type
		values["parent_name"] = parent_name
		if frappe.db.exists("DocType", "Linked Service Usage"):
			ownership_parts.append(
				"EXISTS ("
				"SELECT 1 FROM `tabLinked Service Usage` u "
				"WHERE u.parent = `tabLinked Service`.name "
				"AND u.parenttype = 'Linked Service' "
				"AND u.used_on_doctype = %(parent_type)s "
				"AND u.used_on_name = %(parent_name)s"
				")"
			)
	if sales_quote:
		ownership_parts.append(
			"(`tabLinked Service`.parent_booking_type = 'Sales Quote' "
			"AND `tabLinked Service`.parent_booking_name = %(sales_quote)s)"
		)
		values["sales_quote"] = sales_quote

	if ownership_parts:
		conditions.append("(" + " OR ".join(ownership_parts) + ")")
	elif not sales_quote:
		return []

	where_sql = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT `tabLinked Service`.name, IFNULL(`tabLinked Service`.service_type, '')
		FROM `tabLinked Service`
		WHERE {where_sql}
		ORDER BY `tabLinked Service`.creation ASC
		LIMIT %(start)s, %(page_len)s
		""",
		values,
	)


# Backward-compatible aliases
InternalJob = LinkedService
get_internal_jobs_for_booking = get_linked_services_for_booking
