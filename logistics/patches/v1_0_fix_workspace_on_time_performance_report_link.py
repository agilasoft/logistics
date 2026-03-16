# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Fix invalid workspace link "On-Time Performance Report" - the report was renamed to
# "Air Freight On-Time Performance Report" and "Sea Freight On-Time Performance Report".

import frappe


def execute():
	"""Update Workspace Link rows with invalid 'On-Time Performance Report' to correct report names."""
	# Map parent workspace name -> correct report name
	corrections = {
		"Air Freight": "Air Freight On-Time Performance Report",
		"Sea Freight": "Sea Freight On-Time Performance Report",
	}

	updated = 0
	for workspace_name, correct_report in corrections.items():
		links = frappe.get_all(
			"Workspace Link",
			filters={
				"parent": workspace_name,
				"parenttype": "Workspace",
				"link_to": "On-Time Performance Report",
			},
			fields=["name", "parent"],
		)
		for link in links:
			frappe.db.set_value(
				"Workspace Link",
				link.name,
				"link_to",
				correct_report,
				update_modified=False,
			)
			updated += 1

	if updated:
		frappe.db.commit()
		print(f"  Fixed {updated} invalid 'On-Time Performance Report' workspace link(s).")
