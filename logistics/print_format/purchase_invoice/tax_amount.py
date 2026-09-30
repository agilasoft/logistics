# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Printed tax amount on the Purchase Invoice HTML."""

from __future__ import annotations


def printed_tax_amount(signed_tax, is_debit_note=False, is_credit_note=False, label=""):
	"""Return the tax amount shown on the invoice line.

	Purchase Invoice keeps the signed amount, so a withholding deduction stays
	negative. Debit Note and Credit Note lines are shown positive, except
	Debit Note withholding, which stays negative like the Purchase Invoice.
	"""
	amount = signed_tax or 0
	if is_debit_note and _is_withholding(label):
		return -abs(amount)
	if is_debit_note or is_credit_note:
		return abs(amount)
	return amount


def _is_withholding(label):
	return "withhold" in (label or "").lower()
