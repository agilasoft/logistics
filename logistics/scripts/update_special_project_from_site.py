"""Apply source Special Project values onto an existing target document."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import copy_doc

from logistics.scripts.copy_document_between_sites import _load_from_site


def run(
	source_site: str,
	source_name: str,
	target_name: str,
):
	if not frappe.db.exists("Special Project", target_name):
		frappe.throw(_("Target Special Project {0} was not found.").format(target_name))

	src_doc = _load_from_site(source_site, "Special Project", source_name)
	if not src_doc:
		frappe.throw(
			_("Special Project {0} was not found on site {1}.").format(source_name, source_site)
		)

	prepared = copy_doc(src_doc, ignore_no_copy=True)

	target = frappe.get_doc("Special Project", target_name)
	_apply_source_to_target(prepared, target)

	frappe.set_user("Administrator")
	target.flags.ignore_validate = True
	target.flags.ignore_links = True
	target.save(ignore_permissions=True)
	frappe.db.commit()

	result = {
		"source_site": source_site,
		"source_name": source_name,
		"target_name": target_name,
		"project_name": target.project_name,
		"child_counts": {
			df.fieldname: len(target.get(df.fieldname) or [])
			for df in target.meta.fields
			if df.fieldtype == "Table"
		},
	}
	print(frappe.as_json(result))
	return result


def _apply_source_to_target(source, target):
	meta = target.meta
	skip = {
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"project",
		"job_number",
		"wip_journal_entry",
		"sales_invoice",
		"purchase_invoice",
		"amended_from",
		"naming_series",
	}

	for df in meta.fields:
		fn = df.fieldname
		if fn in skip or df.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button"):
			continue
		if df.fieldtype == "Table":
			continue
		if not source.meta.has_field(fn):
			continue
		val = source.get(fn)
		if df.fieldtype in ("Link", "Dynamic Link") and val:
			link_dt = df.options
			if df.fieldtype == "Dynamic Link":
				link_dt = source.get(df.options)
			if link_dt and not frappe.db.exists(link_dt, val):
				continue
		target.set(fn, val)

	for df in meta.fields:
		if df.fieldtype != "Table":
			continue
		fn = df.fieldname
		target.set(fn, [])
		for row in source.get(fn) or []:
			child = target.append(fn, {})
			for cdf in child.meta.fields:
				cfn = cdf.fieldname
				if cfn in (
					"name",
					"owner",
					"creation",
					"modified",
					"modified_by",
					"parent",
					"parenttype",
					"parentfield",
				):
					continue
				if cdf.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button"):
					continue
				val = row.get(cfn)
				if cdf.fieldtype in ("Link", "Dynamic Link") and val:
					link_dt = cdf.options
					if cdf.fieldtype == "Dynamic Link":
						link_dt = row.get(cdf.options)
					if link_dt and not frappe.db.exists(link_dt, val):
						continue
				child.set(cfn, val)
