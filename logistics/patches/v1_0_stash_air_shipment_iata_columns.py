# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Before schema sync removes legacy IATA/CASS/TACT/e-AWB columns from `tabAir Shipment`,
dump any non-empty values to a site-local JSON file for post_model_sync migration.
"""

import json
import os

import frappe

_STASH_FILENAME = ".air_iata_migration_stash.json"

_MIGRATION_COLUMNS = (
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
)


def execute():
	table = "`tabAir Shipment`"
	if not frappe.db.has_table("tabAir Shipment"):
		return True
	if not frappe.db.has_column("tabAir Shipment", "iata_status"):
		return True

	select_parts = ["name"] + [c for c in _MIGRATION_COLUMNS if frappe.db.has_column("tabAir Shipment", c)]
	if len(select_parts) <= 1:
		return True

	cols_sql = ", ".join(f"`{c}`" for c in select_parts)
	rows = frappe.db.sql(f"SELECT {cols_sql} FROM {table}", as_dict=True)

	def _row_has_data(row):
		for k in _MIGRATION_COLUMNS:
			if k not in row:
				continue
			v = row.get(k)
			if v is None or v == "":
				continue
			if k == "eawb_enabled" and (v == 0 or v is False):
				continue
			if k == "tact_rate_lookup" and (v == 0 or v is False):
				continue
			return True
		return False

	stash_rows = [r for r in rows if _row_has_data(r)]
	path = frappe.get_site_path("private", "files", _STASH_FILENAME)
	if stash_rows:
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w", encoding="utf-8") as f:
			json.dump(stash_rows, f, default=str)
		print(f"Stashed {len(stash_rows)} Air Shipment row(s) for IATA migration to {path}")
	elif os.path.isfile(path):
		os.remove(path)
	return True
