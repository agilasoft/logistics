"""Reinstall Tariff ALTA with 15 charge rows per printed page."""

from logistics.pricing_center.print_format.tariff_alta.install_print_format import (
	install_tariff_alta_print_format,
)


def execute():
	install_tariff_alta_print_format()
