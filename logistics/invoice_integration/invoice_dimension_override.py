# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Re-apply company dimensions after ERPNext fills invoice defaults.

``AccountsController.validate`` calls ``set_missing_values`` before it checks
that a Cost Center belongs to the invoice company. A default from the other
company has to be replaced inside that call, or the check still fails.
"""

from __future__ import annotations

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


def _realign(doc) -> None:
	from logistics.invoice_integration.purchase_invoice_dimensions import (
		align_invoice_dimensions_to_company,
	)

	align_invoice_dimensions_to_company(doc)


class LogisticsSalesInvoice(SalesInvoice):
	def set_missing_values(self, for_validate=False):
		super().set_missing_values(for_validate=for_validate)
		_realign(self)


class LogisticsPurchaseInvoice(PurchaseInvoice):
	def set_missing_values(self, for_validate=False):
		super().set_missing_values(for_validate=for_validate)
		_realign(self)
