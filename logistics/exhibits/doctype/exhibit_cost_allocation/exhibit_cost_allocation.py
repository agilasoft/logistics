# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ExhibitCostAllocation(Document):
	"""Per-target cost allocation row for Exhibit consolidation charges.

	One row per Docket or Exhibit Job that participates in cost allocation.
	The percentage and allocated amount are computed by ``Exhibit.allocate_costs``
	(Equal / Weight-based / Volume-based / Value-based / Custom).
	"""

	pass
