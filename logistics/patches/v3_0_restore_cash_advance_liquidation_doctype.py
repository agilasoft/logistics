# Copyright (c) 2026, Agilasoft and contributors
"""Reimport Cash Advance Liquidation when the parent DocType is missing.

The desk route /desk/cash-advance-liquidation is the DocType list. If the
DocType row is gone, or the name still belongs to the old child table, that
route is a Page that does not exist.
"""

from __future__ import annotations

from logistics.cash_advance.install import ensure_cash_advance_liquidation_doctype


def execute():
	ensure_cash_advance_liquidation_doctype()
