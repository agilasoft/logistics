# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove the ``Exhibit Job Participant`` DocType and its underlying table.

The Participants tabs/tables on ``Exhibit Job``, ``Exhibit Order``, and
``Docket`` have been removed. Frappe's orphan cleanup at the end of ``migrate``
will drop the DocType record (its JSON file no longer exists), but the database
table ``tabExhibit Job Participant`` is left behind by design. This patch
drops it explicitly. Safe to re-run.
"""

from __future__ import annotations

import frappe


def execute():
	dt = "Exhibit Job Participant"

	if frappe.db.exists("DocType", dt):
		try:
			frappe.delete_doc("DocType", dt, force=True, ignore_missing=True)
		except Exception:
			frappe.log_error(
				title=f"Failed to delete orphan DocType {dt}",
				message=frappe.get_traceback(),
			)

	if frappe.db.table_exists(dt):
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{dt}`")

	frappe.db.commit()
	frappe.clear_cache()
