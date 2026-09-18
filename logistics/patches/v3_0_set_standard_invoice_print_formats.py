"""Set Sales Invoice and Purchase Invoice HTML designs as the standard print formats."""

from logistics.print_format.purchase_invoice.install_print_format import (
	install_purchase_invoice_print_format,
)
from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	install_sales_invoice_print_format()
	install_purchase_invoice_print_format()
