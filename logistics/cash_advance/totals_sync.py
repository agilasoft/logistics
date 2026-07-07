# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Roll up liquidation and cash-acknowledgment totals for Cash Advance Request."""

from __future__ import unicode_literals

from typing import Dict, Optional

import frappe
from frappe.utils import flt


def compute_unliquidated(
	total_requested: float, total_liquidated: float, returned: float = 0, refunded: float = 0
) -> float:
	"""Outstanding balance: Total Requested - Total Liquidated + Refunded - Returned."""
	return flt(
		flt(total_requested) - flt(total_liquidated) + flt(refunded) - flt(returned), 2
	)


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


def get_release_journal_entry(cash_advance_request: Optional[str]) -> Optional[str]:
	"""Release journal entry linked to a submitted Cash Advance Request."""
	if not cash_advance_request:
		return None

	je_name = frappe.db.get_value(
		"Journal Entry",
		{"bill_no": cash_advance_request, "docstatus": 1},
		"name",
		order_by="creation asc",
	)
	if je_name:
		return je_name

	# Legacy column before virtual-field migration.
	if frappe.db.has_column("Cash Advance Request", "advance_journal_entry"):
		return frappe.db.get_value("Cash Advance Request", cash_advance_request, "advance_journal_entry")

	return None


def get_cash_advance_request_totals(cash_advance_request: Optional[str]) -> Dict[str, float]:
	"""Computed totals from submitted Cash Advance child documents."""
	if not cash_advance_request or not frappe.db.exists("Cash Advance Request", cash_advance_request):
		return {
			"total_requested": 0,
			"total_liquidated": 0,
			"returned": 0,
			"refunded": 0,
			"unliquidated": 0,
		}

	total_requested = flt(
		frappe.db.get_value("Cash Advance Request", cash_advance_request, "total_requested"), 2
	)
	total_liquidated = _sum_submitted_liquidations(cash_advance_request)
	returned = _sum_submitted_acknowledgments(cash_advance_request, "Receipt")
	refunded = _sum_submitted_acknowledgments(cash_advance_request, "Payment")
	unliquidated = compute_unliquidated(total_requested, total_liquidated, returned, refunded)
	return {
		"total_requested": total_requested,
		"total_liquidated": total_liquidated,
		"returned": returned,
		"refunded": refunded,
		"unliquidated": unliquidated,
	}


def unliquidated_sql_expr(car_alias: str = "car") -> str:
	"""SQL expression for outstanding balance from child cash-advance documents."""
	return (
		f"IFNULL({car_alias}.total_requested, 0) "
		f"- IFNULL(liq.total_liquidated, 0) "
		f"+ IFNULL(ack.refunded, 0) - IFNULL(ack.returned, 0)"
	)


def unliquidated_join_sql(car_alias: str = "car") -> str:
	"""LEFT JOINs for liquidation and acknowledgment rollups used with ``unliquidated_sql_expr``."""
	return f"""
		LEFT JOIN (
			SELECT cash_advance_request, SUM(total_liquidated) AS total_liquidated
			FROM `tabCash Advance Liquidation`
			WHERE docstatus = 1
			GROUP BY cash_advance_request
		) liq ON liq.cash_advance_request = {car_alias}.name
		LEFT JOIN (
			SELECT
				cash_advance_request,
				SUM(CASE WHEN acknowledgment_type = 'Receipt' THEN amount ELSE 0 END) AS returned,
				SUM(CASE WHEN acknowledgment_type = 'Payment' THEN amount ELSE 0 END) AS refunded
			FROM `tabCash Acknowledgment`
			WHERE docstatus = 1
			GROUP BY cash_advance_request
		) ack ON ack.cash_advance_request = {car_alias}.name
	"""


def sync_cash_advance_request_totals(cash_advance_request: Optional[str]) -> None:
	"""No-op: request totals are virtual and read from child documents."""
	return None


def sync_cash_advance_request_liquidation_totals(cash_advance_request: Optional[str]) -> None:
	sync_cash_advance_request_totals(cash_advance_request)


def sync_cash_advance_request_settlement_totals(cash_advance_request: Optional[str]) -> None:
	sync_cash_advance_request_totals(cash_advance_request)
