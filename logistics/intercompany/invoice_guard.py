# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Decisions that keep intercompany invoice creation from repeating itself."""

from __future__ import annotations


# Job types that can be intercompany legs (must have company and charges).
INTERCOMPANY_JOB_TYPES = (
	"Transport Job",
	"Air Shipment",
	"Sea Shipment",
	"Warehouse Job",
	"Declaration",
	"Declaration Order",
)

# Stable prefix on the operating-company Sales Invoice. Kept untranslated so the
# submit hook can tell this invoice apart from the customer invoice.
INTERCOMPANY_SI_REMARKS_PREFIX = "Intercompany:"


def intercompany_sales_invoice_marked(is_intercompany_flag, remarks):
	"""Return True when this Sales Invoice is the operating-company leg.

	The flag set while the pair is created wins. Otherwise the remarks prefix
	identifies an invoice that was already created as the intercompany leg.
	"""
	if is_intercompany_flag:
		return True
	return (remarks or "").strip().startswith(INTERCOMPANY_SI_REMARKS_PREFIX)


def relationship_for_companies(relationships, main_job_company, operating_company):
	"""Return the internal customer and supplier for one company pair.

	``main_job_company`` matches the relationship row's billing company.
	The first matching row wins. No match returns ``None``.
	"""
	for row in relationships or []:
		if row.get("billing_company") == main_job_company and row.get("operating_company") == operating_company:
			return {
				"internal_customer": row.get("internal_customer"),
				"internal_supplier": row.get("internal_supplier"),
			}
	return None
