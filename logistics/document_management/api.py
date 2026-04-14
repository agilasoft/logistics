# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""API for document management: template resolution, population, and alerts."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import getdate, add_days, date_diff, today

from logistics.utils import alert_utils


# CSS for document alert cards (used when HTML is shown without dashboard layout, e.g. Transport Order Documents tab)
DOC_ALERT_CARDS_CSS = """
.doc-alerts-cards-wrapper { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 16px; }
.doc-alerts-cards { display: flex; flex-wrap: wrap; gap: 12px; align-items: stretch; }
.doc-alert-card { min-width: 80px; flex: 1; background: #fff; border-radius: 6px; border: 1px solid #e0e0e0; padding: 12px 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: box-shadow 0.15s ease; }
.doc-alert-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
.doc-alert-card-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
.doc-alert-card-title { font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; font-weight: 600; }
.doc-alert-card-warning .doc-alert-card-value { color: #856404; }
.doc-alert-card-warning { border-left: 4px solid #ffc107; }
.doc-alert-card-danger .doc-alert-card-value { color: #721c24; }
.doc-alert-card-danger { border-left: 4px solid #dc3545; }
.doc-alert-card-info .doc-alert-card-value { color: #0c5460; }
.doc-alert-card-info { border-left: 4px solid #17a2b8; }
.doc-alert-card-success .doc-alert-card-value { color: #155724; }
.doc-alert-card-success { border-left: 4px solid #28a745; }
.doc-alert-card-secondary .doc-alert-card-value { color: #383d41; }
.doc-alert-card-secondary { border-left: 4px solid #6c757d; }
.doc-alert-card-permits { border-left: 4px solid #ff9800; }
.doc-alert-card-permits .doc-alert-card-value { color: #e65100; }
.doc-alert-card-exemptions { border-left: 4px solid #9c27b0; }
.doc-alert-card-exemptions .doc-alert-card-value { color: #7b1fa2; }
@media (max-width: 768px) { .doc-alert-card { min-width: 70px; } }
"""

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
	"Air Consolidation": ("Air Freight", "Shipment/Job"),
	"Sea Shipment": ("Sea Freight", "Shipment/Job"),
	"Sea Consolidation": ("Sea Freight", "Shipment/Job"),
	"Transport Job": ("Transport", "Shipment/Job"),
	"Warehouse Job": ("Warehousing", "Shipment/Job"),
	"General Job": ("General", "Shipment/Job"),
	"Declaration": ("Customs", "Shipment/Job"),
	"Special Project": ("Special Projects", "Shipment/Job"),
}

# Doctypes that have milestone child table (field "milestones")
MILESTONE_DOCTYPES = ("Air Booking", "Air Shipment", "Air Consolidation", "Sea Booking", "Sea Shipment", "Sea Consolidation", "Transport Order", "Transport Job", "Declaration", "Declaration Order")

# Child table doctype for each parent
MILESTONE_CHILD_DOCTYPE = {
	"Air Booking": "Air Booking Milestone",
	"Air Shipment": "Air Shipment Milestone",
	"Air Consolidation": "Air Consolidation Milestone",
	"Sea Booking": "Sea Booking Milestone",
	"Sea Shipment": "Sea Shipment Milestone",
	"Sea Consolidation": "Sea Consolidation Milestone",
	"Transport Order": "Transport Order Milestone",
	"Transport Job": "Transport Job Milestone",
	"Declaration": "Declaration Milestone",
	"Declaration Order": "Declaration Order Milestone",
}


def _milestone_row_field(row, fieldname):
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def get_milestone_display_rows_and_editor_doctype(doc):
	"""
	Milestone rows for HTML timeline: prefer parent child table; if empty, use legacy Job Milestone
	(job_type = parent doctype, job_number = parent name). Returns (list of dicts, doctype for edit prompts).
	"""
	if not doc or not getattr(doc, "doctype", None):
		return [], "Job Milestone"
	doctype = doc.doctype
	child_doctype = MILESTONE_CHILD_DOCTYPE.get(doctype, "") or "Job Milestone"
	table_rows = list(doc.get("milestones") or [])
	source_rows = table_rows
	editor_dt = child_doctype
	if not source_rows and doc.name:
		jm = frappe.get_all(
			"Job Milestone",
			filters={"job_type": doctype, "job_number": doc.name},
			fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
			order_by="planned_start",
		)
		if jm:
			source_rows = jm
			editor_dt = "Job Milestone"
	milestones = []
	for row in source_rows:
		milestones.append({
			"name": _milestone_row_field(row, "name"),
			"milestone": _milestone_row_field(row, "milestone"),
			"status": (_milestone_row_field(row, "status") or "Planned"),
			"planned_start": _milestone_row_field(row, "planned_start"),
			"planned_end": _milestone_row_field(row, "planned_end"),
			"actual_start": _milestone_row_field(row, "actual_start"),
			"actual_end": _milestone_row_field(row, "actual_end"),
		})
	return milestones, editor_dt


