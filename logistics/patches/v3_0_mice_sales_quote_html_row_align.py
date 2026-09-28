"""Reinstall MICE Sales Quote HTML with left-aligned rates and a 1mm row gap."""

from logistics.pricing_center.print_format.mice_sales_quote_html.install_print_format import (
	install_mice_sales_quote_html_print_format,
)


def execute():
	install_mice_sales_quote_html_print_format()
