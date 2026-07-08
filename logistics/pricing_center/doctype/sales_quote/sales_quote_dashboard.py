from frappe import _


def get_data():
	return {
		"fieldname": "sales_quote",
		# CRM source records are linked from fields on Sales Quote itself, not the other way around.
		"internal_links": {
			"Opportunity": "opportunity",
			"Lead": "lead",
			"Prospect": "prospect",
		},
		# One-off MICE quotes link via Sales Quote.exhibit; Project (PQ) quotes also set MICE Project.sales_quote.
		"internal_and_external_links": {
			"MICE Project": "exhibit",
		},
		"transactions": [
			{"items": ["Opportunity", "Lead", "Prospect"]},
		],
	}
