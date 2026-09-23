"""Reinstall Tariff ALTA without Import / Valid Until on rate rows."""

from logistics.pricing_center.print_format.tariff_alta.install_print_format import (
	install_tariff_alta_print_format,
)


def execute():
	install_tariff_alta_print_format()