@frappe.whitelist()
def get_milestone_html(doctype, docname):
	"""Generate graphical milestone HTML for Milestones tab (child table; legacy Job Milestone if empty)."""
	if not doctype or not docname or docname == "new":
		return '<div class="alert alert-info">Save the document to view milestones.</div>'
	if doctype not in MILESTONE_DOCTYPES:
		return '<div class="alert alert-warning">Milestones not supported for this doctype.</div>'
	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		return '<div class="alert alert-warning">Document not found.</div>'

	milestones, child_doctype = get_milestone_display_rows_and_editor_doctype(doc)

	# Resolve origin/destination per doctype (detail items section removed)
	origin_name = (
		getattr(doc, "origin_port", None) or getattr(doc, "port_of_loading", None)
		or getattr(doc, "origin", None) or getattr(doc, "origin_terminal", None) or ""
	)
	destination_name = (
		getattr(doc, "destination_port", None) or getattr(doc, "port_of_discharge", None)
		or getattr(doc, "destination", None) or getattr(doc, "destination_terminal", None) or ""
	)
	detail_items = []  # Status, Booking Date, Scheduled Date section removed

	def format_dt(v):
		return frappe.utils.format_datetime(v, "dd-MM-yyyy HH:mm") if v else None

	from logistics.document_management.milestone_html import build_milestone_html
	return build_milestone_html(
		doctype=doctype,
		docname=docname,
		origin_name=origin_name or "Origin",
		destination_name=destination_name or "Destination",
		detail_items=detail_items,
		milestones=milestones,
		format_datetime_fn=format_dt,
		child_milestone_doctype=child_doctype,
		include_doc_alerts=False,
		include_origin_destination=False,
	)


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
	now_dt = frappe.utils.now()
	for item in items:
		if item.document_type in existing_types:
			continue
		date_required = _compute_date_required(doc, item)
		doc.append("documents", {
			"document_type": item.document_type,
			"is_required": 1 if item.is_mandatory else 0,
			"status": "Pending",
			"date_required": date_required,
			"source": "Fetched",
			"created_at": now_dt,
		})
		existing_types.add(item.document_type)
		added += 1

	if added:
		doc.flags.ignore_validate = True
		doc.save()

	return {"message": f"Added {added} document(s) from template.", "added": added}


def update_milestone_status_on_parent_before_save(doc, method=None):
	"""Before save: sync ata <-> milestone actual_end (Date Based) and set status from actual dates.
	Called from before_save on milestone parent doctypes so the save persists both directions."""
	if not doc or doc.doctype not in MILESTONE_DOCTYPES:
		return
	if not hasattr(doc, "milestones") or not doc.get("milestones"):
		return
	# Run Date Based sync in-place (ata <-> actual_end) using row automation data
	from logistics.document_management.milestone_sync import apply_milestone_sync_in_place
	apply_milestone_sync_in_place(doc, method)
	# Ensure status from actual_start/actual_end (in case sync didn't set it)
	from logistics.utils.milestone_status_utils import update_milestone_status
	for row in doc.milestones:
		update_milestone_status(row)


def update_job_document_status_on_parent_before_save(doc, method=None):
	"""Before save: validate and apply status updates to Job Document child rows. Child table rows
	do not run their controller validate/before_save when parent is saved, so we must run from parent."""
	if not doc:
		return
	if not hasattr(doc, "documents") or not doc.get("documents"):
		return
	from logistics.logistics.doctype.job_document.job_document import (
		apply_job_document_status_updates,
		validate_job_document_status_aligned,
	)
	for row in doc.documents:
		# Apply date/status realignment and activity rules first; then validate. Validating first
		# blocked saves when e.g. Overdue + user extended date_required (status still old until apply).
		apply_job_document_status_updates(row)
		validate_job_document_status_aligned(row)


