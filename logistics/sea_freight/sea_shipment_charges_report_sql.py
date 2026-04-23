# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
#
# `tabSea Shipment Charges` has no `total_amount` column in the schema. Reports use
# actual/base/estimated revenue and cost instead.

# Expression for a single line's selling amount (sfc alias in JOINs).
SFC_SELLING_AMOUNT = """(CASE
	WHEN IFNULL(sfc.charge_type, 'Revenue') = 'Cost' THEN 0
	ELSE COALESCE(sfc.actual_revenue, sfc.base_amount, sfc.estimated_revenue, 0)
END)"""

# Same, for a subquery on `tabSea Shipment Charges` without a table alias.
SFC_SELLING_AMOUNT_BARE = """(CASE
	WHEN IFNULL(charge_type, 'Revenue') = 'Cost' THEN 0
	ELSE COALESCE(actual_revenue, base_amount, estimated_revenue, 0)
END)"""

# One line's payable / cost side amount (sfc alias).
SFC_COST_AMOUNT = """COALESCE(sfc.actual_cost, sfc.cost_base_amount, sfc.estimated_cost, 0)"""
