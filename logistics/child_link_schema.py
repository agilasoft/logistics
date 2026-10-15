# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Child-link columns for tables that were not created as child tables.

Frappe adds ``parent``, ``parentfield``, and ``parenttype`` only in
``MariaDBTable.create()``. ``alter()`` does not add them, and module import
skips ``DocType.validate_child_table``. A table created as a normal document,
or a normal document used as a Table field, has no ``parent`` column.
``get_doc`` then fails with unknown column ``parent``.

Job Task has its own repair. This module covers the other tables.
"""

from __future__ import annotations

from dataclasses import dataclass

CHILD_LINK_COLUMNS = ("parent", "parentfield", "parenttype")


@dataclass(frozen=True)
class ChildLinkRepair:
	"""One physical table that can be queried as a child grid."""

	doctype: str
	# (parent DocType, Table fieldname) for every form that loads this table.
	parents: tuple[tuple[str, str], ...] = ()
	# Columns that still name the old parent document. Empty when none exist.
	legacy_columns: tuple[str, ...] = ()
	legacy_parentfield: str = ""

	@property
	def table(self) -> str:
		return f"tab{self.doctype}"

	def table_exists_argument(self) -> str:
		"""Name to pass to ``frappe.db.table_exists``.

		That helper looks up ``tab`` + the argument. Passing ``tabSomething``
		searches for ``tabtabSomething`` and the repair does nothing.
		"""
		return self.doctype


# Tables whose current JSON has no parent column for schema sync to add.
# Rate rows have no column that names the old Tariff parent.
REPAIRS: tuple[ChildLinkRepair, ...] = (
	ChildLinkRepair(
		"Default Emission Factors",
		parents=(("Sustainability Settings", "default_emission_factors"),),
	),
	ChildLinkRepair(
		"Integrated Modules",
		parents=(("Sustainability Settings", "integrated_modules"),),
	),
	ChildLinkRepair(
		"Road Compliance Requirement",
		parents=(("Road Compliance", "requirements"),),
	),
	ChildLinkRepair("Air Freight Rate"),
	ChildLinkRepair("Sea Freight Rate"),
	ChildLinkRepair("Customs Rate"),
	ChildLinkRepair("Warehouse Rate"),
)


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


def should_relink_legacy_rows(repair: ChildLinkRepair, existing_columns) -> bool:
	"""True when leftover standalone rows still name their old parent."""
	if len(repair.legacy_columns) != 2 or not repair.legacy_parentfield:
		return False
	existing = set(existing_columns or [])
	if any(name not in existing for name in CHILD_LINK_COLUMNS):
		return False
	return all(name in existing for name in repair.legacy_columns)


def relink_statement(repair: ChildLinkRepair) -> str:
	"""Point leftover rows at the parent column they already stored.

	``legacy_columns`` is ``(parent source, parenttype source)``.
	"""
	if len(repair.legacy_columns) != 2 or not repair.legacy_parentfield:
		raise ValueError(f"{repair.doctype} has no legacy parent link")
	parent_source, parenttype_source = repair.legacy_columns
	return (
		f"UPDATE `{repair.table}` "
		f"SET parent = `{parent_source}`, parenttype = `{parenttype_source}`, "
		f"parentfield = '{repair.legacy_parentfield}' "
		"WHERE IFNULL(parent, '') = '' "
		f"AND IFNULL(`{parent_source}`, '') != '' "
		f"AND IFNULL(`{parenttype_source}`, '') != ''"
	)
