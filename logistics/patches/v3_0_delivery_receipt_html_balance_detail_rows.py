"""Delivery Receipt HTML: 6 detail rows left, 5 right (REFERENCE on right)."""

from logistics.transport.print_format.delivery_receipt.install_print_format import (
	install_delivery_receipt_print_format,
)


def execute():
	install_delivery_receipt_print_format()
