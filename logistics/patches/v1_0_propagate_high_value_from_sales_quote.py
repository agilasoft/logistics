# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Back-fill ``is_high_value=1`` on all downstream docs linked to a high-value Sales Quote.

Mirrors the runtime ripple installed in ``Sales Quote.on_update`` so historical Sales Quotes
that were marked high value before this change retroactively flag their connected bookings,
shipments, consolidations, orders, and jobs.
"""

from __future__ import annotations

import frappe

from logistics.utils.module_integration import propagate_high_value_from_sales_quote


def execute():
	names = frappe.get_all("Sales Quote", filters={"is_high_value": 1}, pluck="name")
	for name in names:
		try:
			propagate_high_value_from_sales_quote(name)
		except Exception:
			frappe.log_error(
				title="v1_0_propagate_high_value_from_sales_quote",
				message=f"Sales Quote {name}",
			)
	frappe.db.commit()
