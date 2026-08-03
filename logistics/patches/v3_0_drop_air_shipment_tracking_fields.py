# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Drop the ``Real-time Tracking`` columns on ``Air Shipment``.

The section was never wired to a tracking provider (the placeholder
``update_tracking_status`` method only ever printed a message), so every column
below is empty on every existing shipment.

This must run in ``pre_model_sync``: ``tabAir Shipment`` sits ~900 bytes under
MariaDB's 65,535-byte row limit, and the same release widens
``insurance_policy_number`` / ``insurance_claim_number`` from Small Text (TEXT,
12 bytes) to Data (VARCHAR(140), 562 bytes). Reclaiming these columns first,
together with 40-character limits on the two time-sensitive Link fields, keeps
the model-sync ALTER inside the limit.

Idempotent: only touches what still exists.
"""

from __future__ import unicode_literals

import frappe


TABLE = "tabAir Shipment"

LEGACY_COLUMNS = (
	"tracking_provider",
	"tracking_number",
	"tracking_url",
	"real_time_tracking_enabled",
	"last_tracking_update",
	"tracking_status",
)

LEGACY_LAYOUT_FIELDS = (
	"tracking_section",
	"column_break_tracking",
)


def execute():
	if not frappe.db.table_exists("Air Shipment"):
		return

	_drop_columns()
	_purge_customizations()
	frappe.db.commit()


def _drop_columns():
	# DESC returns tuples (Field, Type, Null, Key, Default, Extra)
	existing = {row[0] for row in frappe.db.sql(f"DESC `{TABLE}`")}
	for column in LEGACY_COLUMNS:
		if column not in existing:
			continue
		try:
			frappe.db.sql(f"ALTER TABLE `{TABLE}` DROP COLUMN `{column}`")
			frappe.db.commit()
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"drop column {column} from {TABLE} failed",
			)


def _purge_customizations():
	"""Property Setters / Custom Fields on the gone fields would otherwise
	linger and surface as warnings during ``bench migrate``."""
	for fieldname in LEGACY_COLUMNS + LEGACY_LAYOUT_FIELDS:
		frappe.db.delete(
			"Property Setter",
			{"doc_type": "Air Shipment", "field_name": fieldname},
		)
		frappe.db.delete(
			"Custom Field",
			{"dt": "Air Shipment", "fieldname": fieldname},
		)
