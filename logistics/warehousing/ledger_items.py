# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Whether a Warehouse Job has rows to post to the stock ledger."""

from __future__ import annotations


def empty_ledger_items_reason(job_type, has_items, populate_adjustment_triggered=False):
	"""Return why an empty job cannot post, or ``None`` when posting may continue.

	A job with rows is never blocked here. A Stocktake that has already run
	Populate Adjustments may post with no rows. Any other empty job is
	blocked. ``populate_or_add`` is the Stocktake message. ``items_required``
	is the message for every other type.
	"""
	if has_items:
		return None
	if (job_type or "").strip() == "Stocktake":
		if populate_adjustment_triggered:
			return None
		return "populate_or_add"
	return "items_required"
