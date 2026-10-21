# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Job Task rows on bookings and the execution jobs they become.

The rows are a child table, filled from Job Task Template the same way
milestones are filled from Milestone Template. Programme documents are not
included.
"""

from __future__ import unicode_literals

import frappe
from frappe import _

# doctype -> (product_type, applies_to)
JOB_TASK_PARENTS = {
	"Air Booking": ("Air Freight", "Booking"),
	"Sea Booking": ("Sea Freight", "Booking"),
	"Transport Order": ("Transport", "Booking"),
	"Declaration Order": ("Customs", "Booking"),
	"Inbound Order": ("Warehousing", "Booking"),
	"Release Order": ("Warehousing", "Booking"),
	"Transfer Order": ("Warehousing", "Booking"),
	"Cross-Docking Order": ("Warehousing", "Booking"),
	"VAS Order": ("Warehousing", "Booking"),
	"Stocktake Order": ("Warehousing", "Booking"),
	"Project Order": ("Special Projects", "Booking"),
	"MICE Order": ("MICE", "Shipment/Job"),
	"Air Shipment": ("Air Freight", "Shipment/Job"),
	"Air Consolidation": ("Air Freight", "Shipment/Job"),
	"Sea Shipment": ("Sea Freight", "Shipment/Job"),
	"Sea Consolidation": ("Sea Freight", "Shipment/Job"),
	"Transport Job": ("Transport", "Shipment/Job"),
	"Transport Consolidation": ("Transport", "Shipment/Job"),
	"Warehouse Job": ("Warehousing", "Shipment/Job"),
	"Declaration": ("Customs", "Shipment/Job"),
	"General Job": ("General", "Shipment/Job"),
	"Project Job": ("Special Projects", "Shipment/Job"),
	"MICE Job": ("MICE", "Shipment/Job"),
	"Exhibit Job": ("Exhibits", "Shipment/Job"),
	"Time Sensitive Case": ("General", "Shipment/Job"),
}

# Default checklist rows seeded once per parent. task_code is the merge key.
DEFAULT_TASKS = {
	"Air Booking": (
		{"task_code": "CONFIRM_BOOKING", "subject": "Confirm booking details", "description": "Check shipper, consignee, pieces, and weight against the booking request.", "sequence": 10, "is_required": 1},
		{"task_code": "ARRANGE_SPACE", "subject": "Arrange airline space", "description": "Secure space with the airline or GSA and record the flight.", "sequence": 20, "is_required": 1},
		{"task_code": "ISSUE_AWB", "subject": "Prepare air waybill", "description": "Prepare the air waybill from the confirmed booking.", "sequence": 30, "is_required": 1},
		{"task_code": "CONFIRM_CUTOFF", "subject": "Confirm cargo cutoff", "description": "Tell the shipper the acceptance cutoff and delivery point.", "sequence": 40, "is_required": 1},
	),
	"Sea Booking": (
		{"task_code": "CONFIRM_BOOKING", "subject": "Confirm booking details", "description": "Check parties, equipment, and cargo against the booking request.", "sequence": 10, "is_required": 1},
		{"task_code": "ARRANGE_SPACE", "subject": "Arrange vessel space", "description": "Secure space with the carrier and record the vessel and voyage.", "sequence": 20, "is_required": 1},
		{"task_code": "ISSUE_HBL", "subject": "Prepare house bill", "description": "Prepare the house bill of lading from the confirmed booking.", "sequence": 30, "is_required": 1},
		{"task_code": "CONFIRM_CUTOFF", "subject": "Confirm cargo cutoff", "description": "Tell the shipper the CY or CFS cutoff and delivery point.", "sequence": 40, "is_required": 1},
	),
	"Transport Order": (
		{"task_code": "CONFIRM_ORDER", "subject": "Confirm order", "description": "Confirm pickup, delivery, and cargo with the customer.", "sequence": 10, "is_required": 1},
		{"task_code": "PLAN_LEGS", "subject": "Plan legs", "description": "Set the legs, stops, and requested times.", "sequence": 20, "is_required": 1},
		{"task_code": "ASSIGN_CARRIER", "subject": "Assign carrier", "description": "Choose the carrier or own fleet for the order.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create transport job", "description": "Create the transport job once the order is ready to execute.", "sequence": 40, "is_required": 1},
	),
	"Declaration Order": (
		{"task_code": "REVIEW_INVOICE", "subject": "Review commercial invoice", "description": "Check the invoice, packing list, and permits against the order.", "sequence": 10, "is_required": 1},
		{"task_code": "CLASSIFY", "subject": "Classify goods", "description": "Confirm tariff classification and duty treatment.", "sequence": 20, "is_required": 1},
		{"task_code": "PREPARE_ENTRY", "subject": "Prepare entry", "description": "Prepare the customs entry data before filing.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_DECLARATION", "subject": "Create declaration", "description": "Create the declaration once the entry is ready to lodge.", "sequence": 40, "is_required": 1},
	),
	"Inbound Order": (
		{"task_code": "CONFIRM_ASN", "subject": "Confirm expected receipt", "description": "Confirm the expected items, quantities, and arrival window.", "sequence": 10, "is_required": 1},
		{"task_code": "BOOK_DOCK", "subject": "Book dock", "description": "Reserve a dock for the inbound vehicle.", "sequence": 20, "is_required": 1},
		{"task_code": "CHECK_DOCS", "subject": "Check receiving documents", "description": "Check the delivery note and packing list before unload.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create warehouse job", "description": "Create the warehouse job for receiving.", "sequence": 40, "is_required": 1},
	),
	"Release Order": (
		{"task_code": "CONFIRM_RELEASE", "subject": "Confirm release request", "description": "Confirm the items, quantities, and consignee on the release.", "sequence": 10, "is_required": 1},
		{"task_code": "ALLOCATE", "subject": "Allocate stock", "description": "Allocate stock to the release.", "sequence": 20, "is_required": 1},
		{"task_code": "BOOK_DOCK", "subject": "Book dock", "description": "Reserve a dock for the outbound vehicle.", "sequence": 30, "is_required": 0},
		{"task_code": "CREATE_JOB", "subject": "Create warehouse job", "description": "Create the warehouse job for picking and dispatch.", "sequence": 40, "is_required": 1},
	),
	"Transfer Order": (
		{"task_code": "CONFIRM_TRANSFER", "subject": "Confirm transfer", "description": "Confirm the source, destination, and quantities.", "sequence": 10, "is_required": 1},
		{"task_code": "ALLOCATE", "subject": "Allocate stock", "description": "Allocate the stock to move.", "sequence": 20, "is_required": 1},
		{"task_code": "PLAN_MOVE", "subject": "Plan move", "description": "Plan the locations and handling for the move.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create warehouse job", "description": "Create the warehouse job for the transfer.", "sequence": 40, "is_required": 1},
	),
	"Cross-Docking Order": (
		{"task_code": "CONFIRM_CROSSDOCK", "subject": "Confirm cross-dock", "description": "Confirm inbound cargo and the outbound plan.", "sequence": 10, "is_required": 1},
		{"task_code": "MATCH_INBOUND", "subject": "Match inbound", "description": "Match the inbound receipt to this order.", "sequence": 20, "is_required": 1},
		{"task_code": "PLAN_OUTBOUND", "subject": "Plan outbound", "description": "Plan the outbound dispatch from the cross-dock.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create warehouse job", "description": "Create the warehouse job for the cross-dock.", "sequence": 40, "is_required": 1},
	),
	"VAS Order": (
		{"task_code": "CONFIRM_VAS", "subject": "Confirm value-added work", "description": "Confirm the service, quantities, and instructions.", "sequence": 10, "is_required": 1},
		{"task_code": "PLAN_WORK", "subject": "Plan work", "description": "Plan the work sequence and location.", "sequence": 20, "is_required": 1},
		{"task_code": "CHECK_MATERIALS", "subject": "Check materials", "description": "Check materials and packaging needed for the work.", "sequence": 30, "is_required": 0},
		{"task_code": "CREATE_JOB", "subject": "Create warehouse job", "description": "Create the warehouse job for the value-added work.", "sequence": 40, "is_required": 1},
	),
	"Stocktake Order": (
		{"task_code": "PLAN_COUNT", "subject": "Plan count", "description": "Confirm the locations and items in the count.", "sequence": 10, "is_required": 1},
		{"task_code": "FREEZE_LOCATIONS", "subject": "Freeze locations", "description": "Stop movements in the locations being counted.", "sequence": 20, "is_required": 1},
		{"task_code": "ASSIGN_COUNTERS", "subject": "Assign counters", "description": "Assign the people who will count.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create warehouse job", "description": "Create the warehouse job for the stocktake.", "sequence": 40, "is_required": 1},
	),
	"Project Order": (
		{"task_code": "CONFIRM_ORDER", "subject": "Confirm project order", "description": "Confirm scope, site, and dates with the customer.", "sequence": 10, "is_required": 1},
		{"task_code": "PLAN_RESOURCES", "subject": "Plan resources", "description": "Plan people, equipment, and materials for the order.", "sequence": 20, "is_required": 1},
		{"task_code": "CONFIRM_SCHEDULE", "subject": "Confirm schedule", "description": "Confirm the schedule with the site.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create project job", "description": "Create the project job once the order is ready to execute.", "sequence": 40, "is_required": 1},
	),
	"MICE Order": (
		{"task_code": "CONFIRM_ORDER", "subject": "Confirm order", "description": "Confirm the event services, venue, and dates.", "sequence": 10, "is_required": 1},
		{"task_code": "PLAN_SERVICES", "subject": "Plan services", "description": "Plan freight, warehousing, and on-site services.", "sequence": 20, "is_required": 1},
		{"task_code": "CONFIRM_SCHEDULE", "subject": "Confirm schedule", "description": "Confirm the move-in and move-out schedule.", "sequence": 30, "is_required": 1},
		{"task_code": "CREATE_JOB", "subject": "Create MICE job", "description": "Create the MICE job once the order is ready to execute.", "sequence": 40, "is_required": 1},
	),
	"Air Shipment": (
		{"task_code": "CONFIRM_DEPARTURE", "subject": "Confirm departure", "description": "Confirm the flight has departed with the booked cargo.", "sequence": 10, "is_required": 1},
		{"task_code": "TRACK_FLIGHT", "subject": "Track flight", "description": "Track the flight until arrival.", "sequence": 20, "is_required": 1},
		{"task_code": "FILE_ARRIVAL", "subject": "File arrival documents", "description": "File the documents needed for arrival and delivery.", "sequence": 30, "is_required": 1},
		{"task_code": "RELEASE_CARGO", "subject": "Release cargo", "description": "Release the cargo to the consignee or onward carrier.", "sequence": 40, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close shipment", "description": "Close the shipment after delivery and billing checks.", "sequence": 50, "is_required": 1},
	),
	"Air Consolidation": (
		{"task_code": "BUILD_CONSOL", "subject": "Build consolidation", "description": "Open the consolidation and set the master route.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_SHIPMENTS", "subject": "Assign shipments", "description": "Attach the house shipments that move on this consolidation.", "sequence": 20, "is_required": 1},
		{"task_code": "CONFIRM_MAWB", "subject": "Confirm master air waybill", "description": "Confirm the master air waybill details.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_CONSOL", "subject": "Close consolidation", "description": "Close the consolidation after the houses are accounted for.", "sequence": 40, "is_required": 1},
	),
	"Sea Shipment": (
		{"task_code": "CONFIRM_SAILING", "subject": "Confirm sailing", "description": "Confirm the vessel has sailed with the booked cargo.", "sequence": 10, "is_required": 1},
		{"task_code": "FILE_DOCUMENTS", "subject": "File shipment documents", "description": "File bills, manifests, and arrival documents.", "sequence": 20, "is_required": 1},
		{"task_code": "ARRIVAL_NOTICE", "subject": "Send arrival notice", "description": "Send the arrival notice to the consignee.", "sequence": 30, "is_required": 1},
		{"task_code": "RELEASE_CARGO", "subject": "Release cargo", "description": "Release the cargo after freight and charges are cleared.", "sequence": 40, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close shipment", "description": "Close the shipment after delivery and billing checks.", "sequence": 50, "is_required": 1},
	),
	"Sea Consolidation": (
		{"task_code": "BUILD_CONSOL", "subject": "Build consolidation", "description": "Open the consolidation and set the master route.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_SHIPMENTS", "subject": "Assign shipments", "description": "Attach the house shipments that move on this consolidation.", "sequence": 20, "is_required": 1},
		{"task_code": "CONFIRM_MBL", "subject": "Confirm master bill", "description": "Confirm the master bill of lading details.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_CONSOL", "subject": "Close consolidation", "description": "Close the consolidation after the houses are accounted for.", "sequence": 40, "is_required": 1},
	),
	"Transport Job": (
		{"task_code": "CONFIRM_PICKUP", "subject": "Confirm pickup", "description": "Confirm the pickup window and site contact.", "sequence": 10, "is_required": 1},
		{"task_code": "DISPATCH", "subject": "Dispatch vehicle", "description": "Dispatch the vehicle and driver.", "sequence": 20, "is_required": 1},
		{"task_code": "PROOF_OF_DELIVERY", "subject": "Collect proof of delivery", "description": "Collect the signed proof of delivery.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close job", "description": "Close the job after delivery and billing checks.", "sequence": 40, "is_required": 1},
	),
	"Transport Consolidation": (
		{"task_code": "BUILD_CONSOL", "subject": "Build consolidation", "description": "Open the consolidation and set the trunk route.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_JOBS", "subject": "Assign transport jobs", "description": "Attach the transport jobs that move together.", "sequence": 20, "is_required": 1},
		{"task_code": "CONFIRM_ROUTE", "subject": "Confirm route", "description": "Confirm the route, departure, and vehicle.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_CONSOL", "subject": "Close consolidation", "description": "Close the consolidation after the jobs are delivered.", "sequence": 40, "is_required": 1},
	),
	"Warehouse Job": (
		{"task_code": "START_JOB", "subject": "Start warehouse job", "description": "Start the job and confirm the team and location.", "sequence": 10, "is_required": 1},
		{"task_code": "CONFIRM_QTY", "subject": "Confirm quantities", "description": "Confirm counted or picked quantities.", "sequence": 20, "is_required": 1},
		{"task_code": "COMPLETE_OPS", "subject": "Complete operations", "description": "Complete the warehouse operations on the job.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close job", "description": "Close the job after the operations and billing checks.", "sequence": 40, "is_required": 1},
	),
	"Declaration": (
		{"task_code": "LODGE_ENTRY", "subject": "Lodge entry", "description": "Lodge the customs entry.", "sequence": 10, "is_required": 1},
		{"task_code": "RESPOND_QUERY", "subject": "Respond to customs query", "description": "Answer any query from customs.", "sequence": 20, "is_required": 0},
		{"task_code": "CONFIRM_RELEASE", "subject": "Confirm release", "description": "Confirm customs has released the goods.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_FILE", "subject": "Close declaration", "description": "Close the declaration after release and billing checks.", "sequence": 40, "is_required": 1},
	),
	"General Job": (
		{"task_code": "CONFIRM_SCOPE", "subject": "Confirm scope", "description": "Confirm what this job covers.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_OWNER", "subject": "Assign owner", "description": "Assign the person responsible for the job.", "sequence": 20, "is_required": 1},
		{"task_code": "COMPLETE_WORK", "subject": "Complete work", "description": "Complete the work described on the job.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close job", "description": "Close the job after the work and billing checks.", "sequence": 40, "is_required": 1},
	),
	"Project Job": (
		{"task_code": "CONFIRM_TASK", "subject": "Confirm task", "description": "Confirm the site task and access.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_RESOURCES", "subject": "Assign resources", "description": "Assign people and equipment.", "sequence": 20, "is_required": 1},
		{"task_code": "EXECUTE", "subject": "Execute work", "description": "Complete the site work.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close job", "description": "Close the job after the site work and billing checks.", "sequence": 40, "is_required": 1},
	),
	"MICE Job": (
		{"task_code": "CONFIRM_SCOPE", "subject": "Confirm scope", "description": "Confirm the on-site scope and venue contact.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_RESOURCES", "subject": "Assign resources", "description": "Assign people and equipment.", "sequence": 20, "is_required": 1},
		{"task_code": "EXECUTE", "subject": "Execute work", "description": "Complete the event work.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close job", "description": "Close the job after the event work and billing checks.", "sequence": 40, "is_required": 1},
	),
	"Exhibit Job": (
		{"task_code": "CONFIRM_SCOPE", "subject": "Confirm exhibit scope", "description": "Confirm the exhibit work, booth, and access.", "sequence": 10, "is_required": 1},
		{"task_code": "ASSIGN_RESOURCES", "subject": "Assign resources", "description": "Assign people and equipment.", "sequence": 20, "is_required": 1},
		{"task_code": "EXECUTE", "subject": "Execute work", "description": "Complete the exhibit work.", "sequence": 30, "is_required": 1},
		{"task_code": "CLOSE_JOB", "subject": "Close job", "description": "Close the job after the exhibit work and billing checks.", "sequence": 40, "is_required": 1},
	),
	"Time Sensitive Case": (
		{"task_code": "ACKNOWLEDGE", "subject": "Acknowledge case", "description": "Acknowledge the case and the customer contact.", "sequence": 10, "is_required": 1},
		{"task_code": "CONFIRM_SLA", "subject": "Confirm SLA", "description": "Confirm the response and completion times.", "sequence": 20, "is_required": 1},
		{"task_code": "COORDINATE", "subject": "Coordinate services", "description": "Coordinate the services linked to the case.", "sequence": 30, "is_required": 1},
		{"task_code": "UPDATE_STAKEHOLDERS", "subject": "Update stakeholders", "description": "Send a status update to the stakeholders.", "sequence": 40, "is_required": 1},
		{"task_code": "CLOSE_CASE", "subject": "Close case", "description": "Close the case after the service is complete.", "sequence": 50, "is_required": 1},
	),
}


def _text(value):
	return (value or "").strip()


def _context_ok(template_value, doc_value):
	"""Blank and All templates match any parent value. A set parent value excludes other specifics."""
	value = _text(template_value)
	wanted = _text(doc_value)
	if not wanted or wanted == "All":
		return True
	return value in ("", "All", wanted)


def _field_rank(template_value, doc_value):
	value = _text(template_value)
	wanted = _text(doc_value)
	if wanted and wanted != "All":
		if value == wanted:
			return 2
		if value == "All":
			return 1
		return 0
	if not value or value == "All":
		return 1
	return 0


def _rank(template, doctype, direction, entry_type):
	applies = _text(template.get("applies_to_doctype"))
	return (
		1 if applies == doctype else 0,
		_field_rank(template.get("direction"), direction),
		_field_rank(template.get("entry_type"), entry_type),
		1 if int(template.get("is_default") or 0) else 0,
	)


def choose_job_task_template(doctype, templates, direction=None, entry_type=None):
	"""Pick one template. DocType-specific defaults beat a generic default."""
	kept = []
	for template in templates or []:
		applies = _text(template.get("applies_to_doctype"))
		if applies and applies != doctype:
			continue
		if not _context_ok(template.get("direction"), direction):
			continue
		if not _context_ok(template.get("entry_type"), entry_type):
			continue
		kept.append(template)
	if not kept:
		return None
	return max(kept, key=lambda template: _rank(template, doctype, direction, entry_type))


def tasks_to_insert(existing_rows, template_items):
	"""Return template rows whose task_code is not already on the parent."""
	existing = set()
	for row in existing_rows or []:
		code = _text(row.get("task_code") if isinstance(row, dict) else getattr(row, "task_code", None))
		if code:
			existing.add(code)
	missing = []
	for item in template_items or []:
		code = _text(item.get("task_code") if isinstance(item, dict) else getattr(item, "task_code", None))
		if not code or code in existing:
			continue
		existing.add(code)
		missing.append(item)
	return missing


def _load_candidate_templates(product_type, applies_to):
	return frappe.get_all(
		"Job Task Template",
		filters=[
			["product_type", "=", product_type],
			["applies_to", "in", [applies_to, "Both"]],
			["is_active", "=", 1],
		],
		fields=["name", "template_name", "is_default", "direction", "entry_type", "applies_to_doctype"],
		ignore_permissions=True,
	)


def _load_template_items(template_name):
	return frappe.get_all(
		"Job Task Template Item",
		filters={"parent": template_name},
		fields=["task_code", "subject", "description", "sequence", "is_required", "assignee_role"],
		order_by="sequence asc, idx asc",
		ignore_permissions=True,
	)


def _parent_value(doc, fieldname):
	if doc is None:
		return None
	getter = getattr(doc, "get", None)
	if callable(getter):
		return getter(fieldname)
	return getattr(doc, fieldname, None)


def _has_job_tasks(doc):
	meta = getattr(doc, "meta", None)
	if meta is not None and hasattr(meta, "has_field"):
		return bool(meta.has_field("job_tasks"))
	return _parent_value(doc, "job_tasks") is not None


def _row_value(row, fieldname):
	if isinstance(row, dict):
		return row.get(fieldname)
	getter = getattr(row, "get", None)
	if callable(getter):
		return getter(fieldname)
	return getattr(row, fieldname, None)


def _template_items_for_doc(doc):
	"""Use the template selected on the document, otherwise the matching default.

	Declaration Type Application uses the permit-application-only checklist
	unless a Job Task Template is selected on the document.
	"""
	explicit = _text(_parent_value(doc, "job_task_template"))
	if explicit:
		return explicit, _load_template_items(explicit)
	from logistics.customs.permit_application_only import permit_application_only_template

	permit_only = permit_application_only_template(doc)
	if permit_only:
		return permit_only
	product_type, applies_to = JOB_TASK_PARENTS[doc.doctype]
	template = choose_job_task_template(
		doc.doctype,
		_load_candidate_templates(product_type, applies_to),
		direction=_parent_value(doc, "direction") or "",
		entry_type=_parent_value(doc, "entry_type") or "",
	)
	if not template:
		return None, []
	template_name = template.get("name")
	return template_name, _load_template_items(template_name)


def append_missing_job_tasks(doc):
	"""Append template rows whose task_code is not already on the child table.

	Does not save and does not change rows that are already there.
	"""
	if not doc or doc.doctype not in JOB_TASK_PARENTS or not _has_job_tasks(doc):
		return {"message": _("Job Tasks are not used on this document."), "added": 0, "template": None}
	template_name, items = _template_items_for_doc(doc)
	if not template_name:
		return {"message": _("No Job Task Template matched."), "added": 0, "template": None}
	missing = tasks_to_insert(doc.get("job_tasks") or [], items)
	for item in missing:
		doc.append(
			"job_tasks",
			{
				"task_code": item.get("task_code"),
				"subject": item.get("subject"),
				"description": item.get("description"),
				"sequence": item.get("sequence") or 0,
				"status": "Open",
				"is_required": 1 if int(item.get("is_required") or 0) else 0,
				"source": "Fetched",
			},
		)
	return {
		"message": _("Added {0} job task(s).").format(len(missing)),
		"added": len(missing),
		"template": template_name,
	}


def reject_duplicate_job_task_codes(doc):
	seen = set()
	for row in doc.get("job_tasks") or []:
		code = _text(_row_value(row, "task_code"))
		if not code:
			continue
		if code in seen:
			frappe.throw(
				_("Job Task {0} is already on this document.").format(code),
				title=_("Job Task"),
			)
		seen.add(code)


def _populate_job_tasks(doctype, docname, doc=None, check_permission=True):
	if not doctype or not docname or docname == "new":
		return {"message": _("Save the document first."), "added": 0}
	if doctype not in JOB_TASK_PARENTS:
		return {"message": _("Job Tasks are not used on this document."), "added": 0}
	if doc is None:
		doc = frappe.get_doc(doctype, docname)
	if check_permission:
		from logistics.utils.menu_permission import assert_perm

		assert_perm(doctype, "write", doc=doc)
	result = append_missing_job_tasks(doc)
	if result.get("added") and not frappe.flags.get("in_ensure_job_tasks"):
		doc.save()
	return result


@frappe.whitelist()
def populate_job_tasks(doctype, docname):
	"""Add missing Job Task rows from the template. Existing rows are left as they are."""
	return _populate_job_tasks(doctype, docname, check_permission=True)


def ensure_job_tasks_from_template(doc, method=None):
	"""before_save: append missing Job Task rows in the same save as milestones."""
	if not doc or not getattr(doc, "doctype", None):
		return
	if doc.doctype not in JOB_TASK_PARENTS or not _has_job_tasks(doc):
		return
	flags = getattr(doc, "flags", None)
	if flags and flags.get("ignore_job_tasks"):
		return
	if getattr(frappe.flags, "in_ensure_job_tasks", False):
		return
	name = getattr(doc, "name", None)
	if not name or name == "new":
		return
	frappe.flags.in_ensure_job_tasks = True
	try:
		reject_duplicate_job_task_codes(doc)
		append_missing_job_tasks(doc)
	except frappe.ValidationError:
		raise
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Job Task populate")
	finally:
		frappe.flags.in_ensure_job_tasks = False
