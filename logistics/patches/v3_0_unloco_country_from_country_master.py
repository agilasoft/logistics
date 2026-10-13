# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
"""Point UNLOCO.country at the Country document.

The field is a Link to Country. Older rows stored the UN/LOCODE codelist label
(``United States of America (the)``, ``Philippines (the)``), which is not a
Country name. Rewrite from the ISO code, then clear any value that is still
not a Country record so the link is valid.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("UNLOCO") or not frappe.db.table_exists("Country"):
		return
	if not frappe.db.has_column("UNLOCO", "country") or not frappe.db.has_column("UNLOCO", "country_code"):
		return
	if not frappe.db.has_column("Country", "code"):
		return

	# The first two letters of a UN/LOCODE are the ISO country code.
	frappe.db.sql(
		"""
		UPDATE `tabUNLOCO`
		SET country_code = UPPER(LEFT(unlocode, 2))
		WHERE IFNULL(TRIM(country_code), '') = ''
		  AND CHAR_LENGTH(IFNULL(unlocode, '')) = 5
		"""
	)

	now = frappe.utils.now()
	frappe.db.sql(
		"""
		UPDATE `tabUNLOCO` u
		INNER JOIN `tabCountry` c
			ON UPPER(TRIM(c.code)) = UPPER(TRIM(u.country_code))
		SET u.country = c.name,
			u.modified = %(now)s
		WHERE IFNULL(TRIM(u.country_code), '') != ''
		  AND IFNULL(c.name, '') != ''
		  AND IFNULL(u.country, '') != c.name
		""",
		{"now": now},
	)

	# Anything left that is not a Country name cannot sit in the Link field.
	frappe.db.sql(
		"""
		UPDATE `tabUNLOCO` u
		LEFT JOIN `tabCountry` c ON c.name = u.country
		SET u.country = '',
			u.modified = %(now)s
		WHERE IFNULL(TRIM(u.country), '') != ''
		  AND c.name IS NULL
		""",
		{"now": now},
	)

	# Party country links that were copied from the old UNLOCO label.
	for doctype in ("Consignee", "Freight Agent"):
		if not frappe.db.table_exists(doctype):
			continue
		if not frappe.db.has_column(doctype, "country") or not frappe.db.has_column(doctype, "default_unloco"):
			continue
		table = f"tab{doctype}"
		frappe.db.sql(
			f"""
			UPDATE `{table}` p
			INNER JOIN `tabUNLOCO` u ON u.name = p.default_unloco
			INNER JOIN `tabCountry` c ON c.name = u.country
			LEFT JOIN `tabCountry` existing ON existing.name = p.country
			SET p.country = c.name,
				p.modified = %(now)s
			WHERE IFNULL(TRIM(u.country), '') != ''
			  AND (
				IFNULL(TRIM(p.country), '') = ''
				OR existing.name IS NULL
			  )
			  AND IFNULL(p.country, '') != c.name
			""",
			{"now": now},
		)

	frappe.db.commit()
