# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from typing import Optional

import frappe
from frappe import _
from frappe.model.document import Document


class ProjectOrder(Document):
	pass


def _copy_child_rows_by_common_fields(
	src_doc: Document, src_table_field: str, dst_doc: Document, dst_table_field: str
):
	"""Copy child rows from src to dst, matching by common fieldnames only."""
	src_rows = src_doc.get(src_table_field) or []
	if not src_rows:
		return

	dst_parent_meta = frappe.get_meta(dst_doc.doctype)
	dst_tbl_df = dst_parent_meta.get_field(dst_table_field)
	if not dst_tbl_df or not dst_tbl_df.options:
		return

	dst_child_dt = dst_tbl_df.options
	dst_child_meta = frappe.get_meta(dst_child_dt)

	excluded_types = {"Section Break", "Column Break", "Tab Break", "Table", "Table MultiSelect"}
	excluded_names = {
		"name",
		"owner",
		"modified_by",
		"creation",
		"modified",
		"parent",
		"parentfield",
		"parenttype",
		"idx",
		"docstatus",
	}
	dst_fields = {
		df.fieldname
		for df in dst_child_meta.fields
		if df.fieldtype not in excluded_types and df.fieldname not in excluded_names
	}

	for s in src_rows:
		s_dict = s.as_dict()
		new_row = {fn: s_dict.get(fn) for fn in dst_fields if fn in s_dict}
		dst_doc.append(dst_table_field, new_row)


def _company_fieldname(doctype: str) -> Optional[str]:
	"""Return the fieldname on `doctype` that links to Company (if any).

	Some doctypes (e.g. standard Branch, this app's Profit Center) have no company
	field at all; some installations add `company` or `custom_company` via custom
	fields. Returns None when no company link exists.
	"""
	dt_meta = frappe.get_meta(doctype)
	for fn in ("company", "custom_company"):
		if dt_meta.has_field(fn):
			return fn
	return None


def _apply_org_defaults_to_job(job: Document, order: Document):
	"""Fill company / branch / cost center / profit center on the job from the order or global defaults."""
	meta = frappe.get_meta("Project Job")
	d = frappe.defaults.get_defaults()
	company = getattr(order, "company", None) or d.get("company")
	if company and meta.has_field("company"):
		job.company = company

	branch = getattr(order, "branch", None)
	if not branch and company:
		branch_company_fn = _company_fieldname("Branch")
		if branch_company_fn:
			branch = frappe.db.get_value(
				"Branch",
				{branch_company_fn: company},
				"name",
				order_by="modified desc",
			)
	if branch and meta.has_field("branch"):
		job.branch = branch

	cc = getattr(order, "cost_center", None)
	if not cc and company:
		cc_filters = {"is_group": 0, "disabled": 0}
		cc_company_fn = _company_fieldname("Cost Center")
		if cc_company_fn:
			cc_filters[cc_company_fn] = company
		cc = frappe.db.get_value(
			"Cost Center",
			cc_filters,
			"name",
			order_by="creation asc",
		)
	if cc and meta.has_field("cost_center"):
		job.cost_center = cc

	pc = getattr(order, "profit_center", None)
	if not pc:
		pc_company_fn = _company_fieldname("Profit Center")
		if pc_company_fn and company:
			pc = frappe.db.get_value(
				"Profit Center",
				{pc_company_fn: company},
				"name",
				order_by="creation asc",
			)
		else:
			pc = frappe.db.get_value(
				"Profit Center",
				{},
				"name",
				order_by="creation asc",
			)
	if pc and meta.has_field("profit_center"):
		job.profit_center = pc

	if not job.company:
		frappe.throw(
			_(
				"Set Company on this Project Order (Charges tab) or set a default Company in Global Defaults before creating a job."
			)
		)
	if meta.has_field("branch") and not job.branch:
		frappe.throw(_("Set Branch on this Project Order or ensure a Branch exists for the selected Company."))
	if meta.has_field("cost_center") and not job.cost_center:
		frappe.throw(
			_("Set Cost Center on this Project Order or ensure a Cost Center exists for the selected Company.")
		)
	if meta.has_field("profit_center") and not job.profit_center:
		frappe.throw(
			_("Set Profit Center on this Project Order or ensure a Profit Center exists for the selected Company.")
		)


