# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Give Importer Category a unique code before schema sync adds the unique index.

atndemo has legacy rows whose code is blank or repeated (the ATN sheet lists DIM
twice). MariaDB rejects the new unique index until those values are distinct.
"""

import frappe

# Sheet code + description -> code to keep when the source repeats a code.
CODE_OVERRIDES = {
	("DIM", "DISTRIBUTOR"): "DIS",
}


def execute():
	if not frappe.db.table_exists("Importer Category"):
		return
	if not frappe.db.has_column("Importer Category", "code"):
		return

	has_description = frappe.db.has_column("Importer Category", "description")
	fields = "name, code" + (", description" if has_description else "")
	rows = frappe.db.sql(
		f"SELECT {fields} FROM `tabImporter Category` ORDER BY creation, name",
		as_dict=True,
	)

	seen = set()
	for row in rows:
		code = (row.code or "").strip()
		key = code.casefold()
		if code and key not in seen:
			if code != row.code:
				_set_code(row.name, code)
			seen.add(key)
			continue

		description = (row.description or "") if has_description else ""
		new_code = _replacement_code(row.name, code, description, seen)
		_set_code(row.name, new_code)
		seen.add(new_code.casefold())

	frappe.db.commit()


def _replacement_code(name, code, description, seen):
	override = CODE_OVERRIDES.get((code, (description or "").strip().upper()))
	if override and override.casefold() not in seen:
		return override

	candidate = (name or "").strip()[:140]
	if candidate and candidate.casefold() not in seen:
		return candidate

	stem = (code or candidate or "IC")[:130]
	n = 2
	while True:
		candidate = f"{stem}-{n}"
		if candidate.casefold() not in seen:
			return candidate
		n += 1


def _set_code(name, code):
	frappe.db.set_value("Importer Category", name, "code", code, update_modified=False)