def ensure_documents_and_milestones_from_template(doc, method=None):
	"""On parent save: auto-populate documents and milestones from applicable default template if empty or new.
	Called from doc_events on_update for doctypes that have documents/milestones tabs.
	Frappe passes (doc, method) to doc_event handlers."""
	if not doc or getattr(doc, "flags", None) and doc.flags.ignore_documents_milestones_populate:
		return
	if getattr(frappe.flags, "in_ensure_documents_milestones", False):
		return
	name = getattr(doc, "name", None)
	if not name or name == "new" or getattr(doc, "__islocal", True):
		return
	doctype = doc.doctype
	frappe.flags.in_ensure_documents_milestones = True
	try:
		# Documents: populate if this doctype has documents and template resolution
		if doctype in DOCTYPE_CONTEXT and hasattr(doc, "documents"):
			try:
				populate_documents_from_template(doctype, name)
			except Exception as e:
				frappe.log_error(
					f"Error auto-populating documents for {doctype} {name}: {e}",
					"Documents/Milestones Auto-Populate",
				)
		# Milestones: populate if this doctype has milestones
		if doctype in MILESTONE_DOCTYPES and hasattr(doc, "milestones"):
			try:
				populate_milestones_from_template(doctype, name)
			except Exception as e:
				frappe.log_error(
					f"Error auto-populating milestones for {doctype} {name}: {e}",
					"Documents/Milestones Auto-Populate",
				)
		# Sync parent date <-> milestone actual_end and field triggers
		if doctype in MILESTONE_DOCTYPES and hasattr(doc, "milestones"):
			try:
				from logistics.document_management.milestone_sync import apply_milestone_sync_and_triggers
				apply_milestone_sync_and_triggers(doc, method)
			except Exception as e:
				frappe.log_error(
					f"Error applying milestone sync/triggers for {doctype} {name}: {e}",
					"Milestone Sync/Trigger Error",
				)
	finally:
		frappe.flags.in_ensure_documents_milestones = False


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
		base_date = (
			getattr(doc, "booking_date", None)
			or getattr(doc, "order_date", None)
			or getattr(doc, "start_date", None)
			or getattr(doc, "planned_start", None)
			or doc.creation
		)
	if not base_date:
		return None
	base_date = getdate(base_date)
	return add_days(base_date, offset)


# --- Milestone template and population ---


@frappe.whitelist()
def get_milestone_template_filters(doctype):
	"""Return filters for milestone_template Link field so only templates for this doctype are shown."""
	context = DOCTYPE_CONTEXT.get(doctype)
	if not context:
		return {"filters": []}
	product_type, applies_to = context
	filters = [
		["product_type", "=", product_type],
		["applies_to", "in", [applies_to, "Both"]],
	]
	# applies_to_doctype: empty/NULL = available for all; set = only for that doctype
	filters.append([
		"or",
		["applies_to_doctype", "=", ""],
		["applies_to_doctype", "is", "not set"],
		["applies_to_doctype", "=", doctype],
	])
	return {"filters": filters}


@frappe.whitelist()
def get_doctype_fields_for_milestone(doctype):
	"""Return list of field names from the given doctype for use in Milestone Template Item (trigger field, sync field).
	Only includes fields that exist on the doctype and are not layout-only (section/column break)."""
	if not doctype or not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	fieldnames = []
	for df in meta.get("fields", []):
		if df.fieldtype in ("Section Break", "Column Break", "Tab Break", "Table MultiSelect", "HTML", "Button"):
			continue
		if df.hidden or (getattr(df, "permlevel", 0) or 0) > 0:
			continue
		if df.fieldname:
			fieldnames.append(df.fieldname)
	return fieldnames


@frappe.whitelist()
def get_milestone_template_items(product_type, applies_to, direction=None, entry_type=None, doctype=None):
	"""Resolve milestone template for context and return list of Milestone Template Items."""
	if doctype:
		filters = [
			["product_type", "=", product_type],
			"and",
			["applies_to", "in", [applies_to, "Both"]],
			"and",
			[
				["applies_to_doctype", "=", ""],
				"or",
				["applies_to_doctype", "is", "not set"],
				"or",
				["applies_to_doctype", "=", doctype],
			],
		]
	else:
		filters = [
			["product_type", "=", product_type],
			["applies_to", "in", [applies_to, "Both"]],
		]
	templates = frappe.get_all(
		"Milestone Template",
		filters=filters,
		fields=["name", "template_name", "is_default", "direction", "entry_type", "applies_to_doctype"],
		order_by="is_default asc",
	)
	if direction and direction != "All":
		templates = [t for t in templates if (t.direction or "") in ("", "All", direction)]
	if entry_type and entry_type != "All":
		templates = [t for t in templates if (t.entry_type or "") in ("", "All", entry_type)]
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
		"Milestone Template Item",
		filters={"parent": template_name},
		fields=[
			"milestone", "icon", "date_basis", "planned_days_offset",
			"update_trigger_type", "sync_parent_date_field", "sync_direction",
			"trigger_field", "trigger_condition", "trigger_value", "trigger_action",
		],
		order_by="idx asc",
	)
	return items


