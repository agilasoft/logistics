# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
"""Point Air Consolidation Packages.commodity at Commodity.

The field used to link Other Commodity Code, a child table on Commodity.
Air Shipment package lines link Commodity, so those values never copied.
Clear any stored value that is not a Commodity name.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("Air Consolidation Packages"):
		return
	if not frappe.db.has_column("Air Consolidation Packages", "commodity"):
		return
	if not frappe.db.table_exists("Commodity"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabAir Consolidation Packages` p
		LEFT JOIN `tabCommodity` c ON c.name = p.commodity
		SET p.commodity = NULL
		WHERE IFNULL(p.commodity, '') != ''
		  AND c.name IS NULL
		"""
	)
