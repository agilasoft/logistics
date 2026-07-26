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
)

SECTION_FIELD_MAP = {
	"Parties": PARTIES_FIELDS,
	"Places & Dates": PLACES_DATES_FIELDS,
	"Notes": NOTES_FIELDS,
}

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
	for section, fields in SECTION_FIELD_MAP.items():
		n = 0
		for fn in fields:
			if not hasattr(cr_doc, fn):
				continue
			if str(header_base.get(fn) or "") != str(cr_doc.get(fn) or ""):
				n += 1
		counts[section] = n

	pkg_count = 0
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
	counts["Charges"] = len(cr_doc.get("charges") or [])
	return counts


def _refresh_change_summary(cr_doc, baseline=None):
	if baseline is None:
		try:
			baseline = json.loads(cr_doc.baseline_json or "{}")
		except Exception:
			baseline = {}
	lines = []
	header_base = (baseline or {}).get("header") or {}
	for fn in all_amendable_header_fields():
		if not hasattr(cr_doc, fn):
			continue
		new_val = cr_doc.get(fn)
		old_val = header_base.get(fn)
		if str(old_val or "") == str(new_val or ""):
			continue
		label = _field_label("Change Request", fn)
		lines.append(f"<li><b>{frappe.bold(label)}</b>: {_fmt(old_val)} → {_fmt(new_val)}</li>")

	pkg_lines = []
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
	# Apply mirrored header fields for selected sections (Charges alone → no header apply).
	apply_headers = ()
	if not sections:
		apply_headers = all_amendable_header_fields()
	else:
		wanted = set()
		for sec in sections:
			wanted.update(SECTION_FIELD_MAP.get(sec) or ())
		apply_headers = tuple(fn for fn in all_amendable_header_fields() if fn in wanted)

	changed = False
	for fn in apply_headers:
		if not hasattr(job, fn) or not hasattr(cr_doc, fn):
			continue
		new_val = cr_doc.get(fn)
		if str(job.get(fn) or "") == str(new_val or ""):
			continue
		job.set(fn, new_val)
		changed = True

	if (not sections or "Packages" in sections) and hasattr(cr_doc, "package_changes"):
		if _apply_package_changes(job, cr_doc):
			changed = True

	if not changed:
		return

	job.flags.from_change_request = True
	job.flags.ignore_job_change_lock = True
	frappe.flags.from_change_request = True
	try:
		job.save(ignore_permissions=True)
	finally:
		frappe.flags.from_change_request = False


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
