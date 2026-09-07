# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Quotation → booking/order charge flow (product rules).

**One-off Sales Quotes** (``quotation_type`` = One-off): operational jobs must be created **from
the Sales Quote** document (create booking/order actions). They are **not** selectable in
**Action → Get Charges from Quotation**; linkage is set only during that create flow.

**Regular Sales Quotes**: users **create** Sea Booking, Air Booking, Transport Order, Declaration Order,
or Time Sensitive Case first, then use **Action → Get Charges from Quotation** to pick a quotation and
apply **charges** (+ **routing legs** on Sea/Air where applicable). Time Sensitive Case lists Regular
submitted quotes with ``is_time_sensitive`` (any ``main_service``). The ``sales_quote`` link is
**read-only** on the form and is written only by create-from-quote or by the apply step. The Action button is
**hidden on the desk** when a Sales Quote is already linked, or when linked (or pending) to a
One-off or Project Sales Quote.

**Customer match**: only Sales Quotes whose ``customer`` matches the job's customer
(``local_customer`` on Sea/Air, ``customer`` on Transport Order) are listed and may be applied.
Dialog **filter_overrides** (per-module keys in ``GCFQ_FILTER_KEYS``) refine corridor / customs matching
for listing, preview, and apply **without** saving the job document first.
When the client sends **no** overrides, filters match the saved parent. When the user changes **any**
filter, **only** keys present in ``filter_overrides`` apply; every other filter field is treated as a
wildcard (empty), so e.g. changing only ``airline`` lists quotes by carrier without constraining ports from the parent.

**Apply / preview**: After dialog filters pass, the quotation must **match the saved document**
(corridor / customs fields / org dimensions). If dialog filters widened the search, this blocks apply when
the quote still does not fit the booking/order on disk. Mismatch surfaces as an error (preview) or
``Cannot apply quotation`` (apply).

**Branch / Cost Center / Profit Center**: When set on the job (or in the dialog filters), the Sales Quote
**header** must equal each value or be blank on the quotation (wildcard); empty job value = no filter for
that field.

**Corridor match**: Sea Booking uses ``origin_port`` / ``destination_port`` and optional ``shipping_line``
(quotation charge row or header; blank line = wildcard). **Air Booking** matches those ports and ``airline``
when set. If the booking has ``airline`` but both ports are empty, eligible quotes are filtered **by airline
only** (unified/legacy Air charge lines). Transport Order uses ``location_from`` / ``location_to``.

**Extra header filters** (catalog): commercial / party / programme fields mapped in ``GCFQ_SQ_HEADER_FIELD_MAP``
(e.g. direction, load type, house type, shipper, project type). Match is Sales Quote **header** blank-or-equal
(same rule as Branch / Cost Center / Profit Center). Sea ``house_type`` maps to ``sea_house_type``;
Air ``house_type`` to ``air_house_type``; Declaration ports map to quote ``origin_port`` / ``destination_port``.

**Main service**: the Sales Quote header ``main_service`` must match the job (Declaration Order →
Customs, Air Booking → Air, etc.). A multimodal quote whose main service is Sea is **not** listed on
a Declaration Order even if it has Customs charge lines.

**Declaration Order** optional filters: **Customs Authority**, **Declaration Type**, **Customs Broker**, and
**Transport Mode** (when set on the job or dialog) further narrow by matching charge lines; blanks are
wildcards. A blank broker on a charge line still matches any broker filter.

**Sea / Air / Transport** corridor filters (ports, airline, shipping line) still use charge rows or
quotation header when set. **Sales Quote** routing legs are not used for corridor matching.

**Submitted only**: Only **submitted** Sales Quotes (``docstatus`` = 1) are listed; draft quotations
are excluded.

