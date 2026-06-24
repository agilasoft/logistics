# Copyright (c) 2026, www.agilasoft.com and contributors
# Copy a Frappe document from one bench site to another.
#
# Run:
#   bench --site <target_site> execute logistics.scripts.copy_document_between_sites.run \
#     --kwargs '{"source_site":"cargonext.io","doctype":"Special Project","name":"PROJ-0011"}'

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import copy_doc


# Header link fields to clear when copying Special Project to a new site.
_SPECIAL_PROJECT_CLEAR_FIELDS = (
	"project",
	"sales_quote",
	"job_number",
	"wip_journal_entry",
	"sales_invoice",
	"purchase_invoice",
	"amended_from",
	"milestone_template",
	"document_list_template",
	"tc_name",
	"logistics_service_level",
)

# Child-table link fields that reference site-specific operational documents.
_SPECIAL_PROJECT_CHILD_LINK_FIELDS = (
	"job_no",
	"job_type",
	"order_no",
	"order_type",
	"shipment",
	"booking",
	"declaration",
	"warehouse_job",
	"transport_job",
	"air_shipment",
	"sea_shipment",
	"project_order",
	"project_job",
)


def run(
	source_site: str,
	doctype: str,
	name: str,
	target_site: str | None = None,
	title_suffix: str = " (demo copy)",
):
	"""Load *name* from *source_site* and insert a copy on *target_site* (current site if omitted)."""
	target_site = target_site or frappe.local.site
	if source_site == target_site:
		frappe.throw(_("Source and target site must differ."))

	src_doc = _load_from_site(source_site, doctype, name)
	if not src_doc:
		frappe.throw(_("{0} {1} was not found on site {2}.").format(doctype, name, source_site))

	new_doc = copy_doc(src_doc, ignore_no_copy=False)
	_prepare_for_target(new_doc, title_suffix=title_suffix)

	frappe.set_user("Administrator")
	new_doc.insert(ignore_permissions=True)
	frappe.db.commit()

	result = {
		"source_site": source_site,
		"source_name": name,
		"target_site": target_site,
		"target_doctype": doctype,
		"new_name": new_doc.name,
		"project_name": getattr(new_doc, "project_name", None),
	}
	print(frappe.as_json(result))
	return result


def _load_from_site(site: str, doctype: str, name: str):
	"""Read a document from another site on the same bench."""
	current = frappe.local.site
	frappe.destroy()
	try:
		frappe.init(site=site)
		frappe.connect()
		if not frappe.db.exists(doctype, name):
			return None
		return frappe.get_doc(doctype, name)
	finally:
		frappe.destroy()
		frappe.init(site=current)
		frappe.connect()


def _prepare_for_target(doc, title_suffix: str = ""):
	"""Strip site-specific links so insert succeeds on the target site."""
	if doc.doctype == "Special Project":
		_prepare_special_project(doc, title_suffix)
		return

	# Generic: ensure link targets exist or clear them.
	meta = doc.meta
	for df in meta.get_link_fields():
		val = doc.get(df.fieldname)
		if val and not frappe.db.exists(df.options, val):
			doc.set(df.fieldname, None)


def _prepare_special_project(doc, title_suffix: str):
	for fn in _SPECIAL_PROJECT_CLEAR_FIELDS:
		if doc.meta.has_field(fn):
			doc.set(fn, None)

	if title_suffix and doc.get("project_name"):
		doc.project_name = f"{doc.project_name}{title_suffix}"

	for row in doc.get_all_children():
		for fn in _SPECIAL_PROJECT_CHILD_LINK_FIELDS:
			if row.meta.has_field(fn):
				row.set(fn, None)

	# Operational child rows that only make sense with linked jobs should be cleared.
	for row in doc.get("lifecycle_jobs") or []:
		for fn in ("order", "order_type", "job", "job_type"):
			if row.meta.has_field(fn):
				row.set(fn, None)

	for row in doc.get("deliveries") or []:
		for fn in ("shipment", "transport_job", "warehouse_job"):
			if row.meta.has_field(fn):
				row.set(fn, None)

	_ensure_link_or_clear(doc, "customer")
	_ensure_link_or_clear(doc, "company")
	_ensure_link_or_clear(doc, "branch")
	_ensure_link_or_clear(doc, "profit_center")
	_ensure_link_or_clear(doc, "lifecycle_stage")
	_ensure_link_or_clear(doc, "project_type")
	_ensure_cost_center(doc)

	for row in doc.get("scoping_activities") or []:
		_ensure_link_or_clear(row, "activity_type")

	for row in doc.get("charges") or []:
		_ensure_link_or_clear(row, "item")
		_ensure_link_or_clear(row, "supplier")
		_ensure_link_or_clear(row, "customer")


def _ensure_link_or_clear(doc, fieldname: str):
	if not doc.meta.has_field(fieldname):
		return
	df = doc.meta.get_field(fieldname)
	if df.fieldtype not in ("Link", "Dynamic Link"):
		return
	val = doc.get(fieldname)
	if not val:
		return
	link_doctype = df.options
	if df.fieldtype == "Dynamic Link":
		link_doctype = doc.get(df.options)
	if link_doctype and not frappe.db.exists(link_doctype, val):
		doc.set(fieldname, None)


def _ensure_cost_center(doc):
	if not doc.meta.has_field("cost_center"):
		return
	if doc.get("cost_center") and frappe.db.exists("Cost Center", doc.cost_center):
		return
	company = doc.get("company")
	if not company:
		doc.cost_center = None
		return

	for filters in (
		{"company": company, "is_group": 0},
		{"company": company, "is_group": 1},
		{"company": company},
	):
		cc = frappe.db.get_value("Cost Center", filters, "name", order_by="name asc")
		if cc and frappe.db.exists("Cost Center", cc):
			doc.cost_center = cc
			return

	doc.cost_center = None
