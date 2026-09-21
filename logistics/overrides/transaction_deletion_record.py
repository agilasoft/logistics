# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# License: AGPL-3.0-or-later

"""Skip Table fields that do not point at real child tables during company wipe."""

from __future__ import annotations

import frappe
from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
	TransactionDeletionRecord,
)


class LogisticsTransactionDeletionRecord(TransactionDeletionRecord):
	def _get_child_tables(self, doctype_name):
		tables = super()._get_child_tables(doctype_name) or []
		real_children = []
		for table in tables:
			if not table or not frappe.db.exists("DocType", table):
				continue
			if frappe.db.get_value("DocType", table, "istable"):
				if _has_parent_column(table):
					real_children.append(table)
		return real_children


def _has_parent_column(doctype: str) -> bool:
	try:
		return "parent" in frappe.db.get_table_columns(doctype)
	except Exception:
		return False
