# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed / apply non-charge Change Request sections onto locked jobs."""

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cstr, escape_html

# Header fields copied onto Change Request and applied back to the job when present on both.
PARTIES_FIELDS = (
	"customer",
	"local_customer",
	"booking_party",
	"shipper",
	"consignee",
	"shipper_address",
	"consignee_address",
	"shipper_contact",
	"consignee_contact",
	"notify_party",
	"notify_party_address",
	"freight_agent",
	"sending_agent",
	"receiving_agent",
	"broker",
	"controlling_party",
	"incoterm",
	"direction",
	"house_type",
	"release_type",
	"entry_type",
	"service_level",
	"logistics_service_level",
)

PLACES_DATES_FIELDS = (
	"origin_port",
	"destination_port",
	"etd",
	"eta",
	"scheduled_date",
	"booking_date",
	"vehicle_type",
	"transport_mode",
	"load_type",
	"transport_company",
	"transport_job_type",
	"container_type",
	"container_no",
	"cargo_cut_off",
	"document_cut_off",
	"vgm_cut_off",
	"gate_in_cut_off",
	"empty_return_cut_off",
	"other_cut_off",
	# Run Sheet
	"run_date",
	"run_type",
	"route_name",
	"vehicle",
	"driver",
	"trailer_type",
	"dispatch_terminal",
	"return_terminal",
	"estimated_completion_time",
	"estimated_dispatch_datetime",
	"estimated_return_datetime",
	"transport_consolidation",
)

NOTES_FIELDS = (
	"internal_notes",
	"client_notes",
	"sales_rep",
	"operations_rep",
	"customer_service_rep",
	"description",
	"marks_and_nos",
	"customer_ref_no",
	# Run Sheet assignment
	"dispatcher",
	"return_inspector",
	"remarks",
)

SECTION_FIELD_MAP = {
	"Parties": PARTIES_FIELDS,
	"Places & Dates": PLACES_DATES_FIELDS,
	"Notes": NOTES_FIELDS,
}

# Header fields that exist on each job DocType (union of seed/apply mirrors).
# Keep in sync with logistics/public/js/change_request_visibility.js.
_AIR_SEA_PARTIES = (
	"local_customer",
	"booking_party",
	"shipper",
	"consignee",
	"shipper_address",
	"consignee_address",
	"shipper_contact",
	"consignee_contact",
	"notify_party",
	"notify_party_address",
	"freight_agent",
	"sending_agent",
	"receiving_agent",
	"broker",
	"controlling_party",
	"incoterm",
	"direction",
	"house_type",
	"release_type",
	"entry_type",
	"service_level",
)

_AIR_SEA_PLACES = (
	"origin_port",
	"destination_port",
	"etd",
	"eta",
	"booking_date",
	"transport_mode",
	"load_type",
)

_SEA_CUTOFFS = (
	"cargo_cut_off",
	"document_cut_off",
	"vgm_cut_off",
	"gate_in_cut_off",
	"empty_return_cut_off",
	"other_cut_off",
)

_AIR_SEA_NOTES = (
	"internal_notes",
	"client_notes",
	"sales_rep",
	"operations_rep",
	"customer_service_rep",
	"description",
	"marks_and_nos",
)

_TRANSPORT_PARTIES = (
	"customer",
	"shipper",
	"consignee",
	"shipper_address",
	"consignee_address",
	"shipper_contact",
	"consignee_contact",
	"logistics_service_level",
	"service_level",
)

_TRANSPORT_PLACES = (
	"scheduled_date",
	"booking_date",
	"vehicle_type",
	"transport_mode",
	"load_type",
	"transport_company",
	"transport_job_type",
	"container_type",
	"container_no",
)

_TRANSPORT_NOTES = (
	"internal_notes",
	"client_notes",
	"sales_rep",
	"operations_rep",
	"customer_service_rep",
	"customer_ref_no",
)

_RUN_SHEET_PLACES = (
	"vehicle_type",
	"transport_company",
	"run_date",
	"run_type",
	"route_name",
	"vehicle",
	"driver",
	"trailer_type",
	"dispatch_terminal",
	"return_terminal",
	"estimated_completion_time",
	"estimated_dispatch_datetime",
	"estimated_return_datetime",
	"transport_consolidation",
)

_RUN_SHEET_NOTES = (
	"dispatcher",
	"return_inspector",
)

