# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop the legacy ``tabExhibit Docket`` table.

``Exhibit Docket`` is now a virtual child doctype (``is_virtual: 1``) that
displays a live view of Dockets linked to an Exhibit. The persisted
participant rows in ``tabExhibit Docket`` are no longer the source of truth
and would otherwise leave orphaned rows that the schema sync keeps around.

We run this in ``pre_model_sync`` so the drop happens before the new (virtual)
doctype's schema sync runs. Frappe's standard sync would otherwise leave the
table in place even though ``is_virtual`` is set on the doctype.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabExhibit Docket"):
		return
	frappe.db.sql_ddl("DROP TABLE `tabExhibit Docket`")
	frappe.db.commit()
