# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Lock submitted jobs/shipments against direct user edits; amendments go via Change Request."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint

# Main operational docs gated after submit (docstatus >= 1).
LOCKED_JOB_TYPES = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Warehouse Job",
		"Declaration",
		"Run Sheet",
	}
)

# Standard Document / system fields never treated as user amendments.
_META_SKIP_FIELDS = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"amended_from",
		"naming_series",
		"parent",
		"parentfield",
		"parenttype",
	}
)

# Execution / system fields that may still change without a Change Request.
EXEMPT_FIELDS = frozenset(
	{
		# Lifecycle
		"job_status",
		"status",
		"shipping_status",
		"tracking_status",
		"consolidation_status",
		"billing_status",
		# Tracking / SLA runtime
		"tracking_number",
		"tracking_url",
		"tracking_provider",
		"real_time_tracking_enabled",
		"last_tracking_update",
		"sla_status",
		"sla_notes",
		"sla_target_date",
		"sla_target_source",
		# Actuals (execution)
		"atd",
		"ata",
		"actual_completion_time",
		# Run Sheet runtime / map
		"route_optimization_score",
		"selected_route_polyline",
		"selected_route_index",
		"driver_name",
		# Templates / display that hooks maintain
		"document_list_template",
		"milestone_template",
		# Recognition / financial rollups (system)
		"wip_recognition_enabled",
		"accrual_recognition_enabled",
		"recognition_policy_reference",
		"recognition_date_basis",
		"recognition_date",
		"estimated_revenue",
		"estimated_costs",
		"wip_amount",
		"accrual_amount",
		"recognized_revenue",
		"recognized_costs",
		"wip_journal_entry",
		"wip_closed",
		"accrual_closed",
		"is_high_value",
		"chargeable",
		"total_packages",
		"total_volume",
		"total_weight",
		"total_distance",
		"fuel_consumption",
		"estimated_carbon_footprint",
		"estimated_fuel_consumption",
		# Sea delay / penalty computed
		"has_delays",
		"delay_count",
		"last_delay_check",
		"delay_alert_sent",
		"has_penalties",
		"detention_days",
		"demurrage_days",
		"free_time_days",
		"penalty_alert_sent",
		"last_penalty_check",
		"estimated_penalty_amount",
		# Address/contact display mirrors
		"shipper_address_display",
		"consignee_address_display",
		"shipper_contact_display",
		"consignee_contact_display",
		"terms",
		"service_level_details",
		# Service role wiring (system)
		"service_role",
		"main_service_type",
		"main_service",
		"linked_service",
		"job_number",
		"branch",
		"cost_center",
		"profit_center",
	}
)

# Child tables maintained by execution / document hooks (not CR-gated in this phase).
EXEMPT_TABLES = frozenset(
	{
		"milestones",
		"documents",
		"operational_exchange_rates",
		"reference_numbers",
	}
)

# Extra child tables exempt per DocType (e.g. Run Sheet leg start/complete stays operational).
EXEMPT_TABLES_BY_DOCTYPE = {
	"Run Sheet": frozenset({"legs"}),
}


def is_job_change_locked(doc):
	"""True when the job is submitted and must not accept direct user amendments."""
	if not doc or getattr(doc, "doctype", None) not in LOCKED_JOB_TYPES:
		return False
	if getattr(doc, "flags", None) and (
		doc.flags.get("from_change_request")
		or doc.flags.get("ignore_job_change_lock")
		or doc.flags.get("in_import")
	):
		return False
	if frappe.flags.get("from_change_request") or frappe.flags.get("in_install") or frappe.flags.get("in_migrate"):
		return False
	if getattr(doc, "docstatus", None) != 1:
		return False
	# Brand-new submit path: before_insert/submit of first version — allow transition Draft→Submitted fields.
	# After submit, further saves are locked.
	if doc.is_new():
		return False
	return True


def validate_job_locked_against_user_edits(doc, method=None):
	"""DocType validate hook: block non-exempt field/table changes on submitted jobs."""
	if not is_job_change_locked(doc):
		return

	before = doc.get_doc_before_save()
	if not before:
		return

	# First submit (Draft → Submitted): accept the form as-is. Lock only applies to
	# already-submitted documents being saved/updated again.
	if cint(getattr(before, "docstatus", 0)) == 0:
		return

	changed = _changed_locked_paths(before, doc)
	if not changed:
		return

	preview = ", ".join(changed[:8])
	more = _(" (+{0} more)").format(len(changed) - 8) if len(changed) > 8 else ""
	frappe.throw(
		_(
			"This {0} is locked after submit. Changed: {1}{2}. "
			"Use Change Request to propose amendments."
		).format(doc.doctype, preview, more),
		title=_("Job locked"),
	)


def _changed_locked_paths(before, doc):
	meta = frappe.get_meta(doc.doctype)
	changed = []

	for df in meta.fields:
		fn = df.fieldname
		if not fn or fn in _META_SKIP_FIELDS or fn in EXEMPT_FIELDS:
			continue
		if df.fieldtype in (
			"Section Break",
			"Column Break",
			"Tab Break",
			"HTML",
			"Button",
			"Heading",
			"Fold",
		):
			continue
		if df.fieldtype == "Table":
			exempt_tables = EXEMPT_TABLES | EXEMPT_TABLES_BY_DOCTYPE.get(doc.doctype, frozenset())
			if fn in exempt_tables:
				continue
			if _child_table_changed(before.get(fn), doc.get(fn)):
				changed.append(df.label or fn)
			continue
		if _scalar_changed(before.get(fn), doc.get(fn)):
			changed.append(df.label or fn)

	return changed


def _is_number(value):
	return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scalar_changed(old, new):
	if old is None and new in (None, ""):
		return False
	if new is None and old in (None, ""):
		return False
	# DB floats (61.0) vs JSON ints (61) must not count as edits.
	if _is_number(old) and _is_number(new):
		return float(old) != float(new)
	if _is_number(old) or _is_number(new):
		try:
			return float(old) != float(new)
		except (TypeError, ValueError):
			pass
	return str(old or "") != str(new or "")


def _child_table_changed(old_rows, new_rows):
	old_rows = old_rows or []
	new_rows = new_rows or []
	if len(old_rows) != len(new_rows):
		return True
	old_by_name = {r.name: r for r in old_rows if getattr(r, "name", None)}
	for row in new_rows:
		name = getattr(row, "name", None)
		if not name or name not in old_by_name:
			return True
		prev = old_by_name[name]
		# Compare as dict excluding meta
		for key, val in row.as_dict().items():
			if key in _META_SKIP_FIELDS:
				continue
			if _scalar_changed(prev.get(key), val):
				return True
	return False


@frappe.whitelist()
def get_open_change_requests(job_type, job_name):
	"""Return draft / submitted CRs for the job (for the Change Request dialog)."""
	if not job_type or not job_name:
		return {"drafts": [], "pending": []}
	rows = frappe.get_all(
		"Change Request",
		filters={
			"job_type": job_type,
			"job": job_name,
			"docstatus": ["<", 2],
		},
		fields=["name", "status", "docstatus", "reason", "modified", "owner"],
		order_by="modified desc",
		limit_page_length=20,
	)
	drafts = [r for r in rows if cint_docstatus(r) == 0]
	pending = [r for r in rows if cint_docstatus(r) == 1]
	return {"drafts": drafts, "pending": pending}


def cint_docstatus(row):
	try:
		return int(row.get("docstatus") or 0)
	except Exception:
		return 0
