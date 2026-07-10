# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Prospect connections: Sales Quote alongside Opportunity and Customer."""


def get_data(data):
	non_standard_fieldnames = data.non_standard_fieldnames or {}
	non_standard_fieldnames["Sales Quote"] = "prospect"
	non_standard_fieldnames["Customer"] = "prospect_name"
	non_standard_fieldnames["Opportunity"] = "party_name"
	data.non_standard_fieldnames = non_standard_fieldnames

	dynamic_links = data.dynamic_links or {}
	dynamic_links["party_name"] = ["Prospect", "opportunity_from"]
	data.dynamic_links = dynamic_links

	transactions = list(data.transactions or [])
	items = []
	for group in transactions:
		items.extend(group.get("items") or [])
	for doctype in ("Sales Quote", "Opportunity", "Customer"):
		if doctype not in items:
			items.append(doctype)
	if not transactions:
		transactions = [{"items": items}]
	else:
		transactions[0]["items"] = items
	data.transactions = transactions
	return data
