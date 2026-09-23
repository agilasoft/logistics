# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Time Sensitive Case Charge qty/rate/amount before standard schema sync.

The child table is being aligned with Air Booking Charges (quantity / unit_rate /
base_amount). Run in pre_model_sync so migrate does not drop the legacy columns.
"""

from __future__ import annotations

import frappe
from frappe.model.utils.rename_field import rename_field

_DOCTYPE = "Time Sensitive Case Charge"
_RENAMES = (
	("qty", "quantity"),
	("rate", "unit_rate"),
	("amount", "base_amount"),
)


def _table_columns(doctype: str) -> set[str]:
	table = f"tab{doctype}"
	if not frappe.db.table_exists(table):
		return set()
	try:
		return {row["Field"] for row in frappe.db.sql(f"DESCRIBE `{table}`", as_dict=True)}
	except Exception:
		return set()


def execute():
	if not frappe.db.exists("DocType", _DOCTYPE):
		return
	if not frappe.db.table_exists(f"tab{_DOCTYPE}"):
		return

	cols = _table_columns(_DOCTYPE)
	for old, new in _RENAMES:
		if old not in cols:
			continue
		if new in cols:
			# Already has the standard column; drop leftover legacy column after copying.
			frappe.db.sql(
				f"UPDATE `tab{_DOCTYPE}` SET `{new}` = `{old}` WHERE IFNULL(`{new}`, 0) = 0 AND IFNULL(`{old}`, 0) != 0"
			)
			frappe.db.sql(f"ALTER TABLE `tab{_DOCTYPE}` DROP COLUMN `{old}`")
			cols.discard(old)
			continue
		rename_field(_DOCTYPE, old, new)
		cols.discard(old)
		cols.add(new)

	frappe.clear_cache()
