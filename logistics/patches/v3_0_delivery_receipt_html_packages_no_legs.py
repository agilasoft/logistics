"""Delivery Receipt HTML: remove Legs; packages show commodity description, no HS."""

from logistics.transport.print_format.delivery_receipt.install_print_format import (
	install_delivery_receipt_print_format,
)


def execute():
	install_delivery_receipt_print_format()
