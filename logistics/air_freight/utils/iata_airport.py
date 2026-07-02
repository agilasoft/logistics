# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe


def resolve_unloco_iata_code(unloco_link, iata_field=None):
	"""Return a 3-letter IATA airport code from an explicit field or UNLOCO link."""
	if iata_field and str(iata_field).strip():
		return str(iata_field).strip()[:3].upper()
	if not unloco_link:
		return None

	row = frappe.db.get_value(
		"UNLOCO",
		unloco_link,
		["iata_code", "unlocode"],
		as_dict=True,
	)
	if not row:
		return None

	if row.iata_code and str(row.iata_code).strip():
		return str(row.iata_code).strip()[:3].upper()

	code = (row.unlocode or unloco_link or "").strip().upper()
	if len(code) == 5:
		return code[2:5]
	if len(code) >= 3:
		return code[:3]
	return None
