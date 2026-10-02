# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Match Permit Applications to operational documents by party, commodity, and shipment tags.

A permit matches when every tag kind it actually has is present on the document.
Within one kind, any tagged record is enough. A permit with no tags matches nothing.
"""

from __future__ import annotations

from collections import defaultdict
from html import escape

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, today

# Importer = Consignee, Exporter = Shipper, items = Commodity.
ENTITY_TYPE_OPTIONS = (
	"Consignee",
	"Shipper",
	"Freight Agent",
	"Customer",
	"Company",
	"Commodity",
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Job Number",
)

ENTITY_KIND = {
	"Consignee": "importer",
	"Shipper": "exporter",
	"Freight Agent": "freight_agent",
	"Customer": "customer",
	"Company": "company",
	"Commodity": "commodity",
	"Air Shipment": "shipment",
	"Sea Shipment": "shipment",
	"Transport Job": "shipment",
	"Warehouse Job": "shipment",
	"Job Number": "shipment",
}

PERMIT_TYPE_FLAG_BY_KIND = {
	"importer": "applies_to_importer",
	"exporter": "applies_to_exporter",
	"freight_agent": "applies_to_freight_agent",
	"customer": "applies_to_customer",
	"company": "applies_to_company",
	"commodity": "applies_to_commodity",
	"shipment": "applies_to_shipment",
}

PERMIT_TYPE_FLAGS = tuple(PERMIT_TYPE_FLAG_BY_KIND.values())

SHIPMENT_DOCTYPES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Job Number",
)

KIND_ENTITY_TYPES = {}
for _entity_type, _kind in ENTITY_KIND.items():
	KIND_ENTITY_TYPES.setdefault(_kind, []).append(_entity_type)

ACTION_FIELD = {
	"missing": "missing_permit",
	"pending": "pending_permit",
	"expiring": "expiring_permit",
	"expired": "expired_permit",
}

_CONDITION_RANK = {"valid": 0, "expiring": 1, "expired": 2, "pending": 3}
_VALID_STATUSES = ("Approved", "Renewed")
_PENDING_STATUSES = ("Draft", "Submitted", "Under Review")
_CHILD_COMMODITY_FIELDS = ("commodity", "commodity_code")
_CHILD_COUNTRY_FIELDS = ("origin_country", "destination_country", "country")
_HEADER_COUNTRY_FIELDS = (
	"country_of_origin",
	"country_of_destination",
	"origin_country",
	"destination_country",
)
_LINKED_SHIPMENT_FIELDS = (
	"job_number",
	"air_shipment",
	"sea_shipment",
	"transport_job",
	"warehouse_job",
)


def build_document_context(doc):
	"""Parties, commodities, countries, and shipment ids present on an operational document."""
	context = {
		"doctype": doc.get("doctype"),
		"direction": _document_direction(doc),
		"importer": _values(doc, "consignee", "importer_consignee"),
		"exporter": _values(doc, "shipper", "exporter_shipper"),
		"freight_agent": _values(doc, "freight_agent", "freight_agent_sea"),
		"customer": _values(doc, "customer", "local_customer"),
		"company": _values(doc, "company"),
		"commodity": set(),
		"shipment": set(),
		"countries": set(),
	}
	if doc.get("doctype") in SHIPMENT_DOCTYPES:
		name = doc.get("name")
		if name and name not in ("new", "None"):
			context["shipment"].add(name)
	for fieldname in _LINKED_SHIPMENT_FIELDS:
		value = doc.get(fieldname)
		if value:
			context["shipment"].add(value)
	for fieldname in _HEADER_COUNTRY_FIELDS:
		value = doc.get(fieldname)
		if value:
			context["countries"].add(value)
	for row in _iter_child_rows(doc):
		for fieldname in _CHILD_COMMODITY_FIELDS:
			value = _row_value(row, fieldname)
			if value:
				context["commodity"].add(value)
		for fieldname in _CHILD_COUNTRY_FIELDS:
			value = _row_value(row, fieldname)
			if value:
				context["countries"].add(value)
	return context


def tags_match(tag_rows, context):
	"""AND across kinds present on the permit, OR within a kind."""
	by_kind = defaultdict(set)
	for row in tag_rows or []:
		entity_type = _row_value(row, "entity_type")
		entity_name = _row_value(row, "entity_name")
		kind = ENTITY_KIND.get(entity_type)
		if not kind or not entity_name:
			continue
		by_kind[kind].add(entity_name)
	if not by_kind:
		return False
	for kind, names in by_kind.items():
		if not names.intersection(context.get(kind) or set()):
			return False
	return True


def classify_permit(status, valid_to, today_date, warn_days):
	"""Return valid, expiring, expired, pending, or None when the permit is not an alert source."""
	status = status or ""
	valid_on = getdate(valid_to) if valid_to else None
	if status in _VALID_STATUSES:
		if valid_on and valid_on < today_date:
			return "expired"
		if valid_on and warn_days and date_diff(valid_on, today_date) <= warn_days:
			return "expiring"
		return "valid"
	if status == "Expired":
		return "expired"
	if status in _PENDING_STATUSES:
		return "pending"
	return None


def collect_findings(doc, warn_days=None):
	"""Raw missing / pending / expiring / expired findings, before Logistics Settings actions."""
	if warn_days is None:
		warn_days = permit_expiring_soon_days()
	warn_days = max(0, cint(warn_days))
	context = build_document_context(doc)
	today_date = getdate(today())
	matched = load_matching_permits(context, today_date, warn_days)
	type_labels = _permit_type_labels()
	by_type = defaultdict(list)
	for permit in matched:
		by_type[permit["permit_type"]].append(permit)

	findings = []
	covered = set()
	for permit_type, rows in by_type.items():
		best = pick_best_permit(rows)
		covered.add(permit_type)
		if not best or best["condition"] == "valid":
			continue
		findings.append(_finding_from_permit(best, type_labels))

	for permit_type, label in required_permit_types(context):
		if permit_type in covered:
			continue
		findings.append(
			{
				"condition": "missing",
				"permit_type": permit_type,
				"permit_application": None,
				"valid_to": None,
				"status": None,
				"msg": _("Required permit {0} is not on file for this document.").format(label),
			}
		)
	return findings


def apply_rule(findings, rule):
	"""Drop Ignore conditions and mark Warn / Block for banners and submit checks."""
	if not rule:
		return []
	visible = []
	for finding in findings or []:
		action = (rule.get(ACTION_FIELD.get(finding["condition"])) or "Ignore").strip()
		if action == "Ignore":
			continue
		row = dict(finding)
		row["action"] = action
		row["level"] = "danger" if action == "Block" else "warning"
		visible.append(row)
	return visible


def visible_permit_alerts(doc):
	"""Dashboard rows for a document. No settings row means no check."""
	doctype = doc.get("doctype") if doc else None
	rule = get_alert_rule(doctype)
	if not rule:
		return []
	if not frappe.db.table_exists("Permit Application Tag"):
		return []
	return apply_rule(collect_findings(doc), rule)


def enforce_permit_alerts(doc, rule=None):
	"""Throw when the settings action for a finding is Block."""
	if rule is None:
		rule = get_alert_rule(doc.get("doctype") if doc else None)
	if not rule:
		return
	if not frappe.db.table_exists("Permit Application Tag"):
		return
	blocked = [row for row in apply_rule(collect_findings(doc), rule) if row.get("action") == "Block"]
	if not blocked:
		return
	frappe.throw(
		"\n".join(row["msg"] for row in blocked),
		title=_("Permit Alerts"),
	)


def enforce_permit_alerts_before_submit(doc, method=None):
	enforce_permit_alerts(doc)


def best_permit_for_type(doc, permit_type, warn_days=None):
	"""Best matching application of this type: valid, then expiring, expired, pending."""
	if not permit_type or not frappe.db.table_exists("Permit Application Tag"):
		return None
	if warn_days is None:
		warn_days = permit_expiring_soon_days()
	context = build_document_context(doc)
	rows = [
		permit
		for permit in load_matching_permits(context, getdate(today()), max(0, cint(warn_days)))
		if permit.get("permit_type") == permit_type
	]
	return pick_best_permit(rows)


def requirement_covered_by_entity_permit(doc, permit_type):
	"""True when a valid or still-in-window permit of this type matches the document."""
	best = best_permit_for_type(doc, permit_type)
	return bool(best and best.get("condition") in ("valid", "expiring"))


def matched_permit_valid_to(doc, permit_type):
	"""Validity end of the best obtained match, including an already expired one."""
	best = best_permit_for_type(doc, permit_type)
	if not best or best.get("condition") not in ("valid", "expiring", "expired"):
		return None
	return best.get("valid_to")


def load_matching_permits(context, today_date, warn_days):
	parents = _candidate_parents(context)
	if not parents:
		return []
	tag_rows = frappe.get_all(
		"Permit Application Tag",
		filters={"parent": ["in", parents], "parenttype": "Permit Application"},
		fields=["parent", "entity_type", "entity_name"],
		limit=10000,
	)
	tags_by_parent = defaultdict(list)
	for row in tag_rows:
		tags_by_parent[row.parent].append(row)
	applications = frappe.get_all(
		"Permit Application",
		filters={"name": ["in", parents]},
		fields=["name", "permit_type", "status", "valid_to", "permit_number"],
		limit=10000,
	)
	matched = []
	for application in applications:
		tags = tags_by_parent.get(application.name) or []
		if not tags_match(tags, context):
			continue
		condition = classify_permit(application.status, application.valid_to, today_date, warn_days)
		if not condition:
			continue
		matched.append(
			{
				"name": application.name,
				"permit_type": application.permit_type,
				"status": application.status,
				"valid_to": application.valid_to,
				"permit_number": application.permit_number,
				"condition": condition,
			}
		)
	return matched


def pick_best_permit(rows):
	if not rows:
		return None
	return sorted(rows, key=lambda row: (_CONDITION_RANK.get(row.get("condition"), 9), row.get("name") or ""))[0]


def required_permit_types(context):
	"""Active types this document must have a valid permit for. Yields (name, label)."""
	types = frappe.get_all(
		"Permit Type",
		filters={"is_active": 1},
		fields=["name", "permit_name", "applicable_to", "is_mandatory", *PERMIT_TYPE_FLAGS],
		limit=10000,
	)
	if not types:
		return []
	names = [row.name for row in types]
	commodities = frappe.get_all(
		"Permit Type Commodity",
		filters={"parent": ["in", names], "parenttype": "Permit Type"},
		fields=["parent", "commodity"],
		limit=10000,
	)
	countries = frappe.get_all(
		"Permit Type Country",
		filters={"parent": ["in", names], "parenttype": "Permit Type"},
		fields=["parent", "country"],
		limit=10000,
	)
	commodities_by_type = defaultdict(set)
	for row in commodities:
		if row.commodity:
			commodities_by_type[row.parent].add(row.commodity)
	countries_by_type = defaultdict(set)
	for row in countries:
		if row.country:
			countries_by_type[row.parent].add(row.country)

	direction = context.get("direction")
	doc_commodities = context.get("commodity") or set()
	doc_countries = context.get("countries") or set()
	required = []
	for permit_type in types:
		applicable = permit_type.applicable_to or "All"
		if direction and applicable not in ("All", direction):
			continue
		label = permit_type.permit_name or permit_type.name
		if doc_commodities and commodities_by_type.get(permit_type.name, set()) & doc_commodities:
			required.append((permit_type.name, label))
			continue
		if doc_countries and countries_by_type.get(permit_type.name, set()) & doc_countries:
			required.append((permit_type.name, label))
			continue
		if permit_type.is_mandatory and _mandatory_target_present(permit_type, context):
			required.append((permit_type.name, label))
	return required


def get_alert_rule(doctype):
	"""Logistics Settings row for this document, or None when that document is not checked."""
	if not doctype or not frappe.db.table_exists("Permit Alert Rule"):
		return None
	rows = frappe.get_all(
		"Permit Alert Rule",
		filters={
			"parent": "Logistics Settings",
			"parenttype": "Logistics Settings",
			"reference_doctype": doctype,
		},
		fields=["missing_permit", "pending_permit", "expiring_permit", "expired_permit"],
		limit=1,
	)
	return rows[0] if rows else None


def permit_expiring_soon_days():
	try:
		days = frappe.db.get_single_value("Logistics Settings", "permit_expiring_soon_days")
	except Exception:
		return 30
	if days is None:
		return 30
	return max(0, cint(days))


def render_permit_alerts_html(alerts):
	if not alerts:
		return ""
	css = {"danger": "danger", "warning": "warning", "info": "info"}
	chunks = []
	for alert in alerts:
		level = css.get(alert.get("level"), "warning")
		chunks.append(
			f'<div class="alert alert-{level}" role="alert">{escape(alert.get("msg") or "")}</div>'
		)
	return "".join(chunks)


@frappe.whitelist()
def get_permit_alerts_html(doctype, docname):
	"""Banner HTML for forms that do not render the shared logistics dashboard."""
	if not doctype or not docname or docname == "new":
		return ""
	if not frappe.has_permission(doctype, "read", docname):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	doc = frappe.get_doc(doctype, docname)
	return render_permit_alerts_html(visible_permit_alerts(doc))


def append_source_tags(permit_application, source_doc):
	"""Copy parties, company, commodities, and job number the Permit Type allows.

	Used when a Permit Application is created from a Declaration so the new
	record is checked on quotes and shipments, not only on that declaration.
	"""
	allowed = set(allowed_tag_entity_types(permit_application.permit_type))
	if not allowed or not source_doc:
		return

	def add(entity_type, entity_name):
		if entity_type not in allowed or not entity_name:
			return
		if not frappe.db.exists(entity_type, entity_name):
			return
		for row in permit_application.get("tags") or []:
			if row.get("entity_type") == entity_type and row.get("entity_name") == entity_name:
				return
		permit_application.append("tags", {"entity_type": entity_type, "entity_name": entity_name})

	add("Customer", source_doc.get("customer") or source_doc.get("local_customer"))
	add("Consignee", source_doc.get("importer_consignee") or source_doc.get("consignee"))
	add("Shipper", source_doc.get("exporter_shipper") or source_doc.get("shipper"))
	add("Freight Agent", source_doc.get("freight_agent") or source_doc.get("freight_agent_sea"))
	add("Company", source_doc.get("company"))
	add("Job Number", source_doc.get("job_number"))
	if "Commodity" in allowed:
		for commodity in build_document_context(source_doc)["commodity"]:
			add("Commodity", commodity)


@frappe.whitelist()
def allowed_tag_entity_types(permit_type):
	"""Entity types the Permit Type allows on Permit Application Tag rows."""
	if not permit_type or not frappe.db.exists("Permit Type", permit_type):
		return []
	permit_type_doc = frappe.get_cached_doc("Permit Type", permit_type)
	allowed = []
	for entity_type in ENTITY_TYPE_OPTIONS:
		kind = ENTITY_KIND.get(entity_type)
		flag = PERMIT_TYPE_FLAG_BY_KIND.get(kind)
		if flag and permit_type_doc.get(flag):
			allowed.append(entity_type)
	return allowed


def notify_permit_expiry_alerts():
	"""One desk notification per expiring or expired permit, for the configured role."""
	try:
		if not frappe.db.table_exists("Permit Application"):
			return
		settings = frappe.get_single("Logistics Settings")
		if cint(getattr(settings, "enable_auto_status_updates", 1)) == 0:
			return
		role = getattr(settings, "permit_notify_role", None)
		if not role:
			return
		users = _users_with_role(role)
		if not users:
			return
		warn_days = max(0, cint(getattr(settings, "permit_expiring_soon_days", None) or 30))
		today_date = getdate(today())
		if warn_days:
			horizon = frappe.utils.add_days(today_date, warn_days)
			expiring = frappe.get_all(
				"Permit Application",
				filters={"status": "Approved", "valid_to": ["between", [today_date, horizon]]},
				fields=["name", "permit_type", "valid_to"],
				limit=500,
			)
			for row in expiring:
				_notify_once(
					users,
					row.name,
					_("Permit {0} ({1}) expires on {2}").format(row.name, row.permit_type or "", row.valid_to),
				)
		expired = frappe.get_all(
			"Permit Application",
			filters={"status": "Expired"},
			fields=["name", "permit_type", "valid_to"],
			limit=500,
		)
		for row in expired:
			if row.valid_to:
				subject = _("Permit {0} ({1}) expired on {2}").format(row.name, row.permit_type or "", row.valid_to)
			else:
				subject = _("Permit {0} ({1}) has expired").format(row.name, row.permit_type or "")
			_notify_once(users, row.name, subject)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Permit Expiry Notification")


def _notify_once(users, permit_name, subject):
	if frappe.db.exists(
		"Notification Log",
		{"document_type": "Permit Application", "document_name": permit_name, "subject": subject},
	):
		return
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	enqueue_create_notification(
		users,
		{
			"subject": subject,
			"type": "Alert",
			"document_type": "Permit Application",
			"document_name": permit_name,
			"from_user": frappe.session.user or "Administrator",
			"email_content": subject,
		},
	)


def _users_with_role(role):
	names = frappe.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User"},
		pluck="parent",
		limit=500,
	)
	if not names:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", names], "enabled": 1, "user_type": "System User"},
		pluck="name",
		limit=500,
	)


def _candidate_parents(context):
	if not frappe.db.table_exists("Permit Application Tag"):
		return []
	parents = set()
	for kind, entity_types in KIND_ENTITY_TYPES.items():
		names = list(context.get(kind) or [])
		if not names:
			continue
		rows = frappe.get_all(
			"Permit Application Tag",
			filters={
				"parenttype": "Permit Application",
				"entity_type": ["in", entity_types],
				"entity_name": ["in", names],
			},
			pluck="parent",
			limit=10000,
		)
		parents.update(rows)
	return list(parents)


def _finding_from_permit(permit, type_labels):
	label = type_labels.get(permit["permit_type"]) or permit["permit_type"] or permit["name"]
	condition = permit["condition"]
	if condition == "expiring":
		msg = _("Permit {0} ({1}) expires on {2}.").format(permit["name"], label, permit["valid_to"])
	elif condition == "expired":
		if permit.get("valid_to"):
			msg = _("Permit {0} ({1}) expired on {2}.").format(permit["name"], label, permit["valid_to"])
		else:
			msg = _("Permit {0} ({1}) is expired.").format(permit["name"], label)
	else:
		msg = _("Permit {0} ({1}) is {2}.").format(permit["name"], label, permit.get("status") or _("Pending"))
	return {
		"condition": condition,
		"permit_type": permit["permit_type"],
		"permit_application": permit["name"],
		"valid_to": permit.get("valid_to"),
		"status": permit.get("status"),
		"msg": msg,
	}


def _permit_type_labels():
	rows = frappe.get_all("Permit Type", fields=["name", "permit_name"], limit=10000)
	return {row.name: (row.permit_name or row.name) for row in rows}


def _mandatory_target_present(permit_type, context):
	for kind, flag in PERMIT_TYPE_FLAG_BY_KIND.items():
		if permit_type.get(flag) and context.get(kind):
			return True
	return False


def _document_direction(doc):
	declaration_type = (doc.get("declaration_type") or "").strip()
	if declaration_type in ("Import", "Export", "Transit"):
		return declaration_type
	return None


def _values(doc, *fieldnames):
	found = set()
	for fieldname in fieldnames:
		value = doc.get(fieldname)
		if value:
			found.add(value)
	return found


def _iter_child_rows(doc):
	doctype = doc.get("doctype")
	if doctype:
		try:
			meta = frappe.get_meta(doctype)
		except Exception:
			meta = None
		if meta:
			for df in meta.get_table_fields():
				for row in doc.get(df.fieldname) or []:
					yield row
			return
	for fieldname in ("packages", "commercial_invoice_line_items", "commodities", "items"):
		for row in doc.get(fieldname) or []:
			yield row


def _row_value(row, fieldname):
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return row.get(fieldname) if hasattr(row, "get") else getattr(row, fieldname, None)
