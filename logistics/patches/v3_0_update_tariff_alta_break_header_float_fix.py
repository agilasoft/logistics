"""Reinstall Tariff ALTA so break_header skips db.exists for float unit-break keys."""

from logistics.pricing_center.print_format.tariff_alta.install_print_format import (
	install_tariff_alta_print_format,
)


def execute():
	install_tariff_alta_print_format()
