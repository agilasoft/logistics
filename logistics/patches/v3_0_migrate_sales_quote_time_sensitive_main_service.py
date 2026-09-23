# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Sales Quote: Time Sensitive is a checkbox overlay, not a Primary Service Type.

Existing quotes with ``main_service = Time Sensitive`` are flagged ``is_time_sensitive``
and reassigned to a real mode inferred from charge lines (first Air/Sea/Transport/Customs/
Warehousing). Quotes with no matching charge default to Air.
"""

from __future__ import annotations

from collections import defaultdict

import frappe

_CANON_TO_MAIN = {
	"air": "Air",
	"sea": "Sea",
	"transport": "Transport",
	"custom": "Customs",
	"warehousing": "Warehousing",
}


def infer_main_service_from_charge_types(service_types: list[str] | None) -> str:
	from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage

	for st in service_types or []:
		canon = canonical_charge_service_type_for_storage(st)
		if canon in _CANON_TO_MAIN:
			return _CANON_TO_MAIN[canon]
	return "Air"


def execute():
	if not frappe.db.exists("DocType", "Sales Quote"):
		return
	if not frappe.db.has_column("Sales Quote", "main_service"):
		return

	names = frappe.get_all(
		"Sales Quote",
		filters={"main_service": "Time Sensitive"},
		pluck="name",
	)
	if not names:
		frappe.clear_cache(doctype="Sales Quote")
		return

	if frappe.db.has_column("Sales Quote", "is_time_sensitive"):
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET is_time_sensitive = 1
			WHERE name IN %(names)s
			""",
			{"names": tuple(names)},
		)

	charges_by_parent: dict[str, list[str]] = defaultdict(list)
	if frappe.db.exists("DocType", "Sales Quote Charge"):
		for row in frappe.get_all(
			"Sales Quote Charge",
			filters={"parent": ["in", names]},
			fields=["parent", "service_type"],
			order_by="parent, idx",
		):
			charges_by_parent[row.parent].append(row.service_type or "")

	by_main: dict[str, list[str]] = defaultdict(list)
	for name in names:
		main = infer_main_service_from_charge_types(charges_by_parent.get(name))
		by_main[main].append(name)

	for main, group in by_main.items():
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET main_service = %(main)s
			WHERE name IN %(names)s
			""",
			{"main": main, "names": tuple(group)},
		)

	frappe.clear_cache(doctype="Sales Quote")
	frappe.db.commit()
