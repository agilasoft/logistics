# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Guards Main Service Type / Main Service on linked services after they are linked to a main."""

import frappe
from frappe import _

from logistics.utils.service_role_rules import (
	get_main_service_name,
	get_main_service_type,
	is_linked_service_satellite,
)


def validate_internal_job_main_link_unchanged(doc) -> None:
	"""On update: block changing main_service_type or main_service when linked service is already fully linked.

	First-time link (from empty) is allowed; only changes to an existing pair are rejected.
	"""
	if doc.is_new() or not is_linked_service_satellite(doc):
		return
	if not (
		hasattr(doc, "main_service_type")
		or hasattr(doc, "main_job_type")
		or hasattr(doc, "main_service")
		or hasattr(doc, "main_job")
	):
		return
	mjt = get_main_service_type(doc)
	mj = get_main_service_name(doc)
	if not mjt or not mj:
		return
	try:
		meta = frappe.get_meta(doc.doctype)
		fields = [
			f
			for f in ("main_service_type", "main_service", "main_job_type", "main_job")
			if meta.has_field(f)
		]
		if not fields:
			return
		prev = frappe.db.get_value(doc.doctype, doc.name, fields, as_dict=True)
	except Exception:
		return
	if not prev:
		return
	pmjt = (prev.get("main_service_type") or prev.get("main_job_type") or "").strip()
	pmj = (prev.get("main_service") or prev.get("main_job") or "").strip()
	if not pmjt or not pmj:
		return
	if mjt == pmjt and mj == pmj:
		return
	frappe.throw(
		_("Main Job Type and Main Job cannot be changed for an internal job that is already linked to a main job."),
		title=_("Main job link"),
	)
