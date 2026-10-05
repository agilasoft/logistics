# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Signed quantity posted to the Warehouse Stock Ledger for one job row."""

from __future__ import annotations


def ledger_delta(job_type, quantity):
	"""Return ``(delta, error)`` for one Warehouse Job item row.

	Putaway posts a positive quantity. Pick posts a negative quantity.
	Move, Stocktake, and every other type post the signed quantity on the
	row. Stocktake may post zero. ``error`` is ``positive_required``,
	``nonzero_required``, or ``None``.
	"""
	job_type = (job_type or "").strip()
	qty = quantity or 0
	if job_type in ("Putaway", "Pick"):
		if qty <= 0:
			return None, "positive_required"
		return (qty if job_type == "Putaway" else -qty), None
	if qty == 0 and job_type != "Stocktake":
		return None, "nonzero_required"
	return qty, None
