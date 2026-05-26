# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename DocType ``Exhibit Participant`` -> ``Exhibit Docket``.

Runs in ``pre_model_sync`` so the rename happens before schema sync reads the
new ``exhibit_docket.json`` file. ``frappe.rename_doc`` on a DocType:

* renames the DocType record in ``tabDocType``
* renames the underlying table from ``tabExhibit Participant`` to
  ``tabExhibit Docket``
* updates ``parenttype`` references in any child tables that point at it
* rewrites Link field ``options`` and Property Setters that point at it
"""

from __future__ import annotations

import frappe


def execute():
	old = "Exhibit Participant"
	new = "Exhibit Docket"

	if not frappe.db.exists("DocType", old):
		return
	if frappe.db.exists("DocType", new):
		return

	frappe.rename_doc("DocType", old, new, force=True, merge=False)
	frappe.db.commit()
	frappe.clear_cache()