JOB_TYPE_HEADER_FIELDS = {
	"Air Shipment": frozenset(_AIR_SEA_PARTIES + _AIR_SEA_PLACES + _AIR_SEA_NOTES),
	"Air Booking": frozenset(_AIR_SEA_PARTIES + _AIR_SEA_PLACES + _AIR_SEA_NOTES),
	"Sea Shipment": frozenset(
		_AIR_SEA_PARTIES + _AIR_SEA_PLACES + _SEA_CUTOFFS + ("internal_notes",)
		+ (
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
			"marks_and_nos",
		)
	),
	"Sea Booking": frozenset(_AIR_SEA_PARTIES + _AIR_SEA_PLACES + _SEA_CUTOFFS + _AIR_SEA_NOTES),
	"Transport Job": frozenset(
		("customer", "shipper", "consignee", "shipper_address", "consignee_address",
		 "shipper_contact", "consignee_contact", "logistics_service_level")
		+ _TRANSPORT_PLACES
		+ _TRANSPORT_NOTES
	),
	"Transport Order": frozenset(
		("customer", "shipper", "consignee", "shipper_address", "consignee_address",
		 "shipper_contact", "consignee_contact", "service_level")
		+ _TRANSPORT_PLACES
		+ _TRANSPORT_NOTES
	),
	"Warehouse Job": frozenset(
		("customer", "shipper", "consignee", "logistics_service_level")
	),
	"Inbound Order": frozenset(("customer", "shipper", "consignee")),
	"Release Order": frozenset(("customer", "shipper", "consignee")),
	"Cross-Docking Order": frozenset(("customer", "shipper", "consignee")),
	"Declaration": frozenset(
		(
			"customer",
			"notify_party",
			"notify_party_address",
			"freight_agent",
			"incoterm",
			"service_level",
			"etd",
			"eta",
			"transport_mode",
			"internal_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"remarks",
		)
	),
	"Declaration Order": frozenset(
		(
			"customer",
			"notify_party",
			"freight_agent",
			"incoterm",
			"service_level",
			"etd",
			"eta",
			"transport_mode",
			"internal_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"remarks",
		)
	),
	"Special Project": frozenset(
		(
			"customer",
			"logistics_service_level",
			"internal_notes",
			"client_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
		)
	),
	"Docket": frozenset(
		(
			"customer",
			"internal_notes",
			"client_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
		)
	),
	"Run Sheet": frozenset(_RUN_SHEET_PLACES + _RUN_SHEET_NOTES),
}

JOB_TYPES_WITH_PACKAGES = frozenset(
	{
		"Air Shipment",
		"Air Booking",
		"Sea Shipment",
		"Sea Booking",
		"Transport Job",
		"Transport Order",
		"Declaration",
		"Declaration Order",
		"Special Project",
		"Docket",
	}
)

JOB_TYPES_WITHOUT_CHARGES = frozenset({"Run Sheet"})

JOB_TYPES_WITHOUT_SERVICES = frozenset({"Run Sheet"})

# Package fields shared across Air / Sea / Transport package child tables.
PACKAGE_COPY_FIELDS = (
	"package_row",
	"commodity",
	"warehouse_item",
	"hs_code",
	"reference_no",
	"goods_description",
	"description",
	"no_of_packs",
	"quantity",
	"uom",
	"dimension_uom",
	"length",
	"width",
	"height",
	"volume_uom",
	"volume",
	"weight_uom",
	"weight",
	"contains_dangerous_goods",
	"dg_substance",
	"un_number",
	"proper_shipping_name",
	"dg_class",
	"packing_group",
)

SECTION_LABELS = (
	"Parties",
	"Places & Dates",
	"Packages",
	"Charges",
	"Notes",
)


def parse_change_sections(value):
	if not value:
		return set()
	if isinstance(value, (list, tuple, set)):
		return {cstr(v).strip() for v in value if cstr(v).strip()}
	parts = []
	for chunk in cstr(value).replace(",", "\n").split("\n"):
		chunk = chunk.strip()
		if chunk:
			parts.append(chunk)
	return set(parts)


def header_fields_for_job_type(job_type):
	"""Amendable header fields that exist on the linked job DocType."""
	if not job_type:
		return frozenset(all_amendable_header_fields())
	known = JOB_TYPE_HEADER_FIELDS.get(job_type)
	if known is not None:
		return known
	return frozenset(all_amendable_header_fields())


def job_type_supports_packages(job_type):
	if not job_type:
		return True
	return job_type in JOB_TYPES_WITH_PACKAGES


def job_type_supports_charges(job_type):
	if not job_type:
		return True
	return job_type not in JOB_TYPES_WITHOUT_CHARGES


def job_type_supports_services(job_type):
	if not job_type:
		return True
	return job_type not in JOB_TYPES_WITHOUT_SERVICES