def _get_planned_date_basis_value(doc, template_item):
	"""Return the base date from parent doc using template item's Planned Date Basis (date_basis). Used for planned_end and for planned_start offset."""
	basis = (template_item or {}).get("date_basis")
	if not basis or basis == "Manual" or basis == "None":
		return None
	if basis == "ETD":
		return getattr(doc, "etd", None)
	if basis == "ETA":
		return getattr(doc, "eta", None)
	if basis == "Booking Date":
		return getattr(doc, "booking_date", None) or getattr(doc, "order_date", None)
	if basis == "Job Date":
		return (
			getattr(doc, "booking_date", None)
			or getattr(doc, "order_date", None)
			or getattr(doc, "start_date", None)
			or getattr(doc, "planned_start", None)
			or getattr(doc, "declaration_date", None)
			or getattr(doc, "scheduled_date", None)
			or doc.creation
		)
	return None


def _compute_milestone_planned_dates(doc, template_item):
	"""Return (planned_start, planned_end). Planned Date Basis sets planned_end; reduction days set planned_start (base minus reduction)."""
	base = _get_planned_date_basis_value(doc, template_item)
	if not base:
		return None, None
	base_date = getdate(base)
	reduction_days = (template_item or {}).get("planned_days_offset") or 0
	planned_end = base_date
	planned_start = add_days(base_date, -reduction_days)
	return planned_start, planned_end


@frappe.whitelist()
def populate_milestones_from_template(doctype, docname):
	"""Populate parent's milestones child table from template. Only adds missing milestones."""
	if not doctype or not docname or docname == "new":
		return {"message": "Save the document first.", "added": 0}
	if doctype not in MILESTONE_DOCTYPES:
		return {"message": "Milestones not supported for this doctype.", "added": 0}
	doc = frappe.get_doc(doctype, docname)
	context = DOCTYPE_CONTEXT.get(doctype)
	if not context:
		return {"message": "Context not found.", "added": 0}
	product_type, applies_to = context
	direction = getattr(doc, "direction", None) or ""
	entry_type = getattr(doc, "entry_type", None) or ""

	template_name = getattr(doc, "milestone_template", None)
	if template_name:
		items = frappe.get_all(
			"Milestone Template Item",
			filters={"parent": template_name},
			fields=[
				"milestone", "icon", "date_basis", "planned_days_offset",
				"update_trigger_type", "sync_parent_date_field", "sync_direction",
				"trigger_field", "trigger_condition", "trigger_value", "trigger_action",
			],
			order_by="idx asc",
		)
	else:
		items = get_milestone_template_items(product_type, applies_to, direction, entry_type, doctype=doctype)

	existing_milestones = {row.milestone for row in (doc.get("milestones") or [])}
	added = 0
	now_dt = frappe.utils.now()
	for item in items:
		milestone = item.get("milestone")
		if not milestone or milestone in existing_milestones:
			continue
		planned_start, planned_end = _compute_milestone_planned_dates(doc, item)
		row_data = {
			"milestone": milestone,
			"status": "Planned",
			"planned_start": planned_start,
			"planned_end": planned_end,
			"source": "Fetched",
			"fetched_at": now_dt,
			"created_at": now_dt,
		}
		# Copy automation config from template for trigger reference when saving
		row_data["automation_planned_date_basis"] = (item.get("date_basis") or "").strip() or None
		row_data["automation_update_trigger_type"] = (item.get("update_trigger_type") or "").strip() or None
		row_data["automation_sync_parent_date_field"] = (item.get("sync_parent_date_field") or "").strip() or None
		row_data["automation_sync_direction"] = (item.get("sync_direction") or "").strip() or None
		row_data["automation_trigger_field"] = (item.get("trigger_field") or "").strip() or None
		row_data["automation_trigger_condition"] = (item.get("trigger_condition") or "").strip() or None
		row_data["automation_trigger_value"] = (item.get("trigger_value") or "").strip() or None
		row_data["automation_trigger_action"] = (item.get("trigger_action") or "").strip() or None
		icon = item.get("icon")
		if not icon:
			lm = frappe.db.get_value("Logistics Milestone", milestone, "icon")
			if lm:
				icon = lm
		if icon:
			row_data["icon"] = icon
		doc.append("milestones", row_data)
		existing_milestones.add(milestone)
		added += 1
	if added:
		doc.flags.ignore_validate = True
		doc.save()
	return {"message": f"Added {added} milestone(s) from template.", "added": added}


