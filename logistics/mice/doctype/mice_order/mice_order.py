# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from typing import Optional

import frappe
from frappe import _
from frappe.model.document import Document


class MICEOrder(Document):
	def validate(self):
		self._sync_customer_from_exhibit_organizer()

	def _sync_customer_from_exhibit_organizer(self):
		"""Resolve ``customer`` from ``Exhibit -> MICE Organizer.customer``.

		Replaces the deprecated ``fetch_from: exhibit.customer`` chain now that
		``MICE Project`` no longer carries a direct Customer link.
		"""
		if not self.exhibit:
			self.customer = None
			return
		organizer = frappe.db.get_value("MICE Project", self.exhibit, "organizer")
		if not organizer:
			self.customer = None
			return
		self.customer = (
			frappe.db.get_value("MICE Organizer", organizer, "customer") or None
		)


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
	meta = frappe.get_meta("MICE Job")
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
				"Set Company on this Exhibit Order (Charges tab) or set a default Company in Global Defaults before creating a job."
			)
		)
	if meta.has_field("branch") and not job.branch:
		frappe.throw(_("Set Branch on this Exhibit Order or ensure a Branch exists for the selected Company."))
	if meta.has_field("cost_center") and not job.cost_center:
		frappe.throw(
			_("Set Cost Center on this Exhibit Order or ensure a Cost Center exists for the selected Company.")
		)
	if meta.has_field("profit_center") and not job.profit_center:
		frappe.throw(
			_("Set Profit Center on this Exhibit Order or ensure a Profit Center exists for the selected Company.")
		)


@frappe.whitelist()
def create_task_job(docname: str, title: Optional[str] = None):
	"""Create a MICE Job from this order and copy resources, charges, milestones, and documents."""
	return action_create_mice_job(docname=docname, title=title)


@frappe.whitelist()
def action_create_mice_job(docname: str, title: Optional[str] = None):
	"""Create (or reuse) a MICE Job from a MICE Order; mirrors Transport Order → Transport Job."""
	if not docname:
		frappe.throw(_("MICE Order is required."))
	if str(docname).startswith("new-"):
		frappe.throw(_("Save the MICE Order before creating a job."))

	order = frappe.get_doc("MICE Order", docname)
	frappe.has_permission("MICE Order", "write", doc=order, throw=True)

	existing = frappe.db.get_value("MICE Job", {"exhibit_order": order.name}, "name")
	if existing:
		return {"name": existing, "created": False, "already_exists": True}

	title = (title or "").strip()
	if not title:
		title = (getattr(order, "order_title", None) or "").strip() or order.name

	job = frappe.new_doc("MICE Job")
	job.exhibit = order.exhibit
	job.exhibit_order = order.name
	job.title = title
	if order.order_date and job.meta.has_field("job_date"):
		job.job_date = order.order_date

	_apply_org_defaults_to_job(job, order)

	if getattr(order, "billing_status", None) and job.meta.has_field("billing_status"):
		job.billing_status = order.billing_status

	if getattr(order, "milestone_template", None) and job.meta.has_field("milestone_template"):
		job.milestone_template = order.milestone_template
	if getattr(order, "document_list_template", None) and job.meta.has_field("document_list_template"):
		job.document_list_template = order.document_list_template

	if getattr(order, "site", None) and job.meta.has_field("site"):
		job.site = order.site

	for fieldname in (
		"shipper",
		"consignee",
		"shipper_address",
		"shipper_address_display",
		"shipper_contact",
		"shipper_contact_display",
		"consignee_address",
		"consignee_address_display",
		"consignee_contact",
		"consignee_contact_display",
	):
		if job.meta.has_field(fieldname) and getattr(order, fieldname, None):
			setattr(job, fieldname, getattr(order, fieldname))

	_copy_child_rows_by_common_fields(order, "order_resources", job, "job_resources")
	_copy_child_rows_by_common_fields(order, "charges", job, "charges")
	_copy_child_rows_by_common_fields(order, "milestones", job, "milestones")
	_copy_child_rows_by_common_fields(order, "documents", job, "documents")

	job.flags.ignore_permissions = False
	try:
		job.insert()
	except frappe.DuplicateEntryError:
		frappe.db.rollback()
		existing = frappe.db.get_value("MICE Job", {"exhibit_order": order.name}, "name")
		if existing:
			return {"name": existing, "created": False, "already_exists": True}
		raise

	frappe.db.commit()
	return {"name": job.name, "created": True, "already_exists": False}
