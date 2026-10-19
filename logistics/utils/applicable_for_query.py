# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Link search for Applicable For.

Permission Studio used to pass the permission DocType as the link target. The
field then looked for a Company record named Company and cleared the text.
This search stays on DocType and always offers the permission DocType itself.
"""

from __future__ import annotations

import frappe

from logistics.utils.applicable_for_choices import applicable_for_page, clean_text


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def applicable_for_query(doctype, txt, searchfield, start, page_len, filters):
	frappe.only_for("System Manager")
	del doctype, searchfield
	reference = clean_text((filters or {}).get("doctype"))
	names = applicable_for_page(reference, _linked_doctype_map(reference), txt, start, page_len)
	return [[name] for name in names]


def _linked_doctype_map(reference: str) -> dict:
	if not reference or not frappe.db.exists("DocType", reference):
		return {}
	from frappe.desk.form.linked_with import get_linked_doctypes

	return get_linked_doctypes(reference, True) or {}
