# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate ``MICE Project.customer`` (Link to Customer) to ``MICE Project.organizer``
(Link to the new ``MICE Organizer`` master).

Why
---
The ``customer`` field on ``MICE Project`` always held the *programme-level
organizer* of the show (the field description literally said "e.g. show
organizer"). The new ``MICE Organizer`` master makes that concept first-class,
and lets the same organizer be reused across many MICE Projects independently
of any billing Customer.

What this patch does
--------------------
1. Adds the ``organizer`` column to ``tabMICE Project`` if schema sync hasn't
   already populated it (we set it via raw SQL so it lands even when the column
   already exists with a different definition).
2. For every distinct legacy ``MICE Project.customer`` value, creates one
   ``MICE Organizer`` row whose ``customer`` field points back to that Customer
   and whose ``organizer_name`` comes from the Customer's ``customer_name``.
3. Backfills ``MICE Project.organizer`` with the newly created (or matched)
   organizer name on every Project that had a customer.
4. Leaves the legacy ``customer`` column in place because the JSON now declares
   it as a read-only mirror (``fetch_from = organizer.customer``) - this keeps
   downstream Docket / MICE Job / MICE Order fetch chains working unchanged.

The patch is idempotent: re-running it skips Projects whose ``organizer`` is
already set and reuses any pre-existing ``MICE Organizer`` whose ``customer``
already matches the legacy value.
"""

from __future__ import annotations

import frappe


_DOCTYPE = "MICE Project"
_ORGANIZER_DT = "MICE Organizer"
_TABLE = f"tab{_DOCTYPE}"


def execute():
	if not frappe.db.exists("DocType", _DOCTYPE):
		return
	if not frappe.db.exists("DocType", _ORGANIZER_DT):
		# DocType sync hasn't created the MICE Organizer doctype yet; the
		# patches.txt entry is in [post_model_sync] so this should not happen,
		# but guard anyway so a partial install does not error out.
		return

	_ensure_organizer_column()

	legacy_customers = _collect_legacy_customer_values()
	if not legacy_customers:
		return

	organizer_by_customer = _ensure_organizers_for_customers(legacy_customers)
	_backfill_project_organizer(organizer_by_customer)

	frappe.db.commit()


def _ensure_organizer_column() -> None:
	"""Make sure ``tabMICE Project`` has an ``organizer`` column to update.

	On a fresh install the schema sync that ran before this patch will have
	added the column. On an existing site that has not yet picked up the new
	DocType JSON we add the column here so the backfill UPDATE below has a
	target.
	"""
	if not frappe.db.table_exists(_DOCTYPE):
		return
	columns = {c.lower() for c in frappe.db.get_table_columns(_DOCTYPE)}
	if "organizer" in columns:
		return
	frappe.db.sql_ddl(
		f"ALTER TABLE `{_TABLE}` ADD COLUMN `organizer` VARCHAR(140) NULL"
	)


def _collect_legacy_customer_values() -> list[str]:
	"""Return the distinct non-empty ``customer`` values on MICE Projects that
	don't yet have ``organizer`` populated.
	"""
	if not frappe.db.table_exists(_DOCTYPE):
		return []
	columns = {c.lower() for c in frappe.db.get_table_columns(_DOCTYPE)}
	if "customer" not in columns:
		return []

	rows = frappe.db.sql(
		f"""
		SELECT DISTINCT `customer`
		FROM `{_TABLE}`
		WHERE
			`customer` IS NOT NULL
			AND TRIM(`customer`) <> ''
			AND (`organizer` IS NULL OR TRIM(`organizer`) = '')
		"""
	)
	return [r[0] for r in rows if r and r[0]]


def _ensure_organizers_for_customers(customers: list[str]) -> dict[str, str]:
	"""Create / look up one ``MICE Organizer`` per legacy customer value.

	Returns a ``{customer_name: organizer_name}`` dict. Customers that no
	longer exist in ``tabCustomer`` still get an organizer (so the legacy
	link is preserved as a flat name string).
	"""
	out: dict[str, str] = {}
	for cust in customers:
		existing = frappe.db.get_value(_ORGANIZER_DT, {"customer": cust}, "name")
		if existing:
			out[cust] = existing
			continue

		display_name = (
			frappe.db.get_value("Customer", cust, "customer_name")
			or cust
		)

		base = (display_name or cust or "Organizer").strip() or "Organizer"
		organizer_name = base
		idx = 2
		while frappe.db.exists(_ORGANIZER_DT, {"organizer_name": organizer_name}):
			organizer_name = f"{base} ({idx})"
			idx += 1
			if idx > 1000:
				organizer_name = f"{base}-{frappe.generate_hash(length=6)}"
				break

		doc = frappe.new_doc(_ORGANIZER_DT)
		doc.organizer_name = organizer_name
		doc.organizer_type = "Company"
		# The legacy customer value may have been deleted; only set if it still
		# exists so the Link constraint validates.
		if frappe.db.exists("Customer", cust):
			doc.customer = cust
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		out[cust] = doc.name

	return out


def _backfill_project_organizer(organizer_by_customer: dict[str, str]) -> None:
	"""Set ``organizer`` on every MICE Project that has a legacy ``customer``
	but no ``organizer`` yet.
	"""
	for cust, organizer in organizer_by_customer.items():
		frappe.db.sql(
			f"""
			UPDATE `{_TABLE}`
			SET `organizer` = %(organizer)s
			WHERE `customer` = %(customer)s
				AND (`organizer` IS NULL OR TRIM(`organizer`) = '')
			""",
			{"organizer": organizer, "customer": cust},
		)