@frappe.whitelist()
def get_document_alerts(doctype, docname):
	"""Return document alerts for dashboard: missing, overdue, expiring_soon, and counts."""
	if not doctype or not docname or docname == "new":
		return {
			"missing": [], "overdue": [], "expiring_soon": [],
			"counts": {"pending": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0},
		}

	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		# Document not found (may happen immediately after creation due to replication lag)
		return {
			"missing": [], "overdue": [], "expiring_soon": [],
			"counts": {"pending": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0},
		}
	except Exception:
		# Any other error - log and return empty
		frappe.log_error(f"Error getting document alerts for {doctype} {docname}")
		return {
			"missing": [], "overdue": [], "expiring_soon": [],
			"counts": {"pending": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0},
		}

	documents = doc.get("documents") or []

	missing = []
	overdue = []
	expiring_soon = []
	today_date = getdate(today())
	received_count = 0

	for d in documents:
		status = (d.get("status") or "").strip()
		date_required = d.get("date_required")
		expiry_date = d.get("expiry_date")
		is_required = d.get("is_required")

		# Count received/verified/done
		if status in ("Received", "Verified", "Done"):
			received_count += 1

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

		# Expiring soon (within Logistics Settings document_expiring_soon_days)
		if expiry_date:
			exp = getdate(expiry_date)
			if exp >= today_date:
				try:
					expiring_soon_days = alert_utils.get_document_expiring_soon_days()
				except Exception:
					expiring_soon_days = 7
				if date_diff(exp, today_date) <= expiring_soon_days:
					expiring_soon.append({
						"document_type": d.document_type,
						"expiry_date": expiry_date,
					})

	counts = {
		"pending": len(missing),
		"overdue": len(overdue),
		"expiring_soon": len(expiring_soon),
		"received": received_count,
		"total": len(documents),
	}
	return {"missing": missing, "overdue": overdue, "expiring_soon": expiring_soon, "counts": counts}


@frappe.whitelist()
def get_document_alerts_html(doctype, docname):
	"""Return HTML for document alerts as number cards to embed in dashboard."""
	alerts = get_document_alerts(doctype, docname)
	counts = alerts.get("counts") or {}
	pending = counts.get("pending", 0)
	overdue = counts.get("overdue", 0)
	expiring_soon = counts.get("expiring_soon", 0)
	received = counts.get("received", 0)
	total = counts.get("total", 0)

	# Declaration and Declaration Order: add pending permits and exemptions counts
	pending_permits = 0
	exemptions_count = 0
	if doctype in ("Declaration", "Declaration Order") and docname and docname != "new":
		try:
			doc = frappe.get_doc(doctype, docname)
			for pr in (doc.get("permit_requirements") or []):
				if pr.get("is_required") and not getattr(pr, "is_obtained", None):
					pending_permits += 1
			exemptions_count = len(doc.get("exemptions") or [])
		except Exception:
			pass

	# Build number cards: show cards that have meaning (total > 0 or we still show summary)
	# For Declaration and Declaration Order, always show permits and exemptions cards
	has_standard_cards = total > 0 or pending > 0 or overdue > 0 or expiring_soon > 0 or received > 0
	has_declaration_cards = doctype in ("Declaration", "Declaration Order")
	if not has_standard_cards and not has_declaration_cards:
		return ""

	cards = []
	# Pending (required, not yet received, due today or later)
	cards.append(_doc_alert_card("Pending", pending, "doc-alert-card-pending", "warning", "pending"))
	# Overdue (required, past due date)
	cards.append(_doc_alert_card("Overdue", overdue, "doc-alert-card-overdue", "danger", "overdue"))
	# Expiring soon (within 7 days)
	cards.append(_doc_alert_card("Expiring Soon", expiring_soon, "doc-alert-card-expiring", "info", "expiring_soon"))
	# Received/Verified/Done
	cards.append(_doc_alert_card("Received", received, "doc-alert-card-received", "success", "received"))
	# Total documents — on customs doctypes, swap accent with Exemptions (purple ↔ gray)
	total_css, total_alert = "doc-alert-card-total", "secondary"
	if doctype in ("Declaration", "Declaration Order"):
		total_css, total_alert = "doc-alert-card-exemptions", "info"
	cards.append(_doc_alert_card("Total", total, total_css, total_alert, "total"))

	# Declaration and Declaration Order: Pending Permits and Exemptions cards
	if doctype in ("Declaration", "Declaration Order"):
		cards.append(_doc_alert_card("Pending Permits", pending_permits, "doc-alert-card-permits", "warning", "pending_permits"))
		cards.append(
			_doc_alert_card("Exemptions", exemptions_count, "doc-alert-card-total", "secondary", "exemptions")
		)

	cards_html = "\n".join(cards)
	return f'''
	<style>{DOC_ALERT_CARDS_CSS}</style>
	<div class="doc-alerts-cards-wrapper" style="margin-bottom: 16px;" data-doctype="{doctype}" data-docname="{docname}">
		<div class="doc-alerts-cards">
			{cards_html}
		</div>
	</div>
	'''


