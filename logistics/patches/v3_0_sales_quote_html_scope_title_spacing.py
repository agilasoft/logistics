"""Reinstall Sales Quote print format so the route sits under the quote number."""

from logistics.pricing_center.print_format.sales_quote.install_print_format import (
	install_sales_quote_print_format,
)


def execute():
	install_sales_quote_print_format()
