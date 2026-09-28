"""Sales Invoice HTML: exclude 95/5 rows from Total Sales (VAT Inclusive)."""

from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	install_sales_invoice_print_format()