def applicable_header_fields(job_type, sections=None):
	"""Intersection of job-type fields and selected change_sections (empty = all)."""
	allowed = header_fields_for_job_type(job_type)
	section_set = parse_change_sections(sections) if sections is not None else set()
	if not section_set:
		return allowed
	wanted = set()
	for sec in section_set:
		wanted.update(SECTION_FIELD_MAP.get(sec) or ())
	return frozenset(fn for fn in allowed if fn in wanted)


def header_fields_for_sections(sections):
	fields = []
	seen = set()
	for section, flist in SECTION_FIELD_MAP.items():
		if section not in sections and sections:
			# If sections empty, seed all header sections (caller decides).
			continue
		for fn in flist:
			if fn not in seen:
				seen.add(fn)
				fields.append(fn)
	return tuple(fields)


def all_amendable_header_fields():
	fields = []
	seen = set()
	for flist in SECTION_FIELD_MAP.values():
		for fn in flist:
			if fn not in seen:
				seen.add(fn)
				fields.append(fn)
	return tuple(fields)


def build_baseline_snapshot(job_doc, sections=None):
	"""JSON-serialisable snapshot of job values for diff / apply safety."""
	sections = sections or set(SECTION_LABELS)
	if not isinstance(sections, set):
		sections = parse_change_sections(sections)
	header_fields = (
		header_fields_for_sections(sections) if sections else all_amendable_header_fields()
	)
	# If Parties/Places/Notes not selected but empty set means "all" for baseline when seeding.
	if not sections:
		header_fields = all_amendable_header_fields()
	elif sections & set(SECTION_FIELD_MAP.keys()):
		header_fields = header_fields_for_sections(sections & set(SECTION_FIELD_MAP.keys()))
	else:
		header_fields = ()

	# Always include all amendable headers in baseline for accurate diffs even if section toggled later.
	header_fields = all_amendable_header_fields()

	header = {}
	for fn in header_fields:
		if hasattr(job_doc, fn):
			header[fn] = job_doc.get(fn)

	packages = []
	if "Packages" in sections or not sections:
		for row in job_doc.get("packages") or []:
			item = {"source_row_name": row.name, "row_action": "Update"}
			for fn in PACKAGE_COPY_FIELDS:
				if hasattr(row, fn):
					item[fn] = row.get(fn)
			packages.append(item)

	return {
		"job_type": job_doc.doctype,
		"job": job_doc.name,
		"header": header,
		"packages": packages,
	}


def seed_change_request_from_job(cr_doc, job_doc=None, sections=None, reason=None):
	"""Copy current job values into the Change Request (proposed state)."""
	if not cr_doc.job_type or not cr_doc.job:
		return
	if job_doc is None:
		job_doc = frappe.get_doc(cr_doc.job_type, cr_doc.job)

	section_set = parse_change_sections(sections if sections is not None else cr_doc.get("change_sections"))
	if not section_set:
		if cr_doc.job_type == "Run Sheet":
			section_set = {"Places & Dates", "Notes"}
		else:
			section_set = set(SECTION_LABELS)

	if reason is not None:
		cr_doc.reason = reason
	if sections is not None:
		cr_doc.change_sections = "\n".join(sorted(section_set))

	baseline = build_baseline_snapshot(job_doc, section_set)
	cr_doc.baseline_json = json.dumps(baseline, default=str, indent=2)

	for fn in all_amendable_header_fields():
		if not hasattr(cr_doc, fn):
			continue
		if hasattr(job_doc, fn):
			cr_doc.set(fn, job_doc.get(fn))

	if "Packages" in section_set and hasattr(cr_doc, "package_changes"):
		cr_doc.package_changes = []
		for item in baseline.get("packages") or []:
			row = cr_doc.append("package_changes", {})
			for fn, val in item.items():
				if hasattr(row, fn):
					row.set(fn, val)

	_refresh_change_summary(cr_doc, baseline)


