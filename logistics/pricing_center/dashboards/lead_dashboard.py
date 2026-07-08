# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Lead connections: Sales Quote instead of ERPNext Quotation."""


def get_data(data):
	non_standard_fieldnames = data.non_standard_fieldnames or {}
	non_standard_fieldnames.pop("Quotation", None)
	non_standard_fieldnames["Sales Quote"] = "lead"
	data.non_standard_fieldnames = non_standard_fieldnames

	for group in data.transactions:
		if "Quotation" in group.get("items", []):
			group["items"] = [
				"Sales Quote" if item == "Quotation" else item for item in group["items"]
			]
	return data
