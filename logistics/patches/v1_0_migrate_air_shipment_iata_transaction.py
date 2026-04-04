# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Create `Air Shipment IATA Transaction` from stashed legacy `tabAir Shipment` columns
and link back on `Air Shipment.iata_transaction`.
"""

import json
import os

import frappe

_STASH_FILENAME = ".air_iata_migration_stash.json"


def execute():
	if not frappe.db.exists("DocType", "Air Shipment IATA Transaction"):
		return True

	path = frappe.get_site_path("private", "files", _STASH_FILENAME)
	if not os.path.isfile(path):
		return True

	with open(path, encoding="utf-8") as f:
		rows = json.load(f)

	for row in rows:
		shipment_name = row.get("name")
		if not shipment_name or not frappe.db.exists("Air Shipment", shipment_name):
			continue
		if frappe.db.exists("Air Shipment IATA Transaction", {"air_shipment": shipment_name}):
			continue

		doc_dict = {"doctype": "Air Shipment IATA Transaction", "air_shipment": shipment_name}
		for key in (
			"iata_status",
			"iata_message_id",
			"last_status_update",
			"eawb_enabled",
			"eawb_status",
			"eawb_digital_signature",
			"eawb_signed_date",
			"eawb_signed_by",
			"cass_participant_code",
			"cass_settlement_status",
			"cass_settlement_date",
			"cass_billing_reference",
			"cass_settlement_amount",
			"tact_rate_lookup",
			"tact_rate_reference",
			"tact_rate_amount",
			"tact_currency",
			"tact_rate_validity",
		):
			if key in row and row[key] not in (None, ""):
				doc_dict[key] = row[key]

		tx = frappe.get_doc(doc_dict)
		tx.flags.ignore_permissions = True
		tx.insert()
	frappe.db.commit()

	try:
		os.remove(path)
	except OSError:
		pass

	print("Air Shipment IATA Transaction migration completed.")
	return True