def get_dashboard_alerts(doctype, docname):
	"""Return list of {level: "danger"|"warning"|"info", "msg": "..."} for dashboard banners.
	Uses Logistics Settings (Alerts and Delays Notification) for day thresholds.
	Sources: documents (overdue/expiring), milestones (delayed/impending/informational), estimated dates (ETD/ETA past)."""
	if not doctype or not docname or docname == "new":
		return []
	try:
		doc = frappe.get_doc(doctype, docname)
	except (frappe.DoesNotExistError, Exception):
		return []

	# Load milestones from DB for banner alerts (get_doc may not always populate child tables in API context)
	milestone_rows = []
	if doctype in MILESTONE_DOCTYPES and docname and docname != "new":
		child_doctype = MILESTONE_CHILD_DOCTYPE.get(doctype)
		if child_doctype:
			milestone_rows = frappe.get_all(
				child_doctype,
				filters={"parent": docname, "parenttype": doctype},
				fields=["milestone", "planned_end", "actual_end"],
				order_by="idx asc",
			)
		if not milestone_rows and (doc.get("milestones") or []):
			for m in doc.get("milestones"):
				milestone_rows.append({
					"milestone": m.get("milestone"),
					"planned_end": m.get("planned_end"),
					"actual_end": m.get("actual_end"),
				})

	alerts = []
	today_date = getdate(today())

	# 1. Document alerts: consider both required date and expiry (critical/warning/info by days)
	documents = doc.get("documents") or []
	for d in documents:
		status = (d.get("status") or "").strip()
		if status in ("Received", "Verified", "Done"):
			continue
		is_required = d.get("is_required")
		date_required = d.get("date_required")
		expiry_date = d.get("expiry_date")
		doc_type = d.get("document_type") or "—"

		# Required date: past = critical; future within Warning/Information days = warning/info
		if is_required and date_required:
			dr = getdate(date_required)
			if dr < today_date:
				days_overdue = date_diff(today_date, dr)
				alerts.append({
					"level": "danger",
					"msg": _("Document {0} was required on {1} ({2} day(s) overdue).").format(doc_type, date_required, days_overdue),
				})
			else:
				days_until_required = date_diff(dr, today_date)
				severity = alert_utils.get_severity_for_document_expiring(days_until_required)
				if severity == "impending":
					alerts.append({"level": "warning", "msg": _("Document {0} required on {1} (in {2} days).").format(doc_type, date_required, days_until_required)})
				elif severity == "informational":
					alerts.append({"level": "info", "msg": _("Document {0} required on {1} (in {2} days).").format(doc_type, date_required, days_until_required)})

		# Expiry date: past = critical; future within Warning/Information days = warning/info
		if expiry_date:
			exp = getdate(expiry_date)
			if exp >= today_date:
				days_until = date_diff(exp, today_date)
				severity = alert_utils.get_severity_for_document_expiring(days_until)
				if severity == "impending":
					alerts.append({"level": "warning", "msg": _("Document {0} expires on {1}.").format(doc_type, expiry_date)})
				elif severity == "informational":
					alerts.append({"level": "info", "msg": _("Document {0} expires on {1}.").format(doc_type, expiry_date)})
			else:
				alerts.append({"level": "danger", "msg": _("Document {0} expired on {1}.").format(doc_type, expiry_date)})

	# 2. Milestone alerts (critical=delayed, warning=impending, info=informational)
	for m in milestone_rows:
		planned_end = m.get("planned_end")
		actual_end = m.get("actual_end")
		display_status, severity = alert_utils.get_severity_for_milestone(planned_end, actual_end)
		milestone_name = m.get("milestone") or "—"
		if severity == "critical":
			alerts.append({
				"level": "danger",
				"msg": _("Milestone {0} is delayed (planned: {1}).").format(milestone_name, planned_end or "—"),
			})
		elif severity == "impending":
			alerts.append({
				"level": "warning",
				"msg": _("Milestone {0} due soon (planned: {1}).").format(milestone_name, planned_end or "—"),
			})
		elif severity == "informational":
			alerts.append({
				"level": "info",
				"msg": _("Milestone {0} upcoming (planned: {1}).").format(milestone_name, planned_end or "—"),
			})

	# 3. Estimated dates (ETD/ETA in the past) -> critical
	for date_field, label in (("etd", "ETD"), ("eta", "ETA")):
		val = getattr(doc, date_field, None)
		if not val:
			continue
		dt = getdate(val)
		if dt < today_date:
			days_past = date_diff(today_date, dt)
			alerts.append({
				"level": "danger",
				"msg": _("{0} ({1}) was {2} day(s) ago.").format(label, val, days_past),
			})

	return alerts


