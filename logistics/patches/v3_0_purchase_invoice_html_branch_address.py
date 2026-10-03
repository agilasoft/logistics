"""Purchase Invoice HTML: print the header address from Branch Registration Details."""

from logistics.print_format.purchase_invoice.install_print_format import (
	install_purchase_invoice_print_format,
)


def execute():
	install_purchase_invoice_print_format()
