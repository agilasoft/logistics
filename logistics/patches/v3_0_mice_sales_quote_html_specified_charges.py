"""Reinstall MICE Sales Quote HTML so Specified Charges print as a percent of selected items."""

from logistics.pricing_center.print_format.mice_sales_quote_html.install_print_format import (
	install_mice_sales_quote_html_print_format,
)


def execute():
	install_mice_sales_quote_html_print_format()
