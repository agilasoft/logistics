# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Roll up liquidation and cash-acknowledgment totals onto Cash Advance Request."""

from __future__ import unicode_literals

from typing import Optional

import frappe
from frappe.utils import flt


def compute_unliquidated(
	total_requested: float, total_liquidated: float, returned: float = 0, refunded: float = 0
) -> float:
	"""Outstanding advance balance after expenses, cash returned, and additional payouts."""
	return flt(flt(total_requested) - flt(total_liquidated) - flt(returned) + flt(refunded), 2)


def _sum_submitted_acknowledgments(
	cash_advance_request: str, acknowledgment_type: str, exclude: Optional[str] = None
) -> float:
	conditions = ["cash_advance_request = %s", "docstatus = 1", "acknowledgment_type = %s"]
	params: list = [cash_advance_request, acknowledgment_type]
	if exclude:
		conditions.append("name != %s")
		params.append(exclude)
	row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(amount), 0)
		FROM `tabCash Acknowledgment`
		WHERE {" AND ".join(conditions)}
		""",
		tuple(params),
	)
	return flt(row[0][0] if row else 0, 2)


def _sum_submitted_liquidations(cash_advance_request: str) -> float:
	return flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(total_liquidated), 0)
			FROM `tabCash Advance Liquidation`
			WHERE cash_advance_request = %s AND docstatus = 1
			""",
			cash_advance_request,
		)[0][0],
		2,
	)


def sync_cash_advance_request_totals(cash_advance_request: Optional[str]) -> None:
	if not cash_advance_request or not frappe.db.exists("Cash Advance Request", cash_advance_request):
		return
	total_requested = flt(
		frappe.db.get_value("Cash Advance Request", cash_advance_request, "total_requested"), 2
	)
	total_liquidated = _sum_submitted_liquidations(cash_advance_request)
	returned = _sum_submitted_acknowledgments(cash_advance_request, "Receipt")
	refunded = _sum_submitted_acknowledgments(cash_advance_request, "Payment")
	unliquidated = compute_unliquidated(total_requested, total_liquidated, returned, refunded)
	frappe.db.set_value(
		"Cash Advance Request",
		cash_advance_request,
		{
			"total_liquidated": total_liquidated,
			"returned": returned,
			"refunded": refunded,
			"unliquidated": unliquidated,
		},
		update_modified=False,
	)


def sync_cash_advance_request_liquidation_totals(cash_advance_request: Optional[str]) -> None:
	sync_cash_advance_request_totals(cash_advance_request)


def sync_cash_advance_request_settlement_totals(cash_advance_request: Optional[str]) -> None:
	sync_cash_advance_request_totals(cash_advance_request)
