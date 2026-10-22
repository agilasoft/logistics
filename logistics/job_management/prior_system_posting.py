# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Charges already posted in a prior system.

Beginning Jobs tags a charge side with this status instead of creating a
Sales Invoice, Purchase Invoice, or Journal Entry. The amount stays on the
charge row. Recognition and new invoices skip that side.
"""

from __future__ import unicode_literals

PRIOR_SYSTEM_POSTED_STATUS = "Posted in Prior System"


def _status(charge, fieldname):
	if charge is None:
		return ""
	if isinstance(charge, dict):
		value = charge.get(fieldname)
	else:
		value = getattr(charge, fieldname, None)
	return (value or "").strip()


def revenue_posted_in_prior_system(charge) -> bool:
	return _status(charge, "sales_invoice_status") == PRIOR_SYSTEM_POSTED_STATUS


def cost_posted_in_prior_system(charge) -> bool:
	return _status(charge, "purchase_invoice_status") == PRIOR_SYSTEM_POSTED_STATUS
