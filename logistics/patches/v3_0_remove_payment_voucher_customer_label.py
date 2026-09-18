"""Reinstall Payment Voucher HTML without the CUSTOMER heading."""

from logistics.print_format.payment_entry.install_payment_voucher_print_format import (
	install_payment_voucher_print_format,
)


def execute():
	install_payment_voucher_print_format()
