# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop the legacy ``customer`` column from ``tabMICE Project``.

Companion to :mod:`logistics.patches.v1_4_mice_project_customer_to_organizer`,
which created ``MICE Organizer`` rows for each distinct legacy customer and
backfilled ``MICE Project.organizer``.

This patch:

1. Re-runs the v1_4 backfill defensively in case any rows still have ``customer``
   set without an ``organizer`` (handles partial-prior-run scenarios and the
   case where v1_4 was edited after first run).
2. Drops the ``customer`` column from ``tabMICE Project`` because the field is
   no longer declared on the DocType.

Frappe never drops columns automatically on schema sync, so without this patch
the orphan column would linger forever and confuse reports that try to query
it.
"""

from __future__ import annotations

import frappe


_TABLE = "tabMICE Project"


def execute():
	if not frappe.db.table_exists("MICE Project"):
		return

	# Defensive re-run of the v1_4 backfill so the column drop below is safe.
	try:
		from logistics.patches.v1_4_mice_project_customer_to_organizer import (
			execute as _backfill_organizer,
		)

		_backfill_organizer()
	except Exception:
		# v1_4 may have already run; we still want to attempt the column drop.
		pass

	columns = {c.lower() for c in frappe.db.get_table_columns("MICE Project")}
	if "customer" not in columns:
		return

	# At this point ``MICE Project.organizer`` is the source of truth for the
	# billing Customer (resolved via MICE Organizer.customer). Any straggler
	# ``customer`` value that did not make it to an organizer is logged so it
	# can be audited before the column is dropped permanently.
	stragglers = frappe.db.sql(
		f"""
		SELECT name, customer
		FROM `{_TABLE}`
		WHERE
			customer IS NOT NULL
			AND TRIM(customer) <> ''
			AND (organizer IS NULL OR TRIM(organizer) = '')
		"""
	)
	if stragglers:
		frappe.log_error(
			title="MICE Project: customer column dropped without organizer backfill",
			message=(
				"The following MICE Projects had a legacy `customer` value but no "
				"`organizer` set when the column was dropped. Recreate the "
				"organizer link manually if needed:\n\n"
				+ "\n".join(f"- {name}: customer={cust}" for name, cust in stragglers)
			),
		)

	frappe.db.sql_ddl(f"ALTER TABLE `{_TABLE}` DROP COLUMN `customer`")
	frappe.db.commit()
	frappe.clear_cache(doctype="MICE Project")