**Regular only**: Only ``quotation_type`` = **Regular** is listed (One-off and Project are excluded).
"""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.charge_service_type import implied_service_type_for_doctype
from logistics.utils.operational_rep_fields import copy_operational_rep_fields_from_sales_quote_doc
from logistics.utils.sales_quote_link_query import (
	fetch_eligible_regular_sales_quote_names,
	fetch_eligible_time_sensitive_sales_quote_names,
	sales_quote_matches_declaration_order_filters,
	sales_quote_matches_job_airline_only,
	sales_quote_matches_job_corridor,
	sales_quote_matches_job_header_fields,
	sales_quote_matches_job_org_dimensions,
	sales_quote_matches_main_service,
)
from logistics.utils.sales_quote_routing import apply_sales_quote_routing_to_booking

JOB_DOCTYPES = frozenset(
	{
		"Sea Booking",
		"Air Booking",
		"Transport Order",
		"Declaration Order",
		"Special Project",
		"Exhibit",
		"MICE Project",
		"Time Sensitive Case",
	}
)

_PROGRAMME_GCFQ_DOCTYPES = frozenset({"Special Project", "Exhibit", "MICE Project"})
_GCFQ_TIME_SENSITIVE_DOCTYPE = "Time Sensitive Case"


def _gcfq_skip_main_service_match(doctype: str) -> bool:
	"""Time Sensitive Case is multimodal — list/preview/apply use ``is_time_sensitive``, not main_service."""
	return doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE


def _gcfq_skip_corridor_sql(doctype: str) -> bool:
	"""Programme parents and Time Sensitive Case match origin/dest via header filters, not charge-row corridor SQL."""
	return doctype in _PROGRAMME_GCFQ_DOCTYPES or doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE

_DECLARATION_TYPE_OPTIONS = "Import\nExport\nTransit\nBonded"
_DIRECTION_OPTIONS = "Import\nExport\nDomestic"
_HOUSE_TYPE_OPTIONS = (
	"Standard House\nCo-load Master\nBlind Co-load Master\nCo-load House\n"
	"Buyer's Consol Lead\nShipper's Consol Lead\nBreak Bulk"
)
_PRIORITY_OPTIONS = "Low\nNormal\nHigh\nUrgent"

_ORG_DIM_ENTRIES = (
	{"key": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "doc_attr": "branch"},
	{
		"key": "cost_center",
		"label": "Cost Center",
		"fieldtype": "Link",
		"options": "Cost Center",
		"doc_attr": "cost_center",
	},
	{
		"key": "profit_center",
		"label": "Profit Center",
		"fieldtype": "Link",
		"options": "Profit Center",
		"doc_attr": "profit_center",
	},
)

_PARTY_ENTRIES = (
	{"key": "shipper", "label": "Shipper", "fieldtype": "Link", "options": "Shipper", "doc_attr": "shipper"},
	{
		"key": "consignee",
		"label": "Consignee",
		"fieldtype": "Link",
		"options": "Consignee",
		"doc_attr": "consignee",
	},
	{
		"key": "shipper_address",
		"label": "Shipper Address",
		"fieldtype": "Link",
		"options": "Address",
		"doc_attr": "shipper_address",
	},
	{
		"key": "consignee_address",
		"label": "Consignee Address",
		"fieldtype": "Link",
		"options": "Address",
		"doc_attr": "consignee_address",
	},
	{
		"key": "shipper_contact",
		"label": "Shipper Contact",
		"fieldtype": "Link",
		"options": "Contact",
		"doc_attr": "shipper_contact",
	},
	{
		"key": "consignee_contact",
		"label": "Consignee Contact",
		"fieldtype": "Link",
		"options": "Contact",
		"doc_attr": "consignee_contact",
	},
)

_REP_ENTRIES = (
	{"key": "sales_rep", "label": "Sales Rep", "fieldtype": "Link", "options": "Employee", "doc_attr": "sales_rep"},
	{
		"key": "operations_rep",
		"label": "Operations Rep",
		"fieldtype": "Link",
		"options": "Employee",
		"doc_attr": "operations_rep",
	},
	{
		"key": "customer_service_rep",
		"label": "Customer Service Rep",
		"fieldtype": "Link",
		"options": "Employee",
		"doc_attr": "customer_service_rep",
	},
)

_SEA_AIR_COMMERCIAL_ENTRIES = (
	{
		"key": "direction",
		"label": "Direction",
		"fieldtype": "Select",
		"options": "",
		"select_options": _DIRECTION_OPTIONS,
		"doc_attr": "direction",
	},
	{"key": "load_type", "label": "Load Type", "fieldtype": "Link", "options": "Load Type", "doc_attr": "load_type"},
	{
		"key": "transport_mode",
		"label": "Transport Mode",
		"fieldtype": "Link",
		"options": "Transport Mode",
		"doc_attr": "transport_mode",
	},
	{"key": "incoterm", "label": "Incoterm", "fieldtype": "Link", "options": "Incoterm", "doc_attr": "incoterm"},
	{
		"key": "house_type",
		"label": "House Type",
		"fieldtype": "Select",
		"options": "",
		"select_options": _HOUSE_TYPE_OPTIONS,
		"doc_attr": "house_type",
	},
	{
		"key": "freight_agent",
		"label": "Freight Agent",
		"fieldtype": "Link",
		"options": "Freight Agent",
		"doc_attr": "freight_agent",
	},
)

# Fixed catalog: match semantics live in code; settings only toggle enabled / editable / order.
GCFQ_FILTER_CATALOG: dict[str, tuple[dict, ...]] = {
	"Sea Booking": (
		{
			"key": "origin_port",
			"label": "Origin Port",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "origin_port",
		},
		{
			"key": "destination_port",
			"label": "Destination Port",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "destination_port",
		},
		{
			"key": "shipping_line",
			"label": "Shipping Line",
			"fieldtype": "Link",
			"options": "Shipping Line",
			"doc_attr": "shipping_line",
		},
		*_SEA_AIR_COMMERCIAL_ENTRIES,
		*_PARTY_ENTRIES,
		*_REP_ENTRIES,
		*_ORG_DIM_ENTRIES,
	),
	"Air Booking": (
		{
			"key": "origin_port",
			"label": "Origin Port",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "origin_port",
		},
		{
			"key": "destination_port",
			"label": "Destination Port",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "destination_port",
		},
		{
			"key": "airline",
			"label": "Airline",
			"fieldtype": "Link",
			"options": "Airline",
			"doc_attr": "airline",
		},
		*_SEA_AIR_COMMERCIAL_ENTRIES,
		*_PARTY_ENTRIES,
		*_REP_ENTRIES,
		*_ORG_DIM_ENTRIES,
	),
	"Transport Order": (
		{
			"key": "location_from",
			"label": "Location From",
			"fieldtype": "Data",
			"options": "",
			"doc_attr": "location_from",
		},
		{
			"key": "location_to",
			"label": "Location To",
			"fieldtype": "Data",
			"options": "",
			"doc_attr": "location_to",
		},
		{
			"key": "location_type",
			"label": "Location Type",
			"fieldtype": "Link",
			"options": "DocType",
			"doc_attr": "location_type",
		},
		{
			"key": "vehicle_type",
			"label": "Vehicle Type",
			"fieldtype": "Link",
			"options": "Vehicle Type",
			"doc_attr": "vehicle_type",
		},
		{
			"key": "transport_mode",
			"label": "Transport Mode",
			"fieldtype": "Link",
			"options": "Transport Mode",
			"doc_attr": "transport_mode",
		},
		{"key": "load_type", "label": "Load Type", "fieldtype": "Link", "options": "Load Type", "doc_attr": "load_type"},
		{
			"key": "transport_template",
			"label": "Transport Template",
			"fieldtype": "Link",
			"options": "Transport Template",
			"doc_attr": "transport_template",
		},
		{
			"key": "container_type",
			"label": "Container Type",
			"fieldtype": "Link",
			"options": "Container Type",
			"doc_attr": "container_type",
		},
		{"key": "container_no", "label": "Container No.", "fieldtype": "Data", "options": "", "doc_attr": "container_no"},
		*_PARTY_ENTRIES,
		*_REP_ENTRIES,
		*_ORG_DIM_ENTRIES,
	),
	"Declaration Order": (
		{
			"key": "customs_authority",
			"label": "Customs Authority",
			"fieldtype": "Link",
			"options": "Customs Authority",
			"doc_attr": "customs_authority",
		},
		{
			"key": "declaration_type",
			"label": "Declaration Type",
			"fieldtype": "Select",
			"options": "",
			"select_options": _DECLARATION_TYPE_OPTIONS,
			"doc_attr": "declaration_type",
		},
		{
			"key": "customs_broker",
			"label": "Customs Broker",
			"fieldtype": "Link",
			"options": "Broker",
			"doc_attr": "customs_broker",
		},
		{
			"key": "transport_mode",
			"label": "Transport Mode",
			"fieldtype": "Link",
			"options": "Transport Mode",
			"doc_attr": "transport_mode",
		},
		{
			"key": "port_of_loading",
			"label": "Port of Loading/Entry",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "port_of_loading",
		},
		{
			"key": "port_of_discharge",
			"label": "Port of Discharge/Exit",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "port_of_discharge",
		},
		{"key": "incoterm", "label": "Incoterm", "fieldtype": "Link", "options": "Incoterm", "doc_attr": "incoterm"},
		{
			"key": "incoterm_place",
			"label": "Incoterm Place",
			"fieldtype": "Data",
			"options": "",
			"doc_attr": "incoterm_place",
		},
		{
			"key": "freight_agent",
			"label": "Freight Agent",
			"fieldtype": "Link",
			"options": "Freight Agent",
			"doc_attr": "freight_agent",
		},
		*_ORG_DIM_ENTRIES,
	),
	"Special Project": (
		{
			"key": "project_type",
			"label": "Project Type",
			"fieldtype": "Link",
			"options": "Project Type",
			"doc_attr": "project_type",
		},
		{
			"key": "priority",
			"label": "Priority",
			"fieldtype": "Select",
			"options": "",
			"select_options": _PRIORITY_OPTIONS,
			"doc_attr": "priority",
		},
		*_ORG_DIM_ENTRIES,
	),
	"Exhibit": (
		{
			"key": "project_type",
			"label": "Project Type",
			"fieldtype": "Link",
			"options": "Project Type",
			"doc_attr": "project_type",
		},
		{
			"key": "priority",
			"label": "Priority",
			"fieldtype": "Select",
			"options": "",
			"select_options": _PRIORITY_OPTIONS,
			"doc_attr": "priority",
		},
		*_ORG_DIM_ENTRIES,
	),
	"MICE Project": (
		{
			"key": "project_type",
			"label": "Project Type",
			"fieldtype": "Link",
			"options": "Project Type",
			"doc_attr": "project_type",
		},
		{
			"key": "priority",
			"label": "Priority",
			"fieldtype": "Select",
			"options": "",
			"select_options": _PRIORITY_OPTIONS,
			"doc_attr": "priority",
		},
		*_ORG_DIM_ENTRIES,
	),
	"Time Sensitive Case": (
		{
			"key": "origin",
			"label": "Origin",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "origin",
		},
		{
			"key": "destination",
			"label": "Destination",
			"fieldtype": "Link",
			"options": "UNLOCO",
			"doc_attr": "destination",
		},
		{
			"key": "priority",
			"label": "Priority",
			"fieldtype": "Select",
			"options": "",
			"select_options": _PRIORITY_OPTIONS,
			"doc_attr": "priority",
		},
		*_ORG_DIM_ENTRIES,
	),
}

# Job filter_key → Sales Quote header column for blank-or-equal matching.
# Corridor / customs / org dimensions stay on their dedicated match paths.
GCFQ_SQ_HEADER_FIELD_MAP: dict[str, dict[str, str]] = {
	"Sea Booking": {
		"direction": "direction",
		"load_type": "load_type",
		"transport_mode": "transport_mode",
		"incoterm": "incoterm",
		"house_type": "sea_house_type",
		"freight_agent": "freight_agent_sea",
		"shipper": "shipper",
		"consignee": "consignee",
		"shipper_address": "shipper_address",
		"consignee_address": "consignee_address",
		"shipper_contact": "shipper_contact",
		"consignee_contact": "consignee_contact",
		"sales_rep": "sales_rep",
		"operations_rep": "operations_rep",
		"customer_service_rep": "customer_service_rep",
	},
	"Air Booking": {
		"direction": "direction",
		"load_type": "load_type",
		"transport_mode": "transport_mode",
		"incoterm": "incoterm",
		"house_type": "air_house_type",
		"freight_agent": "freight_agent",
		"shipper": "shipper",
		"consignee": "consignee",
		"shipper_address": "shipper_address",
		"consignee_address": "consignee_address",
		"shipper_contact": "shipper_contact",
		"consignee_contact": "consignee_contact",
		"sales_rep": "sales_rep",
		"operations_rep": "operations_rep",
		"customer_service_rep": "customer_service_rep",
	},
	"Transport Order": {
		"location_type": "location_type",
		"vehicle_type": "vehicle_type",
		"transport_mode": "transport_mode",
		"load_type": "load_type",
		"transport_template": "transport_template",
		"container_type": "container_type",
		"container_no": "container_no",
		"shipper": "shipper",
		"consignee": "consignee",
		"shipper_address": "shipper_address",
		"consignee_address": "consignee_address",
		"shipper_contact": "shipper_contact",
		"consignee_contact": "consignee_contact",
		"sales_rep": "sales_rep",
		"operations_rep": "operations_rep",
		"customer_service_rep": "customer_service_rep",
	},
	"Declaration Order": {
		"port_of_loading": "origin_port",
		"port_of_discharge": "destination_port",
		"incoterm": "incoterm",
		"incoterm_place": "incoterm_place",
		"freight_agent": "freight_agent",
	},
	"Special Project": {
		"project_type": "project_type",
		"priority": "priority",
	},
	"Exhibit": {
		"project_type": "project_type",
		"priority": "priority",
	},
	"MICE Project": {
		"project_type": "project_type",
		"priority": "priority",
	},
	"Time Sensitive Case": {
		"origin": "origin_port",
		"destination": "destination_port",
		"priority": "priority",
	},
}

# Whitelisted keys for Action → Get Charges from Quotation dialog filters (client-sent).
GCFQ_FILTER_KEYS: dict[str, frozenset[str]] = {
	dt: frozenset(e["key"] for e in entries) for dt, entries in GCFQ_FILTER_CATALOG.items()
}

_GCFQ_SETTINGS_DOCTYPE = "Get Charges from Quotation Settings"


def _gcfq_catalog_entry(doctype: str, key: str) -> dict | None:
	for entry in GCFQ_FILTER_CATALOG.get(doctype, ()):
		if entry["key"] == key:
			return entry
	return None


def seed_gcfq_filter_settings_rows(settings_doc) -> None:
	"""Append default catalog rows (enabled + editable) when the settings table is empty."""
	if settings_doc.get("filter_settings"):
		return
	for job_doctype, entries in GCFQ_FILTER_CATALOG.items():
		for entry in entries:
			settings_doc.append(
				"filter_settings",
				{
					"job_doctype": job_doctype,
					"filter_key": entry["key"],
					"enabled": 1,
					"editable": 1,
				},
			)


@frappe.whitelist()
def seed_gcfq_filter_settings_if_empty():
	"""Ensure the Single has default filter rows; used by desk refresh and install patch."""
	if not frappe.db.exists("DocType", _GCFQ_SETTINGS_DOCTYPE):
		return {"seeded": False}
	doc = frappe.get_single(_GCFQ_SETTINGS_DOCTYPE)
	if doc.get("filter_settings"):
		return {"seeded": False, "count": len(doc.filter_settings)}
	seed_gcfq_filter_settings_rows(doc)
	doc.save(ignore_permissions=True)
	return {"seeded": True, "count": len(doc.filter_settings)}


@frappe.whitelist()
def get_gcfq_catalog_keys_for_doctype(doctype: str) -> list[str]:
	"""Filter keys valid for a job DocType (settings form helper)."""
	return [e["key"] for e in GCFQ_FILTER_CATALOG.get(doctype, ())]


def _gcfq_settings_rows_for_doctype(doctype: str) -> list[dict]:
	"""Ordered settings rows for a job DocType. Empty list → caller uses catalog defaults."""
	if not frappe.db.exists("DocType", _GCFQ_SETTINGS_DOCTYPE):
		return []
	try:
		rows = frappe.get_all(
			"GCFQ Filter Setting",
			filters={"parent": _GCFQ_SETTINGS_DOCTYPE, "parenttype": _GCFQ_SETTINGS_DOCTYPE, "job_doctype": doctype},
			fields=["filter_key", "enabled", "editable", "idx"],
			order_by="idx asc",
		)
	except Exception:
		return []
	return rows or []


def _gcfq_effective_filter_config(doctype: str) -> list[dict]:
	"""Enabled catalog entries in settings order (or full catalog defaults).

	Each item: catalog entry + ``editable`` (bool).
	"""
	catalog = list(GCFQ_FILTER_CATALOG.get(doctype, ()))
	if not catalog:
		return []
	by_key = {e["key"]: e for e in catalog}
	settings_rows = _gcfq_settings_rows_for_doctype(doctype)
	if not settings_rows:
		return [{**e, "editable": True} for e in catalog]

	out: list[dict] = []
	seen: set[str] = set()
	for row in settings_rows:
		key = (row.get("filter_key") or "").strip()
		if key not in by_key or key in seen:
			continue
		seen.add(key)
		if not cint(row.get("enabled")):
			continue
		out.append({**by_key[key], "editable": bool(cint(row.get("editable")))})

	# Catalog keys missing from settings (new keys after upgrade) stay enabled+editable at end.
	for entry in catalog:
		if entry["key"] in seen:
			continue
		out.append({**entry, "editable": True})
	return out


def _gcfq_overridable_filter_keys(doctype: str) -> frozenset[str]:
	"""Keys the client may send as filter_overrides (enabled + editable)."""
	return frozenset(e["key"] for e in _gcfq_effective_filter_config(doctype) if e.get("editable"))


def _gcfq_assert_settings_write():
	frappe.has_permission(_GCFQ_SETTINGS_DOCTYPE, "write", throw=True)


def _gcfq_dashboard_filters_for_doctype(doctype: str) -> list[dict]:
	"""Full workspace list for a module (includes disabled). Catalog order + settings order."""
	catalog = list(GCFQ_FILTER_CATALOG.get(doctype, ()))
	if not catalog:
		return []
	by_key = {e["key"]: e for e in catalog}
	settings_rows = _gcfq_settings_rows_for_doctype(doctype)
	out: list[dict] = []
	seen: set[str] = set()
	if settings_rows:
		for row in settings_rows:
			key = (row.get("filter_key") or "").strip()
			entry = by_key.get(key)
			if not entry or key in seen:
				continue
			seen.add(key)
			out.append(
				{
					"key": key,
					"label": _(entry.get("label") or key),
					"enabled": bool(cint(row.get("enabled"))),
					"editable": bool(cint(row.get("editable"))),
				}
			)
	for entry in catalog:
		key = entry["key"]
		if key in seen:
			continue
		out.append(
			{
				"key": key,
				"label": _(entry.get("label") or key),
				"enabled": True,
				"editable": True,
			}
		)
	return out


@frappe.whitelist()
def get_gcfq_dashboard_modules() -> dict:
	"""Module list + filter counts for the Settings Dashboard tab."""
	frappe.has_permission(_GCFQ_SETTINGS_DOCTYPE, "read", throw=True)
	modules = []
	for doctype, entries in GCFQ_FILTER_CATALOG.items():
		filters = _gcfq_dashboard_filters_for_doctype(doctype)
		enabled_n = sum(1 for f in filters if f.get("enabled"))
		modules.append(
			{
				"doctype": doctype,
				"label": _(doctype),
				"filter_count": len(filters),
				"enabled_count": enabled_n,
				"catalog_count": len(entries),
			}
		)
	return {"modules": modules}


@frappe.whitelist()
def get_gcfq_dashboard_workspace(doctype: str) -> dict:
	"""Filter cards + locked fields for one job DocType workspace."""
	frappe.has_permission(_GCFQ_SETTINGS_DOCTYPE, "read", throw=True)
	doctype = (doctype or "").strip()
	if doctype not in GCFQ_FILTER_CATALOG:
		frappe.throw(_("Unsupported document type."))
	cust_label = (
		_("Local Customer")
		if doctype in ("Sea Booking", "Air Booking")
		else _("Customer")
	)
	return {
		"doctype": doctype,
		"label": _(doctype),
		"locked": [
			{"key": "_svc", "label": _("Main Service")},
			{"key": "_cust", "label": cust_label},
		],
		"filters": _gcfq_dashboard_filters_for_doctype(doctype),
		"available": [
			{"key": e["key"], "label": _(e.get("label") or e["key"])}
			for e in GCFQ_FILTER_CATALOG[doctype]
			if e["key"] not in {f["key"] for f in _gcfq_dashboard_filters_for_doctype(doctype)}
		],
	}


@frappe.whitelist()
def save_gcfq_dashboard_workspace(doctype: str, filters=None) -> dict:
	"""Replace filter rows for one DocType from dashboard card order/toggles."""
	_gcfq_assert_settings_write()
	doctype = (doctype or "").strip()
	if doctype not in GCFQ_FILTER_CATALOG:
		frappe.throw(_("Unsupported document type."))
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if not isinstance(filters, list):
		frappe.throw(_("Invalid filters payload."))

	allowed = {e["key"] for e in GCFQ_FILTER_CATALOG[doctype]}
	cleaned: list[dict] = []
	seen: set[str] = set()
	for item in filters:
		if not isinstance(item, dict):
			continue
		key = (item.get("key") or "").strip()
		if key not in allowed or key in seen:
			continue
		seen.add(key)
		cleaned.append(
			{
				"job_doctype": doctype,
				"filter_key": key,
				"enabled": 1 if cint(item.get("enabled")) else 0,
				"editable": 1 if cint(item.get("editable")) else 0,
			}
		)

	# Keep catalog keys not sent as disabled at end (admin removed card → treat as disabled row)
	for entry in GCFQ_FILTER_CATALOG[doctype]:
		if entry["key"] in seen:
			continue
		cleaned.append(
			{
				"job_doctype": doctype,
				"filter_key": entry["key"],
				"enabled": 0,
				"editable": 1,
			}
		)

	doc = frappe.get_single(_GCFQ_SETTINGS_DOCTYPE)
	if not doc.filter_settings:
		seed_gcfq_filter_settings_rows(doc)

	kept = [r for r in list(doc.filter_settings) if (r.job_doctype or "").strip() != doctype]
	doc.set("filter_settings", [])
	for row in kept:
		doc.append(
			"filter_settings",
			{
				"job_doctype": row.job_doctype,
				"filter_key": row.filter_key,
				"enabled": cint(row.enabled),
				"editable": cint(row.editable),
			},
		)
	for row in cleaned:
		doc.append("filter_settings", row)
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype=_GCFQ_SETTINGS_DOCTYPE)
	return get_gcfq_dashboard_workspace(doctype)


@frappe.whitelist()
def restore_gcfq_dashboard_defaults(doctype: str) -> dict:
	"""Reset one module's filters to catalog defaults (enabled + editable, catalog order)."""
	_gcfq_assert_settings_write()
	doctype = (doctype or "").strip()
	if doctype not in GCFQ_FILTER_CATALOG:
		frappe.throw(_("Unsupported document type."))
	defaults = [
		{"key": e["key"], "enabled": 1, "editable": 1} for e in GCFQ_FILTER_CATALOG[doctype]
	]
	return save_gcfq_dashboard_workspace(doctype, defaults)


