"""Reinstall Payment Voucher HTML with Supplier Invoice No in column 3."""

from logistics.print_format.payment_entry.install_payment_voucher_print_format import (
	install_payment_voucher_print_format,
)


def execute():
	install_payment_voucher_print_format()
