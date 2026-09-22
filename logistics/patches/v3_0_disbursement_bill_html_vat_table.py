"""Disbursement Bill HTML: Sales Invoice-style table and VAT summary."""

from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	install_sales_invoice_print_format()