def count_section_changes(cr_doc, baseline=None):
	"""Return per-section change counts used by the Summary dashboard tiles."""
	if baseline is None:
		try:
			baseline = json.loads(cr_doc.baseline_json or "{}")
		except Exception:
			baseline = {}
	header_base = (baseline or {}).get("header") or {}
	counts = {
		"Parties": 0,
		"Places & Dates": 0,
		"Packages": 0,
		"Charges": 0,
		"Notes": 0,
	}
	job_type = getattr(cr_doc, "job_type", None)
	applicable = applicable_header_fields(job_type, cr_doc.get("change_sections"))
	for section, fields in SECTION_FIELD_MAP.items():
		n = 0
		for fn in fields:
			if fn not in applicable:
				continue
			if not hasattr(cr_doc, fn):
				continue
			if str(header_base.get(fn) or "") != str(cr_doc.get(fn) or ""):
				n += 1
		counts[section] = n

	pkg_count = 0
	if job_type_supports_packages(job_type):
		base_pkgs = {(p.get("source_row_name") or ""): p for p in (baseline or {}).get("packages") or []}
		for row in cr_doc.get("package_changes") or []:
			action = (row.get("row_action") or "Update").strip()
			src = row.get("source_row_name") or ""
			if action in ("Add", "Remove"):
				pkg_count += 1
				continue
			prev = base_pkgs.get(src) or {}
			for fn in PACKAGE_COPY_FIELDS:
				if not hasattr(row, fn):
					continue
				if str(prev.get(fn) or "") != str(row.get(fn) or ""):
					pkg_count += 1
					break
	counts["Packages"] = pkg_count
	counts["Charges"] = len(cr_doc.get("charges") or []) if job_type_supports_charges(job_type) else 0
	return counts


def _refresh_change_summary(cr_doc, baseline=None):
	if baseline is None:
		try:
			baseline = json.loads(cr_doc.baseline_json or "{}")
		except Exception:
			baseline = {}
	lines = []
	header_base = (baseline or {}).get("header") or {}
	job_type = getattr(cr_doc, "job_type", None)
	applicable = applicable_header_fields(job_type, cr_doc.get("change_sections"))
	for fn in all_amendable_header_fields():
		if fn not in applicable:
			continue
		if not hasattr(cr_doc, fn):
			continue
		new_val = cr_doc.get(fn)
		old_val = header_base.get(fn)
		if str(old_val or "") == str(new_val or ""):
			continue
		label = _field_label("Change Request", fn)
		lines.append(f"<li><b>{frappe.bold(label)}</b>: {_fmt(old_val)} → {_fmt(new_val)}</li>")

	pkg_lines = []
	if job_type_supports_packages(job_type):
		base_pkgs = {(p.get("source_row_name") or ""): p for p in (baseline or {}).get("packages") or []}
		for row in cr_doc.get("package_changes") or []:
			action = (row.get("row_action") or "Update").strip()
			src = row.get("source_row_name") or ""
			if action == "Add":
				pkg_lines.append(
					f"<li>Package <b>Add</b>: {escape_html(cstr(row.get('goods_description') or row.get('commodity') or src or 'new'))}</li>"
				)
				continue
			if action == "Remove":
				pkg_lines.append(f"<li>Package <b>Remove</b>: {escape_html(src)}</li>")
				continue
			prev = base_pkgs.get(src) or {}
			diffs = []
			for fn in PACKAGE_COPY_FIELDS:
				if not hasattr(row, fn):
					continue
				if str(prev.get(fn) or "") != str(row.get(fn) or ""):
					diffs.append(fn)
			if diffs:
				pkg_lines.append(
					f"<li>Package <b>{escape_html(src or '?')}</b> changed: {', '.join(diffs)}</li>"
				)

	counts = count_section_changes(cr_doc, baseline)
	charge_count = counts.get("Charges") or 0
	html = ["<div class='change-request-summary'>"]
	if cr_doc.get("reason"):
		html.append(f"<p><b>{_('Reason')}</b>: {escape_html(cstr(cr_doc.reason))}</p>")
	tiles = "".join(
		f"<span class='indicator-pill blue'>{escape_html(label)}: {counts.get(label) or 0}</span> "
		for label in SECTION_LABELS
	)
	html.append(f"<p><b>{_('Change counts')}</b>: {tiles}</p>")
	if lines:
		html.append(f"<p><b>{_('Header changes')}</b></p><ul>{''.join(lines)}</ul>")
	if pkg_lines:
		html.append(f"<p><b>{_('Package changes')}</b></p><ul>{''.join(pkg_lines)}</ul>")
	if charge_count:
		html.append(f"<p><b>{_('Charge lines')}</b>: {charge_count}</p>")
	if not lines and not pkg_lines and not charge_count and not any(
		counts.get(k) for k in ("Parties", "Places & Dates", "Notes")
	):
		html.append(f"<p class='text-muted'>{_('No differences from baseline yet.')}</p>")
	html.append("</div>")
	if hasattr(cr_doc, "change_summary"):
		cr_doc.change_summary = "".join(html)


def _fmt(val):
	if val is None or val == "":
		return "<i>empty</i>"
	return escape_html(cstr(val))


def _field_label(doctype, fieldname):
	try:
		df = frappe.get_meta(doctype).get_field(fieldname)
		if df and df.label:
			return _(df.label)
	except Exception:
		pass
	return frappe.unscrub(fieldname)


