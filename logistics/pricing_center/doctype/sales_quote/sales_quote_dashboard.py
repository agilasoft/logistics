from frappe import _


def get_data():
	return {
		"fieldname": "sales_quote",
		# One-off MICE quotes link via Sales Quote.exhibit; Project (PQ) quotes also set MICE Project.sales_quote.
		"internal_and_external_links": {
			"MICE Project": "exhibit",
		},
	}
