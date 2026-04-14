# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def execute():
    """Turn on Requires Container No. for existing FCL freight modes (matches prior code-based behavior)."""
    frappe.db.sql(
        """
        UPDATE `tabFreight Mode`
        SET requires_container_no = 1
        WHERE UPPER(IFNULL(code, '')) = 'FCL'
        """
    )