def apply_change_request_fields_to_job(cr_doc):
	"""Write CR header + package_changes onto the linked job (charges handled separately)."""
	if not cr_doc.job_type or not cr_doc.job:
		return
	if not frappe.db.exists(cr_doc.job_type, cr_doc.job):
		frappe.throw(_("Job {0} {1} not found").format(cr_doc.job_type, cr_doc.job))

	job = frappe.get_doc(cr_doc.job_type, cr_doc.job)
	sections = parse_change_sections(cr_doc.get("change_sections"))
	# Apply mirrored header fields for selected sections ∩ job-type fields.
	apply_headers = applicable_header_fields(cr_doc.job_type, sections or None)

	changed = False
	applied_headers = {}
	for fn in apply_headers:
		if not hasattr(job, fn) or not hasattr(cr_doc, fn):
			continue
		new_val = cr_doc.get(fn)
		if str(job.get(fn) or "") == str(new_val or ""):
			continue
		job.set(fn, new_val)
		applied_headers[fn] = new_val
		changed = True

	if (
		job_type_supports_packages(cr_doc.job_type)
		and (not sections or "Packages" in sections)
		and hasattr(cr_doc, "package_changes")
	):
		if _apply_package_changes(job, cr_doc):
			changed = True

	if not changed:
		return

	# Keep fetch_from sources in sync before save — otherwise validate_links re-fetches
	# the old parent value and silently discards the CR change (e.g. Transport Job
	# transport_company ← transport_order.transport_company).
	_sync_fetch_from_sources_for_applied_fields(job, applied_headers)

	job.flags.from_change_request = True
	job.flags.ignore_job_change_lock = True
	frappe.flags.from_change_request = True
	try:
		job.save(ignore_permissions=True)
	finally:
		frappe.flags.from_change_request = False

	_reassert_applied_header_values(job.doctype, job.name, applied_headers)


def _sync_fetch_from_sources_for_applied_fields(job, applied_headers):
	"""Update linked parent fields that the job would re-fetch on save."""
	if not applied_headers:
		return
	meta = frappe.get_meta(job.doctype)
	for fn, new_val in applied_headers.items():
		df = meta.get_field(fn)
		fetch_from = df.fetch_from if df else None
		if not fetch_from or "." not in cstr(fetch_from):
			continue
		link_field, source_field = fetch_from.split(".", 1)
		source_name = job.get(link_field)
		if not source_name:
			continue
		link_df = meta.get_field(link_field)
		source_dt = link_df.options if link_df and link_df.fieldtype == "Link" else None
		if not source_dt or not frappe.db.exists(source_dt, source_name):
			continue
		if not frappe.get_meta(source_dt).has_field(source_field):
			continue
		current = frappe.db.get_value(source_dt, source_name, source_field)
		if str(current or "") == str(new_val or ""):
			continue
		frappe.db.set_value(source_dt, source_name, source_field, new_val)


def _reassert_applied_header_values(doctype, name, applied_headers):
	"""Force CR header values if save-time fetch_from still overwrote them."""
	if not applied_headers:
		return
	for fn, new_val in applied_headers.items():
		current = frappe.db.get_value(doctype, name, fn)
		if str(current or "") == str(new_val or ""):
			continue
		frappe.db.set_value(doctype, name, fn, new_val, update_modified=False)


def _apply_package_changes(job, cr_doc):
	if not hasattr(job, "packages"):
		return False
	meta = frappe.get_meta(job.doctype)
	pkg_df = meta.get_field("packages")
	if not pkg_df or not pkg_df.options:
		return False
	child_dt = pkg_df.options
	child_meta = frappe.get_meta(child_dt)
	child_fields = {df.fieldname for df in child_meta.fields if df.fieldname}

	existing = {r.name: r for r in (job.packages or [])}
	changed = False

	for row in cr_doc.get("package_changes") or []:
		action = (row.get("row_action") or "Update").strip()
		src = row.get("source_row_name") or ""

		if action == "Remove":
			if src and src in existing:
				job.remove(existing[src])
				changed = True
			continue

		payload = {}
		for fn in PACKAGE_COPY_FIELDS:
			if fn in child_fields and hasattr(row, fn):
				payload[fn] = row.get(fn)

		if action == "Add" or not src or src not in existing:
			job.append("packages", payload)
			changed = True
			continue

		target = existing[src]
		for fn, val in payload.items():
			if str(target.get(fn) or "") != str(val or ""):
				target.set(fn, val)
				changed = True

	return changed


def refresh_change_request_summary(cr_doc):
	_refresh_change_summary(cr_doc)