def _apply_sales_quote_link_to_project_job(job: Document, order: Document) -> None:
	"""Copy Sales Quote link and rep fields from the order (mirrors Transport Order → Transport Job)."""
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	copy_sales_quote_fields_to_target(order, job)
	if getattr(job, "sales_quote", None):
		return
	sp_name = getattr(order, "special_project", None)
	if not sp_name or not job.meta.has_field("sales_quote"):
		return
	sp_sq = frappe.db.get_value("Special Project", sp_name, "sales_quote")
	if not sp_sq:
		return
	try:
		sp_doc = frappe.get_cached_doc("Special Project", sp_name)
	except Exception:
		sp_doc = frappe._dict(sales_quote=sp_sq)
	copy_sales_quote_fields_to_target(sp_doc, job)


def _build_project_job_from_order(order: Document, title: Optional[str] = None) -> Document:
	"""Construct a Project Job from a Project Order; populate header + copy charges, milestones, documents."""
	title = (title or "").strip() or order.name
	job = frappe.new_doc("Project Job")
	job.special_project = order.special_project
	job.special_project_order = order.name
	job.title = title
	if order.order_date and job.meta.has_field("job_date"):
		job.job_date = order.order_date

	_apply_org_defaults_to_job(job, order)

	if getattr(order, "job_number", None) and job.meta.has_field("job_number"):
		job.job_number = order.job_number

	if getattr(order, "billing_status", None) and job.meta.has_field("billing_status"):
		job.billing_status = order.billing_status

	if getattr(order, "milestone_template", None) and job.meta.has_field("milestone_template"):
		job.milestone_template = order.milestone_template
	if getattr(order, "document_list_template", None) and job.meta.has_field("document_list_template"):
		job.document_list_template = order.document_list_template

	if getattr(order, "site", None) and job.meta.has_field("site"):
		job.site = order.site

	_apply_sales_quote_link_to_project_job(job, order)

	_copy_child_rows_by_common_fields(order, "order_resources", job, "job_resources")
	_copy_child_rows_by_common_fields(order, "charges", job, "charges")
	_copy_child_rows_by_common_fields(order, "milestones", job, "milestones")
	_copy_child_rows_by_common_fields(order, "documents", job, "documents")

	return job


@frappe.whitelist()
def create_project_job(docname: str, title: Optional[str] = None):
	"""Create a Project Job from this order and copy resources, charges, milestones, and documents."""
	if not docname:
		frappe.throw(_("Project Order is required."))
	if str(docname).startswith("new-"):
		frappe.throw(_("Save the Project Order before creating a job."))

	order = frappe.get_doc("Project Order", docname)
	frappe.has_permission("Project Order", "write", doc=order, throw=True)

	job = _build_project_job_from_order(order, title=title)
	job.flags.ignore_permissions = False
	job.insert()

	return {"name": job.name, "created": True}


@frappe.whitelist()
def action_create_project_job(docname: str, title: Optional[str] = None):
	"""Create (or reuse) a Project Job from a Project Order; mirrors Transport Order → Transport Job."""
	if not docname:
		frappe.throw(_("Project Order is required."))
	if str(docname).startswith("new-"):
		frappe.throw(_("Save the Project Order before creating a job."))

	order = frappe.get_doc("Project Order", docname)
	frappe.has_permission("Project Order", "write", doc=order, throw=True)

	existing = frappe.db.get_value(
		"Project Job", {"special_project_order": order.name}, "name"
	)
	if existing:
		return {"name": existing, "created": False, "already_exists": True}

	job = _build_project_job_from_order(order, title=title)
	job.flags.ignore_permissions = False
	try:
		job.insert()
	except frappe.DuplicateEntryError:
		frappe.db.rollback()
		existing = frappe.db.get_value(
			"Project Job", {"special_project_order": order.name}, "name"
		)
		if existing:
			return {"name": existing, "created": False, "already_exists": True}
		raise

	frappe.db.commit()
	return {"name": job.name, "created": True, "already_exists": False}


# Backwards compatibility: legacy callers may still invoke ``create_task_job``.
@frappe.whitelist()
def create_task_job(docname: str, title: Optional[str] = None):
	return create_project_job(docname=docname, title=title)
