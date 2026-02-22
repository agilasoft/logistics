# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""API for document management: template resolution, population, and alerts."""

from __future__ import unicode_literals

import frappe
from frappe.utils import getdate, add_days, date_diff, today


# Mapping of doctype to (product_type, applies_to)
DOCTYPE_CONTEXT = {
	"Air Booking": ("Air Freight", "Booking"),
	"Sea Booking": ("Sea Freight", "Booking"),
	"Transport Order": ("Transport", "Booking"),
	"Declaration Order": ("Customs", "Booking"),
	"Inbound Order": ("Warehousing", "Booking"),
	"Release Order": ("Warehousing", "Booking"),
	"Transfer Order": ("Warehousing", "Booking"),
	"Air Shipment": ("Air Freight", "Shipment/Job"),
	"Sea Shipment": ("Sea Freight", "Shipment/Job"),
	"Transport Job": ("Transport", "Shipment/Job"),
	"Warehouse Job": ("Warehousing", "Shipment/Job"),
	"General Job": ("General", "Shipment/Job"),
	"Declaration": ("Customs", "Shipment/Job"),
}


@frappe.whitelist()
def get_document_template_items(product_type, applies_to, direction=None, entry_type=None):
	"""Get document template items for the given context."""
	filters = [
		["product_type", "=", product_type],
		["applies_to", "in", [applies_to, "Both"]],
	]

	templates = frappe.get_all(
		"Document List Template",
		filters=filters,
		fields=["name", "template_name", "is_default", "direction", "entry_type"],
		order_by="is_default asc",  # Default last as fallback
	)

	# Filter by direction/entry_type if specified
	if direction and direction != "All":
		templates = [t for t in templates if t.direction in (None, "", "All", direction)]
	if entry_type and entry_type != "All":
		templates = [t for t in templates if t.entry_type in (None, "", "All", entry_type)]

	# Prefer non-default first, then default
	template_name = None
	for t in templates:
		if not t.is_default:
			template_name = t.name
			break
	if not template_name and templates:
		template_name = next((t.name for t in templates if t.is_default), templates[0].name)

	if not template_name:
		return []

	items = frappe.get_all(
		"Document List Template Item",
		filters={"parent": template_name},
		fields=["document_type", "sequence", "is_mandatory", "date_required_basis", "days_offset", "allow_early_upload", "description"],
		order_by="sequence asc",
	)

	return items


@frappe.whitelist()
def populate_documents_from_template(doctype, docname):
	"""Populate documents child table from template. Only adds missing document types."""
	if not doctype or not docname or docname == "new":
		return {"message": "Save the document first."}

	doc = frappe.get_doc(doctype, docname)
	context = DOCTYPE_CONTEXT.get(doctype)
	if not context:
		return {"message": "Documents not supported for this doctype."}

	product_type, applies_to = context
	direction = getattr(doc, "direction", None) or ""
	entry_type = getattr(doc, "entry_type", None) or ""

	# Use override template if set
	template_name = getattr(doc, "document_list_template", None)
	if not template_name:
		items = get_document_template_items(product_type, applies_to, direction, entry_type)
	else:
		items = frappe.get_all(
			"Document List Template Item",
			filters={"parent": template_name},
			fields=["document_type", "sequence", "is_mandatory", "date_required_basis", "days_offset", "allow_early_upload", "description"],
			order_by="sequence asc",
		)

	existing_types = {d.document_type for d in (doc.get("documents") or [])}

	added = 0
	for item in items:
		if item.document_type in existing_types:
			continue
		date_required = _compute_date_required(doc, item)
		row = doc.append("documents", {
			"document_type": item.document_type,
			"is_required": 1 if item.is_mandatory else 0,
			"status": "Pending",
			"date_required": date_required,
		})
		existing_types.add(item.document_type)
		added += 1

	if added:
		doc.flags.ignore_validate = True
		doc.save()

	return {"message": f"Added {added} document(s) from template.", "added": added}