def _parse_gcfq_filter_overrides(doctype: str, filter_overrides) -> dict[str, str]:
	"""Sanitize client filter payload to allowed editable keys only."""
	if not filter_overrides:
		return {}
	if isinstance(filter_overrides, str):
		try:
			filter_overrides = frappe.parse_json(filter_overrides)
		except Exception:
			return {}
	if not isinstance(filter_overrides, dict):
		return {}
	# Must be in catalog AND enabled+editable in settings (disabled/locked → use saved job).
	allowed = GCFQ_FILTER_KEYS.get(doctype, frozenset()) & _gcfq_overridable_filter_keys(doctype)
	out: dict[str, str] = {}
	for k, v in filter_overrides.items():
		if k not in allowed:
			continue
		if v is None:
			out[k] = ""
		else:
			out[k] = str(v).strip()
	return out


def _gcfq_readonly_party_label(doc) -> str:
	"""Display label for locked Customer / Local Customer filter cell."""
	dt = getattr(doc, "doctype", None)
	if dt in ("Sea Booking", "Air Booking"):
		return (
			(getattr(doc, "local_customer_name", None) or getattr(doc, "local_customer", None) or "")
		).strip()
	if dt in (
		"Transport Order",
		"Declaration Order",
		"Special Project",
		"Exhibit",
		"Time Sensitive Case",
	):
		return ((getattr(doc, "customer_name", None) or getattr(doc, "customer", None) or "")).strip()
	if dt == "MICE Project":
		cust = _job_customer(doc) or ""
		return cust
	return ""


def _gcfq_main_service_label(doctype: str) -> str:
	st = implied_service_type_for_doctype(doctype) or ""
	return _(st) if st else ""


def _gcfq_spec_from_catalog_entry(doc, entry: dict) -> dict:
	"""Build one dialog filter spec from a catalog entry (+ editable flag)."""
	key = entry["key"]
	doc_attr = entry.get("doc_attr") or key
	value = (getattr(doc, doc_attr, None) or "").strip() if doc else ""
	editable = bool(entry.get("editable", True))
	fieldtype = entry.get("fieldtype") or "Data"
	options = entry.get("options") or ""
	spec = {
		"key": key,
		"label": _(entry.get("label") or key),
		"value": value,
		"readonly": not editable,
		"fieldtype": fieldtype,
		"options": options,
	}
	if entry.get("select_options"):
		spec["select_options"] = entry["select_options"]

	# Transport locations: Dynamic Link when location_type is set on the job.
	if doc and doc.doctype == "Transport Order" and key in ("location_from", "location_to"):
		loc_type = (getattr(doc, "location_type", None) or "").strip()
		if loc_type:
			spec["fieldtype"] = "Dynamic Link"
			spec["options"] = "location_type"
			spec["use_location_type"] = True
		else:
			spec["fieldtype"] = "Data"
			spec["options"] = ""
	return spec


