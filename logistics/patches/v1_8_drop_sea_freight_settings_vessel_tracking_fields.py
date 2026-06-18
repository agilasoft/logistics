# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Drop the per-company vessel-tracking columns + password rows on
``Sea Freight Settings``.

These have been replaced by site-wide settings in
``GoConnect Settings ▸ Vessel`` (see ``goconnect.sea.aggregator``). Removing
the columns prevents the orphan fields from showing up in customizations and
deletes any stored API key / API secret rows from ``__Auth`` /
``tabPasswords`` so they don't linger in backups.

Idempotent: the patch only touches what still exists.
"""

from __future__ import unicode_literals

import frappe


LEGACY_DATA_COLUMNS = (
	"enable_vessel_tracking",
	"vessel_tracking_provider",
	"vessel_tracking_api_user",
)

LEGACY_PASSWORD_FIELDS = (
	"vessel_tracking_api_key",
	"vessel_tracking_api_secret",
)


def execute():
	table = "tabSea Freight Settings"
	if not frappe.db.table_exists(table):
		return

	_drop_data_columns(table)
	_purge_password_rows()
	_purge_property_setters()
	frappe.db.commit()


def _drop_data_columns(table):
	# DESC returns tuples (Field, Type, Null, Key, Default, Extra)
	existing = {row[0] for row in frappe.db.sql(f"DESC `{table}`")}
	for column in LEGACY_DATA_COLUMNS + LEGACY_PASSWORD_FIELDS:
		if column not in existing:
			continue
		try:
			# Use plain sql + commit; sql_ddl is a no-op on some backends and
			# MariaDB auto-commits DDL anyway.
			frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `{column}`")
			frappe.db.commit()
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"drop column {column} from {table} failed",
			)


def _purge_password_rows():
	for fieldname in LEGACY_PASSWORD_FIELDS:
		try:
			frappe.db.sql(
				"""
				DELETE FROM `__Auth`
				WHERE doctype = 'Sea Freight Settings' AND fieldname = %s
				""",
				(fieldname,),
			)
		except Exception:
			# Older Frappe versions may not have `__Auth`; ignore.
			pass


def _purge_property_setters():
	"""Customizations / Property Setters referencing the gone fields would
	otherwise linger and surface as warnings during ``bench migrate``."""
	for fieldname in LEGACY_DATA_COLUMNS + LEGACY_PASSWORD_FIELDS + (
		"vessel_tracking_column_break",
	):
		frappe.db.delete(
			"Property Setter",
			{"doc_type": "Sea Freight Settings", "field_name": fieldname},
		)
		frappe.db.delete(
			"Custom Field",
			{"dt": "Sea Freight Settings", "fieldname": fieldname},
		)
