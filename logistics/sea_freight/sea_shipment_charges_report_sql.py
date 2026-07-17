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

# Display vessel name from routing legs (requires outer query alias `sship`).
# Prefers the Main sea leg with a vessel master or carrier text; otherwise the first sea leg.
SEA_SHIPMENT_VESSEL_NAME = """(
	SELECT COALESCE(v.vessel_name, srl.vessel)
	FROM `tabSea Shipment Routing Leg` srl
	LEFT JOIN `tabVessel` v ON v.name = srl.vessel_master
	WHERE srl.parent = sship.name
		AND srl.transport_mode_sea = 1
		AND COALESCE(NULLIF(v.vessel_name, ''), NULLIF(srl.vessel, '')) IS NOT NULL
	ORDER BY
		CASE WHEN IFNULL(srl.type, '') = 'Main' THEN 0 ELSE 1 END,
		srl.idx
	LIMIT 1
)"""