@frappe.whitelist()
def get_gcfq_filter_specs(doctype: str, docname: str) -> dict:
	"""Return ordered filter specs for the Get Charges from Quotation dialog.

	Always includes locked Main Service + Customer, then enabled settings filters.
	"""
	if doctype not in JOB_DOCTYPES:
		frappe.throw(_("Unsupported document type."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	specs: list[dict] = [
		{
			"key": "_svc",
			"readonly": True,
			"label": _("Main Service"),
			"value": _gcfq_main_service_label(doctype),
		},
		{
			"key": "_cust",
			"readonly": True,
			"label": (
				_("Local Customer")
				if doctype in ("Sea Booking", "Air Booking")
				else _("Customer")
			),
			"value": _gcfq_readonly_party_label(doc),
		},
	]
	for entry in _gcfq_effective_filter_config(doctype):
		specs.append(_gcfq_spec_from_catalog_entry(doc, entry))

	return {"specs": specs, "doctype": doctype}


def _pick_gcfq_field(doc, overrides: dict, param_key: str, doc_attr: str) -> str:
	"""Resolve one dialog filter for listing/preview/apply.

	- **No overrides** (user did not change any filter): use the saved document, same as at dialog open.
	- **Any override** (user changed at least one filter): use the value only for keys present in
	  ``overrides``; keys **not** sent are wildcards (empty string), not the parent field — so a single
	  changed field (e.g. ``airline``) does not keep inheriting origin/destination from the booking.
	- **Declaration Order** exception: keys not present in ``overrides`` still use the saved document so
	  changing one customs filter does not drop the others while Link controls are still loading.
	"""
	if not overrides:
		return (getattr(doc, doc_attr, None) or "").strip()
	if param_key in overrides:
		return (overrides[param_key] or "").strip()
	if doc.doctype == "Declaration Order":
		return (getattr(doc, doc_attr, None) or "").strip()
	return ""


def _effective_sea_air_transport_corridor(
	doc, overrides: dict
) -> tuple[str, str, str | None, str | None]:
	"""(origin, destination, airline, shipping_line) — third set for Air, fourth for Sea."""
	dt = doc.doctype
	if dt == "Sea Booking":
		o = _pick_gcfq_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcfq_field(doc, overrides, "destination_port", "destination_port")
		sl = _pick_gcfq_field(doc, overrides, "shipping_line", "shipping_line")
		return o, d, None, (sl or None)
	if dt == "Air Booking":
		o = _pick_gcfq_field(doc, overrides, "origin_port", "origin_port")
		d = _pick_gcfq_field(doc, overrides, "destination_port", "destination_port")
		al = _pick_gcfq_field(doc, overrides, "airline", "airline")
		return o, d, (al or None), None
	if dt == "Transport Order":
		o = _pick_gcfq_field(doc, overrides, "location_from", "location_from")
		d2 = _pick_gcfq_field(doc, overrides, "location_to", "location_to")
		return o, d2, None, None
	if dt == _GCFQ_TIME_SENSITIVE_DOCTYPE:
		o = _pick_gcfq_field(doc, overrides, "origin", "origin")
		d = _pick_gcfq_field(doc, overrides, "destination", "destination")
		return o, d, None, None
	return "", "", None, None


def _effective_org_dimension_fields(doc, overrides: dict) -> tuple[str, str, str]:
	"""Branch, Cost Center, Profit Center — dialog overrides or saved job (all job doctypes)."""
	b = _pick_gcfq_field(doc, overrides, "branch", "branch")
	cc = _pick_gcfq_field(doc, overrides, "cost_center", "cost_center")
	pc = _pick_gcfq_field(doc, overrides, "profit_center", "profit_center")
	return b, cc, pc


def _effective_sq_header_filters(doc, overrides: dict) -> dict[str, str]:
	"""Sales Quote header column → filter value for blank-or-equal matching.

	Uses ``GCFQ_SQ_HEADER_FIELD_MAP`` (commercial / party / programme fields). Empty values are
	omitted (no constraint). Disabled catalog cards still contribute the saved job value.
	"""
	mapping = GCFQ_SQ_HEADER_FIELD_MAP.get(getattr(doc, "doctype", None) or "", {})
	if not mapping:
		return {}
	by_key = {e["key"]: e for e in GCFQ_FILTER_CATALOG.get(doc.doctype, ())}
	out: dict[str, str] = {}
	for filter_key, sq_field in mapping.items():
		entry = by_key.get(filter_key) or {}
		doc_attr = entry.get("doc_attr") or filter_key
		val = _pick_gcfq_field(doc, overrides, filter_key, doc_attr)
		if val:
			out[sq_field] = val
	return out


def _effective_declaration_order_filter_fields(
	doc, overrides: dict
) -> tuple[str, str, str, str | None, str, str]:
	"""authority, declaration_type, broker, transport_mode name or None, pol, pod."""
	ca = _pick_gcfq_field(doc, overrides, "customs_authority", "customs_authority")
	dt = _pick_gcfq_field(doc, overrides, "declaration_type", "declaration_type")
	cb = _pick_gcfq_field(doc, overrides, "customs_broker", "customs_broker")
	tm_raw = _pick_gcfq_field(doc, overrides, "transport_mode", "transport_mode")
	jtm = tm_raw or None
	pol = _pick_gcfq_field(doc, overrides, "port_of_loading", "port_of_loading")
	pod = _pick_gcfq_field(doc, overrides, "port_of_discharge", "port_of_discharge")
	return ca, dt, cb, jtm, pol, pod


def _gcfq_airline_only_effective(
	service_type: str, job_airline: str | None, origin: str, dest: str
) -> bool:
	"""True when the dialog should show *airline-only* mode: Air + carrier set + both port filters empty."""
	ja = (job_airline or "").strip()
	o = (origin or "").strip()
	d = (dest or "").strip()
	if (service_type or "").strip() != "Air" or not ja:
		return False
	return not o and not d


def _sales_quote_row_eligible_for_gcfq_list(
	name: str, expected_customer: str, *, require_time_sensitive: bool = False
) -> bool:
	"""Defensive check: list must match the same rules as preview/apply (Regular, submitted, customer).

	Customer compare is case-insensitive so it stays aligned with typical SQL collations: otherwise the
	main query can return rows that this step stripped away and the user sees “no quotes” despite matches.
	"""
	fields = ["quotation_type", "docstatus", "customer"]
	if require_time_sensitive:
		fields.append("is_time_sensitive")
	row = frappe.db.get_value(
		"Sales Quote",
		name,
		fields,
		as_dict=True,
	)
	if not row:
		return False
	if (row.get("quotation_type") or "").strip().lower() != "regular":
		return False
	if cint(row.get("docstatus")) != 1:
		return False
	if not _gcfq_customer_matches_job(row.get("customer"), expected_customer):
		return False
	if require_time_sensitive and not cint(row.get("is_time_sensitive")):
		return False
	return True


def assert_sales_quote_customer_matches_job_before_submit(doc):
	"""Block submit when the linked Sales Quote customer does not match the job customer."""
	if doc.doctype not in JOB_DOCTYPES:
		return
	from logistics.utils.operational_rep_fields import _resolve_sales_quote_name_from_doc

	sq_name = _resolve_sales_quote_name_from_doc(doc)
	if not sq_name:
		return
	job_customer = _job_customer(doc)
	if not job_customer:
		frappe.throw(_("Set the customer on this document before submitting."))
	sq_customer = frappe.db.get_value("Sales Quote", sq_name, "customer")
	if not _gcfq_customer_matches_job(sq_customer, job_customer):
		frappe.throw(
			_("Sales Quote customer does not match this document."),
			title=_("Customer mismatch"),
		)


def assert_one_off_sales_quote_job_rules(doc):
	"""One-off ``Sales Quote`` may only appear on jobs created as main/internal from Sales Quote."""
	if not getattr(doc, "sales_quote", None):
		return
	qtp = frappe.db.get_value("Sales Quote", doc.sales_quote, "quotation_type")
	if (qtp or "") != "One-off":
		return
	from logistics.utils.service_role_rules import (
		SERVICE_ROLE_LINKED,
		SERVICE_ROLE_MAIN,
		get_service_role,
	)

	if get_service_role(doc) in (SERVICE_ROLE_MAIN, SERVICE_ROLE_LINKED):
		return
	frappe.throw(
		_(
			"A One-off Sales Quote can only be linked when this document is created from Sales Quote "
			"(main service) or is a valid internal job."
		),
		title=_("Invalid Sales Quote"),
	)


def _job_customer(doc) -> str | None:
	if doc.doctype in ("Sea Booking", "Air Booking"):
		return (getattr(doc, "local_customer", None) or "").strip() or None
	if doc.doctype == "MICE Project":
		getter = getattr(doc, "get_organizer_customer", None)
		if callable(getter):
			return (getter() or "").strip() or None
		return None
	if doc.doctype in (
		"Transport Order",
		"Declaration Order",
		"Special Project",
		"Exhibit",
		"Time Sensitive Case",
	):
		return (getattr(doc, "customer", None) or "").strip() or None
	return None


def _gcfq_customer_matches_job(sales_quote_customer: str | None, job_customer: str | None) -> bool:
	"""Link fields compared case-insensitively (matches SQL LIKE typical collations; avoids empty lists after SQL)."""
	return (sales_quote_customer or "").strip().lower() == (job_customer or "").strip().lower()


def _gcfq_merge_org_dimension_display(
	filters_payload: dict, branch: str, cost_center: str, profit_center: str
):
	"""Append Branch / Cost Center / Profit Center to dialog ``extra_criteria`` and rules when set."""
	br = (branch or "").strip()
	cc = (cost_center or "").strip()
	pc = (profit_center or "").strip()
	extra_rows = []
	if br:
		extra_rows.append({"label": _("Branch"), "value": br})
	if cc:
		extra_rows.append({"label": _("Cost Center"), "value": cc})
	if pc:
		extra_rows.append({"label": _("Profit Center"), "value": pc})
	if not extra_rows:
		return
	existing = list(filters_payload.get("extra_criteria") or [])
	filters_payload["extra_criteria"] = existing + extra_rows
	rules = list(filters_payload.get("rules") or [])
	rule = _(
		"When Branch, Cost Center, or Profit Center is set on the filter, the Sales Quote header must "
		"match or be blank on the quotation (blank = any)."
	)
	if rules and rule not in rules:
		rules.insert(max(len(rules) - 1, 0), rule)
		filters_payload["rules"] = rules


def _gcfq_list_filters_payload(
	doctype: str,
	customer: str,
	origin: str,
	dest: str,
	service_type: str,
	**kwargs,
) -> dict:
	"""Structured labels/values + rule lines for the Get Charges from Quotation dialog."""
	if doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE:
		return {
			"service_type": service_type,
			"customer_label": _("Customer"),
			"customer": customer,
			"origin_label": _("Origin"),
			"origin": origin,
			"destination_label": _("Destination"),
			"destination": dest,
			"rules": [
				_("Submitted quotations only (draft quotations are excluded)"),
				_("Regular quotations only (One-off quotations are excluded)"),
				_("Valid until is not set or is on or after today"),
				_("Status is not Lost or Expired"),
				_("The quotation must be marked Time Sensitive"),
				_(
					"Main Service on the quotation is not required to be Time Sensitive "
					"(Air, Sea, and other services are eligible)"
				),
				_(
					"When Origin, Destination, or Priority is set on the filter, the Sales Quote header "
					"must match or be blank on the quotation (blank = any)"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	if doctype == "Transport Order":
		return {
			"service_type": service_type,
			"customer_label": _("Customer"),
			"customer": customer,
			"origin_label": _("Location From"),
			"origin": origin,
			"destination_label": _("Location To"),
			"destination": dest,
			"rules": [
				_("Submitted quotations only (draft quotations are excluded)"),
				_("Regular quotations only (One-off quotations are excluded)"),
				_("Valid until is not set or is on or after today"),
				_("Status is not Lost or Expired"),
				_("Main Service on the quotation must be Transport"),
				_(
					"When location from or to is set on the filter, the quotation must match on a charge row "
					"or header — not Sales Quote routing legs"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	if doctype == "Declaration Order":
		extra = [
			{"label": _("Customs Authority"), "value": kwargs.get("customs_authority") or ""},
			{"label": _("Declaration Type"), "value": kwargs.get("declaration_type") or ""},
			{"label": _("Customs Broker"), "value": kwargs.get("customs_broker") or ""},
		]
		tm = (kwargs.get("transport_mode_display") or "").strip()
		if tm:
			extra.append({"label": _("Transport Mode"), "value": tm})
		pol = (kwargs.get("port_of_loading") or "").strip()
		pod = (kwargs.get("port_of_discharge") or "").strip()
		if pol or pod:
			extra.append({"label": _("Port of Loading"), "value": pol})
			extra.append({"label": _("Port of Discharge"), "value": pod})
		return {
			"service_type": service_type,
			"customer_label": _("Customer"),
			"customer": customer,
			"extra_criteria": extra,
			"rules": [
				_("Submitted quotations only (draft quotations are excluded)"),
				_("Regular quotations only (One-off quotations are excluded)"),
				_("Valid until is not set or is on or after today"),
				_("Status is not Lost or Expired"),
				_("Main Service on the quotation must be Customs"),
				_(
					"When Customs Authority, Declaration Type, or Customs Broker is set on the filter, "
					"matching charge lines on the quotation further narrow the list (blank filter = any; "
					"blank broker on a line still matches any broker)"
				),
				_(
					"When Transport Mode is set, legacy customs lines with a transport mode must match it; "
					"unified Customs charge lines are not filtered by mode"
				),
				_("Respects your permission to read Sales Quote records"),
			],
		}
	if service_type == "Sea":
		sl = (kwargs.get("shipping_line") or "").strip()
		extra_criteria = []
		if sl:
			extra_criteria.append({"label": _("Shipping Line"), "value": sl})
		rules = [
			_("Submitted quotations only (draft quotations are excluded)"),
			_("Regular quotations only (One-off quotations are excluded)"),
			_("Valid until is not set or is on or after today"),
			_("Status is not Lost or Expired"),
			_("Main Service on the quotation must be Sea"),
			_(
				"When origin, destination, or shipping line is set on the filter, the quotation must match "
				"on a charge row or header — not Sales Quote routing legs"
			),
		]
		if sl:
			rules.append(
				_(
					"When Shipping Line is set on the booking, the quotation must match that line on a Sea charge row "
					"or header (blank shipping line on a quotation line matches any line)"
				)
			)
		rules.append(_("Respects your permission to read Sales Quote records"))
		out = {
			"service_type": service_type,
			"customer_label": _("Local Customer"),
			"customer": customer,
			"origin_label": _("Origin Port"),
			"origin": origin,
			"destination_label": _("Destination Port"),
			"destination": dest,
			"rules": rules,
		}
		if extra_criteria:
			out["extra_criteria"] = extra_criteria
		return out
	al = (kwargs.get("airline") or "").strip()
	airline_only = bool(kwargs.get("airline_only_mode"))
	extra_criteria = []
	if al:
		extra_criteria.append({"label": _("Airline"), "value": al})
	rules = [
		_("Submitted quotations only (draft quotations are excluded)"),
		_("Regular quotations only (One-off quotations are excluded)"),
		_("Valid until is not set or is on or after today"),
		_("Status is not Lost or Expired"),
		_("Main Service on the quotation must be Air"),
	]
	if airline_only and al:
		rules.append(
			_(
				"With Airline set and ports not both filled, only quotations with an Air charge line "
				"matching that carrier (or a blank line airline) are listed — not Sales Quote routing legs"
			)
		)
	else:
		rules.append(
			_(
				"Origin and destination must match a charge row (or legacy line) on the quotation, "
				"or the quotation header — not Sales Quote routing legs"
			)
		)
		if al:
			rules.append(
				_(
					"When Airline is set on the booking, the quotation must match that airline on a charge row "
					"or header (blank airline on a quotation line matches any carrier)"
				)
			)
	rules.append(_("Respects your permission to read Sales Quote records"))
	out = {
		"service_type": service_type,
		"customer_label": _("Local Customer"),
		"customer": customer,
		"origin_label": _("Origin Port"),
		"origin": origin,
		"destination_label": _("Destination Port"),
		"destination": dest,
		"rules": rules,
	}
	if extra_criteria:
		out["extra_criteria"] = extra_criteria
	out["airline_only_mode"] = airline_only
	return out


def _corridor_mismatch_message_for_preview(
	doc, service_type: str, sales_quote: str, overrides: dict | None = None
) -> str | None:
	"""Return error message if corridor does not match, else None (for API preview responses)."""
	if _gcfq_skip_corridor_sql(getattr(doc, "doctype", None) or ""):
		return None
	ov = overrides or {}
	origin, dest, ja_eff, jsl_eff = _effective_sea_air_transport_corridor(doc, ov)
	o = (origin or "").strip()
	d = (dest or "").strip()
	ja = (ja_eff or "").strip() or None if doc.doctype == "Air Booking" else None
	jsl = (jsl_eff or "").strip() or None if doc.doctype == "Sea Booking" else None
	airline_only = _gcfq_airline_only_effective(service_type, ja, o, d)
	if doc.doctype == "Air Booking" and airline_only:
		if not sales_quote_matches_job_airline_only(sales_quote, (ja or "").strip()):
			return str(
				_("Sales Quote {0} does not match this document's airline (charge lines).").format(sales_quote)
			)
		return None
	if not sales_quote_matches_job_corridor(
		sales_quote, service_type, o, d, job_airline=ja, job_shipping_line=jsl
	):
		if jsl and service_type == "Sea":
			return str(
				_("Sales Quote {0} does not match this document's sea corridor (ports and shipping line).").format(
					sales_quote
				)
			)
		if ja:
			return str(
				_("Sales Quote {0} does not match this document's air corridor (ports and airline).").format(
					sales_quote
				)
			)
		return str(_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote))
	return None


def _org_dimension_mismatch_message_for_preview(
	doc, sales_quote: str, overrides: dict | None = None
) -> str | None:
	ov = overrides or {}
	jb, jcc, jpc = _effective_org_dimension_fields(doc, ov)
	if sales_quote_matches_job_org_dimensions(sales_quote, jb, jcc, jpc):
		return None
	return str(
		_("Sales Quote {0} does not match this document's Branch, Cost Center, or Profit Center.").format(
			sales_quote
		)
	)


def _header_fields_mismatch_message_for_preview(
	doc, sales_quote: str, overrides: dict | None = None
) -> str | None:
	ov = overrides or {}
	header_filters = _effective_sq_header_filters(doc, ov)
	if sales_quote_matches_job_header_fields(sales_quote, header_filters):
		return None
	return str(
		_("Sales Quote {0} does not match one or more filter fields on this document.").format(sales_quote)
	)


def _gcfq_saved_parent_match_error(
	doc, service_type: str, sales_quote: str, overrides: dict | None = None
) -> str | None:
	"""If the quotation does not match fields saved on the document, return a message; else None."""
	if not _gcfq_skip_main_service_match(doc.doctype):
		ms_err = _main_service_mismatch_message(service_type, sales_quote)
		if ms_err:
			return ms_err
	parent = overrides if overrides is not None else {}
	if doc.doctype == "Declaration Order":
		ca, dt, cb, jtm, _pol, _pod = _effective_declaration_order_filter_fields(doc, parent)
		if not sales_quote_matches_declaration_order_filters(sales_quote, ca, dt, cb, jtm):
			return str(
				_("Sales Quote {0} does not match the customs fields saved on this document.").format(sales_quote)
			)
	elif not _gcfq_skip_corridor_sql(doc.doctype):
		corr_err = _corridor_mismatch_message_for_preview(doc, service_type, sales_quote, parent)
		if corr_err:
			return corr_err
	org_err = _org_dimension_mismatch_message_for_preview(doc, sales_quote, parent)
	if org_err:
		return org_err
	return _header_fields_mismatch_message_for_preview(doc, sales_quote, parent)


def _assert_sales_quote_org_dimensions_match_job(
	doc, sales_quote: str, overrides: dict | None = None
):
	ov = overrides or {}
	jb, jcc, jpc = _effective_org_dimension_fields(doc, ov)
	if not sales_quote_matches_job_org_dimensions(sales_quote, jb, jcc, jpc):
		frappe.throw(
			_("Sales Quote {0} does not match this document's Branch, Cost Center, or Profit Center.").format(
				sales_quote
			)
		)


def _assert_sales_quote_header_fields_match_job(
	doc, sales_quote: str, overrides: dict | None = None
):
	ov = overrides or {}
	header_filters = _effective_sq_header_filters(doc, ov)
	if not sales_quote_matches_job_header_fields(sales_quote, header_filters):
		frappe.throw(
			_("Sales Quote {0} does not match one or more filter fields on this document.").format(sales_quote)
		)


def _assert_sales_quote_corridor_matches_job(
	doc, service_type: str, sales_quote: str, overrides: dict | None = None
):
	ov = overrides or {}
	origin, dest, ja_eff, jsl_eff = _effective_sea_air_transport_corridor(doc, ov)
	o = (origin or "").strip()
	d = (dest or "").strip()
	ja = (ja_eff or "").strip() or None if doc.doctype == "Air Booking" else None
	jsl = (jsl_eff or "").strip() or None if doc.doctype == "Sea Booking" else None
	airline_only = _gcfq_airline_only_effective(service_type, ja, o, d)
	if doc.doctype == "Air Booking" and airline_only:
		if not sales_quote_matches_job_airline_only(sales_quote, (ja or "").strip()):
			frappe.throw(
				_("Sales Quote {0} does not match this document's airline (charge lines).").format(sales_quote)
			)
		return
	if not sales_quote_matches_job_corridor(
		sales_quote, service_type, o, d, job_airline=ja, job_shipping_line=jsl
	):
		if jsl and service_type == "Sea":
			frappe.throw(
				_("Sales Quote {0} does not match this document's sea corridor (ports and shipping line).").format(
					sales_quote
				)
			)
		if ja:
			frappe.throw(
				_("Sales Quote {0} does not match this document's air corridor (ports and airline).").format(
					sales_quote
				)
			)
		frappe.throw(
			_("Sales Quote {0} does not match this document's origin and destination.").format(sales_quote)
		)


def _assert_sales_quote_main_service_matches_job(service_type: str, sales_quote: str):
	if not sales_quote_matches_main_service(sales_quote, service_type):
		frappe.throw(
			_("Sales Quote {0} main service must be {1}.").format(sales_quote, service_type),
			title=_("Invalid Sales Quote"),
		)


def _main_service_mismatch_message(service_type: str, sales_quote: str) -> str | None:
	if sales_quote_matches_main_service(sales_quote, service_type):
		return None
	return str(_("Sales Quote {0} main service must be {1}.").format(sales_quote, service_type))


def _sales_quote_is_time_sensitive(sq) -> bool:
	return bool(cint(getattr(sq, "is_time_sensitive", 0)))


def _time_sensitive_quote_mismatch_message(sq) -> str | None:
	if _sales_quote_is_time_sensitive(sq):
		return None
	name = getattr(sq, "name", None) or ""
	return str(_("Sales Quote {0} is not marked Time Sensitive.").format(name))


@contextmanager
def _suppress_msgprint():
	orig = frappe.msgprint

	def _noop(*args, **kwargs):
		return None

	frappe.msgprint = _noop  # type: ignore[assignment]
	try:
		yield
	finally:
		frappe.msgprint = orig  # type: ignore[assignment]


def _sync_quote_fields(doc):
	if doc.doctype == "Sea Booking":
		from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(doc)
	elif doc.doctype == "Air Booking":
		from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(doc)
	elif doc.doctype == "Transport Order":
		from logistics.transport.doctype.transport_order.transport_order import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(doc)


@frappe.whitelist()
def list_sales_quotes_for_job(doctype: str, docname: str, filter_overrides=None):
	"""Return regular (non–One-off) Sales Quotes eligible for Get Charges from Quotation.

	``filter_overrides``: optional JSON dict of dialog filter fields (see ``GCFQ_FILTER_KEYS``).
	Values override the saved document for listing only.
	"""
	if doctype not in JOB_DOCTYPES:
		frappe.throw(_("Unsupported document type."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	service_type = implied_service_type_for_doctype(doctype)
	if not _gcfq_skip_main_service_match(doctype) and not service_type:
		frappe.throw(_("Could not determine service type for {0}.").format(doctype))
	if _gcfq_skip_main_service_match(doctype):
		service_type = service_type or "Time Sensitive"

	customer = _job_customer(doc)
	if not customer:
		return {
			"quotes": [],
			"message": _("Set the customer on this document before loading charges from a quotation."),
			"filters": None,
		}

	ov = _parse_gcfq_filter_overrides(doctype, filter_overrides)
	jb, jcc, jpc = _effective_org_dimension_fields(doc, ov)
	header_filters = _effective_sq_header_filters(doc, ov)

	if doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE:
		origin, dest, _ja, _jsl = _effective_sea_air_transport_corridor(doc, ov)
		filters_payload = _gcfq_list_filters_payload(doctype, customer, origin or "", dest or "", service_type)
		_gcfq_merge_org_dimension_display(filters_payload, jb, jcc, jpc)
		names = fetch_eligible_time_sensitive_sales_quote_names(
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			job_branch=jb or None,
			job_cost_center=jcc or None,
			job_profit_center=jpc or None,
			header_filters=header_filters,
		)
		empty_msg = (
			_("No matching Sales Quotes for these filters.")
			if (origin or dest or jb or jcc or jpc or header_filters)
			else _("No matching Time Sensitive Sales Quotes found.")
		)
	elif doctype == "Declaration Order":
		ca, dt, cb, jtm, pol, pod = _effective_declaration_order_filter_fields(doc, ov)
		tm_disp = ""
		if jtm:
			tm_disp = frappe.db.get_value("Transport Mode", jtm, "mode_name") or jtm
		filters_payload = _gcfq_list_filters_payload(
			doctype,
			customer,
			pol or "",
			pod or "",
			service_type,
			customs_authority=ca,
			declaration_type=dt,
			customs_broker=cb,
			transport_mode_display=tm_disp,
			port_of_loading=pol,
			port_of_discharge=pod,
		)
		_gcfq_merge_org_dimension_display(filters_payload, jb, jcc, jpc)
		names = fetch_eligible_regular_sales_quote_names(
			service_type,
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			customs_authority=ca or None,
			declaration_type=dt or None,
			customs_broker=cb or None,
			job_transport_mode=jtm,
			job_branch=jb or None,
			job_cost_center=jcc or None,
			job_profit_center=jpc or None,
			header_filters=header_filters,
		)
		empty_msg = (
			_("No matching Sales Quotes for these filters.")
			if (ca or dt or cb or jtm or jb or jcc or jpc or header_filters)
			else _("No matching Sales Quotes found.")
		)
	else:
		origin, dest, job_airline, job_shipping_line = _effective_sea_air_transport_corridor(doc, ov)
		job_airline = (job_airline or "").strip() or None if doctype == "Air Booking" else None
		job_shipping_line = (job_shipping_line or "").strip() or None if doctype == "Sea Booking" else None
		airline_only = _gcfq_airline_only_effective(service_type, job_airline, origin, dest)
		if airline_only and job_airline:
			filters_payload = _gcfq_list_filters_payload(
				doctype,
				customer,
				origin or "",
				dest or "",
				service_type,
				airline=job_airline,
				airline_only_mode=True,
			)
		else:
			extra_kw = {}
			if job_airline:
				extra_kw["airline"] = job_airline
			if job_shipping_line:
				extra_kw["shipping_line"] = job_shipping_line
			filters_payload = _gcfq_list_filters_payload(
				doctype,
				customer,
				origin,
				dest,
				service_type,
				**extra_kw,
			)
		_gcfq_merge_org_dimension_display(filters_payload, jb, jcc, jpc)

		names = fetch_eligible_regular_sales_quote_names(
			service_type,
			customer=customer,
			reference_doctype=doctype,
			reference_name=docname,
			limit=150,
			corridor_origin=origin,
			corridor_dest=dest,
			job_airline=job_airline,
			job_shipping_line=job_shipping_line,
			job_branch=jb or None,
			job_cost_center=jcc or None,
			job_profit_center=jpc or None,
			header_filters=header_filters,
		)
		# Clearer copy when corridor is not narrowing (e.g. only Branch/CC/PC set — matches screenshot UX).
		has_corridor_constraint = False
		if doctype == "Air Booking":
			has_corridor_constraint = bool(
				(origin or "").strip() or (dest or "").strip() or (job_airline or "").strip()
			)
		elif doctype == "Sea Booking":
			has_corridor_constraint = bool(
				(origin or "").strip() or (dest or "").strip() or (job_shipping_line or "").strip()
			)
		elif doctype == "Transport Order":
			has_corridor_constraint = bool((origin or "").strip() or (dest or "").strip())
		if airline_only:
			empty_msg = _("No matching Sales Quotes for this airline.")
		elif not has_corridor_constraint and (jb or jcc or jpc or header_filters):
			empty_msg = _("No matching Sales Quotes for these filters.")
		elif not has_corridor_constraint:
			empty_msg = _("No matching Sales Quotes found.")
		else:
			empty_msg = _("No matching Sales Quotes for this corridor and filters.")

	names = [
		n
		for n in names
		if _sales_quote_row_eligible_for_gcfq_list(
			n, customer, require_time_sensitive=_gcfq_skip_main_service_match(doctype)
		)
	]
	if not names:
		return {
			"quotes": [],
			"message": empty_msg,
			"filters": filters_payload,
		}

	fields = [
		"name",
		"customer",
		"status",
		"date",
		"valid_until",
		"company",
		"origin_port",
		"destination_port",
		"location_from",
		"location_to",
		"branch",
		"cost_center",
		"profit_center",
	]
	rows = frappe.get_all("Sales Quote", filters={"name": ["in", names]}, fields=fields, order_by="modified desc")
	order = {n: i for i, n in enumerate(names)}
	rows.sort(key=lambda r: order.get(r.name, 9999))
	return {"quotes": rows, "message": None, "filters": filters_payload}


@frappe.whitelist()
def preview_quotation_charges_for_job(
	doctype: str, docname: str, sales_quote: str, filter_overrides=None
):
	"""Preview charges (and routing for Sea/Air) without saving."""
	if doctype not in JOB_DOCTYPES or not sales_quote:
		return {"error": _("Invalid arguments.")}

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=doc, throw=True)

	service_type = implied_service_type_for_doctype(doctype)
	if not _gcfq_skip_main_service_match(doctype) and not service_type:
		return {"error": _("Could not determine service type for {0}.").format(doctype)}
	if _gcfq_skip_main_service_match(doctype):
		service_type = service_type or "Time Sensitive"

	ov = _parse_gcfq_filter_overrides(doctype, filter_overrides)

	sq = frappe.get_doc("Sales Quote", sales_quote)
	if cint(sq.docstatus) != 1:
		return {"error": _("Only submitted Sales Quotes can be used (draft quotations are excluded).")}
	qtp = (sq.quotation_type or "").strip()
	if qtp != "Regular":
		if qtp == "One-off":
			return {"error": _("One-off quotations cannot be applied from this action.")}
		return {"error": _("Only Regular quotations can be used from this action.")}

	customer = _job_customer(doc)
	if not customer or not _gcfq_customer_matches_job(sq.customer, customer):
		return {"error": _("Sales Quote customer does not match this document.")}

	if _gcfq_skip_main_service_match(doctype):
		ts_err = _time_sensitive_quote_mismatch_message(sq)
		if ts_err:
			return {"error": ts_err}
	else:
		ms_err = _main_service_mismatch_message(service_type, sales_quote)
		if ms_err:
			return {"error": ms_err}

	if doctype == "Declaration Order":
		ca, dt, cb, jtm, _pol, _pod = _effective_declaration_order_filter_fields(doc, ov)
		if not sales_quote_matches_declaration_order_filters(sales_quote, ca, dt, cb, jtm):
			return {
				"error": str(
					_("Sales Quote {0} does not match this order's customs filters (charge lines).").format(
						sales_quote
					)
				),
			}
		corr_err = None
	elif not _gcfq_skip_corridor_sql(doctype):
		corr_err = _corridor_mismatch_message_for_preview(doc, service_type, sales_quote, ov)
		if corr_err:
			return {"error": corr_err}

	org_err = _org_dimension_mismatch_message_for_preview(doc, sales_quote, ov)
	if org_err:
		return {"error": org_err}

	parent_err = _gcfq_saved_parent_match_error(doc, service_type, sales_quote, ov)
	if parent_err:
		return {"error": parent_err}

	if doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE:
		return _preview_time_sensitive_case_charges_from_sales_quote(sq)

	if doctype == "Special Project":
		from logistics.utils.sales_quote_programme_charges import preview_programme_charges_from_sales_quote

		return preview_programme_charges_from_sales_quote(docname, doctype, sales_quote)
	if doctype in ("Exhibit", "MICE Project"):
		from logistics.utils.sales_quote_programme_charges import preview_programme_charges_from_sales_quote

		return preview_programme_charges_from_sales_quote(docname, doctype, sales_quote)

	if doctype == "Sea Booking":
		from logistics.sea_freight.doctype.sea_booking.sea_booking import populate_charges_from_sales_quote

		main_response = populate_charges_from_sales_quote(
			docname, sales_quote, gcfq_main_service_only=1
		)
	elif doctype == "Air Booking":
		from logistics.air_freight.doctype.air_booking.air_booking import populate_charges_from_sales_quote

		main_response = populate_charges_from_sales_quote(
			docname, sales_quote, gcfq_main_service_only=1
		)
	elif doctype == "Transport Order":
		from logistics.transport.doctype.transport_order.transport_order import populate_charges_from_sales_quote

		main_response = populate_charges_from_sales_quote(
			docname, sales_quote, gcfq_main_service_only=1
		)
	elif doctype == "Declaration Order":
		from logistics.customs.doctype.declaration_order.declaration_order import populate_charges_from_sales_quote

		main_response = populate_charges_from_sales_quote(
			docname, sales_quote, gcfq_main_service_only=1
		)
	else:
		return {"error": _("Unsupported document type.")}

	# Append Internal-Job-scoped Sales Quote Charge rows alongside Main rows so the dialog preview
	# matches what apply_quotation_charges_to_job will tag onto the Main charges table.
	return _gcfq_attach_internal_job_scoped_preview_rows(main_response, doc, sq)


# Operational booking/order doctypes whose charges child table carries the per-scope columns
# (``charge_scope`` / ``internal_job``). Only these accept the Internal-Job-scoped pass; programme
# parents (Special Project / Exhibit) keep their existing single-pass population.
_GCFQ_PER_SCOPE_PARENT_DOCTYPES = frozenset(
	{"Sea Booking", "Air Booking", "Transport Order", "Declaration Order"}
)


def _gcfq_internal_job_label(ij_name: str) -> str:
	"""Best-effort human label for an Internal Job (``<name> (Service · Job no/type)``) for previews."""
	if not ij_name:
		return ""
	try:
		info = (
			frappe.db.get_value(
				"Internal Job",
				ij_name,
				("service_type", "job_no", "job_type"),
				as_dict=True,
			)
			or {}
		)
	except Exception:
		info = {}
	bits = [b for b in (info.get("service_type"), info.get("job_no") or info.get("job_type")) if b]
	if not bits:
		return ij_name
	return f"{ij_name} ({' · '.join(bits)})"


def _preview_time_sensitive_case_charges_from_sales_quote(sq) -> dict:
	"""Map Sales Quote charges onto the GCFQ preview table (Main / Linked, not Internal Job)."""
	from logistics.time_sensitive.ts_sq_fetch import _quote_charge_payload

	charges: list[dict] = []
	linked_n = 0
	for ch in sq.get("charges") or []:
		payload = _quote_charge_payload(ch)
		scope = (payload.get("charge_scope") or "Main").strip() or "Main"
		ls = (payload.get("linked_service") or "").strip()
		if scope == "Linked":
			linked_n += 1
		charges.append(
			{
				"item_code": payload.get("item_code") or "",
				"item_name": payload.get("description") or payload.get("label") or "",
				"service_type": payload.get("service_type") or "",
				"unit_rate": payload.get("rate"),
				"rate": payload.get("rate"),
				"currency": payload.get("currency") or "",
				"charge_scope": scope,
				"linked_service": ls,
				"internal_job": ls if scope == "Linked" else "",
				"internal_job_label": ls,
			}
		)
	return {
		"charges": charges,
		"charges_count": len(charges),
		"linked_charge_count": linked_n,
		"internal_job_charge_count": 0,
	}


def _gcfq_quote_row_to_preview_dict(row, scope: str, internal_job: str | None) -> dict:
	"""Lightweight preview row matching the JS dialog table shape (service_type, item_code, …).

	The Main pass uses the booking's own response shape; this helper only builds rows for the
	Internal-Job-scoped pass so the preview can show what will be tagged onto the Main charges
	table when the user applies the quotation.
	"""

	def _g(fn):
		if isinstance(row, dict):
			return row.get(fn)
		return getattr(row, fn, None)

	preview = {
		"name": _g("name"),
		"item_code": _g("item_code"),
		"item_name": _g("item_name"),
		"service_type": _g("service_type"),
		"charge_type": _g("charge_type"),
		"charge_category": _g("charge_category"),
		"unit_rate": _g("unit_rate"),
		"rate": _g("unit_rate"),
		"currency": _g("currency"),
		"uom": _g("uom"),
		"charge_scope": scope,
		"internal_job": internal_job or "",
	}
	if internal_job:
		preview["internal_job_label"] = _gcfq_internal_job_label(internal_job)
	return preview


def _gcfq_attach_internal_job_scoped_preview_rows(main_response, parent_doc, sq_doc):
	"""Append Internal-Job-scoped preview rows to a Main preview response (no-op when not eligible).

	Reuses ``populate_charges_from_quote_by_scope`` so the per-IJ matching logic is exactly the same
	as ``_append_internal_job_scoped_charges_to_main`` (the apply path).
	"""
	if not isinstance(main_response, dict) or main_response.get("error"):
		return main_response
	if (
		not parent_doc
		or not sq_doc
		or getattr(parent_doc, "doctype", None) not in _GCFQ_PER_SCOPE_PARENT_DOCTYPES
	):
		return main_response

	from logistics.utils.charge_service_type import is_combined_billing_main_service_booking

	if is_combined_billing_main_service_booking(parent_doc, sq_doc):
		main_charges = list(main_response.get("charges") or [])
		for ch in main_charges:
			if isinstance(ch, dict) and not ch.get("charge_scope"):
				ch["charge_scope"] = "Main"
		main_response["charges"] = main_charges
		main_response["charges_count"] = main_response.get("charges_count", len(main_charges))
		main_response["internal_job_charge_count"] = 0
		return main_response

	from logistics.utils.sales_quote_charge_copy import (
		SCOPE_INTERNAL_JOB,
		populate_charges_from_quote_by_scope,
	)

	# Existing Main response charges first; preserve scope tags when a downstream caller already
	# stamped them. Use a defensive copy so we never mutate the input list in place.
	main_charges = list(main_response.get("charges") or [])
	for ch in main_charges:
		if isinstance(ch, dict) and not ch.get("charge_scope"):
			ch["charge_scope"] = "Main"

	ij_charges: list[dict] = []

	def _on_scope_match(quote_row, scope, internal_job):
		if scope != SCOPE_INTERNAL_JOB:
			return
		if not internal_job:
			return
		ij_charges.append(_gcfq_quote_row_to_preview_dict(quote_row, scope, internal_job))

	try:
		populate_charges_from_quote_by_scope(parent_doc, sq_doc, _on_scope_match)
	except Exception:
		frappe.log_error(
			title=_("GCFQ → IJ-scope preview failed"),
			message=frappe.get_traceback(),
		)
		ij_charges = []

	if not ij_charges:
		# Still tag the existing Main rows so the JS preview can render the Scope column.
		main_response["charges"] = main_charges
		main_response["charges_count"] = main_response.get("charges_count", len(main_charges))
		main_response["internal_job_charge_count"] = 0
		return main_response

	combined = main_charges + ij_charges
	main_response["charges"] = combined
	main_response["charges_count"] = len(combined)
	main_response["main_charge_count"] = len(main_charges)
	main_response["internal_job_charge_count"] = len(ij_charges)
	return main_response

# Generic Sales Quote Charge → operational charge field copy list. Each field is only copied when
# present on the target child doctype, so the same map is safe across Sea/Air/Transport/Customs
# charge tables (and any future ones that follow the same conventions).
_SQ_CHARGE_COPY_FIELDS: tuple[str, ...] = (
	"item_code",
	"item_name",
	"description",
	"service_type",
	"charge_type",
	"charge_category",
	"revenue_calculation_method",
	"calculation_method",
	"uom",
	"currency",
	"unit_rate",
	"unit_type",
	"quantity",
	"minimum_quantity",
	"minimum_unit_rate",
	"minimum_charge",
	"maximum_charge",
	"base_amount",
	"base_quantity",
	"estimated_revenue",
	"cost_calculation_method",
	"unit_cost",
	"cost_unit_type",
	"cost_currency",
	"cost_quantity",
	"cost_minimum_quantity",
	"cost_minimum_unit_rate",
	"cost_minimum_charge",
	"cost_maximum_charge",
	"cost_base_amount",
	"cost_base_quantity",
	"cost_uom",
	"estimated_cost",
	"use_tariff_in_revenue",
	"use_tariff_in_cost",
	"tariff",
	"revenue_tariff",
	"cost_tariff",
	"bill_to",
	"bill_to_exchange_rate",
	"bill_to_exchange_rate_source",
	"pay_to",
	"pay_to_exchange_rate",
	"pay_to_exchange_rate_source",
	"apply_95_5_rule",
	"taxable_freight_item",
	"taxable_freight_item_tax_template",
	"origin_port",
	"destination_port",
	"location_from",
	"location_to",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
)


def _operational_child_doctype_for_charges(parent_doc) -> str | None:
	"""Return the child doctype configured on ``parent_doc.meta`` for the ``charges`` table."""
	try:
		meta = frappe.get_meta(getattr(parent_doc, "doctype", None))
	except Exception:
		return None
	df = meta.get_field("charges") if meta else None
	if not df:
		return None
	return (df.options or "").strip() or None


def _sq_charge_row_to_operational_dict(
	sq_row, child_doctype: str, sales_quote_name: str
) -> dict | None:
	"""Generic mapper: SQ Charge row (Document or dict) → operational charge child row dict.

	Only fields declared on the target child doctype are written, so the same helper is safe across
	Sea/Air/Transport/Customs charge tables. The per-doctype ``_map_…`` methods already exist on
	the booking docs but they assume their own service type; here we keep the appended IJ-scoped
	rows as ``service_type`` from the quote so reports / downstream conversion can distinguish them.
	"""
	try:
		child_meta = frappe.get_meta(child_doctype)
	except Exception:
		return None
	valid = {f.fieldname for f in child_meta.fields}

	def _get(fn):
		if isinstance(sq_row, dict):
			return sq_row.get(fn)
		return getattr(sq_row, fn, None)

	out: dict = {}
	for fn in _SQ_CHARGE_COPY_FIELDS:
		if fn not in valid:
			continue
		val = _get(fn)
		if val is None:
			continue
		out[fn] = val

	rev_basis = _get("revenue_calculation_method") or _get("calculation_method")
	if "revenue_calculation_method" in valid and rev_basis and not out.get(
		"revenue_calculation_method"
	):
		out["revenue_calculation_method"] = rev_basis

	if "sales_quote_link" in valid and sales_quote_name:
		out.setdefault("sales_quote_link", sales_quote_name)
	if "charge_type" in valid:
		from logistics.utils.charges_calculation import normalize_operational_charge_type

		out["charge_type"] = normalize_operational_charge_type(out.get("charge_type"), default="Revenue")
	if not out.get("item_code"):
		return None
	return out


def _append_internal_job_scoped_charges_to_main(parent_doc, sq_doc) -> dict[str, int]:
	"""Append IJ-scoped Sales Quote Charge rows to ``parent_doc.charges`` (Main charges stay intact).

	For every Internal Job linked from ``parent_doc.internal_job_details`` (via the canonical
	``internal_job`` link to the ``Internal Job`` doctype), this iterates the quote's charge rows
	whose service type matches the IJ and whose parameters match the IJ's snapshot, then appends a
	new charge row tagged with ``charge_scope = "Internal Job"`` and ``internal_job = ij.name``.

	The same Sales Quote Charge row may be appended multiple times — once per matching IJ —
	matching the existing ``populate_charges_from_quote_by_scope`` semantics.
	"""
	from logistics.utils.sales_quote_charge_copy import (
		SCOPE_INTERNAL_JOB,
		populate_charges_from_quote_by_scope,
		stamp_scope_fields_on_charge_row,
	)

	counts = {"main": 0, "internal_job": 0}
	if not parent_doc or not sq_doc:
		return counts
	if getattr(parent_doc, "doctype", None) not in _GCFQ_PER_SCOPE_PARENT_DOCTYPES:
		return counts

	from logistics.utils.charge_service_type import is_combined_billing_main_service_booking

	# Combined billing: main pass already loaded every quote row; skip IJ-scoped duplicates.
	if is_combined_billing_main_service_booking(parent_doc, sq_doc):
		return counts

	child_doctype = _operational_child_doctype_for_charges(parent_doc)
	if not child_doctype:
		return counts
	try:
		child_meta = frappe.get_meta(child_doctype)
	except Exception:
		return counts
	# Without the per-scope columns the IJ-scoped pass has nothing to write into — bail out.
	if not (child_meta.has_field("charge_scope") and child_meta.has_field("internal_job")):
		return counts

	sales_quote_name = getattr(sq_doc, "name", None)

	def _on_scope_match(quote_row, scope, internal_job):
		# Main pass is intentionally a no-op — the booking's own ``_populate_charges_from_sales_quote``
		# already filled Main-scope rows in this transaction (``gcfq_main_service_only = 1``).
		if scope != SCOPE_INTERNAL_JOB:
			counts["main"] += 1
			return
		if not internal_job:
			return
		row_dict = _sq_charge_row_to_operational_dict(quote_row, child_doctype, sales_quote_name)
		if not row_dict:
			return
		child = parent_doc.append("charges", row_dict)
		stamp_scope_fields_on_charge_row(child, scope, internal_job)
		counts["internal_job"] += 1

	populate_charges_from_quote_by_scope(parent_doc, sq_doc, _on_scope_match)
	return counts


@frappe.whitelist()
def apply_quotation_charges_to_job(
	doctype: str, docname: str, sales_quote: str, filter_overrides=None
):
	"""Set ``sales_quote``, routing (Sea/Air), and charges; then save.

	When ``separate_billings_per_service_type`` is off on the quote, the booking whose doctype
	matches quote ``main_service`` receives **all** quote charge rows (regardless of ``is_main_service``).
	When separate billings is on, each job keeps only its implied service type; Internal Job–scoped
	rows may still be appended for linked IJs.
	"""
	if doctype not in JOB_DOCTYPES or not sales_quote:
		frappe.throw(_("Invalid arguments."))

	doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "write", doc=doc, throw=True)

	if doc.docstatus != 0:
		frappe.throw(_("Only draft documents can load charges from a quotation."))

	ov = _parse_gcfq_filter_overrides(doctype, filter_overrides)

	sq = frappe.get_doc("Sales Quote", sales_quote)
	if cint(sq.docstatus) != 1:
		frappe.throw(_("Only submitted Sales Quotes can be used (draft quotations are excluded)."))
	qtp = (sq.quotation_type or "").strip()
	if qtp != "Regular":
		if qtp == "One-off":
			frappe.throw(
				_("One-off Sales Quotes can only be used when creating the job from Sales Quote.")
			)
		frappe.throw(_("Only Regular quotations can be used from this action."))

	customer = _job_customer(doc)
	if not customer:
		frappe.throw(_("Set the customer on this document first."))
	if not _gcfq_customer_matches_job(sq.customer, customer):
		frappe.throw(_("Sales Quote customer does not match this document."))

	service_type = implied_service_type_for_doctype(doctype)
	if not _gcfq_skip_main_service_match(doctype) and not service_type:
		frappe.throw(_("Could not determine service type for {0}.").format(doctype))
	if _gcfq_skip_main_service_match(doctype):
		service_type = service_type or "Time Sensitive"
		ts_err = _time_sensitive_quote_mismatch_message(sq)
		if ts_err:
			frappe.throw(ts_err, title=_("Invalid Sales Quote"))
	else:
		_assert_sales_quote_main_service_matches_job(service_type, sales_quote)
	if doctype == "Declaration Order":
		ca, dt, cb, jtm, _pol, _pod = _effective_declaration_order_filter_fields(doc, ov)
		if not sales_quote_matches_declaration_order_filters(sales_quote, ca, dt, cb, jtm):
			frappe.throw(
				_("Sales Quote {0} does not match this order's customs filters (charge lines).").format(
					sales_quote
				)
			)
	elif not _gcfq_skip_corridor_sql(doctype):
		_assert_sales_quote_corridor_matches_job(doc, service_type, sales_quote, ov)

	_assert_sales_quote_org_dimensions_match_job(doc, sales_quote, ov)
	_assert_sales_quote_header_fields_match_job(doc, sales_quote, ov)

	parent_err = _gcfq_saved_parent_match_error(doc, service_type, sales_quote, ov)
	if parent_err:
		frappe.throw(parent_err, title=_("Cannot apply quotation"))

	doc.flags.skip_sales_quote_on_change = True
	# Action → Get Charges from Quotation: per-service charge fetch on main jobs when separate
	# billings is on; combined billing (separate off) loads all quote rows on the main job.
	# See sales_quote_charge_filters / is_combined_billing_main_service_booking.
	doc.flags.gcfq_main_service_only = 1
	doc.sales_quote = sales_quote
	_sync_quote_fields(doc)
	copy_operational_rep_fields_from_sales_quote_doc(doc, sq)

	if doc.meta.has_field("routing_legs"):
		apply_sales_quote_routing_to_booking(doc, sq)

	with _suppress_msgprint():
		if doctype == "Sea Booking":
			doc._populate_charges_from_sales_quote(sq)
		elif doctype == "Air Booking":
			doc._populate_charges_from_sales_quote(sales_quote)
			if hasattr(doc, "_normalize_charges_before_save"):
				doc._normalize_charges_before_save()
		elif doctype == "Transport Order":
			doc._populate_charges_from_sales_quote()
		elif doctype == "Declaration Order":
			doc._populate_charges_from_sales_quote()
		elif doctype == "Special Project":
			doc.populate_charges_from_sales_quote(sales_quote)
		elif doctype in ("Exhibit", "MICE Project"):
			doc.populate_charges_from_sales_quote(sales_quote)
		elif doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE:
			from logistics.time_sensitive.ts_sq_fetch import copy_charges_from_sales_quote_to_case

			copy_charges_from_sales_quote_to_case(doc, sq, clear_existing=True)

	# Append Internal-Job-scoped Sales Quote Charge rows into the Main's charges table (no separate
	# write to internal job documents — the Main now carries both scopes side by side).
	with _suppress_msgprint():
		scope_counts = _append_internal_job_scoped_charges_to_main(doc, sq)

	from logistics.utils.sales_quote_one_off_internal_jobs import (
		apply_linked_services_from_sales_quote_on_fetch,
	)

	apply_linked_services_from_sales_quote_on_fetch(sq, doc)

	try:
		doc.save()
	finally:
		doc.flags.skip_sales_quote_on_change = False
		doc.flags.gcfq_main_service_only = 0

	if doctype == _GCFQ_TIME_SENSITIVE_DOCTYPE:
		from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
			stamp_sales_quote_from_case,
		)

		stamp_sales_quote_from_case(sales_quote, doc)

	ij_count = scope_counts.get("internal_job", 0)
	if ij_count:
		message = _(
			"Charges applied from Sales Quote {0} ({1} internal-job line{2} tagged on this document)."
		).format(
			sales_quote,
			ij_count,
			"" if ij_count == 1 else "s",
		)
	else:
		message = _("Charges applied from Sales Quote {0}.").format(sales_quote)

	return {
		"success": True,
		"message": message,
		"name": doc.name,
		"internal_job_charge_lines": ij_count,
	}
