# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""When a Sales Quote may be marked as a blanket quotation."""

from __future__ import annotations


def blanket_quotation_block(blanket_quotation, quotation_type, additional_charge, docstatus, has_charges):
	"""Return why a blanket quotation is blocked, or ``None`` when it is allowed.

	``not_regular`` means the quotation type is not Regular.
	``additional_charge`` means the quote is an additional-charge quote.
	``missing_charges`` means a submitted blanket quote has no charge lines.
	A quote that is not a blanket quotation is allowed.
	"""
	if not blanket_quotation:
		return None
	if (quotation_type or "").strip() != "Regular":
		return "not_regular"
	if additional_charge:
		return "additional_charge"
	if docstatus == 1 and not has_charges:
		return "missing_charges"
	return None
