# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Fields a Warehouse Job row must have before it posts to the stock ledger."""

from __future__ import annotations


def ledger_row_gap(location, item):
	"""Return ``location`` or ``item`` when that field is missing, else ``None``.

	Location is checked first. A row with both fields is ready for the
	quantity and balance checks.
	"""
	if not location:
		return "location"
	if not item:
		return "item"
	return None
