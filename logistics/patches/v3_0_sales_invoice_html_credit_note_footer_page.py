"""Sales Invoice HTML: keep a short credit note VAT summary on page 1."""

from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	install_sales_invoice_print_format()
