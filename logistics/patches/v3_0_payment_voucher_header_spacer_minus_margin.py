"""Reinstall Payment Voucher HTML with header spacer 3.5in minus page top margin."""

from logistics.print_format.payment_entry.install_payment_voucher_print_format import (
	install_payment_voucher_print_format,
)


def execute():
	install_payment_voucher_print_format()