def _compute_date_required(doc, template_item):
	"""Compute date_required from parent doc and template item."""
	if not template_item or not template_item.get("date_required_basis"):
		return None
	basis = template_item["date_required_basis"]
	offset = template_item.get("days_offset") or 0

	base_date = None
	if basis == "ETD":
		base_date = getattr(doc, "etd", None)
	elif basis == "ETA":
		base_date = getattr(doc, "eta", None)
	elif basis == "Booking Date":
		base_date = getattr(doc, "booking_date", None) or getattr(doc, "order_date", None)
	elif basis == "Job Date":
		base_date = getattr(doc, "booking_date", None) or doc.creation
	if not base_date:
		return None
	base_date = getdate(base_date)
	return add_days(base_date, offset)


@frappe.whitelist()
def get_document_alerts(doctype, docname):
	"""Return document alerts for dashboard: missing, overdue, expiring_soon."""
	if not doctype or not docname or docname == "new":
		return {"missing": [], "overdue": [], "expiring_soon": []}

	doc = frappe.get_doc(doctype, docname)
	documents = doc.get("documents") or []

	missing = []
	overdue = []
	expiring_soon = []
	today_date = getdate(today())

	for d in documents:
		status = (d.get("status") or "").strip()
		date_required = d.get("date_required")
		expiry_date = d.get("expiry_date")
		is_required = d.get("is_required")

		# Overdue: required, not received/verified, past date_required
		if is_required and status in ("Pending", "Uploaded", "Overdue"):
			if date_required and getdate(date_required) < today_date:
				days_overdue = date_diff(today_date, getdate(date_required))
				overdue.append({
					"document_type": d.document_type,
					"date_required": date_required,
					"days_overdue": days_overdue,
					"status": status,
				})
			elif not d.get("attachment"):
				missing.append({
					"document_type": d.document_type,
					"date_required": date_required,
					"status": status,
				})

		# Expiring soon (within 7 days)
		if expiry_date:
			exp = getdate(expiry_date)
			if exp >= today_date and date_diff(exp, today_date) <= 7:
				expiring_soon.append({
					"document_type": d.document_type,
					"expiry_date": expiry_date,
				})

	return {"missing": missing, "overdue": overdue, "expiring_soon": expiring_soon}


@frappe.whitelist()
def get_document_alerts_html(doctype, docname):
	"""Return HTML for document alerts to embed in dashboard."""
	alerts = get_document_alerts(doctype, docname)
	parts = []

	if alerts["overdue"]:
		items = "\n".join(
			f'<li>{a["document_type"]} – {a["days_overdue"]} day(s) overdue</li>'
			for a in alerts["overdue"]
		)
		parts.append(
			f'<div class="alert alert-danger" style="margin-bottom: 12px;">'
			f'<strong>Documents Overdue</strong><ul style="margin: 8px 0 0 20px;">{items}</ul>'
			f'<a href="#Form/{doctype}/{docname}" data-tab="documents_tab">View Documents</a>'
			f'</div>'
		)

	if alerts["missing"]:
		items = "\n".join(
			f'<li>{a["document_type"]}' + (f' – due {a["date_required"]}' if a.get("date_required") else '') + '</li>'
			for a in alerts["missing"][:5]  # Limit to 5
		)
		parts.append(
			f'<div class="alert alert-warning" style="margin-bottom: 12px;">'
			f'<strong>Required Documents Pending</strong><ul style="margin: 8px 0 0 20px;">{items}</ul>'
			f'<a href="#Form/{doctype}/{docname}" data-tab="documents_tab">View Documents</a>'
			f'</div>'
		)

	if alerts["expiring_soon"]:
		items = "\n".join(
			f'<li>{a["document_type"]} – expires {a["expiry_date"]}</li>'
			for a in alerts["expiring_soon"]
		)
		parts.append(
			f'<div class="alert alert-info" style="margin-bottom: 12px;">'
			f'<strong>Documents Expiring Soon</strong><ul style="margin: 8px 0 0 20px;">{items}</ul>'
			f'</div>'
		)

	return "\n".join(parts) if parts else ""
