"""Set Housebill Number digits to 16pt on Cargo Label HTML."""

from logistics.air_freight.print_format.cargo_label_html.install_print_format import (
	install_cargo_label_html_print_format,
)


def execute():
	install_cargo_label_html_print_format()
