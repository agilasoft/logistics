# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Guards Main Job Type / Main Job on internal jobs after they are linked to a main job."""

import frappe
from frappe import _
from frappe.utils import cint


def validate_internal_job_main_link_unchanged(doc) -> None:
	"""On update: block changing main_job_type or main_job when internal job is already fully linked.

	First-time link (from empty) is allowed; only changes to an existing pair are rejected.
	"""
	if doc.is_new() or not cint(getattr(doc, "is_internal_job", 0)):
		return
	if not hasattr(doc, "main_job_type") or not hasattr(doc, "main_job"):
		return
	mjt = (getattr(doc, "main_job_type", None) or "").strip()
	mj = (getattr(doc, "main_job", None) or "").strip()
	if not mjt or not mj:
		return
	try:
		prev = frappe.db.get_value(
			doc.doctype, doc.name, ("main_job_type", "main_job"), as_dict=True
		)
	except Exception:
		return
	if not prev:
		return
	pmjt = (prev.get("main_job_type") or "").strip()
	pmj = (prev.get("main_job") or "").strip()
	if not pmjt or not pmj:
		return
	if mjt == pmjt and mj == pmj:
		return
	frappe.throw(
		_("Main Job Type and Main Job cannot be changed for an internal job that is already linked to a main job."),
		title=_("Main job link"),
	)
