"""Sales Invoice HTML: print Weight/Volume/Chargeable with UOM."""

from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	install_sales_invoice_print_format()
