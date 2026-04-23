# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
#
# `tabAir Shipment Charges` has no `total_amount` column. Use actual/base/estimated fields.

# Selling amount (aschg alias in JOINs).
AFC_SELLING_AMOUNT = """(CASE
	WHEN IFNULL(aschg.charge_type, 'Revenue') = 'Cost' THEN 0
	ELSE COALESCE(aschg.actual_revenue, aschg.base_amount, aschg.estimated_revenue, 0)
END)"""

# Same, subquery on `tabAir Shipment Charges` without table alias.
AFC_SELLING_AMOUNT_BARE = """(CASE
	WHEN IFNULL(charge_type, 'Revenue') = 'Cost' THEN 0
	ELSE COALESCE(actual_revenue, base_amount, estimated_revenue, 0)
END)"""

# Payable / cost (aschg alias).
AFC_COST_AMOUNT = """COALESCE(aschg.actual_cost, aschg.cost_base_amount, aschg.estimated_cost, 0)"""
