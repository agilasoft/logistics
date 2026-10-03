"""Match the Return Shipping Instruction local-delivery fields."""

from logistics.mice.print_format.return_shipping_instruction_html.install_print_format import (
	install_return_shipping_instruction_html_print_format,
)


def execute():
	install_return_shipping_instruction_html_print_format()
