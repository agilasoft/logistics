"""Reinstall Sales Quote print format without an underline on charge group labels."""

from logistics.pricing_center.print_format.sales_quote.install_print_format import (
	install_sales_quote_print_format,
)


def execute():
	install_sales_quote_print_format()
