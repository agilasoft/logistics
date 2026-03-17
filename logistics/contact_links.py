# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Helpers for Contact Dynamic Links. Used by client set_query to avoid permission errors on contact.link_doctype."""

import frappe


@frappe.whitelist()
def get_contact_names_for_dynamic_link(link_doctype: str, link_name: str):
	"""Return list of Contact names linked to the given doctype/name via Dynamic Link.
	Used by client-side set_query for Contact fields to avoid permission errors when
	the user role cannot read contact.link_doctype.
	"""
	if not link_doctype or not link_name:
		return []

	try:
		links = frappe.get_all(
			"Dynamic Link",
			filters={
				"parenttype": "Contact",
				"link_doctype": link_doctype,
				"link_name": link_name,
			},
			fields=["parent"],
			order_by="creation ASC",
		)
		return [d.parent for d in links] if links else []
	except Exception as e:
		frappe.log_error(
			frappe.get_traceback(),
			"Contact Links: get_contact_names_for_dynamic_link",
		)
		return []
