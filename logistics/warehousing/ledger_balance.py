# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Ending balance for one Warehouse Stock Ledger post."""

from __future__ import annotations


def ledger_balance_after_post(beginning_qty, delta):
	"""Return ``(ending_qty, blocked)``.

	An outbound post that would finish below zero is blocked. An inbound
	post is allowed when the beginning balance is zero. Ending at zero is
	allowed.
	"""
	beginning = beginning_qty or 0
	change = delta or 0
	ending = beginning + change
	return ending, change < 0 and ending < 0