def get_dashboard_alerts_html(doctype, docname):
	"""Return HTML for dashboard alerts banner. Critical (red), Warning (yellow), Information (blue).
	Collapsible per level; grouping is applied by JS (_group_and_collapse_dash_alerts).
	Uses Logistics Settings day thresholds. Applies to documents, milestones, estimated dates."""
	alerts = get_dashboard_alerts(doctype, docname)
	if not alerts:
		return ""

	icons = {"danger": "fa-exclamation-circle", "warning": "fa-exclamation-triangle", "info": "fa-info-circle"}
	items = []
	for a in alerts:
		level = a.get("level") or "info"
		icon = icons.get(level, "fa-info-circle")
		items.append(
			'<div class="dash-alert-item {0}"><i class="fa {1}"></i><span>{2}</span></div>'.format(
				level, icon, frappe.utils.escape_html(a.get("msg", ""))
			)
		)
	return "\n".join(items)


def _doc_alert_card(title, count, css_class, alert_type, category):
	"""Return HTML for a single document count card (clickable, data-category for dialog)."""
	return (
		f'<div class="doc-alert-card {css_class} doc-alert-card-{alert_type}" data-category="{category}" style="cursor: pointer;">'
		f'<div class="doc-alert-card-value">{count}</div>'
		f'<div class="doc-alert-card-title">{title}</div>'
		f'</div>'
	)


@frappe.whitelist()
def get_document_list_for_category(doctype, docname, category):
	"""Return list of documents for a category (pending, overdue, expiring_soon, received, total) for dialog."""
	if not doctype or not docname or docname == "new" or not category:
		return {"documents": [], "category": category}

	doc = frappe.get_doc(doctype, docname)
	documents = doc.get("documents") or []
	today_date = getdate(today())
	out = []

	for d in documents:
		idx = d.get("idx")
		if not idx:
			continue
		status = (d.get("status") or "").strip()
		date_required = d.get("date_required")
		expiry_date = d.get("expiry_date")
		is_required = d.get("is_required")
		attachment = d.get("attachment") or ""

		row = {
			"idx": idx,
			"document_type": d.get("document_type"),
			"document_name": d.get("document_name") or d.get("document_type"),
			"status": status,
			"date_required": date_required,
			"expiry_date": expiry_date,
			"attachment": attachment,
			"has_attachment": 1 if attachment else 0,
			"is_required": is_required,
		}

		if category == "total":
			out.append(row)
			continue
		if category == "pending":
			if is_required and status in ("Pending", "Uploaded", "Overdue") and not attachment:
				if not date_required or getdate(date_required) >= today_date:
					out.append(row)
			continue
		if category == "overdue":
			if is_required and status in ("Pending", "Uploaded", "Overdue") and date_required and getdate(date_required) < today_date:
				out.append(row)
			continue
		if category == "expiring_soon":
			if expiry_date:
				exp = getdate(expiry_date)
				if exp >= today_date:
					try:
						expiring_soon_days = alert_utils.get_document_expiring_soon_days()
					except Exception:
						expiring_soon_days = 7
					if date_diff(exp, today_date) <= expiring_soon_days:
						out.append(row)
			continue
		if category == "received":
			if status in ("Received", "Verified", "Done"):
				out.append(row)

	return {"documents": out, "category": category}


@frappe.whitelist()
def set_document_attachment(doctype, docname, idx, file_url):
	"""Set attachment on a document row by child table idx. Returns ok/message."""
	if not doctype or not docname or docname == "new":
		return {"ok": False, "message": "Invalid document."}
	try:
		idx = int(idx)
	except (TypeError, ValueError):
		return {"ok": False, "message": "Invalid row index."}
	doc = frappe.get_doc(doctype, docname)
	documents = doc.get("documents") or []
	found = False
	for row in documents:
		if row.get("idx") == idx:
			row.attachment = file_url or ""
			found = True
			break
	if not found:
		return {"ok": False, "message": "Row not found."}
	doc.flags.ignore_validate = True
	doc.save()
	return {"ok": True, "message": "Attachment updated."}


