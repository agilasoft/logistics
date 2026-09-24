"""Sales Invoice HTML: omit 95/5 Taxable Freight Item lines from the item table."""

from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	install_sales_invoice_print_format()
