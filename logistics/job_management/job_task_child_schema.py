# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Repair ``tabJob Task`` after it changed from a standalone DocType to a child table.

Frappe adds ``parent``, ``parentfield``, and ``parenttype`` only when it creates
a table. Altering an existing table does not add them, so opening a booking
queries ``WHERE parent = ...`` and MariaDB reports an unknown column.
"""

from __future__ import annotations

DOCTYPE = "Job Task"
TABLE = "tabJob Task"
CHILD_LINK_COLUMNS = ("parent", "parentfield", "parenttype")
LEGACY_LINK_COLUMNS = ("job_no", "job_type")
PARENTFIELD = "job_tasks"


def table_exists_argument() -> str:
	"""Name to pass to ``frappe.db.table_exists``.

	That helper looks up ``tab`` + the argument. Passing ``tabJob Task``
	searches for ``tabtabJob Task``, the repair thinks the table is missing,
	and opening an order still fails with unknown column ``parent``.
	"""
	return DOCTYPE


def missing_child_link_columns(existing_columns) -> list[str]:
	"""Child-link columns that are not on the table yet."""
	existing = set(existing_columns or [])
	return [name for name in CHILD_LINK_COLUMNS if name not in existing]


def add_column_clauses(columns, varchar_len) -> list[str]:
	"""``ALTER TABLE`` fragments for the missing child-link columns."""
	length = int(varchar_len)
	if not 1 <= length <= 1000:
		raise ValueError(f"varchar length {length} is out of range")
	clauses = []
	for name in columns:
		if name not in CHILD_LINK_COLUMNS:
			raise ValueError(f"unexpected column {name}")
		clauses.append(f"ADD COLUMN `{name}` varchar({length})")
	return clauses


def should_relink_legacy_rows(existing_columns) -> bool:
	"""True when standalone rows can be pointed at the job they already named."""
	existing = set(existing_columns or [])
	if any(name not in existing for name in CHILD_LINK_COLUMNS):
		return False
	return all(name in existing for name in LEGACY_LINK_COLUMNS)


def relink_statement(*, has_sequence: bool) -> str:
	"""Point leftover standalone rows at ``job_tasks`` on the job they belonged to."""
	idx_sql = ""
	if has_sequence:
		idx_sql = ", idx = IF(IFNULL(idx, 0) = 0, IFNULL(sequence, 0), idx)"
	return (
		f"UPDATE `{TABLE}` "
		f"SET parent = job_no, parenttype = job_type, parentfield = '{PARENTFIELD}'{idx_sql} "
		"WHERE IFNULL(parent, '') = '' "
		"AND IFNULL(job_no, '') != '' "
		"AND IFNULL(job_type, '') != ''"
	)
