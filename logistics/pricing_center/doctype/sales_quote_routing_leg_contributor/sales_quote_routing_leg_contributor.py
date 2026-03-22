# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

from frappe.model.document import Document


class SalesQuoteRoutingLegContributor(Document):
	"""Contributing job (bill-with) for a routing leg. Charges from this job are included in the same Sales Invoice as the leg's anchor job."""
	pass
