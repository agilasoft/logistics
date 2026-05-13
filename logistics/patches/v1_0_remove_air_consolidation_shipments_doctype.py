# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove obsolete DocType Air Consolidation Shipments.

The "attached shipments" child table on Air Consolidation has been retired in favour of
deriving per-shipment allocation rows from ``consolidation_packages`` (one entry per distinct
``air_freight_job``). This patch drops the standalone DocType and its table so existing
installs do not carry orphan schema after the field is removed from Air Consolidation.
"""

from __future__ import unicode_literals

import frappe


def execute():
    name = "Air Consolidation Shipments"
    if frappe.db.exists("DocType", name):
        frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
    # Explicit commit before DDL: Frappe wrappers raise ImplicitCommitError otherwise.
    frappe.db.commit()
    frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabAir Consolidation Shipments`")
    frappe.db.commit()
