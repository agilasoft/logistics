# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Customer connections: Sales Quote instead of ERPNext Quotation."""


def get_data(data):
	for group in data.transactions:
		if "Quotation" in group.get("items", []):
			group["items"] = [
				"Sales Quote" if item == "Quotation" else item for item in group["items"]
			]
	return data