@frappe.whitelist()
def get_google_maps_api_key():
	"""Get Google Maps API key from Logistics Settings for client-side map use."""
	try:
		from frappe.utils.password import get_decrypted_password
		api_key = get_decrypted_password(
			"Logistics Settings",
			"Logistics Settings",
			"routing_google_api_key",
			raise_exception=False,
		)
		if not api_key:
			api_key = get_decrypted_password(
				"Transport Settings",
				"Transport Settings",
				"routing_google_api_key",
				raise_exception=False,
			)
		if api_key and len(api_key) > 10:
			return {"api_key": api_key, "has_key": True}
		return {"api_key": None, "has_key": False}
	except Exception as e:
		frappe.log_error(f"get_google_maps_api_key: {e}", "Dashboard Map")
		return {"api_key": None, "has_key": False}


def _decode_google_polyline(encoded):
	"""Decode Google polyline encoding to list of [lat, lng] coordinates."""
	if not encoded:
		return []
	inv = 1.0 / 1e5
	coords = []
	x, y = 0, 0
	i = 0
	while i < len(encoded):
		b, shift, result = 0, 0, 0
		while True:
			b = ord(encoded[i]) - 63
			i += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		dlat = ~(result >> 1) if result & 1 else result >> 1
		x += dlat
		result, shift = 0, 0
		while True:
			b = ord(encoded[i]) - 63
			i += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		dlng = ~(result >> 1) if result & 1 else result >> 1
		y += dlng
		coords.append([x * inv, y * inv])
	return coords


@frappe.whitelist()
def get_route_geometry(waypoints):
	"""
	Get road-following route geometry for waypoints (same logic as Run Sheet).
	Uses Google Directions API when key is configured, else OSRM public API.
	Returns coordinates suitable for polyline drawing on any map.

	Args:
		waypoints: "lat,lon|lat,lon|..." or list of [lat, lon]

	Returns:
		dict: {success, coordinates: [[lat,lng],...], error?}
	"""
	try:
		points = []
		if isinstance(waypoints, str):
			for p in waypoints.split("|"):
				p = p.strip()
				if not p:
					continue
				parts = p.split(",")
				if len(parts) >= 2:
					lat = float(parts[0].strip())
					lon = float(parts[1].strip())
					if -90 <= lat <= 90 and -180 <= lon <= 180:
						points.append((lat, lon))
		elif isinstance(waypoints, (list, tuple)):
			for wp in waypoints:
				if isinstance(wp, (list, tuple)) and len(wp) >= 2:
					lat, lon = float(wp[0]), float(wp[1])
					if -90 <= lat <= 90 and -180 <= lon <= 180:
						points.append((lat, lon))
				elif isinstance(wp, dict):
					lat = wp.get("lat") or wp.get("latitude")
					lon = wp.get("lon") or wp.get("lng") or wp.get("longitude")
					if lat is not None and lon is not None:
						lat, lon = float(lat), float(lon)
						if -90 <= lat <= 90 and -180 <= lon <= 180:
							points.append((lat, lon))

		if len(points) < 2:
			return {"success": False, "error": "Need at least 2 waypoints", "coordinates": []}

		# Try Google Directions API first (same as Run Sheet)
		try:
			from logistics.transport.api_vehicle_tracking import get_google_route_polyline
			wp_str = "|".join(f"{p[0]},{p[1]}" for p in points)
			res = get_google_route_polyline(wp_str)
			if res and res.get("success") and res.get("polyline"):
				coords = _decode_google_polyline(res["polyline"])
				if coords:
					return {"success": True, "coordinates": coords}
		except Exception:
			pass

		# Fallback: OSRM public API (no key required)
		try:
			import requests
			coords_str = ";".join(f"{p[1]},{p[0]}" for p in points)  # lon,lat for OSRM
			url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
			r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=10)
			if r.ok:
				js = r.json()
				routes = (js or {}).get("routes") or []
				if routes:
					geom = routes[0].get("geometry") or {}
					coords_raw = geom.get("coordinates") or []
					# GeoJSON is [lon, lat]
					coords = [[c[1], c[0]] for c in coords_raw if len(c) >= 2]
					if coords:
						return {"success": True, "coordinates": coords}
		except Exception:
			pass

		# Final fallback: straight line between points
		return {"success": True, "coordinates": [[p[0], p[1]] for p in points]}

	except Exception as e:
		frappe.log_error(f"get_route_geometry: {e}", "Route Geometry")
		return {"success": False, "error": str(e), "coordinates": []}
